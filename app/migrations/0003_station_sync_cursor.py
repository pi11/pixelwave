from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('models', '0002_track_votes')]

    initial = False

    operations = [
        ops.AddField(
            model_name='Radio',
            name='sync_offset',
            field=fields.IntField(default=0, null=True),
        ),
        ops.RunSQL(
            sql='UPDATE "radios" SET "sync_offset" = 0',
            reverse_sql='SELECT 1',
        ),
        ops.AlterField(
            model_name='Radio',
            name='sync_offset',
            field=fields.IntField(default=0),
        ),
    ]
