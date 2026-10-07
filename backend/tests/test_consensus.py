"""The confirmation rules (CLAUDE.md 3.6)."""

from datetime import timedelta

from app.consensus import decide, numbers_add_up, required_confirms

FRESH = timedelta(hours=1)
OLD = timedelta(hours=73)


def test_required_confirms():
    assert required_confirms(2) == 2
    assert required_confirms(6) == 2
    assert required_confirms(7) == 3
    assert required_confirms(10) == 4


def test_confirmed_when_enough_confirms():
    assert decide(confirms=2, disputes=0, players_in=6, age=FRESH) == "confirmed"
    assert decide(confirms=3, disputes=1, players_in=9, age=FRESH) == "confirmed"


def test_pending_until_enough():
    assert decide(confirms=1, disputes=0, players_in=6, age=FRESH) == "pending"
    assert decide(confirms=3, disputes=0, players_in=10, age=FRESH) == "pending"  # needs 4


def test_more_confirms_than_disputes_needed():
    assert decide(confirms=2, disputes=2, players_in=6, age=FRESH) == "disputed"


def test_disputed_needs_two_disputes():
    assert decide(confirms=0, disputes=1, players_in=6, age=FRESH) == "pending"
    assert decide(confirms=0, disputes=2, players_in=6, age=FRESH) == "disputed"
    assert decide(confirms=1, disputes=2, players_in=6, age=FRESH) == "disputed"


def test_auto_confirm_after_72_hours():
    assert decide(confirms=1, disputes=0, players_in=2, age=OLD) == "confirmed"
    assert decide(confirms=1, disputes=0, players_in=2, age=FRESH) == "pending"
    assert decide(confirms=0, disputes=0, players_in=2, age=OLD) == "pending"
    assert decide(confirms=1, disputes=1, players_in=6, age=OLD) == "pending"


def claim(goals, us, them):
    return {"stats": {"goals": goals, "score": {"us": us, "them": them}}}


def test_numbers_add_up():
    team_a = [claim(2, 5, 3), claim(3, 5, 3)]
    team_b = [claim(3, 3, 5)]
    assert numbers_add_up(team_a + team_b)
    assert not numbers_add_up(team_a + [claim(1, 5, 3)])  # 6 goals, but they scored 5
    assert not numbers_add_up([claim(4, 3, 5)])  # 4 goals for a team that scored 3


def test_numbers_add_up_draw_and_missing_score():
    assert numbers_add_up([claim(2, 2, 2), claim(2, 2, 2)])  # both teams, 4 goals in all
    assert not numbers_add_up([claim(3, 2, 2), claim(2, 2, 2)])
    assert numbers_add_up([{"stats": {"goals": 9, "score": None}}])
