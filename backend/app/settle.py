""""Settle it": who has been better, Player A or Player B?

The code builds the comparison table from CONFIRMED stats. Gemma only writes
the verdict's words, and verify.py checks it used no number of its own."""

import re

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


# Rows that say how much someone played, not how well. They don't decide anything.
NOT_DECIDING = ("Games played", "Games both played")


def decide(table: list[dict]) -> dict:
    """Who wins? Decided here in code, so the verdict is always clear and the
    same numbers always give the same winner. Gemma only explains it.

    Each stat a player leads in is one point. If the points are level, total
    goals + assists breaks the tie. Only if that is level too is it a draw.
    Returns {"winner": "a" | "b" | "draw", "leads_a": [labels], "leads_b": [labels]}."""
    def number(text: str) -> float:
        return float(text.rstrip("%"))

    values = {row["label"]: (number(row["a"]), number(row["b"])) for row in table}
    leads_a = [label for label, (a, b) in values.items() if a > b and label not in NOT_DECIDING]
    leads_b = [label for label, (a, b) in values.items() if b > a and label not in NOT_DECIDING]

    points_a, points_b = len(leads_a), len(leads_b)
    if points_a == points_b:
        points_a = values["Goals"][0] + values["Assists"][0]
        points_b = values["Goals"][1] + values["Assists"][1]
    winner = "a" if points_a > points_b else "b" if points_b > points_a else "draw"
    return {"winner": winner, "leads_a": leads_a, "leads_b": leads_b}


def facts_text(name_a: str, name_b: str, scope: str, table: list[dict]) -> str:
    """What Gemma gets: the names, the scope, the table and the decision. Nothing else."""
    decision = decide(table)
    lines = [f"Players: {name_a} vs {name_b}", f"Scope: {scope}", "", f"Stat | {name_a} | {name_b}"]
    lines += [f"{row['label']} | {row['a']} | {row['b']}" for row in table]
    lines += [
        "",
        f"{name_a} leads in: {', '.join(decision['leads_a']) or 'nothing'}",
        f"{name_b} leads in: {', '.join(decision['leads_b']) or 'nothing'}",
    ]
    if decision["winner"] == "draw":
        lines.append("DECISION: it is a draw.")
    else:
        lines.append(f"DECISION: {name_a if decision['winner'] == 'a' else name_b} wins.")
    return "\n".join(lines)


def verdict_is_clear(text: str, winner_name: str | None) -> bool:
    """The verdict must name the winner the code picked, and not hedge."""
    lowered = text.lower()
    if "decision" in lowered:
        return False  # it copied our instruction line instead of writing its own
    if winner_name is None:
        return "draw" in lowered
    return winner_name.lower() in lowered and "draw" not in lowered


def numbers_belong(text: str, name_a: str, name_b: str, table: list[dict]) -> bool:
    """Is each number given to the right player?

    verify.py only knows a number is somewhere in the table. This catches
    "Tunde has 5 goals" when the 5 is Bayo's. It looks at each sentence that
    names exactly ONE player, a stat and some numbers: that player's own value
    for the stat must be among the numbers."""
    # Longest labels first, so "Goals per game" isn't read as "Goals".
    rows = sorted(table, key=lambda row: -len(row["label"]))
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        lowered = sentence.lower()
        has_a, has_b = name_a.lower() in lowered, name_b.lower() in lowered
        if has_a == has_b:
            continue  # both players or neither: can't tell whose number it is
        said = verify.numbers_in(sentence)
        if not said:
            continue
        for row in rows:
            label = row["label"].lower()
            if label not in lowered:
                continue
            lowered = lowered.replace(label, " ")
            own_value = float((row["a"] if has_a else row["b"]).rstrip("%"))
            if own_value not in said:
                return False
    return True


def template_verdict(name_a: str, name_b: str, reports_a: list[dict], reports_b: list[dict]) -> str:
    """The plain verdict used if Gemma fails, hedges or invents a number twice."""
    a, b = totals(reports_a), totals(reports_b)
    winner = decide(build_table(reports_a, reports_b))["winner"]

    def line(name, t):
        return (f"{name}: {t['goals']} goals, {t['assists']} assists and {t['wins']} wins "
                f"in {t['games']} {'game' if t['games'] == 1 else 'games'}.")

    numbers = f"{line(name_a, a)} {line(name_b, b)}"
    if winner == "draw":
        return f"Too close to call: na draw. {numbers} Settle it on the pitch. ⚽"
    best, other = (name_a, name_b) if winner == "a" else (name_b, name_a)
    return f"{best} takes it on the numbers. {numbers} {other}, the pitch is waiting for your reply. ⚽"


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
        "winner": decide(table)["winner"],
        "fallback": template_verdict(name_a, name_b, reports_a, reports_b),
    }


@jobs.handler("verdict")
async def write_verdict(job: dict) -> dict:
    """The AI job: Gemma writes the verdict from the table, then we verify it."""
    data = job["input"]
    await jobs.set_stage(job["_id"], "thinking")
    return await verify.write_with_facts(
        prompts.SETTLE_SYSTEM, data["facts"], lambda: data["fallback"],
        also_check=lambda text: (
            verdict_is_clear(text, data.get("winner_name"))
            and numbers_belong(text, data["names"]["a"], data["names"]["b"], data["table"])))
