import re
from typing import Literal
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from tortoise.expressions import Q
from tortoise.functions import Count
from tortoise.transactions import in_transaction

from app.auth import require_admin, valid_credentials
from app.catalog import ERRORS as CATALOG_ERRORS
from app.catalog import next_track, refresh_radio
from app.models import Radio, Track, TrackVote
from app.ratings import wilson_score

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class VoteInput(BaseModel):
    value: Literal[-1, 1]


def _words(value: str) -> list[str]:
    return list(dict.fromkeys(word.strip().lower() for word in value.split(",") if word.strip()))


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    radios = await Radio.filter(enabled=True).order_by("name")
    return templates.TemplateResponse(request, "index.html", {"radios": radios})


@router.get("/api/radios/{slug}/next")
async def radio_next(slug: str):
    radio = await Radio.get_or_none(slug=slug, enabled=True)
    if not radio:
        raise HTTPException(404, "Radio not found")
    try:
        track = await next_track(radio)
    except (*CATALOG_ERRORS, httpx.HTTPError) as exc:
        raise HTTPException(502, str(exc)) from exc
    if not track:
        raise HTTPException(503, "No tracks available for this radio")
    return JSONResponse(
        {
            "id": track.id,
            "provider": track.provider,
            "name": track.name,
            "artist": track.artist_name,
            "album": track.album_name,
            "duration": track.duration,
            "image": track.image_url,
            "audio": track.audio_url,
            "share_url": track.share_url,
            "license_url": track.license_url,
            "likes": track.likes,
            "dislikes": track.dislikes,
            "rating": round(wilson_score(track.likes, track.dislikes), 6),
        }
    )


@router.post("/api/tracks/{track_id}/vote")
async def vote_track(request: Request, track_id: int, vote: VoteInput):
    raw_voter_id = request.cookies.get("pixelwave_voter")
    try:
        voter_id = UUID(raw_voter_id) if raw_voter_id else uuid4()
    except ValueError:
        voter_id = uuid4()

    async with in_transaction():
        track = await Track.filter(id=track_id).select_for_update().first()
        if not track:
            raise HTTPException(404, "Track not found")
        existing = await TrackVote.get_or_none(track_id=track.id, voter_id=voter_id)
        if existing and existing.value != vote.value:
            if existing.value == 1:
                track.likes -= 1
            else:
                track.dislikes -= 1
            existing.value = vote.value
            await existing.save(update_fields=["value", "updated_at"])
        elif not existing:
            await TrackVote.create(track_id=track.id, voter_id=voter_id, value=vote.value)
        else:
            return _vote_response(track, voter_id, vote.value)

        if vote.value == 1:
            track.likes += 1
        else:
            track.dislikes += 1
        await track.save(update_fields=["likes", "dislikes"])
    return _vote_response(track, voter_id, vote.value)


def _vote_response(track: Track, voter_id: UUID, value: int) -> JSONResponse:
    response = JSONResponse(
        {
            "likes": track.likes,
            "dislikes": track.dislikes,
            "rating": round(wilson_score(track.likes, track.dislikes), 6),
            "vote": value,
        }
    )
    response.set_cookie(
        "pixelwave_voter", str(voter_id), max_age=31_536_000, httponly=True, samesite="lax"
    )
    return response


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse(request, "admin/login.html", {"error": None})


@router.post("/admin/login", response_class=HTMLResponse)
async def admin_login_post(request: Request, username: str = Form(), password: str = Form()):
    if not valid_credentials(username, password):
        return templates.TemplateResponse(
            request, "admin/login.html", {"error": "Invalid credentials"}, status_code=401
        )
    request.session["admin"] = True
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@router.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    require_admin(request)
    radios = (
        await Radio.all()
        .annotate(
            track_count=Count("tracks", distinct=True),
            jamendo_track_count=Count(
                "tracks", distinct=True, _filter=Q(tracks__provider="jamendo")
            ),
            audius_track_count=Count(
                "tracks", distinct=True, _filter=Q(tracks__provider="audius")
            ),
        )
        .order_by("name")
    )
    return templates.TemplateResponse(request, "admin/index.html", {"radios": radios})


@router.post("/admin/radios")
async def create_radio(
    request: Request,
    name: str = Form(),
    description: str = Form(""),
    tags: str = Form(),
    speeds: str = Form(""),
    instrumental: bool = Form(False),
):
    require_admin(request)
    slug = _slug(name)
    parsed_tags = _words(tags)
    if not parsed_tags:
        raise HTTPException(400, "At least one tag is required")
    if not slug or await Radio.exists(slug=slug):
        raise HTTPException(400, "Name must produce a unique slug")
    await Radio.create(
        name=name.strip(),
        slug=slug,
        description=description.strip(),
        tags=parsed_tags,
        speeds=_words(speeds),
        instrumental=instrumental,
    )
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/radios/{radio_id}")
async def edit_radio(
    request: Request,
    radio_id: int,
    name: str = Form(),
    description: str = Form(""),
    tags: str = Form(),
    speeds: str = Form(""),
    instrumental: bool = Form(False),
    enabled: bool = Form(False),
):
    require_admin(request)
    radio = await Radio.get_or_none(id=radio_id)
    if not radio:
        raise HTTPException(404)
    parsed_tags = _words(tags)
    if not parsed_tags:
        raise HTTPException(400, "At least one tag is required")
    query_changed = (
        radio.tags != parsed_tags
        or radio.speeds != _words(speeds)
        or radio.instrumental != instrumental
    )
    radio.name, radio.description = name.strip(), description.strip()
    radio.tags, radio.speeds = parsed_tags, _words(speeds)
    radio.instrumental, radio.enabled = instrumental, enabled
    if query_changed:
        await radio.tracks.clear()
        radio.last_synced_at = None
        radio.sync_offset = 0
        radio.audius_sync_offset = 0
    await radio.save()
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/radios/{radio_id}/sync")
async def sync_radio(request: Request, radio_id: int):
    require_admin(request)
    radio = await Radio.get_or_none(id=radio_id)
    if not radio:
        raise HTTPException(404)
    await refresh_radio(radio, force=True)
    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/radios/{radio_id}/delete")
async def delete_radio(request: Request, radio_id: int):
    require_admin(request)
    await Radio.filter(id=radio_id).delete()
    return RedirectResponse("/admin", status_code=303)


@router.get("/health")
async def health():
    return {"status": "ok"}
