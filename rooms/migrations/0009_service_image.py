from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0008_service_reservation_services_and_totals'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='uploads/services/'),
        ),
    ]