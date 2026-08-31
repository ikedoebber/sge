from django import forms
from . import models
from clients.models import Client


class SaleForm(forms.ModelForm):

    class Meta:
        model = models.Sale
        fields = ['client', 'sale_date', 'description', 'total_value', 'down_payment', 'num_installments', 'payment_method']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control'}),
            'sale_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'total_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'down_payment': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'num_installments': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'client': 'Cliente',
            'sale_date': 'Data da Venda',
            'description': 'Descricao da Compra',
            'total_value': 'Valor Total da Venda',
            'down_payment': 'Valor de Entrada',
            'num_installments': 'Quantidade de Parcelas',
            'payment_method': 'Forma de Pagamento',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].required = True
        self.fields['sale_date'].required = True
        self.fields['total_value'].required = True
        self.fields['description'].required = False
        self.fields['down_payment'].required = False
        self.fields['num_installments'].required = False
        self.fields['payment_method'].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Calcular saldo devedor
        down = self.cleaned_data.get('down_payment', 0) or 0
        total = self.cleaned_data.get('total_value', 0)
        instance.balance_due = total - down
        instance.amount_paid = down
        if commit:
            instance.save()
            # Gerar parcelas automaticamente
            num = self.cleaned_data.get('num_installments', 1) or 1
            if num > 0:
                valor_parcela = (total - down) / num
                from django.utils import timezone
                sale_date = instance.sale_date
                for i in range(1, num + 1):
                    # Calcular data de vencimento (30 dias * parcela)
                    from datetime import timedelta
                    due = sale_date + timedelta(days=30 * i)
                    models.Installment.objects.create(
                        sale=instance,
                        installment_number=i,
                        value=valor_parcela,
                        due_date=due,
                    )
        return instance


class InstallmentPayForm(forms.Form):
    """Formulario para registrar pagamento de uma parcela."""
    amount = forms.DecimalField(
        label='Valor a Pagar',
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    payment_date = forms.DateField(
        label='Data do Pagamento',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
