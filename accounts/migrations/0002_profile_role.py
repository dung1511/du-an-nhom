from django.db import migrations, models


def set_default_role(apps, schema_editor):
    Profile = apps.get_model('accounts', 'Profile')
    Profile.objects.filter(role__isnull=True).update(role='customer')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='role',
            field=models.CharField(
                choices=[('customer', 'Khách hàng'), ('receptionist', 'Lễ tân'), ('admin', 'Quản trị viên')],
                default='customer',
                max_length=20,
            ),
        ),
        migrations.RunPython(set_default_role, migrations.RunPython.noop),
    ]