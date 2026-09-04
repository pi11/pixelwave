from tortoise import fields, migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("models", "0003_station_sync_cursor")]

    initial = False

    operations = [
        ops.AddField(
            model_name="Radio",
            name="audius_sync_offset",
            field=fields.IntField(default=0, null=True),
        ),
        ops.RunSQL(
            sql='UPDATE "radios" SET "audius_sync_offset" = 0',
            reverse_sql="SELECT 1",
        ),
        ops.AlterField(
            model_name="Radio",
            name="audius_sync_offset",
            field=fields.IntField(default=0),
        ),
        ops.AddField(
            model_name="Track",
            name="provider",
            field=fields.CharField(max_length=20, default="jamendo", null=True),
        ),
        ops.RunSQL(
            sql='UPDATE "tracks" SET "provider" = \'jamendo\' WHERE "provider" IS NULL',
            reverse_sql="SELECT 1",
        ),
        ops.AlterField(
            model_name="Track",
            name="provider",
            field=fields.CharField(max_length=20, default="jamendo"),
        ),
        ops.AddField(
            model_name="Track",
            name="source_id",
            field=fields.CharField(max_length=100, null=True, db_index=True),
        ),
        ops.RunSQL(
            sql='UPDATE "tracks" SET "source_id" = "jamendo_id"::text',
            reverse_sql="SELECT 1",
        ),
        ops.AlterField(
            model_name="Track",
            name="source_id",
            field=fields.CharField(max_length=100, db_index=True),
        ),
        ops.AlterField(
            model_name="Track",
            name="jamendo_id",
            field=fields.BigIntField(unique=True, db_index=True, null=True),
        ),
        ops.AddConstraint(
            model_name="Track",
            constraint=ops.UniqueConstraint(fields=("provider", "source_id")),
        ),
    ]
