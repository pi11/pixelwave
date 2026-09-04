from app import catalog
from app.audius import _is_instrumental as is_audius_instrumental
from app.audius import _license_url, _matches_speed
from app.auth import valid_credentials
from app.config import settings
from app.jamendo import _is_instrumental
from app.main import app
from app.ratings import wilson_score
from app.routes import _slug, _words, router


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
    assert "/admin" in paths
    assert "/health" in paths
    assert "/api/tracks/{track_id}/vote" in paths


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
