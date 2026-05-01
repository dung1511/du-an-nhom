from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0009_service_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='checkout_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]