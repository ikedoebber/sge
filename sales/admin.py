from django.contrib import admin
from . import models


class InstallmentInline(admin.TabularInline):
    model = models.Installment
    extra = 0
    readonly_fields = ('status',)


@admin.register(models.Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'sale_date', 'total_value', 'amount_paid', 'balance_due', 'num_installments', 'payment_method')
    list_filter = ('payment_method', 'sale_date')
    search_fields = ('client__name', 'description')
    inlines = [InstallmentInline]


@admin.register(models.Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = ('sale', 'installment_number', 'value', 'due_date', 'amount_paid', 'payment_date', 'status')
    list_filter = ('status', 'due_date')
    search_fields = ('sale__client__name',)
