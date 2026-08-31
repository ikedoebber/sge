from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Sum, Q, Count
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView
from . import models, forms


class SaleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.Sale
    template_name = 'sale_list.html'
    context_object_name = 'sales'
    paginate_by = 10
    permission_required = 'sales.view_sale'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('client')
        client = self.request.GET.get('client')
        status = self.request.GET.get('status')

        if client:
            queryset = queryset.filter(client__name__icontains=client)
        if status == 'paid':
            queryset = queryset.filter(balance_due__lte=0)
        elif status == 'pending':
            queryset = queryset.filter(balance_due__gt=0)
        elif status == 'overdue':
            from django.utils import timezone
            today = timezone.now().date()
            queryset = queryset.filter(
                installments__status='overdue',
                installments__due_date__lt=today
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context['total_vendas'] = qs.count()
        context['total_valor'] = qs.aggregate(total=Sum('total_value'))['total'] or 0
        context['total_recebido'] = qs.aggregate(total=Sum('amount_paid'))['total'] or 0
        context['total_pendente'] = qs.aggregate(total=Sum('balance_due'))['total'] or 0
        return context


class SaleCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = models.Sale
    template_name = 'sale_create.html'
    form_class = forms.SaleForm
    success_url = reverse_lazy('sale_list')
    permission_required = 'sales.add_sale'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Venda #{self.object.id} criada com sucesso! Parcelas geradas automaticamente.')
        return response

    def get_initial(self):
        initial = super().get_initial()
        client_id = self.request.GET.get('client')
        if client_id:
            initial['client'] = client_id
        return initial


class SaleDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Sale
    template_name = 'sale_detail.html'
    permission_required = 'sales.view_sale'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sale = self.object
        context['installments'] = sale.installments.all()
        context['pay_form'] = forms.InstallmentPayForm()
        return context


class InstallmentPayView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Installment
    permission_required = 'sales.change_sale'

    def post(self, request, *args, **kwargs):
        installment = self.get_object()
        form = forms.InstallmentPayForm(request.POST)
        
        if form.is_valid():
            amount = form.cleaned_data['amount']
            payment_date = form.cleaned_data['payment_date']
            
            installment.amount_paid += amount
            installment.payment_date = payment_date
            installment.save()
            
            # Atualizar valor pago da venda
            installment.sale.update_amount_paid()
            
            messages.success(
                request,
                f'Pagamento de R$ {amount:.2f} registrado na parcela {installment.installment_number}.'
            )
        
        return redirect('sale_detail', pk=installment.sale.pk)
