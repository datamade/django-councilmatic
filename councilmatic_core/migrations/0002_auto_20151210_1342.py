# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('councilmatic_core', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bill',
            old_name='date_created',
            new_name='ocd_created_at',
        ),
        migrations.RenameField(
            model_name='bill',
            old_name='date_updated',
            new_name='ocd_updated_at',
        ),
        migrations.RemoveField(
            model_name='action',
            name='bill',
        ),
        migrations.RemoveField(
            model_name='action',
            name='organization',
        ),
        migrations.RemoveField(
            model_name='actionrelatedentity',
            name='action',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='from_organization',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='legislative_session',
        ),
        migrations.RemoveField(
            model_name='membership',
            name='organization',
        ),
        migrations.RemoveField(
            model_name='membership',
            name='person',
        ),
        migrations.RemoveField(
            model_name='membership',
            name='post',
        ),
        migrations.RemoveField(
            model_name='organization',
            name='parent',
        ),
        migrations.RemoveField(
            model_name='post',
            name='organization',
        ),
        migrations.RemoveField(
            model_name='sponsorship',
            name='bill',
        ),
        migrations.RemoveField(
            model_name='sponsorship',
            name='person',
        ),
        migrations.AddField(
            model_name='action',
            name='_bill',
            field=models.ForeignKey(
                null=True, related_name='actions', db_column='bill_id', to='councilmatic_core.Bill'),
        ),
        migrations.AddField(
            model_name='action',
            name='_organization',
            field=models.ForeignKey(null=True, related_name='actions',
                                    db_column='organization_id', to='councilmatic_core.Organization'),
        ),
        migrations.AddField(
            model_name='actionrelatedentity',
            name='_action',
            field=models.ForeignKey(null=True, related_name='related_entities',
                                    db_column='action_id', to='councilmatic_core.Action'),
        ),
        migrations.AddField(
            model_name='bill',
            name='_from_organization',
            field=models.ForeignKey(null=True, related_name='bills',
                                    db_column='from_organization_id', to='councilmatic_core.Organization'),
        ),
        migrations.AddField(
            model_name='bill',
            name='_legislative_session',
            field=models.ForeignKey(null=True, related_name='bills',
                                    db_column='legislative_session_id', to='councilmatic_core.LegislativeSession'),
        ),
        migrations.AddField(
            model_name='event',
            name='ocd_created_at',
            field=models.DateTimeField(default=None),
        ),
        migrations.AddField(
            model_name='event',
            name='ocd_updated_at',
            field=models.DateTimeField(default=None),
        ),
        migrations.AddField(
            model_name='membership',
            name='_organization',
            field=models.ForeignKey(null=True, related_name='memberships',
                                    db_column='organization_id', to='councilmatic_core.Organization'),
        ),
        migrations.AddField(
            model_name='membership',
            name='_person',
            field=models.ForeignKey(null=True, related_name='memberships',
                                    db_column='person_id', to='councilmatic_core.Person'),
        ),
        migrations.AddField(
            model_name='membership',
            name='_post',
            field=models.ForeignKey(null=True, related_name='memberships',
                                    db_column='post_id', to='councilmatic_core.Post'),
        ),
        migrations.AddField(
            model_name='organization',
            name='_parent',
            field=models.ForeignKey(null=True, related_name='children',
                                    db_column='parent_id', to='councilmatic_core.Organization'),
        ),
        migrations.AddField(
            model_name='post',
            name='_organization',
            field=models.ForeignKey(null=True, related_name='posts',
                                    db_column='organization_id', to='councilmatic_core.Organization'),
        ),
        migrations.AddField(
            model_name='sponsorship',
            name='_bill',
            field=models.ForeignKey(null=True, related_name='sponsorships',
                                    db_column='bill_id', to='councilmatic_core.Bill'),
        ),
        migrations.AddField(
            model_name='sponsorship',
            name='_person',
            field=models.ForeignKey(null=True, related_name='sponsorships',
                                    db_column='person_id', to='councilmatic_core.Person'),
        ),
    ]
