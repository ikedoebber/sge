from rest_framework import generics
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Sum, Q, Count, Avg, F
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from . import models, forms, serializers


class ClientListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.Client
    template_name = 'client_list.html'
    context_object_name = 'clients'
    paginate_by = 10
    permission_required = 'clients.view_client'

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.GET.get('name')

        if name:
            queryset = queryset.filter(name__icontains=name)

        return queryset


class ClientCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = models.Client
    template_name = 'client_create.html'
    form_class = forms.ClientForm
    success_url = reverse_lazy('client_list')
    permission_required = 'clients.add_client'

    def get_success_url(self):
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return f'{next_url}?client={self.object.id}'
        return reverse_lazy('client_list')


class ClientDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Client
    template_name = 'client_detail.html'
    permission_required = 'clients.view_client'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.object
        
        from outflows.models import Outflow, Installment, OutflowItem
        
        outflows = Outflow.objects.filter(client=client)
        active_outflows = outflows.filter(status='active')
        
        context['sales'] = active_outflows
        context['total_vendido'] = active_outflows.aggregate(total=Sum('total_value'))['total'] or 0
        context['total_recebido'] = active_outflows.aggregate(total=Sum('amount_paid'))['total'] or 0
        context['total_receber'] = active_outflows.aggregate(total=Sum('balance_due'))['total'] or 0
        
        total_vencido = Installment.objects.filter(
            outflow__client=client,
            outflow__status='active',
            status='overdue'
        ).aggregate(total=Sum('value'))['total'] or 0
        context['total_vencido'] = total_vencido

        # Metricas de consumo
        total_compras = active_outflows.count()
        context['total_compras'] = total_compras

        if total_compras > 0:
            context['ticket_medio'] = context['total_vendido'] / total_compras
        else:
            context['ticket_medio'] = 0

        total_itens = OutflowItem.objects.filter(
            outflow__client=client,
            outflow__status='active'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        context['total_itens'] = total_itens

        produto_mais_comprado = OutflowItem.objects.filter(
            outflow__client=client,
            outflow__status='active'
        ).values('product__title').annotate(
            total_qtd=Sum('quantity')
        ).order_by('-total_qtd').first()

        if produto_mais_comprado:
            context['produto_mais_comprado'] = produto_mais_comprado['product__title']
            context['produto_mais_comprado_qtd'] = produto_mais_comprado['total_qtd']
        else:
            context['produto_mais_comprado'] = '-'
            context['produto_mais_comprado_qtd'] = 0

        ultima_compra = active_outflows.order_by('-sale_date').first()
        if ultima_compra:
            context['ultima_compra_data'] = ultima_compra.sale_date
            context['ultima_compra_id'] = ultima_compra.id
        else:
            context['ultima_compra_data'] = None
            context['ultima_compra_id'] = None

        forma_pagamento = active_outflows.values('payment_method').annotate(
            total=Count('id')
        ).order_by('-total').first()

        if forma_pagamento:
            pagamento_display = dict(Outflow.PAYMENT_METHOD_CHOICES).get(
                forma_pagamento['payment_method'], forma_pagamento['payment_method']
            )
            context['forma_pagamento_preferida'] = pagamento_display
        else:
            context['forma_pagamento_preferida'] = '-'

        return context


class ClientUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = models.Client
    template_name = 'client_update.html'
    form_class = forms.ClientForm
    success_url = reverse_lazy('client_list')
    permission_required = 'clients.change_client'


class ClientDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = models.Client
    template_name = 'client_delete.html'
    success_url = reverse_lazy('client_list')
    permission_required = 'clients.delete_client'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                f'Nao e possivel excluir o cliente "{self.object.name}" '
                f'porque ele possui {self.object.outflows.count()} venda(s) registrada(s).'
            )
            return redirect('client_detail', pk=self.object.pk)


class ClientCreateListAPIView(generics.ListCreateAPIView):
    queryset = models.Client.objects.all()
    serializer_class = serializers.ClientSerializer


class ClientRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.Client.objects.all()
    serializer_class = serializers.ClientSerializer
