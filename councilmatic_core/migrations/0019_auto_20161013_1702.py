# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-10-13 22:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("councilmatic_core", "0018_auto_20161013_1656"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bill",
            name="subject",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
