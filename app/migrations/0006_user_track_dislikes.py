from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("models", "0005_users_and_channels")]

    initial = False

    operations = [
        ops.AddField(
            model_name="TrackVote",
            name="user",
            field=fields.ForeignKeyField(
                "models.User",
                source_field="user_id",
                related_name="track_votes",
                null=True,
                on_delete=OnDelete.CASCADE,
            ),
        ),
        ops.AddConstraint(
            model_name="TrackVote",
            constraint=ops.UniqueConstraint(fields=("track", "user")),
        ),
    ]
