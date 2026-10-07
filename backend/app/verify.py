"""Checks that Gemma only used numbers we gave it.

Gemma writes the words of a verdict or a game summary, but every number in
its text must already be in the facts that the code computed. If it isn't,
we ask once more, and after that use a plain template instead."""

import logging
import re
from typing import Callable

from . import llm

log = logging.getLogger("starboy.verify")

# Number words we check too. "one" and "two" are left out: they are everyday
# words ("the two of you", "one more thing"), not stats.
WORD_VALUES = {
    "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}


def numbers_in(text: str) -> list[float]:
    """Every number in a text: digits ("5-3" gives 5 and 3, "1.50" gives 1.5)
    and spelled-out words from three to twenty."""
    found = [float(match) for match in re.findall(r"\d+(?:\.\d+)?", text)]
    found += [float(WORD_VALUES[word]) for word in re.findall(r"[a-z]+", text.lower())
              if word in WORD_VALUES]
    return found


def invented_numbers(text: str, facts: str) -> list[float]:
    """Numbers in `text` that do not appear in `facts`. Empty list = all good.
    Comparing as numbers means 1.5 and 1.50 are the same."""
    allowed = set(numbers_in(facts))
    return [number for number in numbers_in(text) if number not in allowed]


async def write_with_facts(system: str, facts: str, fallback: Callable[[], str],
                           max_tokens: int = 220) -> dict:
    """Let Gemma write from the facts; verify; retry once; else use the template.
    Returns {"text": ..., "source": "gemma" or "template"}."""
    for attempt in (1, 2):
        try:
            text = (await llm.chat(system, facts, temperature=0.6, max_tokens=max_tokens)).strip()
        except Exception as error:
            log.warning("Gemma failed (attempt %d): %s", attempt, type(error).__name__)
            continue
        bad = invented_numbers(text, facts)
        if text and not bad:
            return {"text": text, "source": "gemma"}
        log.warning("Gemma used numbers that are not in the facts (attempt %d): %s", attempt, bad)
    return {"text": fallback(), "source": "template"}
