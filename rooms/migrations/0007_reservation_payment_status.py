from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0006_reservation_is_checked_out'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='payment_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('paid', 'Paid'),
                    ('failed', 'Failed'),
                    ('refunded', 'Refunded'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
