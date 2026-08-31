from django.db import models
from clients.models import Client


class Sale(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('money', 'Dinheiro'),
        ('credit', 'Cartao de Credito'),
        ('debit', 'Cartao de Debito'),
        ('pix', 'PIX'),
        ('boleto', 'Boleto'),
        ('other', 'Outros'),
    ]

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='sales')
    sale_date = models.DateField('Data da Venda')
    description = models.TextField('Descricao da Compra', blank=True, null=True)
    total_value = models.DecimalField('Valor Total da Venda', max_digits=12, decimal_places=2)
    down_payment = models.DecimalField('Valor de Entrada', max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField('Valor Pago', max_digits=12, decimal_places=2, default=0)
    balance_due = models.DecimalField('Saldo Devedor', max_digits=12, decimal_places=2, default=0)
    num_installments = models.IntegerField('Quantidade de Parcelas', default=1)
    payment_method = models.CharField('Forma de Pagamento', max_length=10, choices=PAYMENT_METHOD_CHOICES, default='money')
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        ordering = ['-sale_date', '-created_at']
        verbose_name = 'Venda'
        verbose_name_plural = 'Vendas'

    def __str__(self):
        return f'Venda #{self.id} - {self.client.name}'

    def save(self, *args, **kwargs):
        # Calcular saldo devedor automaticamente
        self.balance_due = self.total_value - self.down_payment - self.amount_paid
        super().save(*args, **kwargs)

    def update_amount_paid(self):
        """Recalcula valor pago total e saldo a partir das parcelas."""
        total_parcelas_pago = sum(p.amount_paid for p in self.installments.all())
        self.amount_paid = self.down_payment + total_parcelas_pago
        self.balance_due = self.total_value - self.amount_paid
        self.save(update_fields=['amount_paid', 'balance_due'])

    def get_status_display_summary(self):
        """Retorna resumo do status das parcelas."""
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


class Installment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('partial', 'Parcial'),
        ('paid', 'Pago'),
        ('overdue', 'Atrasado'),
    ]

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='installments')
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
        return f'Parcela {self.installment_number}/{self.sale.num_installments} - {self.sale.client.name}'

    def save(self, *args, **kwargs):
        # Atualizar status automaticamente
        from django.utils import timezone
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
