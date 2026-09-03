from django.db.models import Sum, F
from django.utils.formats import number_format
from django.utils import timezone
from brands.models import Brand
from categories.models import Category
from products.models import Product
from suppliers.models import Supplier
from outflows.models import Outflow, OutflowItem
from inflows.models import Inflow


def get_product_metrics():
    products = Product.objects.all()
    total_cost_price = sum(product.cost_price * product.quantity for product in products)
    total_selling_price = sum(product.selling_price * product.quantity for product in products)
    total_quantity = sum(product.quantity for product in products)
    total_profit = total_selling_price - total_cost_price

    return dict(
        total_cost_price=number_format(total_cost_price, decimal_pos=2, force_grouping=True),
        total_selling_price=number_format(total_selling_price, decimal_pos=2, force_grouping=True),
        total_quantity=total_quantity,
        total_profit=number_format(total_profit, decimal_pos=2, force_grouping=True),
    )


def get_stock_metrics_by_type():
    """Retorna metricas de estoque separadas por tipo (proprio/consignado)."""
    proprio = Product.objects.filter(stock_type='proprio')
    consignado = Product.objects.filter(stock_type='consignado')

    def _calc_metrics(queryset):
        products = list(queryset)
        cost = sum(p.cost_price * p.quantity for p in products)
        selling = sum(p.selling_price * p.quantity for p in products)
        qty = sum(p.quantity for p in products)
        profit = selling - cost
        return {
            'total_cost_price': cost,
            'total_cost_price_fmt': number_format(cost, decimal_pos=2, force_grouping=True),
            'total_selling_price': selling,
            'total_selling_price_fmt': number_format(selling, decimal_pos=2, force_grouping=True),
            'total_quantity': qty,
            'total_profit': profit,
            'total_profit_fmt': number_format(profit, decimal_pos=2, force_grouping=True),
            'count': queryset.count(),
        }

    proprio_metrics = _calc_metrics(proprio)
    consignado_metrics = _calc_metrics(consignado)

    # Total consolidado
    all_products = list(Product.objects.all())
    total_cost = sum(p.cost_price * p.quantity for p in all_products)
    total_selling = sum(p.selling_price * p.quantity for p in all_products)
    total_qty = sum(p.quantity for p in all_products)

    return {
        'proprio': proprio_metrics,
        'consignado': consignado_metrics,
        'total': {
            'total_cost_price': total_cost,
            'total_cost_price_fmt': number_format(total_cost, decimal_pos=2, force_grouping=True),
            'total_selling_price': total_selling,
            'total_selling_price_fmt': number_format(total_selling, decimal_pos=2, force_grouping=True),
            'total_quantity': total_qty,
            'total_profit': total_selling - total_cost,
            'total_profit_fmt': number_format(total_selling - total_cost, decimal_pos=2, force_grouping=True),
        },
    }


def get_sales_metrics():
    active_outflows = Outflow.objects.filter(status='active')
    total_sales = active_outflows.count()
    total_products_sold = OutflowItem.objects.filter(outflow__status='active').aggregate(total=Sum('quantity'))['total'] or 0
    total_sales_value = OutflowItem.objects.filter(outflow__status='active').aggregate(
        total=Sum(F('unit_price') * F('quantity'))
    )['total'] or 0
    total_sales_cost = OutflowItem.objects.filter(outflow__status='active').aggregate(
        total=Sum(F('product__cost_price') * F('quantity'))
    )['total'] or 0
    total_sales_profit = total_sales_value - total_sales_cost

    return dict(
        total_sales=total_sales,
        total_products_sold=total_products_sold,
        total_sales_value=number_format(total_sales_value, decimal_pos=2, force_grouping=True),
        total_sales_profit=number_format(total_sales_profit, decimal_pos=2, force_grouping=True),
    )


def get_payment_method_metrics():
    choices = dict(Outflow.PAYMENT_METHOD_CHOICES)
    metrics = {}
    for key, label in choices.items():
        total = Outflow.objects.filter(payment_method=key, status='active').aggregate(
            total=Sum('total_value')
        )['total'] or 0
        count = Outflow.objects.filter(payment_method=key, status='active').count()
        metrics[key] = {
            'label': label,
            'total': number_format(total, decimal_pos=2, force_grouping=True),
            'count': count,
        }
    return metrics


def get_daily_sales_data():
    today = timezone.now().date()
    dates = [str(today - timezone.timedelta(days=i)) for i in range(6, -1, -1)]
    values = list()

    for date in dates:
        sales_total = OutflowItem.objects.filter(
            outflow__created_at__date=date,
            outflow__status='active'
        ).aggregate(
            total_sales=Sum(F('unit_price') * F('quantity'))
        )['total_sales'] or 0
        values.append(float(sales_total))

    return dict(
        dates=dates,
        values=values,
    )


def get_daily_sales_quantity_data():
    today = timezone.now().date()
    dates = [str(today - timezone.timedelta(days=i)) for i in range(6, -1, -1)]
    quantities = list()

    for date in dates:
        sales_quantity = Outflow.objects.filter(created_at__date=date, status='active').count()
        quantities.append(sales_quantity)

    return dict(
        dates=dates,
        values=quantities,
    )


def get_graphic_product_category_metric():
    categories = Category.objects.all()
    return {category.name: Product.objects.filter(category=category).count() for category in categories}


def get_graphic_product_brand_metric():
    brands = Brand.objects.all()
    return {brand.name: Product.objects.filter(brand=brand).count() for brand in brands}


def get_supplier_metrics():
    suppliers = Supplier.objects.all()
    result = []

    for supplier in suppliers:
        product_ids = Inflow.objects.filter(supplier=supplier).values_list('product_id', flat=True).distinct()
        products = Product.objects.filter(id__in=product_ids)

        stock_qty = sum(p.quantity for p in products)
        stock_cost = sum(p.cost_price * p.quantity for p in products)
        stock_selling = sum(p.selling_price * p.quantity for p in products)

        sales_data = OutflowItem.objects.filter(
            product_id__in=product_ids,
            outflow__status='active'
        ).aggregate(
            sales_value=Sum(F('unit_price') * F('quantity')),
            sales_cost=Sum(F('product__cost_price') * F('quantity')),
            qty_sold=Sum('quantity'),
        )
        sales_value = sales_data['sales_value'] or 0
        sales_cost = sales_data['sales_cost'] or 0
        qty_sold = sales_data['qty_sold'] or 0
        profit = sales_value - sales_cost

        result.append({
            'supplier': supplier,
            'stock_qty': stock_qty,
            'stock_cost_fmt': number_format(stock_cost, decimal_pos=2, force_grouping=True),
            'stock_selling_fmt': number_format(stock_selling, decimal_pos=2, force_grouping=True),
            'sales_value_fmt': number_format(sales_value, decimal_pos=2, force_grouping=True),
            'profit_fmt': number_format(profit, decimal_pos=2, force_grouping=True),
            'qty_sold': qty_sold,
        })

    return sorted(result, key=lambda x: x['sales_value_fmt'], reverse=True)
