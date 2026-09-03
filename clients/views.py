from rest_framework import generics
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Sum, Q
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
        
        from outflows.models import Outflow, Installment
        
        outflows = Outflow.objects.filter(client=client)
        
        context['sales'] = outflows
        context['total_vendido'] = outflows.aggregate(total=Sum('total_value'))['total'] or 0
        context['total_recebido'] = outflows.aggregate(total=Sum('amount_paid'))['total'] or 0
        context['total_receber'] = outflows.aggregate(total=Sum('balance_due'))['total'] or 0
        
        total_vencido = Installment.objects.filter(
            outflow__client=client,
            status='overdue'
        ).aggregate(total=Sum('value'))['total'] or 0
        context['total_vencido'] = total_vencido
        
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
