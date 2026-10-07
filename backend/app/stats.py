"""Player stats and leaderboards, computed by MongoDB aggregation pipelines.

What counts (CLAUDE.md 3.6):
- appearance: the player was "in" and sent a report that wasn't disputed.
  Someone who added themselves after kickoff ("I played") also needs at
  least one teammate's confirm.
- goals, assists, wins, saves, clean sheets: CONFIRMED reports only.
"""

from bson import ObjectId

from .db import get_db

STAT_FIELDS = ["appearances", "goals", "assists", "wins", "saves", "clean_sheets"]
ZERO_STATS = {field: 0 for field in STAT_FIELDS}

# The four boards on a pitch page: (key, stat it ranks by).
BOARDS = [
    ("most_consistent", "appearances"),
    ("golden_boot", "goals"),
    ("playmaker", "assists"),
    ("most_wins", "wins"),
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
    "wins": _sum_if_confirmed({"$cond": [{"$eq": ["$stats.result", "won"]}, 1, 0]}),
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
}


async def totals_by_player(match_game: dict) -> dict[ObjectId, dict]:
    """{user_id: {appearances, goals, ...}} for the games matching `match_game`."""
    pipeline = _claims_with_games(match_game) + [
        {"$group": {"_id": "$user_id", **_TOTALS}},
    ]
    rows = await get_db().claims.aggregate(pipeline).to_list(None)
    return {row.pop("_id"): row for row in rows}


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
    return [
        {**{k: v for k, v in player.items() if k != "user_id"},
         **totals.get(player["user_id"], ZERO_STATS)}
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
            for board, stat in BOARDS
        }},
    ]
    result = await get_db().claims.aggregate(pipeline).to_list(None)
    return result[0] if result else {board: [] for board, _ in BOARDS}


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
