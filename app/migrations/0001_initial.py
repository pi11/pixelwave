from tortoise import migrations
from tortoise.migrations import operations as ops
import functools
from json import dumps, loads
from tortoise.fields.base import OnDelete
from tortoise import fields

class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name='Radio',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('name', fields.CharField(max_length=100)),
                ('slug', fields.CharField(unique=True, db_index=True, max_length=100)),
                ('description', fields.CharField(default='', max_length=280)),
                ('tags', fields.JSONField(default=list, encoder=functools.partial(dumps, separators=(',', ':')), decoder=loads)),
                ('speeds', fields.JSONField(default=list, encoder=functools.partial(dumps, separators=(',', ':')), decoder=loads)),
                ('instrumental', fields.BooleanField(default=True)),
                ('enabled', fields.BooleanField(default=True)),
                ('last_synced_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
                ('created_at', fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ('updated_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={'table': 'radios', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
        ops.CreateModel(
            name='Track',
            fields=[
                ('id', fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ('jamendo_id', fields.BigIntField(unique=True, db_index=True)),
                ('name', fields.CharField(max_length=300)),
                ('artist_id', fields.BigIntField(null=True)),
                ('artist_name', fields.CharField(max_length=300)),
                ('album_id', fields.BigIntField(null=True)),
                ('album_name', fields.CharField(default='', max_length=300)),
                ('duration', fields.IntField(default=0)),
                ('released_at', fields.DateField(null=True)),
                ('image_url', fields.TextField(default='', unique=False)),
                ('audio_url', fields.TextField(unique=False)),
                ('share_url', fields.TextField(default='', unique=False)),
                ('license_url', fields.TextField(default='', unique=False)),
                ('download_url', fields.TextField(default='', unique=False)),
                ('download_allowed', fields.BooleanField(default=False)),
                ('raw_data', fields.JSONField(default=dict, encoder=functools.partial(dumps, separators=(',', ':')), decoder=loads)),
                ('fetched_at', fields.DatetimeField(auto_now=True, auto_now_add=False)),
                ('play_count', fields.BigIntField(default=0)),
                ('last_played_at', fields.DatetimeField(null=True, auto_now=False, auto_now_add=False)),
                ('radios', fields.ManyToManyField('models.Radio', unique=True, db_constraint=True, through='radio_tracks', forward_key='radio_id', backward_key='tracks_id', related_name='tracks', on_delete=OnDelete.CASCADE)),
            ],
            options={'table': 'tracks', 'app': 'models', 'pk_attr': 'id'},
            bases=['Model'],
        ),
    ]
