from django.conf import settings
from django.db import migrations


def promote_existing_admin(apps, schema_editor):
    user_model = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    user_model.objects.filter(username='Kanagu@22').update(
        is_active=True,
        is_staff=True,
        is_superuser=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(promote_existing_admin, migrations.RunPython.noop),
    ]