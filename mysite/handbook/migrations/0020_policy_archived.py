# Generated by Django 5.1.2 on 2024-12-04 02:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('handbook', '0019_policyapprovalrequest_number_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='policy',
            name='archived',
            field=models.BooleanField(default=False),
        ),
    ]