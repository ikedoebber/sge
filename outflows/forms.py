from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from . import models


class OutflowItemForm(forms.ModelForm):
    class Meta:
        model = models.OutflowItem
        fields = ['product', 'quantity', 'unit_price']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'block w-full px-3 py-2 bg-gray-800/50 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent product-select',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'block w-full px-3 py-2 bg-gray-800/50 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent item-quantity',
                'min': '1',
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'block w-full px-3 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-white text-sm cursor-not-allowed item-price',
                'step': '0.01',
                'readonly': 'readonly',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unit_price'].required = False


OutflowItemFormSet = forms.inlineformset_factory(
    models.Outflow,
    models.OutflowItem,
    form=OutflowItemForm,
    extra=1,
    can_delete=True,
)


class OutflowForm(forms.ModelForm):
    class Meta:
        model = models.Outflow
        fields = ['client', 'description', 'total_value', 'down_payment', 'num_installments', 'payment_method']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'total_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_total_value'}),
            'down_payment': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'num_installments': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].required = False
        self.fields['client'].empty_label = 'Selecione o cliente (opcional)'
        self.fields['total_value'].required = False
        self.fields['total_value'].initial = 0
        self.fields['down_payment'].initial = 0
        self.fields['description'].required = False


class InstallmentPayForm(forms.Form):
    PAYMENT_METHOD_CHOICES = [
        ('', 'Selecione...'),
        ('money', 'Dinheiro'),
        ('credit', 'Cartao de Credito'),
        ('debit', 'Cartao de Debito'),
        ('pix', 'PIX'),
        ('boleto', 'Boleto'),
        ('other', 'Em Aberto'),
    ]

    amount = forms.DecimalField(
        label='Valor a Pagar',
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'block w-full px-4 py-3 bg-gray-800/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all duration-200',
            'step': '0.01',
            'placeholder': '0.00',
        })
    )
    payment_date = forms.DateField(
        label='Data do Pagamento',
        widget=forms.DateInput(attrs={
            'class': 'block w-full px-4 py-3 bg-gray-800/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all duration-200',
            'type': 'date',
        })
    )
    payment_method = forms.ChoiceField(
        label='Forma de Pagamento',
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'block w-full px-4 py-3 bg-gray-800/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all duration-200',
        })
    )
