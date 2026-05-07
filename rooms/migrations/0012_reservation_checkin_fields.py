from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0011_reservation_deposit_and_damage_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='is_checked_in',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='reservation',
            name='checked_in_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='checked_in_adults',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='reservation',
            name='checked_in_children',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
