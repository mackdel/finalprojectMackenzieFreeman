# Generated by Django 5.1.2 on 2024-12-05 02:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('handbook', '0027_alter_archivedpolicy_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='policy',
            name='updated_at',
            field=models.DateField(auto_now=True, verbose_name='Last Updated'),
        ),
    ]
