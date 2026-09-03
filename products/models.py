from django.db import models
from categories.models import Category
from brands.models import Brand
from suppliers.models import Supplier


class Product(models.Model):
    STOCK_TYPE_CHOICES = [
        ('proprio', 'Proprio'),
        ('consignado', 'Consignado'),
    ]

    title = models.CharField(max_length=500)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    description = models.TextField(null=True, blank=True)
    serie_number = models.CharField(max_length=200, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=20, decimal_places=2)
    selling_price = models.DecimalField(max_digits=20, decimal_places=2)
    quantity = models.IntegerField(default=0)
    stock_type = models.CharField(max_length=10, choices=STOCK_TYPE_CHOICES, default='proprio')
    consignment_supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consignment_products', verbose_name='Fornecedor Consignado'
    )
    consignment_return_date = models.DateField(
        null=True, blank=True, verbose_name='Data de Retorno da Consignacao'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    @property
    def profit_per_unit(self):
        """Lucro por unidade."""
        if self.cost_price and self.selling_price:
            return self.selling_price - self.cost_price
        return 0

    @property
    def profit_margin_percent(self):
        """Margem de lucro em percentual."""
        if self.cost_price and self.selling_price and self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return 0

    @property
    def total_profit_in_stock(self):
        """Lucro total considerando todo o estoque."""
        return self.profit_per_unit * self.quantity
