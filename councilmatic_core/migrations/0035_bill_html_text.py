# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-01-08 16:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("councilmatic_core", "0034_event_guid"),
    ]

    operations = [
        migrations.AddField(
            model_name="bill",
            name="html_text",
            field=models.TextField(blank=True, null=True),
        ),
    ]