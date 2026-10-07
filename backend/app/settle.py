""""Settle it": who has been better, Player A or Player B?

The code builds the comparison table from CONFIRMED stats. Gemma only writes
the verdict's words, and verify.py checks it used no number of its own."""

from bson import ObjectId

from . import jobs, prompts, verify
from .db import get_db
from .util import display_name

MIN_GAMES = 2
NOT_ENOUGH = "Not enough confirmed games to settle this yet. Play more! ⚽"


async def confirmed_reports(user_id: ObjectId, match_game: dict) -> list[dict]:
    """A player's confirmed reports in scope, oldest game first."""
    pipeline = [
        {"$match": {"user_id": user_id, "status": "confirmed"}},
        {"$lookup": {"from": "games", "localField": "game_id", "foreignField": "_id", "as": "game"}},
        {"$unwind": "$game"},
        {"$match": {"game.status": {"$ne": "cancelled"}, **match_game}},
        {"$sort": {"game.kickoff_at": 1}},
        {"$project": {"game_id": 1, "stats": 1}},
    ]
    return await get_db().claims.aggregate(pipeline).to_list(None)


def per_game(total: int, games: int) -> str:
    """'1.5' or '0.67': at most 2 decimals, no trailing zeros."""
    return f"{total / games:.2f}".rstrip("0").rstrip(".") if games else "0"


def totals(reports: list[dict]) -> dict:
    stats = [report["stats"] for report in reports]
    streak = 0
    for report in reversed(stats):  # newest game first
        if report.get("result") != "won":
            break
        streak += 1
    return {
        "games": len(stats),
        "wins": sum(1 for s in stats if s.get("result") == "won"),
        "goals": sum(s.get("goals") or 0 for s in stats),
        "assists": sum(s.get("assists") or 0 for s in stats),
        "saves": sum(s.get("saves") or 0 for s in stats),
        "clean_sheets": sum(1 for s in stats if s.get("clean_sheet")),
        "streak": streak,
    }


def head_to_head(reports_a: list[dict], reports_b: list[dict]) -> dict:
    """Games both played. They were on opposite teams when one won and the
    other lost (teams aren't recorded, so that is how we can tell)."""
    by_game_b = {report["game_id"]: report["stats"] for report in reports_b}
    together = a_wins = b_wins = 0
    for report in reports_a:
        other = by_game_b.get(report["game_id"])
        if other is None:
            continue
        together += 1
        results = (report["stats"].get("result"), other.get("result"))
        if results == ("won", "lost"):
            a_wins += 1
        elif results == ("lost", "won"):
            b_wins += 1
    return {"together": together, "a_wins": a_wins, "b_wins": b_wins}


def build_table(reports_a: list[dict], reports_b: list[dict]) -> list[dict]:
    """The comparison table: rows of {"label", "a", "b"} (values are text)."""
    a, b = totals(reports_a), totals(reports_b)

    def row(label, value_a, value_b):
        return {"label": label, "a": str(value_a), "b": str(value_b)}

    rows = [
        row("Games played", a["games"], b["games"]),
        row("Wins", a["wins"], b["wins"]),
        row("Goals", a["goals"], b["goals"]),
        row("Assists", a["assists"], b["assists"]),
    ]
    if a["games"] > 1 or b["games"] > 1:
        rows += [
            row("Goals per game", per_game(a["goals"], a["games"]), per_game(b["goals"], b["games"])),
            row("Assists per game", per_game(a["assists"], a["games"]), per_game(b["assists"], b["games"])),
            row("Win rate", f"{round(100 * a['wins'] / a['games'])}%", f"{round(100 * b['wins'] / b['games'])}%"),
            row("Current win streak", a["streak"], b["streak"]),
        ]
    if a["saves"] or b["saves"] or a["clean_sheets"] or b["clean_sheets"]:
        rows += [row("Saves", a["saves"], b["saves"]),
                 row("Clean sheets", a["clean_sheets"], b["clean_sheets"])]

    h2h = head_to_head(reports_a, reports_b)
    if h2h["together"] and (a["games"] > 1 or b["games"] > 1):
        rows.append(row("Games both played", h2h["together"], h2h["together"]))
        if h2h["a_wins"] or h2h["b_wins"]:
            rows.append(row("Wins against each other", h2h["a_wins"], h2h["b_wins"]))
    return rows


def facts_text(name_a: str, name_b: str, scope: str, table: list[dict]) -> str:
    """What Gemma gets: the two names, the scope and the table. Nothing else."""
    lines = [f"Players: {name_a} vs {name_b}", f"Scope: {scope}", "", f"Stat | {name_a} | {name_b}"]
    lines += [f"{row['label']} | {row['a']} | {row['b']}" for row in table]
    return "\n".join(lines)


def template_verdict(name_a: str, name_b: str, reports_a: list[dict], reports_b: list[dict]) -> str:
    """The plain verdict used if Gemma fails or invents a number twice."""
    a, b = totals(reports_a), totals(reports_b)

    def line(name, t):
        return (f"{name}: {t['goals']} goals, {t['assists']} assists and {t['wins']} wins "
                f"in {t['games']} {'game' if t['games'] == 1 else 'games'}.")

    points_a = a["goals"] + a["assists"] + a["wins"]
    points_b = b["goals"] + b["assists"] + b["wins"]
    numbers = f"{line(name_a, a)} {line(name_b, b)}"
    if points_a == points_b:
        return f"Too close to call: na draw. {numbers} Settle it on the pitch. ⚽"
    winner, loser = (name_a, name_b) if points_a > points_b else (name_b, name_a)
    return f"{winner} takes it on the numbers. {numbers} {loser}, the pitch is waiting for your reply. ⚽"


def names_for(user_a: dict, user_b: dict) -> tuple[str, str]:
    """Short names, unless both would be the same ("Tunde" vs "Tunde")."""
    name_a, name_b = display_name(user_a), display_name(user_b)
    if name_a.lower() == name_b.lower():
        return user_a["name"], user_b["name"]
    return name_a, name_b


async def compare(user_a: dict, user_b: dict, pitch: dict, game: dict | None) -> dict:
    """Build the table for a scope. Returns {"enough": False} when there
    aren't enough confirmed games, otherwise the table plus what the job needs."""
    if game:
        match, needed = {"game._id": game["_id"]}, 1
    else:
        match, needed = {"game.pitch_id": pitch["_id"]}, MIN_GAMES
    reports_a = await confirmed_reports(user_a["_id"], match)
    reports_b = await confirmed_reports(user_b["_id"], match)
    if len(reports_a) < needed or len(reports_b) < needed:
        return {"enough": False}

    name_a, name_b = names_for(user_a, user_b)
    table = build_table(reports_a, reports_b)
    return {
        "enough": True,
        "names": {"a": name_a, "b": name_b},
        "table": table,
        "fallback": template_verdict(name_a, name_b, reports_a, reports_b),
    }


@jobs.handler("verdict")
async def write_verdict(job: dict) -> dict:
    """The AI job: Gemma writes the verdict from the table, then we verify it."""
    data = job["input"]
    await jobs.set_stage(job["_id"], "thinking")
    return await verify.write_with_facts(prompts.SETTLE_SYSTEM, data["facts"],
                                         lambda: data["fallback"])
