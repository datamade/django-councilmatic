# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-10-13 16:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("councilmatic_core", "0015_auto_20161012_1626"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="legislativesession",
            name="id",
        ),
        migrations.AlterField(
            model_name="legislativesession",
            name="identifier",
            field=models.CharField(max_length=255, primary_key=True, serialize=False),
        ),
    ]
