from django import forms
from . import models


class ProductForm(forms.ModelForm):

    class Meta:
        model = models.Product
        fields = [
            'title', 'category', 'brand', 'description', 'serie_number',
            'cost_price', 'selling_price', 'quantity',
            'stock_type', 'consignment_supplier', 'consignment_return_date',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'serie_number': forms.TextInput(attrs={'class': 'form-control'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_type': forms.Select(attrs={'class': 'form-control'}),
            'consignment_supplier': forms.Select(attrs={'class': 'form-control'}),
            'consignment_return_date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d',
            ),
        }
        labels = {
            'title': 'Titulo',
            'category': 'Categoria',
            'brand': 'Marca',
            'description': 'Descricao',
            'serie_number': 'Numero de Serie',
            'cost_price': 'Preco de Custo',
            'selling_price': 'Preco de Venda',
            'quantity': 'Quantidade',
            'stock_type': 'Tipo de Estoque',
            'consignment_supplier': 'Fornecedor Consignado',
            'consignment_return_date': 'Data de Retorno',
        }
