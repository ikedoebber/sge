from django.db import models
from django.utils import timezone
from products.models import Product
from clients.models import Client


class Outflow(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('money', 'Dinheiro'),
        ('credit', 'Cartao de Credito'),
        ('debit', 'Cartao de Debito'),
        ('pix', 'PIX'),
        ('boleto', 'Boleto'),
        ('other', 'Outros'),
    ]

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='outflows', null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    sale_date = models.DateField('Data da Venda', null=True, blank=True)
    total_value = models.DecimalField('Valor Total', max_digits=12, decimal_places=2, default=0)
    down_payment = models.DecimalField('Entrada', max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField('Valor Pago', max_digits=12, decimal_places=2, default=0)
    balance_due = models.DecimalField('Saldo Devedor', max_digits=12, decimal_places=2, default=0)
    num_installments = models.IntegerField('Parcelas', default=1)
    payment_method = models.CharField('Pagamento', max_length=10, choices=PAYMENT_METHOD_CHOICES, default='money')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Saida'
        verbose_name_plural = 'Saidas'

    def __str__(self):
        client_name = f' - {self.client.name}' if self.client else ''
        first_item = self.items.first()
        product_name = first_item.product.title if first_item else 'Sem itens'
        total_items = self.items.count()
        suffix = f' (+{total_items - 1})' if total_items > 1 else ''
        return f'Saida #{self.id} - {product_name}{suffix}{client_name}'

    def save(self, *args, **kwargs):
        self.balance_due = self.total_value - self.down_payment - self.amount_paid
        if not self.sale_date:
            self.sale_date = timezone.now().date()
        super().save(*args, **kwargs)

    def update_total(self):
        self.total_value = sum(item.subtotal for item in self.items.all())
        self.balance_due = self.total_value - self.down_payment - self.amount_paid
        self.save(update_fields=['total_value', 'balance_due'])

    def update_amount_paid(self):
        total_parcelas_pago = sum(p.amount_paid for p in self.installments.all())
        self.amount_paid = self.down_payment + total_parcelas_pago
        self.balance_due = self.total_value - self.amount_paid
        self.save(update_fields=['amount_paid', 'balance_due'])

    def get_status_display_summary(self):
        total = self.installments.count()
        if total == 0:
            return 'Sem parcelas'
        paid = self.installments.filter(status='paid').count()
        partial = self.installments.filter(status='partial').count()
        overdue = self.installments.filter(status='overdue').count()
        pending = self.installments.filter(status='pending').count()
        parts = []
        if paid:
            parts.append(f'{paid} paga(s)')
        if partial:
            parts.append(f'{partial} parcial')
        if pending:
            parts.append(f'{pending} pendente(s)')
        if overdue:
            parts.append(f'{overdue} atrasada(s)')
        return ', '.join(parts)


class OutflowItem(models.Model):
    outflow = models.ForeignKey(Outflow, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='outflow_items')
    quantity = models.IntegerField('Quantidade', default=1)
    unit_price = models.DecimalField('Preco Unitario', max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Item da Saida'
        verbose_name_plural = 'Itens da Saida'

    def __str__(self):
        return f'{self.product.title} x{self.quantity}'

    @property
    def subtotal(self):
        return self.quantity * self.unit_price


class Installment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('partial', 'Parcial'),
        ('paid', 'Pago'),
        ('overdue', 'Atrasado'),
    ]

    outflow = models.ForeignKey(Outflow, on_delete=models.CASCADE, related_name='installments')
    installment_number = models.IntegerField('Numero da Parcela')
    value = models.DecimalField('Valor da Parcela', max_digits=12, decimal_places=2)
    due_date = models.DateField('Data de Vencimento')
    amount_paid = models.DecimalField('Valor Pago', max_digits=12, decimal_places=2, default=0)
    payment_date = models.DateField('Data do Pagamento', blank=True, null=True)
    status = models.CharField('Situacao', max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        ordering = ['due_date', 'installment_number']
        verbose_name = 'Parcela'
        verbose_name_plural = 'Parcelas'

    def __str__(self):
        client_name = self.outflow.client.name if self.outflow.client else 'Sem cliente'
        return f'Parcela {self.installment_number}/{self.outflow.num_installments} - {client_name}'

    def save(self, *args, **kwargs):
        today = timezone.now().date()
        if self.amount_paid >= self.value:
            self.status = 'paid'
        elif self.amount_paid > 0:
            self.status = 'partial'
        elif self.due_date < today:
            self.status = 'overdue'
        else:
            self.status = 'pending'
        super().save(*args, **kwargs)
