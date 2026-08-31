from django import forms
from . import models


class ClientForm(forms.ModelForm):

    class Meta:
        model = models.Client
        fields = ['name', 'person_type', 'cpf_cnpj', 'email', 'phone', 'address', 'city', 'state', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'person_type': forms.Select(attrs={'class': 'form-control'}),
            'cpf_cnpj': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'name': 'Nome',
            'person_type': 'Tipo de Pessoa',
            'cpf_cnpj': 'CPF/CNPJ',
            'email': 'E-mail',
            'phone': 'Telefone',
            'address': 'Endereco',
            'city': 'Cidade',
            'state': 'Estado',
            'notes': 'Observacoes',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Somente nome e telefone obrigatorios
        self.fields['name'].required = True
        self.fields['phone'].required = True
        self.fields['person_type'].required = False
        self.fields['cpf_cnpj'].required = False
        self.fields['email'].required = False
        self.fields['address'].required = False
        self.fields['city'].required = False
        self.fields['state'].required = False
        self.fields['notes'].required = False
