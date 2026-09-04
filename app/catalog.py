from datetime import UTC, datetime
from random import randrange

import httpx
from tortoise.expressions import F

from app import audius, jamendo
from app.models import Radio, Track

ERRORS = (audius.AudiusError, jamendo.JamendoError)


async def refresh_radio(radio: Radio, *, force: bool = False) -> int:
    errors = []
    for refresh in (jamendo.refresh_radio, audius.refresh_radio):
        try:
            await refresh(radio, force=force)
        except (*ERRORS, httpx.HTTPError) as exc:
            errors.append(exc)
    count = await radio.tracks.all().count()
    if not count and errors:
        raise errors[0]
    return count


async def next_track(radio: Radio) -> Track | None:
    if radio.owner_id is None:
        await refresh_radio(radio)
    query = radio.tracks.all()
    count = await query.count()
    if not count:
        return None
    track = await query.offset(randrange(count)).first()
    if track:
        await Track.filter(id=track.id).update(
            play_count=F("play_count") + 1, last_played_at=datetime.now(UTC)
        )
    return track
