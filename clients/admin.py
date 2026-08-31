from django.contrib import admin
from . import models


class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'person_type', 'cpf_cnpj', 'email', 'phone', 'city', 'state')
    search_fields = ('name', 'cpf_cnpj', 'email')
    list_filter = ('person_type', 'state')


admin.site.register(models.Client, ClientAdmin)
