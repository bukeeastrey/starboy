""""You played like...": the code picks the legend from the stats."""

import random

from app.played_like import LEGENDS, QUIET_LINES, facts_text, kind_of_game, line_is_ok, pick
from app.verify import invented_numbers


def test_kind_of_game_follows_the_rules_in_order():
    assert kind_of_game({"goals": 3}) == "hat_trick"
    assert kind_of_game({"goals": 4, "assists": 2}) == "hat_trick"
    assert kind_of_game({"goals": 2, "assists": 1}) == "brace"
    assert kind_of_game({"goals": 1, "assists": 1}) == "goal_and_assist"
    assert kind_of_game({"goals": 1, "assists": 2}) == "goal_and_assist"
    assert kind_of_game({"goals": 0, "assists": 2}) == "playmaker"
    assert kind_of_game({"goals": 0, "assists": 0, "defending": "6+"}) == "wall"
    assert kind_of_game({"goals": 0, "saves": 4}) == "keeper"
    assert kind_of_game({"goals": 0, "saves": 1, "clean_sheet": True}) == "keeper"


def test_quiet_game_gets_a_gentle_line_and_no_legend():
    for stats in ({}, {"goals": 1}, {"assists": 1}, {"defending": "3-5"}, {"saves": 3, "clean_sheet": False}):
        assert kind_of_game(stats) == "quiet"
    chosen = pick({"goals": 0})
    assert chosen["name"] is None and chosen["line"] in QUIET_LINES


def test_pick_is_from_the_right_pool():
    for _ in range(20):
        assert pick({"goals": 3})["name"] in LEGENDS["hat_trick"]
        assert pick({"goals": 2})["name"] in ("Nwankwo Kanu", "Thierry Henry")


def test_pick_does_not_repeat_the_last_legend():
    rng = random.Random(1)
    for _ in range(30):
        assert pick({"goals": 2}, avoid="Nwankwo Kanu", rng=rng)["name"] == "Thierry Henry"


def test_template_lines_use_only_the_players_numbers():
    stats = {"goals": 4, "assists": 0}
    chosen = pick(stats)
    assert invented_numbers(chosen["line"], facts_text("Tunde", chosen, stats)) == []


def test_line_checks():
    assert line_is_ok("2 goals, cool as you like on a Friday.", "Nwankwo Kanu")
    assert line_is_ok("Kanu himself would clap for those 2 goals.", "Nwankwo Kanu")
    assert not line_is_ok("Even Messi would be jealous of that.", "Nwankwo Kanu")
    assert not line_is_ok("Line one.\nLine two.", "Nwankwo Kanu")
    assert not line_is_ok("", "Nwankwo Kanu")
    assert not line_is_ok("x" * 200, "Nwankwo Kanu")
