from tortoise import fields, models


class User(models.Model):
    id = fields.IntField(primary_key=True)
    telegram_id = fields.BigIntField(unique=True, db_index=True)
    username = fields.CharField(max_length=100, default="")
    display_name = fields.CharField(max_length=200)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"


class Radio(models.Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)
    slug = fields.CharField(max_length=100, unique=True, db_index=True)
    description = fields.CharField(max_length=280, default="")
    tags = fields.JSONField(default=list)
    speeds = fields.JSONField(default=list)
    instrumental = fields.BooleanField(default=True)
    enabled = fields.BooleanField(default=True)
    last_synced_at = fields.DatetimeField(null=True)
    sync_offset = fields.IntField(default=0)
    audius_sync_offset = fields.IntField(default=0)
    visibility = fields.CharField(max_length=20, default="public")
    likes = fields.IntField(default=0)
    dislikes = fields.IntField(default=0)
    owner: fields.ForeignKeyNullableRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="radios", null=True, on_delete=fields.CASCADE
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    tracks: fields.ManyToManyRelation["Track"]

    class Meta:
        table = "radios"


class Track(models.Model):
    id = fields.IntField(primary_key=True)
    jamendo_id = fields.BigIntField(unique=True, db_index=True, null=True)
    provider = fields.CharField(max_length=20, default="jamendo")
    source_id = fields.CharField(max_length=100, db_index=True)
    name = fields.CharField(max_length=300)
    artist_id = fields.BigIntField(null=True)
    artist_name = fields.CharField(max_length=300)
    album_id = fields.BigIntField(null=True)
    album_name = fields.CharField(max_length=300, default="")
    duration = fields.IntField(default=0)
    released_at = fields.DateField(null=True)
    image_url = fields.TextField(default="")
    audio_url = fields.TextField()
    share_url = fields.TextField(default="")
    license_url = fields.TextField(default="")
    download_url = fields.TextField(default="")
    download_allowed = fields.BooleanField(default=False)
    raw_data = fields.JSONField(default=dict)
    fetched_at = fields.DatetimeField(auto_now=True)
    play_count = fields.BigIntField(default=0)
    likes = fields.IntField(default=0)
    dislikes = fields.IntField(default=0)
    last_played_at = fields.DatetimeField(null=True)

    radios: fields.ManyToManyRelation[Radio] = fields.ManyToManyField(
        "models.Radio", related_name="tracks", through="radio_tracks"
    )

    class Meta:
        table = "tracks"
        unique_together = (("provider", "source_id"),)


class TrackVote(models.Model):
    id = fields.IntField(primary_key=True)
    track: fields.ForeignKeyRelation[Track] = fields.ForeignKeyField(
        "models.Track", related_name="votes", on_delete=fields.CASCADE
    )
    voter_id = fields.UUIDField()
    user: fields.ForeignKeyNullableRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="track_votes", null=True, on_delete=fields.CASCADE
    )
    value = fields.SmallIntField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "track_votes"
        unique_together = (("track", "voter_id"), ("track", "user"))


class RadioVote(models.Model):
    id = fields.IntField(primary_key=True)
    radio: fields.ForeignKeyRelation[Radio] = fields.ForeignKeyField(
        "models.Radio", related_name="votes", on_delete=fields.CASCADE
    )
    voter_id = fields.UUIDField()
    value = fields.SmallIntField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "radio_votes"
        unique_together = (("radio", "voter_id"),)


class LoginToken(models.Model):
    id = fields.IntField(primary_key=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="login_tokens", on_delete=fields.CASCADE
    )
    token_hash = fields.CharField(max_length=64, unique=True, db_index=True)
    expires_at = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "login_tokens"
