"""The final score (entered by the creator), sides, and the MOTM vote."""

from app.results import motm_winner, result_for
from app.util import stat_line

CREATOR, MATE, RIVAL = "creator", "mate", "rival"
GAME = {"result": {"us": 5, "them": 3, "team_a": [CREATOR, MATE]}}


def test_result_comes_from_the_games_score():
    assert result_for(GAME, CREATOR) == ("won", {"us": 5, "them": 3})
    assert result_for(GAME, MATE) == ("won", {"us": 5, "them": 3})
    # Everyone not on the creator's side was on the other side.
    assert result_for(GAME, RIVAL) == ("lost", {"us": 3, "them": 5})


def test_the_games_score_beats_what_a_player_said():
    said = {"result": "won", "score": {"us": 9, "them": 0}}
    assert result_for(GAME, RIVAL, said) == ("lost", {"us": 3, "them": 5})


def test_without_a_score_the_players_report_is_used():
    said = {"result": "draw", "score": {"us": 2, "them": 2}}
    assert result_for({}, RIVAL, said) == ("draw", {"us": 2, "them": 2})
    assert result_for({}, RIVAL, {}) == (None, None)


def test_draw():
    game = {"result": {"us": 2, "them": 2, "team_a": [CREATOR]}}
    assert result_for(game, CREATOR)[0] == "draw"
    assert result_for(game, RIVAL)[0] == "draw"


def vote(for_whom, status="pending"):
    return {"motm_vote_id": for_whom, "status": status}


def test_motm_majority_wins():
    assert motm_winner([vote("emeka"), vote("emeka"), vote("tunde")]) == "emeka"
    assert motm_winner([vote("emeka")]) == "emeka"


def test_motm_tie_or_no_votes_is_nobody():
    assert motm_winner([vote("emeka"), vote("tunde")]) is None
    assert motm_winner([vote(None), {"status": "pending"}]) is None
    assert motm_winner([]) is None


def test_motm_ignores_disputed_reports():
    assert motm_winner([vote("emeka"), vote("tunde", "disputed"), vote("tunde", "disputed")]) == "emeka"


def test_stat_line_with_defending():
    assert stat_line({"goals": 2, "assists": 1, "defending": "3-5"}) == "2 goals · 1 assist · 3–5 blocks/tackles"
    assert stat_line({"goals": 0, "assists": 0, "defending": "0"}) == "0 goals · 0 assists"
