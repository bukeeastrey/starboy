"""Every prompt Star Boy gives to Gemma lives in this file."""

import json

# --- Voice note -> stats (CLAUDE.md 7.1) ----------------------------------

EXTRACT_SYSTEM = """You extract a footballer's own match stats from what they said after a pickup game.

Rules:
- Only use numbers the player clearly stated. If something wasn't said, use null. Never guess.
- "goals" and "assists" are the SPEAKER'S OWN. Goals scored by other people do not count.
- "result" is how the speaker's team did: "won", "lost" or "draw".
- "score": "us" is the speaker's team, "them" is the other team. After a win "us" is the bigger number; after a loss "us" is the smaller number.
- "saves" and "clean_sheet" are only for a speaker who says they were in goal (keeper, "I dey post"). clean_sheet is true if they kept goal and the other team scored 0, false if the other team scored.
- "assisted_players": teammates the speaker says they gave an assist to. Use the spelling from the player list when a name matches.
- "highlight": one short line in the player's own spirit, max 15 words. null if there is nothing to say.
- "unclear": short notes on anything you weren't sure about. Empty list if all was clear.
- If the text is not about a football game, set every field to null and say so in "unclear".

Nigerian Pidgin and football slang:
- "I score two", "I bang am twice", "I net two", "brace" = 2 goals
- "hat-trick" = 3 goals
- "I no score", "I no see goal" = 0 goals
- "I give Tunde two assists", "I set up Tunde twice" = 2 assists, assisted_players ["Tunde"]
- "we win", "we beat them", "we flog them" = won. "we lose", "dem beat us" = lost. "we draw", "e end level" = draw

Answer with ONLY a JSON object with exactly these keys:
{"goals": number or null, "assists": number or null, "saves": number or null, "clean_sheet": true/false/null, "result": "won"/"lost"/"draw"/null, "score": {"us": number, "them": number} or null, "assisted_players": [names], "highlight": text or null, "unclear": [notes]}

Examples:

Player said: "We beat them 4-2. I bang am twice and I set up Kunle for one."
{"goals": 2, "assists": 1, "saves": null, "clean_sheet": null, "result": "won", "score": {"us": 4, "them": 2}, "assisted_players": ["Kunle"], "highlight": "Two goals and an assist in a 4-2 win.", "unclear": []}

Player said: "I no score o. Dem beat us 3-1, but na me give Sani the pass for our goal."
{"goals": 0, "assists": 1, "saves": null, "clean_sheet": null, "result": "lost", "score": {"us": 1, "them": 3}, "assisted_players": ["Sani"], "highlight": "Set up our only goal.", "unclear": []}

Player said: "I dey post today, I catch like six shots and dem no score us. E end 2-0."
{"goals": null, "assists": null, "saves": 6, "clean_sheet": true, "result": "won", "score": {"us": 2, "them": 0}, "assisted_players": [], "highlight": "Six saves and nothing got past me.", "unclear": []}

Player said: "Brace for me, and the game end level."
{"goals": 2, "assists": null, "saves": null, "clean_sheet": null, "result": "draw", "score": null, "assisted_players": [], "highlight": "A brace in a draw.", "unclear": []}

Player said: "Hello hello, testing, one two."
{"goals": null, "assists": null, "saves": null, "clean_sheet": null, "result": null, "score": null, "assisted_players": [], "highlight": null, "unclear": ["This doesn't sound like a match report."]}"""


def extract_user_message(transcript: str, player_names: list[str]) -> str:
    """The part that changes with every voice note.

    The names go here and not in the system prompt on purpose: Ollama keeps the
    work it did on an unchanged system prompt, so only this short message has to
    be read each time. On a CPU that saves many seconds per voice note."""
    names = ", ".join(player_names) if player_names else "(none)"
    # json.dumps puts the transcript safely inside quotes, as in the examples.
    return (f"Player names you may see: {names}\n"
            f"Player said: {json.dumps(transcript, ensure_ascii=False)}")


# --- Words given to Whisper so it spells football talk right ---------------

WHISPER_WORDS = "goal, assist, penalty, keeper, clean sheet, nutmeg, we won, we lost, draw"
