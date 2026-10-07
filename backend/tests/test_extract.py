"""The code checks on what Gemma extracts (no AI needed to run these)."""

from app.extract import clean_stats, is_grounded, match_player, numbers_said

PLAYERS = [
    {"id": "1", "name": "Chukwuemeka Obi", "nickname": "Emeka"},
    {"id": "2", "name": "Tunde Bello", "nickname": ""},
]


def test_numbers_said():
    assert numbers_said("We won 5-3, I scored two") >= {5, 3, 2}
    assert 3 in numbers_said("Hat-trick! We draw")
    assert 2 in numbers_said("I bang am twice")
    assert 2 in numbers_said("Brace for me")


def test_grounding():
    said = numbers_said("We won 5-3, I scored two")
    assert is_grounded(2, said)
    assert is_grounded(1, said)  # 1 and 0 can be said without a number
    assert is_grounded(None, said)
    assert not is_grounded(4, said)


def test_clean_stats_ranges_and_types():
    stats = clean_stats({"goals": 25, "assists": "2", "saves": True, "result": "maybe",
                         "clean_sheet": "yes", "highlight": "a " * 30})
    assert stats["goals"] is None
    assert stats["assists"] == 2
    assert stats["saves"] is None
    assert stats["result"] is None
    assert stats["clean_sheet"] is None
    assert len(stats["highlight"].split()) == 15


def test_clean_stats_score_follows_result():
    assert clean_stats({"result": "won", "score": {"us": 3, "them": 5}})["score"] == {"us": 5, "them": 3}
    assert clean_stats({"result": "lost", "score": {"us": 2, "them": 1}})["score"] == {"us": 1, "them": 2}
    stats = clean_stats({"clean_sheet": True, "score": {"us": 1, "them": 1}})
    assert stats["clean_sheet"] is False


def test_match_player():
    assert match_player("Emeka", PLAYERS)["id"] == "1"
    assert match_player("chukwuemeka", PLAYERS)["id"] == "1"
    assert match_player("Tunday", PLAYERS)["id"] == "2"
    assert match_player("Messi", PLAYERS) is None
