from django.db import migrations


def fix_amount_paid(apps, schema_editor):
    Outflow = apps.get_model('outflows', 'Outflow')
    for outflow in Outflow.objects.filter(status='active'):
        parcelas_pagas = sum(
            p.amount_paid for p in outflow.installments.all()
        )
        correct_amount = outflow.down_payment + parcelas_pagas
        if outflow.amount_paid != correct_amount:
            outflow.amount_paid = correct_amount
            outflow.balance_due = max(0, outflow.total_value - correct_amount)
            outflow.save(update_fields=['amount_paid', 'balance_due'])


class Migration(migrations.Migration):

    dependencies = [
        ('outflows', '0004_add_status_field'),
    ]

    operations = [
        migrations.RunPython(fix_amount_paid, migrations.RunPython.noop),
    ]
