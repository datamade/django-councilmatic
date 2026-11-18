from django.db import migrations


class RemoveFieldCascade(migrations.RemoveField):
    """
    Before Django 6.0, the schema editor dropped columns with CASCADE. Some
    historical migrations rely on that to drop the foreign keys that reference
    a removed primary key. Restore that behavior explicitly for those
    migrations, so they apply under any supported Django version.
    """

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        schema_editor.sql_delete_column = (
            "ALTER TABLE %(table)s DROP COLUMN %(column)s CASCADE"
        )
        try:
            super().database_forwards(app_label, schema_editor, from_state, to_state)
        finally:
            del schema_editor.sql_delete_column
