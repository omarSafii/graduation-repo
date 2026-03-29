from django.db import migrations, models


def create_general_admin(apps, schema_editor):
    AdminUser = apps.get_model('application', 'AdminUser')
    AdminUser.objects.update_or_create(
        email='admin@graduation.local',
        defaults={
            'fullname': 'General Admin',
            'password': 'Admin@12345',
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0007_projects_rejection_reason_resubmitted_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='supervisor',
            name='university_id_card',
            field=models.FileField(blank=True, null=True, upload_to='supervisor_ids/'),
        ),
        migrations.RunPython(create_general_admin, migrations.RunPython.noop),
    ]
