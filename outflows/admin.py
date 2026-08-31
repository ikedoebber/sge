from django.contrib import admin
from . import models


class OutflowItemInline(admin.TabularInline):
    model = models.OutflowItem
    extra = 0


class InstallmentInline(admin.TabularInline):
    model = models.Installment
    extra = 0
    readonly_fields = ('status',)


class OutflowAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'total_value', 'balance_due', 'created_at')
    search_fields = ('client__name', 'items__product__title')
    list_filter = ('payment_method', 'created_at')
    inlines = [OutflowItemInline, InstallmentInline]


class OutflowItemAdmin(admin.ModelAdmin):
    list_display = ('outflow', 'product', 'quantity', 'unit_price')
    search_fields = ('product__title',)


class InstallmentAdmin(admin.ModelAdmin):
    list_display = ('outflow', 'installment_number', 'value', 'due_date', 'amount_paid', 'status')
    list_filter = ('status',)
    search_fields = ('outflow__client__name',)


admin.site.register(models.Outflow, OutflowAdmin)
admin.site.register(models.OutflowItem, OutflowItemAdmin)
admin.site.register(models.Installment, InstallmentAdmin)
