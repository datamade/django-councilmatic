# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-08-15 21:18
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ("councilmatic_core", "0030_eventagendaitem_notes"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventdocument",
            name="updated_at",
            field=models.DateTimeField(default=None, null=True),
            preserve_default=False,
        ),
    ]
