from datetime import UTC, datetime, timedelta
from math import ceil

import httpx

from app.config import settings
from app.models import Radio, Track

API_URL = "https://api.audius.co/v1"


class AudiusError(RuntimeError):
    pass


def _tags(item: dict) -> set[str]:
    raw_tags = item.get("tags") or ""
    if isinstance(raw_tags, list):
        values = raw_tags
    else:
        values = raw_tags.split(",")
    return {str(tag).strip().lower() for tag in values if str(tag).strip()}


def _is_instrumental(item: dict) -> bool:
    return "instrumental" in _tags(item)


def _matches_speed(item: dict, speeds: list[str]) -> bool:
    if not speeds:
        return True
    if not item.get("bpm"):
        return False
    bpm = float(item["bpm"])
    speed = (
        "verylow" if bpm < 70 else "low" if bpm < 90 else "medium" if bpm < 120
        else "high" if bpm < 150 else "veryhigh"
    )
    return speed in speeds


def _license_url(item: dict) -> str:
    license_value = str(item.get("license") or "").strip()
    if license_value.startswith(("http://", "https://")):
        return license_value
    licenses = {
        "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
        "by": "https://creativecommons.org/licenses/by/4.0/",
        "by-nc": "https://creativecommons.org/licenses/by-nc/4.0/",
        "by-nd": "https://creativecommons.org/licenses/by-nd/4.0/",
        "by-sa": "https://creativecommons.org/licenses/by-sa/4.0/",
        "by-nc-nd": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "by-nc-sa": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    }
    return licenses.get(license_value.lower().removeprefix("cc-"), "https://audius.org/open-music-license.pdf")


async def refresh_radio(radio: Radio, *, force: bool = False) -> int:
    cache_target = 250 if radio.owner_id else settings.track_cache_target
    if radio.instrumental:
        rejected = [
            track
            for track in await radio.tracks.filter(provider="audius")
            if not _is_instrumental(track.raw_data)
        ]
        if rejected:
            await radio.tracks.remove(*rejected)

    count = await radio.tracks.filter(provider="audius").count()
    fresh_after = datetime.now(UTC) - timedelta(hours=settings.track_cache_ttl_hours)
    if not force and radio.last_synced_at and count >= cache_target:
        synced = radio.last_synced_at
        if synced.tzinfo is None:
            synced = synced.replace(tzinfo=UTC)
        if synced >= fresh_after:
            return count

    limit = min(settings.jamendo_page_size, 100)
    missing = max(0, cache_target - count)
    pages = min(max(settings.refresh_pages, ceil(missing / limit)), ceil(cache_target / limit))
    offset = radio.audius_sync_offset
    headers = {"Authorization": f"Bearer {settings.audius_api_key}"} if settings.audius_api_key else {}
    query = " ".join(radio.tags)
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
        for _ in range(pages):
            response = await client.get(
                f"{API_URL}/tracks/search", params={"query": query, "limit": limit, "offset": offset}
            )
            response.raise_for_status()
            results = response.json().get("data", [])
            if not isinstance(results, list):
                raise AudiusError("Audius returned an invalid track response")
            if not results:
                offset = 0
                break
            for item in results:
                if (
                    item.get("is_stream_gated")
                    or not item.get("is_streamable", True)
                    or (radio.instrumental and not _is_instrumental(item))
                ):
                    continue
                if not _matches_speed(item, radio.speeds):
                    continue
                source_id = str(item["id"])
                artwork = item.get("artwork") or {}
                user = item.get("user") or {}
                permalink = item.get("permalink") or ""
                if permalink.startswith("/"):
                    permalink = f"https://audius.co{permalink}"
                release_date = item.get("release_date") or ""
                track, _ = await Track.update_or_create(
                    provider="audius",
                    source_id=source_id,
                    defaults={
                        "name": item.get("title") or "Unknown track",
                        "artist_name": user.get("name") or item.get("user_name") or "Unknown artist",
                        "album_name": item.get("album_name") or "",
                        "duration": int(item.get("duration") or 0),
                        "released_at": release_date[:10] or None,
                        "image_url": artwork.get("1000x1000") or artwork.get("_1000x1000")
                        or artwork.get("480x480") or artwork.get("_480x480") or "",
                        "audio_url": f"{API_URL}/tracks/{source_id}/stream",
                        "share_url": permalink or f"https://audius.co/tracks/{source_id}",
                        "license_url": _license_url(item),
                        "raw_data": item,
                    },
                )
                await radio.tracks.add(track)
            offset += len(results)
            if len(results) < limit:
                offset = 0
                break

    count = await radio.tracks.filter(provider="audius").count()
    if count > cache_target:
        stale = (
            await radio.tracks.filter(provider="audius")
            .order_by("fetched_at")
            .limit(count - cache_target)
        )
        await radio.tracks.remove(*stale)
    radio.last_synced_at = datetime.now(UTC)
    radio.audius_sync_offset = offset
    await radio.save(update_fields=["last_synced_at", "audius_sync_offset"])
    return await radio.tracks.filter(provider="audius").count()
