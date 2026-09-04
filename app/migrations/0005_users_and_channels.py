from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("models", "0004_audius_provider")]

    initial = False

    operations = [
        ops.CreateModel(
            name="User",
            fields=[
                ("id", fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                ("telegram_id", fields.BigIntField(unique=True, db_index=True)),
                ("username", fields.CharField(max_length=100, default="")),
                ("display_name", fields.CharField(max_length=200)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ("updated_at", fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={"table": "users", "app": "models", "pk_attr": "id"},
            bases=["Model"],
        ),
        ops.AddField(
            model_name="Radio",
            name="owner",
            field=fields.ForeignKeyField(
                "models.User",
                source_field="owner_id",
                related_name="radios",
                null=True,
                on_delete=OnDelete.CASCADE,
            ),
        ),
        ops.AddField(
            model_name="Radio",
            name="visibility",
            field=fields.CharField(max_length=20, default="public", null=True),
        ),
        ops.AddField(
            model_name="Radio", name="likes", field=fields.IntField(default=0, null=True)
        ),
        ops.AddField(
            model_name="Radio", name="dislikes", field=fields.IntField(default=0, null=True)
        ),
        ops.RunSQL(
            sql='UPDATE "radios" SET "visibility" = \'public\', "likes" = 0, "dislikes" = 0',
            reverse_sql="SELECT 1",
        ),
        ops.AlterField(
            model_name="Radio",
            name="visibility",
            field=fields.CharField(max_length=20, default="public"),
        ),
        ops.AlterField(
            model_name="Radio", name="likes", field=fields.IntField(default=0)
        ),
        ops.AlterField(
            model_name="Radio", name="dislikes", field=fields.IntField(default=0)
        ),
        ops.CreateModel(
            name="RadioVote",
            fields=[
                ("id", fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                (
                    "radio",
                    fields.ForeignKeyField(
                        "models.Radio",
                        source_field="radio_id",
                        related_name="votes",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                ("voter_id", fields.UUIDField()),
                ("value", fields.SmallIntField()),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
                ("updated_at", fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={
                "table": "radio_votes",
                "app": "models",
                "unique_together": (("radio", "voter_id"),),
                "pk_attr": "id",
            },
            bases=["Model"],
        ),
        ops.CreateModel(
            name="LoginToken",
            fields=[
                ("id", fields.IntField(generated=True, primary_key=True, unique=True, db_index=True)),
                (
                    "user",
                    fields.ForeignKeyField(
                        "models.User",
                        source_field="user_id",
                        related_name="login_tokens",
                        on_delete=OnDelete.CASCADE,
                    ),
                ),
                ("token_hash", fields.CharField(max_length=64, unique=True, db_index=True)),
                ("expires_at", fields.DatetimeField(auto_now=False, auto_now_add=False)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={"table": "login_tokens", "app": "models", "pk_attr": "id"},
            bases=["Model"],
        ),
    ]
