"""Player stats and leaderboards, computed by MongoDB aggregation pipelines.

What counts (CLAUDE.md 3.6):
- appearance: the player was "in" and sent a report that wasn't disputed.
  Someone who added themselves after kickoff ("I played") also needs at
  least one teammate's confirm.
- goals, assists, wins, saves, clean sheets: CONFIRMED reports only.
"""

from bson import ObjectId

from .db import get_db
from .results import DEFENDING_MIDPOINT

STAT_FIELDS = ["appearances", "goals", "assists", "wins", "saves", "clean_sheets", "wall"]
ZERO_STATS = {field: 0 for field in STAT_FIELDS}

# The four boards on a pitch page: (key, stat it ranks by).
BOARDS = [
    ("most_consistent", "appearances"),
    ("golden_boot", "goals"),
    ("playmaker", "assists"),
    ("most_wins", "wins"),
    ("the_wall", "wall"),
    ("most_motm", "motm"),
]


def _claims_with_games(match_game: dict) -> list[dict]:
    """Pipeline stages: every report (not disputed) joined with its game,
    keeping only games that match `match_game` (e.g. one pitch)."""
    return [
        {"$match": {"status": {"$in": ["pending", "confirmed"]}}},
        {"$lookup": {"from": "games", "localField": "game_id", "foreignField": "_id", "as": "game"}},
        {"$unwind": "$game"},
        {"$match": {"game.status": {"$ne": "cancelled"}, **match_game}},
        # This player's own entry on the game's invite list.
        {"$addFields": {"invite": {"$arrayElemAt": [
            {"$filter": {"input": "$game.invites", "cond": {"$eq": ["$$this.user_id", "$user_id"]}}}, 0,
        ]}}},
        {"$addFields": {
            "is_confirmed": {"$eq": ["$status", "confirmed"]},
            # Did this player win? From the game's final score when the
            # creator entered one (were they on the creator's side or the
            # other?), otherwise from what the player said in their report.
            "won": {"$cond": [
                {"$ifNull": ["$game.result", False]},
                {"$cond": [
                    {"$in": ["$user_id", {"$ifNull": ["$game.result.team_a", []]}]},
                    {"$gt": ["$game.result.us", "$game.result.them"]},
                    {"$gt": ["$game.result.them", "$game.result.us"]},
                ]},
                {"$eq": ["$stats.result", "won"]},
            ]},
            # Blocks + tackles: each bucket counts as its middle value.
            "defending_points": {"$switch": {
                "branches": [
                    {"case": {"$eq": ["$stats.defending", bucket]}, "then": points}
                    for bucket, points in DEFENDING_MIDPOINT.items()
                ],
                "default": 0,
            }},
            "counts_appearance": {"$and": [
                {"$eq": ["$invite.status", "in"]},
                {"$or": [
                    {"$ne": ["$invite.self_added", True]},
                    {"$gte": [{"$size": "$confirmations"}, 1]},
                ]},
            ]},
        }},
    ]


def _sum_if_confirmed(expression) -> dict:
    return {"$sum": {"$cond": ["$is_confirmed", expression, 0]}}


# Adds up one player's reports into their totals.
_TOTALS = {
    "appearances": {"$sum": {"$cond": ["$counts_appearance", 1, 0]}},
    "goals": _sum_if_confirmed({"$ifNull": ["$stats.goals", 0]}),
    "assists": _sum_if_confirmed({"$ifNull": ["$stats.assists", 0]}),
    "wins": _sum_if_confirmed({"$cond": ["$won", 1, 0]}),
    "wall": _sum_if_confirmed("$defending_points"),
    "saves": _sum_if_confirmed({"$ifNull": ["$stats.saves", 0]}),
    "clean_sheets": _sum_if_confirmed({"$cond": [{"$eq": ["$stats.clean_sheet", True]}, 1, 0]}),
}

# Public fields of a user, as a pipeline projection (never phone or PIN).
_PUBLIC_USER = {
    "_id": 0,
    "id": {"$toString": "$user._id"},
    "name": "$user.name",
    "nickname": {"$ifNull": ["$user.nickname", ""]},
    "position": {"$ifNull": ["$user.position", "Anywhere"]},
    "photo": {"$cond": [
        {"$ifNull": ["$user.avatar_photo_id", False]},
        {"$concat": ["/api/photos/", {"$toString": "$user.avatar_photo_id"}, "/thumb"]},
        None,
    ]},
}


async def totals_by_player(match_game: dict) -> dict[ObjectId, dict]:
    """{user_id: {appearances, goals, ...}} for the games matching `match_game`."""
    pipeline = _claims_with_games(match_game) + [
        {"$group": {"_id": "$user_id", **_TOTALS}},
    ]
    rows = await get_db().claims.aggregate(pipeline).to_list(None)
    return {row.pop("_id"): row for row in rows}


async def motm_by_player(match_game: dict) -> dict[ObjectId, int]:
    """{user_id: games where they were voted Man of the Match}.

    Counted in one pipeline: add up the votes per game and player, find each
    game's top player, keep it only if they are clear of second place (a tie
    means nobody won), then count the wins per player."""
    pipeline = [
        {"$match": {"status": {"$in": ["pending", "confirmed"]}, "motm_vote_id": {"$ne": None}}},
        {"$lookup": {"from": "games", "localField": "game_id", "foreignField": "_id", "as": "game"}},
        {"$unwind": "$game"},
        {"$match": {"game.status": {"$ne": "cancelled"}, **match_game}},
        {"$group": {"_id": {"game": "$game_id", "player": "$motm_vote_id"}, "votes": {"$sum": 1}}},
        {"$sort": {"votes": -1}},
        {"$group": {"_id": "$_id.game", "winner": {"$first": "$_id.player"}, "counts": {"$push": "$votes"}}},
        {"$match": {"$expr": {"$or": [
            {"$eq": [{"$size": "$counts"}, 1]},
            {"$gt": [{"$arrayElemAt": ["$counts", 0]}, {"$arrayElemAt": ["$counts", 1]}]},
        ]}}},
        {"$group": {"_id": "$winner", "motm": {"$sum": 1}}},
    ]
    rows = await get_db().claims.aggregate(pipeline).to_list(None)
    return {row["_id"]: row["motm"] for row in rows}


async def player_totals(user_id: ObjectId) -> dict:
    """One player's totals across every pitch (for their player card)."""
    totals = (await totals_by_player({})).get(user_id, ZERO_STATS)
    motm = (await motm_by_player({})).get(user_id, 0)
    return {**totals, "motm": motm}


async def pitch_players(pitch_id: ObjectId) -> list[dict]:
    """Everyone registered at a pitch, with their stats there."""
    pipeline = [
        {"$match": {"pitch_id": pitch_id}},
        {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        {"$project": {**_PUBLIC_USER, "user_id": "$user._id"}},
        {"$sort": {"name": 1}},
    ]
    players = await get_db().registrations.aggregate(pipeline).to_list(None)
    totals = await totals_by_player({"game.pitch_id": pitch_id})
    motm = await motm_by_player({"game.pitch_id": pitch_id})
    return [
        {**{k: v for k, v in player.items() if k != "user_id"},
         **totals.get(player["user_id"], ZERO_STATS),
         "motm": motm.get(player["user_id"], 0)}
        for player in players
    ]


async def leaderboards(pitch_id: ObjectId, limit: int = 10) -> dict:
    """The pitch's four leaderboards in ONE pipeline: $facet runs a ranking
    for each board over the same totals."""
    pipeline = _claims_with_games({"game.pitch_id": pitch_id}) + [
        {"$group": {"_id": "$user_id", **_TOTALS}},
        {"$lookup": {"from": "users", "localField": "_id", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        {"$project": {**_PUBLIC_USER, **{field: 1 for field in STAT_FIELDS}}},
        {"$facet": {
            board: [
                {"$match": {stat: {"$gt": 0}}},
                {"$sort": {stat: -1, "appearances": -1, "name": 1}},
                {"$limit": limit},
            ]
            for board, stat in BOARDS if board != "most_motm"
        }},
    ]
    result = await get_db().claims.aggregate(pipeline).to_list(None)
    boards = result[0] if result else {board: [] for board, _ in BOARDS}

    # Most MOTM comes from the votes, not from the players' own totals.
    players = await pitch_players(pitch_id)
    winners = sorted((p for p in players if p["motm"] > 0), key=lambda p: (-p["motm"], p["name"]))
    boards["most_motm"] = winners[:limit]
    return boards


async def player_pitch_stats(user_id: ObjectId) -> list[dict]:
    """One player's totals at every pitch they've played, most games first."""
    pipeline = _claims_with_games({}) + [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$game.pitch_id", **_TOTALS}},
        {"$lookup": {"from": "pitches", "localField": "_id", "foreignField": "_id", "as": "pitch"}},
        {"$unwind": "$pitch"},
        {"$project": {"_id": 0, "pitch": {"id": {"$toString": "$pitch._id"}, "name": "$pitch.name"},
                      **{field: 1 for field in STAT_FIELDS}}},
        {"$sort": {"appearances": -1}},
    ]
    return await get_db().claims.aggregate(pipeline).to_list(None)
