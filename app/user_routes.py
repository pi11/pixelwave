import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import quote
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from tortoise.expressions import Q
from tortoise.functions import Count
from tortoise.transactions import in_transaction

from app.catalog import ERRORS as CATALOG_ERRORS
from app.catalog import refresh_radio
from app.config import settings
from app.models import LoginToken, Radio, RadioVote, User
from app.ratings import wilson_score
from app.routes import _slug, _words
from app.user_auth import current_user, favorites_radio, hash_login_token

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _channel_rating(radio: Radio) -> float:
    return round(wilson_score(radio.likes, radio.dislikes), 6)


async def _owned_radio(request: Request, radio_id: int) -> tuple[User, Radio]:
    user = await current_user(request)
    if not user:
        raise HTTPException(401, "Log in with Telegram")
    radio = await Radio.get_or_none(id=radio_id, owner_id=user.id)
    if not radio:
        raise HTTPException(404, "Channel not found")
    return user, radio


async def _unique_slug(name: str, user_id: int) -> str:
    base = _slug(name)
    if not base:
        return ""
    candidate = base
    suffix = 1
    while await Radio.exists(slug=candidate):
        candidate = f"{base}-{user_id}" if suffix == 1 else f"{base}-{user_id}-{suffix}"
        suffix += 1
    return candidate


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    if await current_user(request):
        return RedirectResponse("/profile", status_code=303)
    bot_url = (
        f"https://t.me/{quote(settings.telegram_bot_username.lstrip('@'))}"
        if settings.telegram_bot_username
        else ""
    )
    return templates.TemplateResponse(request, "user/login.html", {"bot_url": bot_url})


@router.get("/auth/telegram")
async def telegram_login(request: Request, token: str):
    login_token = await LoginToken.get_or_none(token_hash=hash_login_token(token)).prefetch_related(
        "user"
    )
    if not login_token:
        raise HTTPException(401, "Invalid login link")
    expires_at = login_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise HTTPException(401, "Login link expired")
    request.session["user_id"] = login_token.user_id
    return RedirectResponse("/profile", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    request.session.pop("user_id", None)
    return RedirectResponse("/", status_code=303)


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    supplied_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not settings.telegram_webhook_secret or not secrets.compare_digest(
        supplied_secret, settings.telegram_webhook_secret
    ):
        raise HTTPException(403, "Invalid Telegram webhook secret")

    update = await request.json()
    message = update.get("message") or {}
    sender = message.get("from") or {}
    chat = message.get("chat") or {}
    if not sender.get("id") or chat.get("type") != "private":
        return {"ok": True}

    display_name = " ".join(
        value for value in (sender.get("first_name"), sender.get("last_name")) if value
    ) or sender.get("username") or f"Telegram user {sender['id']}"
    user = await User.get_or_none(telegram_id=sender["id"])
    if user:
        user.username = sender.get("username") or ""
        await user.save(update_fields=["username", "updated_at"])
    else:
        user = await User.create(
            telegram_id=sender["id"],
            username=sender.get("username") or "",
            display_name=display_name,
        )
    await favorites_radio(user)
    raw_token = secrets.token_urlsafe(32)
    await LoginToken.create(
        user=user,
        token_hash=hash_login_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    await LoginToken.filter(expires_at__lte=datetime.now(UTC)).delete()
    login_url = f"{settings.public_base_url.rstrip('/')}/auth/telegram?token={raw_token}"
    return {
        "method": "sendMessage",
        "chat_id": chat["id"],
        "text": f"Your Pixelwave login link (valid for 1 hour):\n{login_url}",
        "link_preview_options": {"is_disabled": True},
    }


@router.get("/user-channels", response_class=HTMLResponse)
async def user_channels(request: Request):
    user = await current_user(request)
    radios = (
        await Radio.filter(owner_id__not_isnull=True, visibility="public")
        .annotate(
            track_count=Count("tracks", distinct=True),
            jamendo_track_count=Count(
                "tracks", distinct=True, _filter=Q(tracks__provider="jamendo")
            ),
            audius_track_count=Count(
                "tracks", distinct=True, _filter=Q(tracks__provider="audius")
            ),
        )
        .prefetch_related("owner")
        .order_by("name")
    )
    for radio in radios:
        radio.overall_rating = _channel_rating(radio)
    return templates.TemplateResponse(
        request,
        "user/channels.html",
        {"radios": radios, "user": user},
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    user = await current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    favorites = await favorites_radio(user)
    radios = (
        await Radio.filter(owner_id=user.id)
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
    for radio in radios:
        radio.overall_rating = _channel_rating(radio)
    return templates.TemplateResponse(
        request,
        "user/profile.html",
        {"radios": radios, "user": user, "favorites": favorites},
    )


@router.post("/profile")
async def edit_profile(request: Request, display_name: str = Form()):
    user = await current_user(request)
    if not user:
        raise HTTPException(401, "Log in with Telegram")
    display_name = display_name.strip()
    if not display_name or len(display_name) > 100:
        raise HTTPException(400, "Username must be between 1 and 100 characters")
    user.display_name = display_name
    await user.save(update_fields=["display_name", "updated_at"])
    return RedirectResponse("/profile", status_code=303)


@router.post("/user-channels")
async def create_user_channel(
    request: Request,
    name: str = Form(),
    description: str = Form(""),
    tags: str = Form(),
    speeds: str = Form(""),
    instrumental: bool = Form(False),
    visibility: Literal["public", "hidden"] = Form("hidden"),
):
    user = await current_user(request)
    if not user:
        raise HTTPException(401, "Log in with Telegram")
    parsed_tags = _words(tags)
    slug = await _unique_slug(name, user.id)
    if not parsed_tags or not slug:
        raise HTTPException(400, "A valid name and at least one tag are required")
    radio = await Radio.create(
        owner=user,
        name=name.strip(),
        slug=slug,
        description=description.strip(),
        tags=parsed_tags,
        speeds=_words(speeds),
        instrumental=instrumental,
        visibility=visibility,
    )
    try:
        await refresh_radio(radio, force=True)
    except (*CATALOG_ERRORS, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Channel saved, but providers could not sync: {exc}") from exc
    return RedirectResponse("/profile", status_code=303)


@router.post("/user-channels/{radio_id}")
async def edit_user_channel(
    request: Request,
    radio_id: int,
    name: str = Form(),
    description: str = Form(""),
    tags: str = Form(),
    speeds: str = Form(""),
    instrumental: bool = Form(False),
    visibility: Literal["public", "hidden"] = Form("hidden"),
):
    user, radio = await _owned_radio(request, radio_id)
    if radio.id == (await favorites_radio(user)).id:
        raise HTTPException(403, "Favorites is managed by track likes")
    parsed_tags = _words(tags)
    if not parsed_tags or not _slug(name):
        raise HTTPException(400, "A valid name and at least one tag are required")
    radio.name = name.strip()
    radio.description = description.strip()
    radio.tags = parsed_tags
    radio.speeds = _words(speeds)
    radio.instrumental = instrumental
    radio.visibility = visibility
    radio.last_synced_at = None
    radio.sync_offset = 0
    radio.audius_sync_offset = 0
    await radio.tracks.clear()
    await radio.save()
    try:
        await refresh_radio(radio, force=True)
    except (*CATALOG_ERRORS, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Channel saved, but providers could not sync: {exc}") from exc
    return RedirectResponse("/profile", status_code=303)


@router.post("/user-channels/{radio_id}/delete")
async def delete_user_channel(request: Request, radio_id: int):
    user, radio = await _owned_radio(request, radio_id)
    if radio.id == (await favorites_radio(user)).id:
        raise HTTPException(403, "Favorites cannot be deleted")
    await radio.delete()
    return RedirectResponse("/profile", status_code=303)


@router.post("/api/radios/{radio_id}/vote")
async def vote_radio(request: Request, radio_id: int, value: int):
    if value not in (-1, 1):
        raise HTTPException(422, "Vote must be -1 or 1")
    user = await current_user(request)
    radio = await Radio.get_or_none(id=radio_id, owner_id__not_isnull=True)
    if not radio or (radio.visibility == "hidden" and (not user or radio.owner_id != user.id)):
        raise HTTPException(404, "Channel not found")

    raw_voter_id = request.cookies.get("pixelwave_voter")
    try:
        voter_id = UUID(raw_voter_id) if raw_voter_id else uuid4()
    except ValueError:
        voter_id = uuid4()
    async with in_transaction():
        radio = await Radio.filter(id=radio_id).select_for_update().first()
        existing = await RadioVote.get_or_none(radio_id=radio_id, voter_id=voter_id)
        if existing and existing.value != value:
            if existing.value == 1:
                radio.likes -= 1
            else:
                radio.dislikes -= 1
            existing.value = value
            await existing.save(update_fields=["value", "updated_at"])
        elif not existing:
            await RadioVote.create(radio_id=radio_id, voter_id=voter_id, value=value)
        else:
            return _radio_vote_response(radio, voter_id, value)
        if value == 1:
            radio.likes += 1
        else:
            radio.dislikes += 1
        await radio.save(update_fields=["likes", "dislikes"])
    return _radio_vote_response(radio, voter_id, value)


def _radio_vote_response(radio: Radio, voter_id: UUID, value: int) -> JSONResponse:
    response = JSONResponse(
        {
            "likes": radio.likes,
            "dislikes": radio.dislikes,
            "rating": _channel_rating(radio),
            "vote": value,
        }
    )
    response.set_cookie(
        "pixelwave_voter",
        str(voter_id),
        max_age=31_536_000,
        httponly=True,
        samesite="lax",
        secure=settings.public_base_url.startswith("https://"),
    )
    return response
