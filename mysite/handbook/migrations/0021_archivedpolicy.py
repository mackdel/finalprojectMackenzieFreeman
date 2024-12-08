# Generated by Django 5.1.2 on 2024-12-04 06:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_alter_customuser_role'),
        ('handbook', '0020_policy_archived'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArchivedPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(max_length=10)),
                ('title', models.CharField(max_length=200)),
                ('version', models.CharField(max_length=10)),
                ('pub_date', models.DateField()),
                ('review_period', models.CharField(max_length=50)),
                ('purpose', models.TextField()),
                ('scope', models.TextField()),
                ('policy_statements', models.TextField()),
                ('responsibilities', models.TextField()),
                ('archived_at', models.DateTimeField(auto_now_add=True)),
                ('definitions', models.ManyToManyField(blank=True, related_name='archived_policies', to='handbook.definition')),
                ('elated_policies', models.ManyToManyField(blank=True, related_name='archived_related_policies', to='handbook.policy')),
                ('policy_owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.department')),
                ('procedure_steps', models.ManyToManyField(blank=True, related_name='archived_policies', to='handbook.procedurestep')),
                ('related_policies', models.ManyToManyField(blank=True, to='handbook.archivedpolicy')),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='archived_policies', to='handbook.policysection')),
            ],
        ),
    ]
