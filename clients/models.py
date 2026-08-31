from django.db import models


class Client(models.Model):
    PERSON_TYPE_CHOICES = [
        ('pf', 'Pessoa Fisica'),
        ('pj', 'Juridica'),
    ]

    name = models.CharField('Nome', max_length=500)
    person_type = models.CharField('Tipo de Pessoa', max_length=2, choices=PERSON_TYPE_CHOICES, default='pf')
    cpf_cnpj = models.CharField('CPF/CNPJ', max_length=18, unique=True, blank=True, null=True)
    email = models.EmailField('E-mail', max_length=254, blank=True, null=True)
    phone = models.CharField('Telefone', max_length=20, default='-')
    address = models.CharField('Endereco', max_length=500, blank=True, null=True)
    city = models.CharField('Cidade', max_length=200, blank=True, null=True)
    state = models.CharField('Estado', max_length=2, blank=True, null=True)
    notes = models.TextField('Observacoes', blank=True, null=True)
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return self.name
