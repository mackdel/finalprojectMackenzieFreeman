# Generated by Django 5.1.2 on 2024-11-22 00:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('handbook', '0010_alter_procedurestep_options_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='procedurestep',
            unique_together=set(),
        ),
    ]