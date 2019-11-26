# Generated by Django 1.11.14 on 2019-03-06 13:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0003_auto_20181203_1101'),
    ]

    operations = [
        migrations.AlterField(
            model_name='intervention',
            name='date_update',
            field=models.DateTimeField(auto_now=True, db_column='date_update', db_index=True, verbose_name='Update date'),
        ),
        migrations.AlterField(
            model_name='project',
            name='date_update',
            field=models.DateTimeField(auto_now=True, db_column='date_update', db_index=True, verbose_name='Update date'),
        ),
    ]
