from django.core.management.base import BaseCommand
from django.utils import timezone
from products.models import Product


class Command(BaseCommand):
    help = 'Zera o estoque de produtos consignados com data de retorno vencida'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra o que seria alterado sem modificar nada',
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        dry_run = options['dry_run']

        products = Product.objects.filter(
            stock_type='consignado',
            consignment_return_date__lte=today,
            consignment_return_date__isnull=False,
            quantity__gt=0,
        )

        if not products.exists():
            self.stdout.write(
                self.style.SUCCESS('Nenhum produto consignado com data de retorno vencida encontrado.')
            )
            return

        total_zeroed = 0
        for product in products:
            old_qty = product.quantity
            if dry_run:
                self.stdout.write(
                    f'  [DRY RUN] {product.title} (ID: {product.id}): '
                    f'{old_qty} -> 0 '
                    f'(retorno: {product.consignment_return_date})'
                )
            else:
                product.quantity = 0
                product.save(update_fields=['quantity'])
                self.stdout.write(
                    f'  {product.title} (ID: {product.id}): '
                    f'{old_qty} -> 0 '
                    f'(retorno: {product.consignment_return_date})'
                )
            total_zeroed += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n[DRY RUN] {total_zeroed} produto(s) seriam zerados. '
                    f'Reexecute sem --dry-run para aplicar.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n{total_zeroed} produto(s) consignado(s) zerado(s) com sucesso!'
                )
            )
