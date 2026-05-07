from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0012_reservation_checkin_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='invoice_notified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
