from datetime import UTC, datetime, timedelta
from math import ceil

import httpx

from app.config import settings
from app.models import Radio, Track

API_URL = "https://api.jamendo.com/v3.0/tracks/"


class JamendoError(RuntimeError):
    pass


async def refresh_radio(radio: Radio, *, force: bool = False) -> int:
    cache_target = max(1, (settings.track_cache_target + 1) // 2)
    if radio.instrumental:
        cached_non_instrumentals = [
            track
            for track in await radio.tracks.filter(provider="jamendo")
            if not _is_instrumental(track.raw_data)
        ]
        if cached_non_instrumentals:
            await radio.tracks.remove(*cached_non_instrumentals)

    count = await radio.tracks.filter(provider="jamendo").count()
    fresh_after = datetime.now(UTC) - timedelta(hours=settings.track_cache_ttl_hours)
    if not force and radio.last_synced_at:
        synced = radio.last_synced_at
        if synced.tzinfo is None:
            synced = synced.replace(tzinfo=UTC)
        cache_full_or_catalog_exhausted = (
            count >= cache_target or radio.sync_offset == 0
        )
        if synced >= fresh_after and cache_full_or_catalog_exhausted:
            return count

    base_params: dict[str, str | int] = {
        "client_id": settings.jamendo_client_id,
        "format": "json",
        "limit": settings.jamendo_page_size,
        "fuzzytags": "+".join(radio.tags),
        "include": "licenses+musicinfo",
        "audioformat": "mp32",
        "boost": "popularity_month",
    }
    if radio.speeds:
        base_params["speed"] = "+".join(radio.speeds)
    if radio.instrumental:
        base_params["vocalinstrumental"] = "instrumental"

    missing = max(0, cache_target - count)
    pages = max(settings.refresh_pages, ceil(missing / settings.jamendo_page_size))
    pages = min(pages, ceil(cache_target / settings.jamendo_page_size))
    offset = radio.sync_offset
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for _ in range(pages):
            params = {**base_params, "offset": offset}
            response = await client.get(API_URL, params=params)
            response.raise_for_status()
            payload = response.json()
            headers = payload.get("headers", {})
            if headers.get("status") != "success":
                raise JamendoError(headers.get("error_message") or "Jamendo request failed")
            results = payload.get("results", [])
            if not results:
                offset = 0
                break
            for item in results:
                if radio.instrumental and not _is_instrumental(item):
                    continue
                track, _ = await Track.update_or_create(
                    provider="jamendo",
                    source_id=str(item["id"]),
                    defaults={"jamendo_id": int(item["id"]), **_track_defaults(item)},
                )
                await radio.tracks.add(track)
            offset += len(results)
            if len(results) < settings.jamendo_page_size:
                offset = 0
                break

    count = await radio.tracks.filter(provider="jamendo").count()
    if count > cache_target:
        overflow = count - cache_target
        stale = (
            await radio.tracks.filter(provider="jamendo").order_by("fetched_at").limit(overflow)
        )
        await radio.tracks.remove(*stale)

    radio.last_synced_at = datetime.now(UTC)
    radio.sync_offset = offset
    await radio.save(update_fields=["last_synced_at", "sync_offset"])
    return await radio.tracks.filter(provider="jamendo").count()


def _is_instrumental(item: dict) -> bool:
    musicinfo = item.get("musicinfo")
    return isinstance(musicinfo, dict) and musicinfo.get("vocalinstrumental") == "instrumental"


def _track_defaults(item: dict) -> dict:
    return {
        "name": item.get("name", "Unknown track"),
        "artist_id": int(item["artist_id"]) if item.get("artist_id") else None,
        "artist_name": item.get("artist_name", "Unknown artist"),
        "album_id": int(item["album_id"]) if item.get("album_id") else None,
        "album_name": item.get("album_name", ""),
        "duration": int(item.get("duration") or 0),
        "released_at": item.get("releasedate") or None,
        "image_url": item.get("image") or item.get("album_image") or "",
        "audio_url": item.get("audio", ""),
        "share_url": item.get("shareurl", ""),
        "license_url": item.get("license_ccurl", ""),
        "download_url": item.get("audiodownload", ""),
        "download_allowed": bool(item.get("audiodownload_allowed", False)),
        "raw_data": item,
    }
