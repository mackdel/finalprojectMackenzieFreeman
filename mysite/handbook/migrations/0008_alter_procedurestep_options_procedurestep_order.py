# Generated by Django 5.1.2 on 2024-11-21 23:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('handbook', '0007_alter_policy_review_period_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='procedurestep',
            options={'ordering': ['order']},
        ),
        migrations.AddField(
            model_name='procedurestep',
            name='order',
            field=models.PositiveIntegerField(blank=True, db_index=True, default=0),
        ),
    ]
