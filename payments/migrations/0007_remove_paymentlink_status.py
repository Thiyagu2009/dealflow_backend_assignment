# Generated by Django 5.1.2 on 2024-11-01 08:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0006_alter_paymentlink_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentlink',
            name='status',
        ),
    ]