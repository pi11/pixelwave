import pytest
from fastapi import HTTPException

from app import catalog
from app.audius import _is_instrumental as is_audius_instrumental
from app.audius import _license_url, _matches_speed
from app.auth import valid_credentials
from app.config import settings
from app.jamendo import _is_instrumental
from app.main import app
from app.ratings import wilson_score
from app.routes import _slug, _words, router
from app.user_auth import hash_login_token
from app.user_routes import router as user_router
from app.user_routes import vote_radio


def test_tag_normalization():
    assert _words(" Ambient, idm, ambient, electronic ") == ["ambient", "idm", "electronic"]


def test_slug_normalization():
    assert _slug("Lo-Fi Terminal!") == "lo-fi-terminal"


def test_admin_credentials():
    assert valid_credentials(settings.admin_username, settings.admin_password)
    assert not valid_credentials(settings.admin_username, f"{settings.admin_password}-incorrect")


def test_core_routes_are_registered():
    assert app.title == "Pixelwave Radio"
    paths = {route.path for route in router.routes}
    assert "/" in paths
    assert "/api/radios/{slug}/next" in paths
    assert "/channels/{slug}" in paths
    assert "/admin" in paths
    assert "/health" in paths
    assert "/api/tracks/{track_id}/vote" in paths
    user_paths = {route.path for route in user_router.routes}
    assert "/user-channels" in user_paths
    assert "/telegram/webhook" in user_paths
    assert "/api/radios/{radio_id}/vote" in user_paths
    assert "/profile" in user_paths


def test_login_tokens_are_hashed_deterministically():
    token_hash = hash_login_token("secret-login-token")
    assert token_hash == hash_login_token("secret-login-token")
    assert token_hash != "secret-login-token"
    assert len(token_hash) == 64


def test_wilson_score_rewards_confident_positive_votes():
    assert wilson_score(0, 0) == 0
    assert wilson_score(10, 0) > wilson_score(1, 0)
    assert wilson_score(8, 2) > wilson_score(5, 5)


def test_instrumental_track_classification_is_strict():
    assert _is_instrumental({"musicinfo": {"vocalinstrumental": "instrumental"}})
    assert not _is_instrumental({"musicinfo": {"vocalinstrumental": "vocal"}})
    assert not _is_instrumental({"musicinfo": {}})
    assert not _is_instrumental({})


def test_audius_filters_are_strict():
    assert is_audius_instrumental({"tags": "Electronic, Instrumental"})
    assert not is_audius_instrumental({"tags": "Electronic, Vocal"})
    assert _matches_speed({"bpm": 100}, ["medium"])
    assert not _matches_speed({}, ["medium"])


def test_audius_license_is_always_a_link():
    assert _license_url({"license": "CC-BY"}) == "https://creativecommons.org/licenses/by/4.0/"
    assert _license_url({}).startswith("https://audius.org/")


async def test_catalog_refreshes_all_providers(monkeypatch):
    calls = []

    async def refresh_jamendo(radio, *, force=False):
        calls.append(("jamendo", force))

    async def refresh_audius(radio, *, force=False):
        calls.append(("audius", force))

    class Tracks:
        def all(self):
            return self

        async def count(self):
            return 2

    class Radio:
        tracks = Tracks()

    monkeypatch.setattr(catalog.jamendo, "refresh_radio", refresh_jamendo)
    monkeypatch.setattr(catalog.audius, "refresh_radio", refresh_audius)

    assert await catalog.refresh_radio(Radio(), force=True) == 2
    assert calls == [("jamendo", True), ("audius", True)]


async def test_catalog_tolerates_one_provider_failure_with_no_matches(monkeypatch):
    async def failed(radio, *, force=False):
        raise catalog.jamendo.JamendoError("temporarily unavailable")

    async def empty(radio, *, force=False):
        return 0

    class Tracks:
        def all(self):
            return self

        async def count(self):
            return 0

    class Radio:
        tracks = Tracks()

    monkeypatch.setattr(catalog.jamendo, "refresh_radio", failed)
    monkeypatch.setattr(catalog.audius, "refresh_radio", empty)
    assert await catalog.refresh_radio(Radio(), force=True) == 0


async def test_channel_vote_rejects_invalid_values_before_database_access():
    with pytest.raises(HTTPException) as error:
        await vote_radio(None, 1, 0)
    assert error.value.status_code == 422
