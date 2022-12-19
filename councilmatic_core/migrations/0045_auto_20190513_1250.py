# Generated by Django 2.1.8 on 2019-05-13 17:50

import django.core.files.storage
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("legislative", "0008_longer_event_name"),
        ("core", "0004_auto_20171005_2028"),
        ("councilmatic_core", "0044_bill_restrict_view"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="action",
            name="_bill",
        ),
        migrations.RemoveField(
            model_name="action",
            name="_organization",
        ),
        migrations.RemoveField(
            model_name="actionrelatedentity",
            name="_action",
        ),
        migrations.RemoveField(
            model_name="billdocument",
            name="bill",
        ),
        migrations.RemoveField(
            model_name="eventagendaitem",
            name="bill",
        ),
        migrations.RemoveField(
            model_name="eventagendaitem",
            name="event",
        ),
        migrations.RemoveField(
            model_name="eventdocument",
            name="event",
        ),
        migrations.RemoveField(
            model_name="eventmedia",
            name="event",
        ),
        migrations.RemoveField(
            model_name="eventparticipant",
            name="event",
        ),
        migrations.RemoveField(
            model_name="membership",
            name="_organization",
        ),
        migrations.RemoveField(
            model_name="membership",
            name="_person",
        ),
        migrations.RemoveField(
            model_name="membership",
            name="_post",
        ),
        migrations.RemoveField(
            model_name="post",
            name="_organization",
        ),
        migrations.RemoveField(
            model_name="relatedbill",
            name="central_bill",
        ),
        migrations.RemoveField(
            model_name="sponsorship",
            name="_bill",
        ),
        migrations.RemoveField(
            model_name="sponsorship",
            name="_person",
        ),
        migrations.RemoveField(
            model_name="subject",
            name="bill",
        ),
        migrations.CreateModel(
            name="BillAction",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
            },
            bases=("legislative.billaction",),
        ),
        migrations.CreateModel(
            name="BillActionRelatedEntity",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
            },
            bases=("legislative.billactionrelatedentity",),
        ),
        migrations.CreateModel(
            name="BillSponsorship",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
            },
            bases=("legislative.billsponsorship",),
        ),
        migrations.RemoveField(
            model_name="bill",
            name="_from_organization",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="_legislative_session",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="abstract",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="bill_type",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="classification",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="description",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="full_text",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="html_text",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="identifier",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="last_action_date",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="ocd_created_at",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="ocd_id",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="ocd_updated_at",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="ocr_full_text",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="source_note",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="source_url",
        ),
        migrations.RemoveField(
            model_name="bill",
            name="updated_at",
        ),
        migrations.RemoveField(
            model_name="event",
            name="all_day",
        ),
        migrations.RemoveField(
            model_name="event",
            name="classification",
        ),
        migrations.RemoveField(
            model_name="event",
            name="description",
        ),
        migrations.RemoveField(
            model_name="event",
            name="end_time",
        ),
        migrations.RemoveField(
            model_name="event",
            name="extras",
        ),
        migrations.RemoveField(
            model_name="event",
            name="location_name",
        ),
        migrations.RemoveField(
            model_name="event",
            name="location_url",
        ),
        migrations.RemoveField(
            model_name="event",
            name="name",
        ),
        migrations.RemoveField(
            model_name="event",
            name="ocd_created_at",
        ),
        migrations.RemoveField(
            model_name="event",
            name="ocd_id",
        ),
        migrations.RemoveField(
            model_name="event",
            name="ocd_updated_at",
        ),
        migrations.RemoveField(
            model_name="event",
            name="source_note",
        ),
        migrations.RemoveField(
            model_name="event",
            name="source_url",
        ),
        migrations.RemoveField(
            model_name="event",
            name="start_time",
        ),
        migrations.RemoveField(
            model_name="event",
            name="status",
        ),
        migrations.RemoveField(
            model_name="event",
            name="updated_at",
        ),
        migrations.RemoveField(
            model_name="organization",
            name="_parent",
        ),
        migrations.RemoveField(
            model_name="organization",
            name="classification",
        ),
        migrations.RemoveField(
            model_name="organization",
            name="jurisdiction",
        ),
        migrations.RemoveField(
            model_name="organization",
            name="name",
        ),
        migrations.RemoveField(
            model_name="organization",
            name="ocd_id",
        ),
        migrations.RemoveField(
            model_name="organization",
            name="source_url",
        ),
        migrations.RemoveField(
            model_name="organization",
            name="updated_at",
        ),
        migrations.RemoveField(
            model_name="person",
            name="email",
        ),
        migrations.RemoveField(
            model_name="person",
            name="name",
        ),
        migrations.RemoveField(
            model_name="person",
            name="ocd_id",
        ),
        migrations.RemoveField(
            model_name="person",
            name="source_note",
        ),
        migrations.RemoveField(
            model_name="person",
            name="source_url",
        ),
        migrations.RemoveField(
            model_name="person",
            name="updated_at",
        ),
        migrations.RemoveField(
            model_name="person",
            name="website_url",
        ),
        migrations.AddField(
            model_name="bill",
            name="bill",
            field=models.OneToOneField(
                default="foo",
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="councilmatic_bill",
                serialize=False,
                to="legislative.Bill",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="event",
            name="event",
            field=models.OneToOneField(
                default="foo",
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="councilmatic_event",
                serialize=False,
                to="legislative.Event",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="organization",
            name="organization",
            field=models.OneToOneField(
                default="foo",
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="councilmatic_organization",
                serialize=False,
                to="core.Organization",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="person",
            name="person",
            field=models.OneToOneField(
                default="foo",
                on_delete=django.db.models.deletion.CASCADE,
                parent_link=True,
                primary_key=True,
                related_name="councilmatic_person",
                serialize=False,
                to="core.Person",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="bill",
            name="slug",
            field=models.SlugField(),
        ),
        migrations.AlterField(
            model_name="event",
            name="slug",
            field=models.SlugField(max_length=200),
        ),
        migrations.AlterField(
            model_name="organization",
            name="slug",
            field=models.SlugField(max_length=200),
        ),
        migrations.AlterField(
            model_name="person",
            name="headshot",
            field=models.FileField(
                default="images/headshot_placeholder.png",
                storage=django.core.files.storage.FileSystemStorage(
                    base_url="/", location="/Users/fgregg/work/chi-councilmatic/static"
                ),
                upload_to="images",
            ),
        ),
        migrations.AlterField(
            model_name="person",
            name="slug",
            field=models.SlugField(),
        ),
        migrations.DeleteModel(
            name="Action",
        ),
        migrations.DeleteModel(
            name="ActionRelatedEntity",
        ),
        migrations.DeleteModel(
            name="BillDocument",
        ),
        migrations.DeleteModel(
            name="EventAgendaItem",
        ),
        migrations.DeleteModel(
            name="EventDocument",
        ),
        migrations.DeleteModel(
            name="EventMedia",
        ),
        migrations.DeleteModel(
            name="EventParticipant",
        ),
        migrations.DeleteModel(
            name="Jurisdiction",
        ),
        migrations.DeleteModel(
            name="LegislativeSession",
        ),
        migrations.DeleteModel(
            name="Membership",
        ),
        migrations.DeleteModel(
            name="Post",
        ),
        migrations.DeleteModel(
            name="RelatedBill",
        ),
        migrations.DeleteModel(
            name="Sponsorship",
        ),
        migrations.DeleteModel(
            name="Subject",
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
            },
            bases=("core.membership",),
        ),
        migrations.CreateModel(
            name="Post",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
            },
            bases=("core.post",),
        ),
    ]
