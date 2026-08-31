from django.contrib import admin
from . import models


class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'person_type', 'cpf_cnpj', 'phone', 'city', 'state')
    search_fields = ('name', 'cpf_cnpj', 'city')
    list_filter = ('person_type', 'state')


admin.site.register(models.Supplier, SupplierAdmin)
