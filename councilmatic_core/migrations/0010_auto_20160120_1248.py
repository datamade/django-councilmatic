# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.utils.timezone import utc
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('councilmatic_core', '0009_bill_updated_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='action',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 46, 57, 767919, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='actionrelatedentity',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 47, 4, 415901, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='agendaitembill',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 47, 8, 919814, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='billdocument',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 47, 14, 71987, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='document',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 47, 18, 455922, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='event',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 47, 23, 135929, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eventagendaitem',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 47, 27, 383947, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eventdocument',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 47, 32, 151960, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eventparticipant',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 47, 36, 336258, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='legislativesession',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 47, 42, 400193, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='membership',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 47, 46, 375945, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='organization',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 47, 50, 855978, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='person',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 47, 54, 823989, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='post',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 48, 1, 399994, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sponsorship',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=datetime.datetime(
                2016, 1, 20, 18, 48, 5, 392000, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
