# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-08-29 12:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backweb', '0012_auto_20180829_1941'),
    ]

    operations = [
        migrations.AlterField(
            model_name='goods',
            name='is_delete',
            field=models.CharField(default=0, max_length=2),
        ),
    ]