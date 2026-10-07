"""When reminders go out, and the catch-up rule after the server was asleep."""

from datetime import datetime, timedelta, timezone

from app.scheduler import due_times, what_to_do

UTC = timezone.utc
# Friday 9 Oct 2026, 5:00 pm in Lagos = 16:00 UTC. Set up three days earlier.
KICKOFF = datetime(2026, 10, 9, 16, 0, tzinfo=UTC)
GAME = {"kickoff_at": KICKOFF, "duration_min": 90, "created_at": KICKOFF - timedelta(days=3)}


def test_due_times():
    due = due_times(GAME)
    assert due["night_before"] == datetime(2026, 10, 8, 19, 0, tzinfo=UTC)  # 8 pm Lagos
    assert due["nudge"] == KICKOFF - timedelta(hours=6)
    assert due["two_hours"] == KICKOFF - timedelta(hours=2)
    assert due["post_game"] == KICKOFF + timedelta(minutes=105)


def test_wait_then_send():
    due = due_times(GAME)["two_hours"]
    assert what_to_do("two_hours", due, GAME, due - timedelta(minutes=1)) == "wait"
    assert what_to_do("two_hours", due, GAME, due + timedelta(minutes=1)) == "send"


def test_catch_up_after_sleeping():
    due = due_times(GAME)["post_game"]
    assert what_to_do("post_game", due, GAME, due + timedelta(minutes=90)) == "send"
    assert what_to_do("post_game", due, GAME, due + timedelta(hours=3)) == "skip"


def test_no_pre_game_reminder_after_kickoff():
    due = due_times(GAME)["two_hours"]
    assert what_to_do("two_hours", due, GAME, KICKOFF + timedelta(minutes=5)) == "skip"


def test_game_created_late_or_in_the_past():
    late = {**GAME, "created_at": KICKOFF - timedelta(hours=1)}
    for kind in ("night_before", "nudge", "two_hours"):
        assert what_to_do(kind, due_times(late)[kind], late, KICKOFF - timedelta(minutes=30)) == "skip"
    # Logged after it was played: the post-game question still goes out.
    logged = {**GAME, "created_at": KICKOFF + timedelta(minutes=100)}
    due = due_times(logged)["post_game"]
    assert what_to_do("post_game", due, logged, due + timedelta(minutes=1)) == "send"
