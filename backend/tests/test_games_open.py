"""Every game must be reachable: past, upcoming and cancelled.

Creates three games through the real API and checks that each one is listed
with its OWN id, opens its OWN page, and that the pitch page puts each in the
right section. Uses the "starboy_test" database (see conftest.py)."""

import random
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import notify
from app.config import FRONTEND_DIST, settings
from app.main import app

WAT = timezone(timedelta(hours=1))
pytestmark = pytest.mark.skipif(not settings.mongodb_uri, reason="MONGODB_URI is not set")


@pytest.fixture(scope="module")
def site():
    """The app, running in-process, with a freshly signed-up player and a new pitch."""
    with TestClient(app) as client:
        phone = "0805" + "".join(random.choice("0123456789") for _ in range(7))
        client.post("/api/auth/signup", json={"name": "Open Tester", "phone": phone, "pin": "1234"}).raise_for_status()
        pitch = client.post("/api/pitches", json={"name": f"Open Test Pitch {random.randint(0, 99999)}"}).json()

        def new_game(days_from_now: int, time: str) -> dict:
            day = datetime.now(WAT) + timedelta(days=days_from_now)
            response = client.post(f"/api/pitches/{pitch['id']}/games",
                                   json={"date": day.strftime("%Y-%m-%d"), "time": time})
            response.raise_for_status()
            return response.json()

        games = {
            "past": new_game(-3, "17:00"),
            "upcoming": new_game(+2, "16:00"),
            "cancelled": new_game(+4, "07:00"),
        }
        client.post(f"/api/games/{games['cancelled']['id']}/cancel").raise_for_status()
        yield client, pitch, games


def test_three_games_have_three_different_ids(site):
    _, _, games = site
    assert len({game["id"] for game in games.values()}) == 3


def test_each_game_opens_its_own_page(site):
    client, _, games = site
    for kind, game in games.items():
        opened = client.get(f"/api/games/{game['id']}")
        assert opened.status_code == 200, kind
        assert opened.json()["id"] == game["id"], kind
        assert opened.json()["kickoff_label"] == game["kickoff_label"], kind
    assert client.get(f"/api/games/{games['cancelled']['id']}").json()["status"] == "cancelled"


def test_pitch_page_lists_every_game_in_the_right_section(site):
    client, pitch, games = site
    listed = client.get(f"/api/pitches/{pitch['id']}").json()["games"]
    assert [game["id"] for game in listed["upcoming"]] == [games["upcoming"]["id"]]
    # Past = played or cancelled, newest kickoff first. Nothing is left out.
    assert [game["id"] for game in listed["past"]] == [games["cancelled"]["id"], games["past"]["id"]]
    assert listed["past_total"] == 2


def test_load_more_pages_through_past_games(site):
    client, pitch, games = site
    first = client.get(f"/api/pitches/{pitch['id']}/games?skip=0").json()
    rest = client.get(f"/api/pitches/{pitch['id']}/games?skip=1").json()
    assert first["total"] == 2
    assert [game["id"] for game in rest["games"]] == [games["past"]["id"]]
    assert client.get(f"/api/pitches/{pitch['id']}/games?skip=2").json()["games"] == []


def test_home_lists_past_and_upcoming_games(site):
    client, _, games = site
    home = client.get("/api/home").json()
    assert games["upcoming"]["id"] in [game["id"] for game in home["next_games"]]
    assert games["past"]["id"] in [game["id"] for game in home["recent_games"]]


@pytest.mark.skipif(not FRONTEND_DIST.is_dir(), reason="the frontend isn't built (npm run build)")
def test_game_address_works_after_a_reload(site):
    """Typing an old game's address (or reloading on it) must serve the app."""
    client, _, games = site
    for game in games.values():
        page = client.get(f"/game/{game['id']}")
        assert page.status_code == 200
        assert '<div id="root">' in page.text


def test_unknown_game_is_a_clean_404(site):
    client, _, _ = site
    assert client.get("/api/games/000000000000000000000000").status_code == 404
    assert client.get("/api/games/not-an-id").status_code == 404


def test_telegram_buttons_point_at_the_right_game():
    """Each "Open game" button carries the id of the game it was made for."""
    settings.public_base_url = "https://starboy.example"
    try:
        for game_id in ("aaaaaaaaaaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbbbbbbbbbb"):
            rows = notify.rsvp_buttons(game_id)
            assert rows[0] == [("I'm in ✅", f"r:i:{game_id}"), ("Can't make it ❌", f"r:o:{game_id}")]
            assert rows[1] == [("Open game", f"https://starboy.example/game/{game_id}")]
            assert notify.open_button(f"/game/{game_id}", "Open game") == [
                [("Open game", f"https://starboy.example/game/{game_id}")]]
    finally:
        settings.public_base_url = ""
