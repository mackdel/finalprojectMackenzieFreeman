# Generated by Django 5.1.2 on 2024-11-21 23:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('handbook', '0008_alter_procedurestep_options_procedurestep_order'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='procedurestep',
            unique_together=set(),
        ),
    ]