# Generated by Django 5.1.2 on 2024-11-20 23:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('handbook', '0005_alter_procedurestep_unique_together'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='policy',
            name='procedures',
        ),
    ]
