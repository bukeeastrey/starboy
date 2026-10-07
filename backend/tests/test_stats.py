"""The aggregation pipelines, checked against the seed data.

Uses a separate database ("starboy_test") on your Atlas cluster, so your real
data is never touched. Skipped if MONGODB_URI isn't set."""

import asyncio
import os

import pytest

os.environ["MONGODB_DB"] = "starboy_test"

from app import db, stats  # noqa: E402
from app.config import Settings  # noqa: E402
from scripts import seed  # noqa: E402

pytestmark = pytest.mark.skipif(not Settings().mongodb_uri, reason="MONGODB_URI is not set")


async def seeded_results():
    # Settings are read when the app is imported, so point them at the test DB.
    db.settings.mongodb_db = "starboy_test"
    db.connect()
    try:
        await seed.run()
        pitch = await db.get_db().pitches.find_one({"name": seed.PITCH_NAME, "seed": True})
        players = await stats.pitch_players(pitch["_id"])
        boards = await stats.leaderboards(pitch["_id"])
        return {p["name"]: p for p in players}, boards
    finally:
        db.close()


@pytest.fixture(scope="module")
def results():
    return asyncio.run(seeded_results())


def test_player_totals(results):
    players, _ = results
    assert players["Tunde Bello"]["goals"] == 3      # 2 + 1 + 0
    assert players["Tunde Bello"]["assists"] == 1
    assert players["Bayo Ogun"]["goals"] == 5        # 2 + 0 + 3
    assert players["Chukwuemeka Obi"]["assists"] == 3
    assert players["Sani Musa"]["appearances"] == 3
    assert players["Tunde Bello"]["wins"] == 1       # team A won only the first game
    assert players["Dayo Akin"]["saves"] == 12       # 4 + 2 + 6


def test_leaderboards(results):
    _, boards = results
    assert boards["golden_boot"][0]["name"] == "Bayo Ogun"
    assert boards["golden_boot"][0]["goals"] == 5
    assert boards["playmaker"][0]["name"] == "Chukwuemeka Obi"
    assert len(boards["most_consistent"]) == 10
    assert all(row["goals"] > 0 for row in boards["golden_boot"])
    assert "phone" not in str(boards)
