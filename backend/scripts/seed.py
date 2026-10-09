"""Demo data: one pitch, 10 players and 3 played games with confirmed stats,
so the leaderboards and "Settle it" have something to show.

Demo data never goes into the real database. It goes into its own database,
"starboy_demo", on the same Atlas cluster. From the backend folder:

    python scripts/seed.py             fill the demo database
    python scripts/seed.py --remove    empty it again

To look at it, start the app on the demo database:

    $env:MONGODB_DB = "starboy_demo"; .\run.ps1

(Close that window afterwards: a new window is back on the real database.)
Every demo player can sign in with phone 0800 000 00XX (01 to 10) and PIN 1234.
"""

import asyncio
import sys
from datetime import timedelta
from pathlib import Path

# Let this script import the app (it lives one folder up).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402
from app import moments, photos, played_like  # noqa: E402
from app.auth import hash_pin  # noqa: E402
from app.util import WAT, now  # noqa: E402

DEMO_DATABASE = "starboy_demo"
PITCH_NAME = "Star Boy Demo Pitch"

# name, nickname, position. The first five are team A, the rest team B.
PLAYERS = [
    ("Tunde Bello", "", "FWD"),
    ("Chukwuemeka Obi", "Emeka", "MID"),
    ("Sani Musa", "", "DEF"),
    ("Kunle Adeyemi", "", "MID"),
    ("Ifeanyi Okafor", "Ify", "GK"),
    ("Bayo Ogun", "", "FWD"),
    ("Femi Lawal", "", "MID"),
    ("Uche Nwosu", "", "DEF"),
    ("Dayo Akin", "", "GK"),
    ("Musa Ibrahim", "", "Anywhere"),
]
TEAM_A = range(0, 5)

# Blocks + tackles for the two defenders (player index: bucket), every game.
DEFENDING = {2: "6+", 7: "3-5"}
# Who most players voted Man of the Match in each game (player index).
# In the second game the vote is split, so nobody wins it.
MOTM = [0, None, 5]

# Each game: days ago, score (team A, team B), {player index: (goals, assists)},
# and keeper saves {player index: saves}.
GAMES = [
    (7, (5, 3), {0: (2, 0), 1: (2, 1), 2: (1, 0), 3: (0, 2), 4: (0, 1),
                 5: (2, 0), 6: (1, 0), 7: (0, 1)}, {4: 3, 8: 4}),
    (4, (2, 2), {0: (1, 0), 3: (1, 0), 1: (0, 2), 6: (1, 0), 9: (1, 0), 5: (0, 1)}, {4: 5, 8: 2}),
    (2, (1, 4), {1: (1, 0), 0: (0, 1), 5: (3, 0), 7: (1, 0), 6: (0, 2), 9: (0, 1)}, {4: 2, 8: 6}),
]


def phone(i: int) -> str:
    return f"+2348000000{i + 1:03d}"


async def remove() -> int:
    """Delete the demo pitch, the demo players and everything that hangs off
    them. Nothing else is touched. Returns how many demo players were removed."""
    database = db.get_db()
    phones = [phone(i) for i in range(len(PLAYERS))]
    old_users = [u["_id"] for u in await database.users.find({"phone": {"$in": phones}}).to_list(None)]
    old_pitch = await database.pitches.find_one({"name": PITCH_NAME, "seed": True})
    if old_pitch:
        old_games = await database.games.distinct("_id", {"pitch_id": old_pitch["_id"]})
        await database.claims.delete_many({"game_id": {"$in": old_games}})
        for photo in await database.photos.find({"game_id": {"$in": old_games}}).to_list(None):
            await photos.remove(photo)
        await database.games.delete_many({"pitch_id": old_pitch["_id"]})
        await database.registrations.delete_many({"pitch_id": old_pitch["_id"]})
        await database.moments.delete_many({"pitch_id": old_pitch["_id"]})
        await database.pitches.delete_one({"_id": old_pitch["_id"]})
    await database.claims.delete_many({"user_id": {"$in": old_users}})
    await database.registrations.delete_many({"user_id": {"$in": old_users}})
    await database.jobs.delete_many({"input.user_id": {"$in": old_users}})
    await database.users.delete_many({"_id": {"$in": old_users}})
    return len(old_users)


async def run() -> None:
    database = db.get_db()
    phones = [phone(i) for i in range(len(PLAYERS))]

    # 1. Remove the old demo data.
    await remove()

    # 2. The pitch and its players.
    pin_hash = hash_pin("1234")
    users = [
        {"name": name, "nickname": nick, "phone": phones[i], "position": pos,
         "pin_hash": pin_hash, "created_at": now()}
        for i, (name, nick, pos) in enumerate(PLAYERS)
    ]
    await database.users.insert_many(users)
    ids = [u["_id"] for u in users]

    pitch = {"name": PITCH_NAME, "area": "Demo data (scripts/seed.py)", "maps_url": "",
             "sport": "football", "created_by": ids[0], "created_at": now(), "seed": True}
    await database.pitches.insert_one(pitch)
    await database.registrations.insert_many(
        [{"pitch_id": pitch["_id"], "user_id": uid, "created_at": now()} for uid in ids]
    )

    # 3. The games, each with a confirmed report from all 10 players.
    for number, (days_ago, (score_a, score_b), contributions, saves) in enumerate(GAMES):
        kickoff = (now().astimezone(WAT) - timedelta(days=days_ago)).replace(
            hour=17, minute=0, second=0, microsecond=0)
        game = {
            "pitch_id": pitch["_id"], "sport": "football", "kickoff_at": kickoff,
            "duration_min": 90, "note": "", "created_by": ids[0], "status": "scheduled",
            "invites": [{"user_id": uid, "status": "in", "responded_at": kickoff} for uid in ids],
            "reminders_sent": {"night_before": True, "two_hours": True, "nudge": True, "post_game": True},
            "summary": None, "flags": [], "created_at": kickoff,
            # The final score, from the creator's side (team A), and who was on it.
            "result": {"us": score_a, "them": score_b, "team_a": [ids[i] for i in TEAM_A]},
        }
        await database.games.insert_one(game)

        claims = []
        for i, uid in enumerate(ids):
            us, them = (score_a, score_b) if i in TEAM_A else (score_b, score_a)
            goals, assists = contributions.get(i, (0, 0))
            result = "won" if us > them else "lost" if us < them else "draw"
            teammates = [ids[j] for j in range(len(ids)) if j != i][:3]
            # The MOTM vote: for the game's star (the star votes for a teammate);
            # in the split game, half vote for player 0 and half for player 5.
            star = MOTM[number] if MOTM[number] is not None else (0 if i % 2 else 5)
            vote = ids[star] if star != i else teammates[0]
            stats = {
                "goals": goals, "assists": assists,
                "saves": saves.get(i), "clean_sheet": (them == 0) if i in saves else None,
                "defending": DEFENDING.get(i),
                "result": result, "score": {"us": us, "them": them},
                "highlight": "", "assisted_players": [], "motm_vote": None,
            }
            claims.append({
                "game_id": game["_id"], "user_id": uid, "transcript": "(demo data)",
                "stats": stats, "source": "buttons", "motm_vote_id": vote,
                "played_like": played_like.pick(stats),
                "status": "confirmed", "confirmations": teammates, "disputes": [],
                "created_at": kickoff + timedelta(hours=2),
                "confirmed_at": kickoff + timedelta(hours=5),
            })
        await database.claims.insert_many(claims)
        await moments.refresh_game(game["_id"])

    print(f"Seeded '{PITCH_NAME}' in database '{database.name}': {len(ids)} players, {len(GAMES)} games.")
    print("Sign in as any of them: phone 0800 000 0001 (to 0010), PIN 1234.")


async def main() -> None:
    # Point the app's database setting at the demo database, never the real one.
    db.settings.mongodb_db = DEMO_DATABASE
    db.connect()
    try:
        if "--remove" in sys.argv:
            count = await remove()
            print(f"Removed the demo pitch and {count} demo players from '{db.get_db().name}'.")
        else:
            await run()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
