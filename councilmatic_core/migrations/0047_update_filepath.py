# Generated by Django 2.1.9 on 2019-06-18 17:30
import os

from django.conf import settings
import django.core.files.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("councilmatic_core", "0046_subclass_ocd_billdocument"),
    ]

    operations = [
        migrations.AlterField(
            model_name="person",
            name="headshot",
            field=models.FileField(
                default="images/headshot_placeholder.png",
                storage=django.core.files.storage.FileSystemStorage(
                    base_url="/", location=os.path.join(settings.STATIC_ROOT)
                ),
                upload_to="images/headshots",
            ),
        ),
    ]
