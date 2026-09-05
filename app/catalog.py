import logging
from datetime import UTC, datetime
from random import randrange
from uuid import UUID

import httpx
from tortoise.expressions import F, Q

from app import audius, jamendo
from app.models import Radio, Track, TrackVote

ERRORS = (audius.AudiusError, jamendo.JamendoError)
logger = logging.getLogger("app.catalog")


async def refresh_radio(radio: Radio, *, force: bool = False) -> int:
    errors = []
    for refresh in (jamendo.refresh_radio, audius.refresh_radio):
        provider = refresh.__module__.rsplit(".", 1)[-1]
        try:
            await refresh(radio, force=force)
        except (*ERRORS, httpx.HTTPError) as exc:
            errors.append(exc)
            logger.exception(
                "Provider sync failed: provider=%s radio_id=%s slug=%s tags=%s speeds=%s "
                "instrumental=%s force=%s",
                provider,
                radio.id,
                radio.slug,
                radio.tags,
                radio.speeds,
                radio.instrumental,
                force,
            )
    count = await radio.tracks.all().count()
    if not count and len(errors) == 2:
        raise errors[0]
    if not count:
        logger.warning(
            "Radio sync completed with no tracks: radio_id=%s slug=%s tags=%s speeds=%s "
            "instrumental=%s provider_errors=%s",
            radio.id,
            radio.slug,
            radio.tags,
            radio.speeds,
            radio.instrumental,
            len(errors),
        )
    return count


async def next_track(
    radio: Radio, *, user_id: int | None = None, voter_id: UUID | None = None
) -> Track | None:
    if radio.owner_id is None:
        await refresh_radio(radio)
    query = radio.tracks.all()
    vote_filter = Q(value=-1)
    if user_id is not None and voter_id is not None:
        vote_filter &= Q(user_id=user_id) | Q(voter_id=voter_id)
    elif user_id is not None:
        vote_filter &= Q(user_id=user_id)
    elif voter_id is not None:
        vote_filter &= Q(voter_id=voter_id)
    else:
        vote_filter = None
    if vote_filter is not None:
        disliked_ids = await TrackVote.filter(vote_filter).values_list("track_id", flat=True)
        if disliked_ids:
            query = query.exclude(id__in=disliked_ids)
    count = await query.count()
    if not count:
        return None
    track = await query.offset(randrange(count)).first()
    if track:
        await Track.filter(id=track.id).update(
            play_count=F("play_count") + 1, last_played_at=datetime.now(UTC)
        )
    return track
