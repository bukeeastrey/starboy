"""Turns what a player said into checked stats.

Gemma reads the transcript, but this code has the last word: every number is
range-checked, big numbers must really appear in the transcript, and names must
belong to players in the game. That is how "the LLM never invents numbers"."""

import difflib
import re

from . import llm, prompts

RESULTS = ("won", "lost", "draw")
MAX_STAT = 20

# Words that mean a number, including football slang.
WORD_VALUES = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20,
    "twice": 2, "double": 2, "brace": 2, "couple": 2, "pair": 2, "both": 2,
    "thrice": 3, "hattrick": 3, "treble": 3,
}


# --- Shape and range checks ----------------------------------------------

def clean_int(value) -> int | None:
    """A whole number from 0 to 20, or None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value)
    if isinstance(value, int) and 0 <= value <= MAX_STAT:
        return value
    return None


def clean_stats(raw: dict) -> dict:
    """Keep only the fields we know, with safe values. Used both for Gemma's
    answer and for the card the player edits and submits."""
    result = raw.get("result") if raw.get("result") in RESULTS else None

    score = None
    if isinstance(raw.get("score"), dict):
        us, them = clean_int(raw["score"].get("us")), clean_int(raw["score"].get("them"))
        if us is not None and them is not None:
            score = {"us": us, "them": them}
    # The result and the score must agree: the winners have the bigger number.
    if score and ((result == "won" and score["us"] < score["them"])
                  or (result == "lost" and score["us"] > score["them"])):
        score = {"us": score["them"], "them": score["us"]}

    clean_sheet = raw.get("clean_sheet") if isinstance(raw.get("clean_sheet"), bool) else None
    if clean_sheet and score and score["them"] > 0:
        clean_sheet = False  # they scored, so it wasn't a clean sheet

    highlight = " ".join(str(raw.get("highlight") or "").split()[:15])[:120]

    return {
        "goals": clean_int(raw.get("goals")),
        "assists": clean_int(raw.get("assists")),
        "saves": clean_int(raw.get("saves")),
        "clean_sheet": clean_sheet,
        "result": result,
        "score": score,
        "highlight": highlight,
    }


# --- "Did the player really say that number?" ------------------------------

def numbers_said(transcript: str) -> set[int]:
    """Every number in the transcript, as digits ("5-3") or words ("brace")."""
    text = re.sub(r"hat[\s-]*trick", "hattrick", transcript.lower())
    found = set()
    for token in re.findall(r"[a-z]+|\d+", text):
        if token.isdigit():
            found.add(int(token))
        elif token in WORD_VALUES:
            found.add(WORD_VALUES[token])
    return found


def is_grounded(value: int | None, said: set[int]) -> bool:
    """0 and 1 are often said without a number ("I no score", "I got the
    winner"), so they pass. From 2 up, the number must be in the transcript."""
    return value is None or value <= 1 or value in said


# --- Names ---------------------------------------------------------------

def match_player(name: str, players: list[dict]) -> dict | None:
    """Find the player in this game that a spoken name refers to, if any."""
    wanted = name.strip().lower()
    if len(wanted) < 2:
        return None

    # Every way each player might be called: full name, each word of it, nickname.
    labels = {}
    for player in players:
        for label in [player["name"], player.get("nickname", ""), *player["name"].split()]:
            if label:
                labels.setdefault(label.lower(), player)

    if wanted in labels:
        return labels[wanted]
    # "Emeka" for "Chukwuemeka": one is inside the other.
    for label, player in labels.items():
        if len(wanted) >= 3 and len(label) >= 3 and (wanted in label or label in wanted):
            return player
    # Small spelling differences from the transcription ("Tunday" for "Tunde").
    close = difflib.get_close_matches(wanted, list(labels), n=1, cutoff=0.7)
    return labels[close[0]] if close else None


# --- The whole step ------------------------------------------------------

async def extract_stats(transcript: str, players: list[dict]) -> dict:
    """Ask Gemma for the stats, then check them. `players` are the OTHER players
    in the game, as {"id", "name", "nickname"}.
    Returns {"stats": {...}, "unclear": ["...", ...]}."""
    names = [player["name"] for player in players]
    raw = await llm.chat_json(prompts.EXTRACT_SYSTEM,
                              prompts.extract_user_message(transcript, names))
    stats = clean_stats(raw)
    unclear = [str(note)[:120] for note in raw.get("unclear") or [] if note][:5]

    # Drop any number of 2 or more that the player never said.
    said = numbers_said(transcript)
    for field in ("goals", "assists", "saves"):
        if not is_grounded(stats[field], said):
            stats[field] = None
            unclear.append(f"how many {field}")
    if stats["score"] and not (is_grounded(stats["score"]["us"], said)
                               and is_grounded(stats["score"]["them"], said)):
        stats["score"] = None
        unclear.append("the score")

    # Keep only the names that belong to players in this game.
    assisted = []
    for name in raw.get("assisted_players") or []:
        player = match_player(str(name), players)
        if player is None:
            unclear.append(f"who “{str(name)[:30]}” is")
        elif player["id"] not in [p["id"] for p in assisted]:
            assisted.append({"id": player["id"], "name": player["name"]})
    stats["assisted_players"] = assisted

    return {"stats": stats, "unclear": unclear}
