"""Moments: which highlights a report and a record earn (rules only, no database)."""

from app.moments import from_report, milestones, ordinal


def kinds(stats):
    return [kind for kind, _, _ in from_report({"stats": stats}, "Tunde")]


def test_goals():
    assert kinds({"goals": 3}) == ["hat_trick"]
    assert kinds({"goals": 2}) == ["brace"]
    assert kinds({"goals": 1}) == []
    assert from_report({"stats": {"goals": 3}}, "Tunde")[0][1:] == ("Hat-trick", "Tunde scored 3 in one game.")
    assert from_report({"stats": {"goals": 5}}, "Tunde")[0][1] == "5 goals"


def test_keeper_and_defender():
    assert kinds({"goals": 0, "clean_sheet": True}) == ["clean_sheet"]
    assert kinds({"goals": 0, "clean_sheet": False}) == []
    assert kinds({"goals": 0, "defending": "6+"}) == ["wall"]
    assert kinds({"goals": 0, "defending": "3-5"}) == []


def test_one_report_can_earn_several():
    assert kinds({"goals": 2, "defending": "6+"}) == ["brace", "wall"]


def test_appearance_milestones():
    assert [m[1] for m in milestones("Tunde", 10, 0, 0)] == ["10th game"]
    assert [m[1] for m in milestones("Tunde", 25, 0, 0)] == ["25th game"]
    assert milestones("Tunde", 11, 0, 0) == []


def test_goal_milestones_only_when_crossed_in_this_game():
    assert [m[1] for m in milestones("Tunde", 7, 10, 1)] == ["10 goals"]   # 9 before, 10 now
    assert [m[1] for m in milestones("Tunde", 7, 11, 3)] == ["10 goals"]   # 8 before, 11 now
    assert milestones("Tunde", 7, 12, 1) == []                             # was already past 10
    assert milestones("Tunde", 7, 9, 2) == []


def test_ordinal():
    assert [ordinal(n) for n in (1, 2, 3, 4, 10, 11, 12, 13, 21, 22, 25, 50)] == [
        "1st", "2nd", "3rd", "4th", "10th", "11th", "12th", "13th", "21st", "22nd", "25th", "50th"]
