# Generated by Django 4.1.7 on 2024-10-15 03:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_provider', '0002_alter_upbitdata_date_time'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='upbitdata',
            unique_together={('market', 'date_time')},
        ),
        migrations.RemoveField(
            model_name='upbitdata',
            name='period',
        ),
    ]