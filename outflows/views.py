from rest_framework import generics
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, FormView
from django.db.models import Q
from django.shortcuts import redirect
from django.utils import timezone
from app import metrics
from products.models import Product
from . import models, forms, serializers


class OutflowListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = models.Outflow
    template_name = 'outflow_list.html'
    context_object_name = 'outflows'
    paginate_by = 10
    permission_required = 'outflows.view_outflow'

    def get_queryset(self):
        queryset = super().get_queryset()
        product = self.request.GET.get('product')
        client = self.request.GET.get('client')
        if product:
            queryset = queryset.filter(items__product__title__icontains=product)
        if client:
            queryset = queryset.filter(client__name__icontains=client)
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product_metrics'] = metrics.get_product_metrics()
        context['sales_metrics'] = metrics.get_sales_metrics()
        context['payment_method_metrics'] = metrics.get_payment_method_metrics()
        context['supplier_metrics'] = metrics.get_supplier_metrics()
        return context


class OutflowCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = models.Outflow
    template_name = 'outflow_create.html'
    form_class = forms.OutflowForm
    success_url = reverse_lazy('outflow_list')
    permission_required = 'outflows.add_outflow'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = forms.OutflowItemFormSet(
                self.request.POST, prefix='items'
            )
        else:
            context['item_formset'] = forms.OutflowItemFormSet(prefix='items')
            context['initial_product_id'] = self.request.GET.get('product', '')
        
        products = Product.objects.select_related('category').filter(quantity__gt=0)
        context['products_json'] = [
            {'id': p.pk, 'title': p.title, 'price': float(p.selling_price)}
            for p in products
        ]
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']

        if item_formset.is_valid():
            product_quantities = {}
            for form_item in item_formset.forms:
                delete_field = form_item.prefix + '-DELETE'
                is_deleted = form_item.data.get(delete_field) == 'on'
                if is_deleted:
                    continue
                product = form_item.cleaned_data.get('product')
                if not product:
                    continue
                qty = form_item.cleaned_data.get('quantity', 0) or 0
                if qty <= 0:
                    continue
                pid = product.pk
                product_quantities[pid] = product_quantities.get(pid, 0) + qty

            stock_errors = []
            for pid, total_qty in product_quantities.items():
                product = Product.objects.get(id=pid)
                if product.quantity < total_qty:
                    stock_errors.append(
                        f'{product.title}: solicitado {total_qty} un., disponivel {product.quantity} un.'
                    )

            if stock_errors:
                messages.error(self.request, 'Estoque insuficiente: ' + '; '.join(stock_errors))
                return self.render_to_response(context)

            self.object = form.save(commit=False)
            self.object.sale_date = timezone.now().date()
            self.object.save()

            items = item_formset.save(commit=False)
            total = 0
            for item in items:
                if not item.unit_price:
                    item.unit_price = item.product.selling_price
                item.outflow = self.object
                item.save()
                total += item.subtotal

                product = item.product
                product.quantity -= item.quantity
                product.save()

            for item in item_formset.deleted_objects:
                product = item.product
                product.quantity += item.quantity
                product.save()
                item.delete()

            self.object.total_value = total
            self.object.balance_due = total - self.object.down_payment
            self.object.save()

            self._generate_installments(self.object)

            return super().form_valid(form)
        return self.render_to_response(context)

    def _generate_installments(self, outflow):
        valor_restante = outflow.total_value - outflow.down_payment
        if valor_restante <= 0:
            return
        num = max(outflow.num_installments, 1)
        valor_parcela = valor_restante / num
        base_date = outflow.sale_date or timezone.now().date()
        from datetime import timedelta
        for i in range(1, num + 1):
            vencimento = base_date + timedelta(days=30 * i)
            models.Installment.objects.create(
                outflow=outflow,
                installment_number=i,
                value=valor_parcela,
                due_date=vencimento,
            )


class OutflowUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = models.Outflow
    template_name = 'outflow_update.html'
    form_class = forms.OutflowForm
    success_url = reverse_lazy('outflow_list')
    permission_required = 'outflows.change_outflow'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = forms.OutflowItemFormSet(
                self.request.POST, prefix='items', instance=self.object
            )
        else:
            context['item_formset'] = forms.OutflowItemFormSet(
                prefix='items', instance=self.object
            )

        existing_product_ids = set(
            self.object.items.values_list('product_id', flat=True)
        )
        all_products = Product.objects.select_related('category').filter(
            Q(quantity__gt=0) | Q(id__in=existing_product_ids)
        )
        context['products_json'] = [
            {'id': p.pk, 'title': p.title, 'price': float(p.selling_price)}
            for p in all_products
        ]
        context['existing_items_json'] = [
            {
                'id': item.product_id,
                'product_id': item.product_id,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price) if item.unit_price else float(item.product.selling_price),
                'item_id': item.pk,
            }
            for item in self.object.items.select_related('product').all()
        ]
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']

        if item_formset.is_valid():
            old_items = {}
            for item in self.object.items.all():
                old_items[item.pk] = {'product_id': item.product_id, 'quantity': item.quantity}

            stock_adjustments = {}
            stock_errors = []

            for form_item in item_formset.forms:
                delete_field = form_item.prefix + '-DELETE'
                is_deleted = form_item.data.get(delete_field) == 'on'

                product = form_item.cleaned_data.get('product')
                if not product:
                    continue
                pid = product.pk
                new_qty = form_item.cleaned_data.get('quantity', 0) or 0

                item_pk = form_item.instance.pk

                if is_deleted and item_pk and item_pk in old_items:
                    old_qty = old_items[item_pk]['quantity']
                    stock_adjustments[pid] = stock_adjustments.get(pid, 0) + old_qty
                elif item_pk and item_pk in old_items:
                    old_qty = old_items[item_pk]['quantity']
                    adjustment = old_qty - new_qty
                    stock_adjustments[pid] = stock_adjustments.get(pid, 0) + adjustment
                elif not item_pk:
                    stock_adjustments[pid] = stock_adjustments.get(pid, 0) - new_qty

            for pid, adjustment in stock_adjustments.items():
                if adjustment < 0:
                    product = Product.objects.get(id=pid)
                    needed = abs(adjustment)
                    stock_errors.append(
                        f'{product.title}: solicitado {needed} un., disponivel {product.quantity} un.'
                    )

            if stock_errors:
                messages.error(self.request, 'Estoque insuficiente: ' + '; '.join(stock_errors))
                return self.render_to_response(context)

            for pid, adjustment in stock_adjustments.items():
                if adjustment != 0:
                    product = Product.objects.get(id=pid)
                    product.quantity += adjustment
                    product.save()

            items = item_formset.save(commit=False)
            total = 0
            for item in items:
                if not item.unit_price:
                    item.unit_price = item.product.selling_price
                item.outflow = self.object
                item.save()
                total += item.subtotal

            for item in item_formset.deleted_objects:
                item.delete()

            self.object.total_value = total
            self.object.balance_due = total - self.object.down_payment
            self.object.save()

            return super().form_valid(form)
        return self.render_to_response(context)


class OutflowDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Outflow
    template_name = 'outflow_detail.html'
    permission_required = 'outflows.view_outflow'


class OutflowCancelView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Outflow
    permission_required = 'outflows.change_outflow'

    def post(self, request, *args, **kwargs):
        outflow = self.get_object()
        if outflow.status == 'cancelled':
            messages.warning(request, 'Esta venda ja foi cancelada.')
            return redirect('outflow_detail', pk=outflow.pk)

        for item in outflow.items.all():
            product = item.product
            product.quantity += item.quantity
            product.save()

        outflow.status = 'cancelled'
        outflow.balance_due = 0
        outflow.amount_paid = outflow.total_value
        outflow.save()

        messages.success(request, f'Venda #{outflow.id} cancelada com sucesso. Estoque devolvido.')
        return redirect('outflow_detail', pk=outflow.pk)


class OutflowInstallmentsCreateView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = models.Outflow
    permission_required = 'outflows.change_outflow'

    def get(self, request, *args, **kwargs):
        outflow = self.get_object()
        if outflow.installments.exists():
            messages.warning(request, 'Parcelas ja existem para esta venda.')
        elif outflow.balance_due <= 0:
            messages.warning(request, 'Nao ha saldo pendente para gerar parcelas.')
        else:
            num = max(outflow.num_installments, 1)
            valor_restante = outflow.balance_due
            valor_parcela = valor_restante / num
            base_date = outflow.sale_date or timezone.now().date()
            from datetime import timedelta
            for i in range(1, num + 1):
                vencimento = base_date + timedelta(days=30 * i)
                models.Installment.objects.create(
                    outflow=outflow,
                    installment_number=i,
                    value=valor_parcela,
                    due_date=vencimento,
                )
            messages.success(request, f'{num} parcela(s) gerada(s) com sucesso!')
        return redirect('outflow_detail', pk=outflow.pk)


class OutflowCreateListAPIView(generics.ListCreateAPIView):
    queryset = models.Outflow.objects.all()
    serializer_class = serializers.OutflowSerializer


class OutflowRetrieveAPIView(generics.RetrieveAPIView):
    queryset = models.Outflow.objects.all()
    serializer_class = serializers.OutflowSerializer


class InstallmentPayView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = forms.InstallmentPayForm
    template_name = 'installment_pay.html'
    permission_required = 'outflows.change_outflow'

    def dispatch(self, request, *args, **kwargs):
        self.installment = models.Installment.objects.get(pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['installment'] = self.installment
        context['outflow'] = self.installment.outflow
        return context

    def get_initial(self):
        return {
            'amount': self.installment.value - self.installment.amount_paid,
            'amount_max': self.installment.value - self.installment.amount_paid,
            'payment_date': timezone.now().date(),
        }

    def form_valid(self, form):
        amount = form.cleaned_data['amount']
        payment_date = form.cleaned_data['payment_date']
        payment_method = form.cleaned_data['payment_method']
        remaining = self.installment.value - self.installment.amount_paid

        if amount > remaining:
            form.add_error('amount', f'Valor maximo e R$ {remaining:.2f}')
            return self.form_invalid(form)

        self.installment.amount_paid += amount
        if payment_date:
            self.installment.payment_date = payment_date
        self.installment.save()

        # Atualizar forma de pagamento na venda
        self.installment.outflow.payment_method = payment_method
        self.installment.outflow.save(update_fields=['payment_method'])

        self.installment.outflow.update_amount_paid()

        messages.success(self.request, f'Pagamento de R$ {amount:.2f} registrado com sucesso!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('outflow_detail', kwargs={'pk': self.installment.outflow.pk})
