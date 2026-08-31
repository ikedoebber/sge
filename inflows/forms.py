from django import forms
from . import models


class InflowForm(forms.ModelForm):
    unit_cost = forms.DecimalField(
        label='Custo Unitario (R$)',
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Deixe vazio para manter o custo atual',
        })
    )
    selling_price = forms.DecimalField(
        label='Preco de Venda (R$)',
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Deixe vazio para manter o preco atual',
        })
    )

    class Meta:
        model = models.Inflow
        fields = ['supplier', 'product', 'quantity', 'unit_cost', 'selling_price', 'description']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'supplier': 'Fornecedor',
            'product': 'Produto',
            'quantity': 'Quantidade',
            'description': 'Descricao',
        }


class InflowXMLUploadForm(forms.Form):
    xml_file = forms.FileField(
        label='Arquivo XML da NFe',
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-300 file:mr-4 file:py-3 file:px-6 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-violet-600 file:text-white hover:file:bg-violet-700 file:cursor-pointer file:transition-all duration-200',
            'accept': '.xml',
        })
    )


class InflowXMLConfirmForm(forms.Form):
    supplier = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=False,
    )
    
    items_json = forms.CharField(
        widget=forms.HiddenInput(),
    )
