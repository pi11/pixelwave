from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.fields.base import OnDelete
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('models', '0001_initial')]

    initial = False

    operations = [
        ops.CreateModel(
            name='TrackVote',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('track', fields.ForeignKeyField('models.Track', source_field='track_id', db_constraint=True, to_field='id', related_name='votes', on_delete=OnDelete.CASCADE)),
                ('voter_id', fields.UUIDField()),
                ('value', fields.SmallIntField()),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={'table': 'track_votes', 'app': 'models', 'unique_together': (('track', 'voter_id'),), 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.AddField(
            model_name='Track',
            name='dislikes',
            field=fields.IntField(default=0, null=True),
        ),
        ops.AddField(
            model_name='Track',
            name='likes',
            field=fields.IntField(default=0, null=True),
        ),
        ops.RunSQL(
            sql='UPDATE "tracks" SET "likes" = 0, "dislikes" = 0',
            reverse_sql='SELECT 1',
        ),
        ops.AlterField(
            model_name='Track',
            name='dislikes',
            field=fields.IntField(default=0),
        ),
        ops.AlterField(
            model_name='Track',
            name='likes',
            field=fields.IntField(default=0),
        ),
    ]
