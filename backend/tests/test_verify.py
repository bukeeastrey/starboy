"""Number verification: Gemma may only use numbers that are in the facts."""

from app.settle import build_table, facts_text, template_verdict
from app.summary import collect_facts, facts_text as summary_facts, template_summary
from app.verify import invented_numbers, numbers_in

TABLE = """Players: Tunde vs Bayo
Stat | Tunde | Bayo
Games played | 3 | 3
Goals | 3 | 5
Goals per game | 1 | 1.67
Win rate | 33% | 67%"""


def test_numbers_in():
    assert numbers_in("We won 5-3, 1.50 per game, 67%") == [5, 3, 1.5, 67]
    assert numbers_in("He scored five") == [5]
    assert numbers_in("the two of you, one more thing") == []  # everyday words


def test_verdict_using_only_table_numbers_passes():
    verdict = "Bayo takes it with 5 goals against 3, and a 67% win rate over 3 games."
    assert invented_numbers(verdict, TABLE) == []


def test_formatting_differences_are_fine():
    assert invented_numbers("That is 1.670 goals per game and 3.0 goals.", TABLE) == []


def test_invented_number_is_caught():
    assert invented_numbers("Bayo scored 7 goals.", TABLE) == [7]
    assert invented_numbers("Tunde has four assists.", TABLE) == [4]
    assert invented_numbers("That is 2 more goals.", TABLE) == [2]  # maths is not allowed either


def report(game_id, goals, assists, result, us, them):
    return {"game_id": game_id, "stats": {"goals": goals, "assists": assists, "result": result,
                                          "score": {"us": us, "them": them}}}


A = [report(1, 2, 0, "won", 5, 3), report(2, 1, 0, "draw", 2, 2), report(3, 0, 1, "lost", 1, 4)]
B = [report(1, 2, 0, "lost", 3, 5), report(2, 0, 1, "draw", 2, 2), report(3, 3, 0, "won", 4, 1)]


def test_table_and_template_verdict_agree():
    table = {row["label"]: (row["a"], row["b"]) for row in build_table(A, B)}
    assert table["Goals"] == ("3", "5")
    assert table["Goals per game"] == ("1", "1.67")
    assert table["Win rate"] == ("33%", "33%")
    assert table["Current win streak"] == ("0", "1")
    assert table["Games both played"] == ("3", "3")
    assert table["Wins against each other"] == ("1", "1")
    # The fallback verdict itself must pass the same check.
    facts = facts_text("Tunde", "Bayo", "Parklane, all time", build_table(A, B))
    verdict = template_verdict("Tunde", "Bayo", A, B)
    assert "Bayo takes it" in verdict
    assert invented_numbers(verdict, facts) == []


def test_summary_facts_and_template():
    from datetime import datetime, timezone
    game = {"kickoff_at": datetime(2026, 10, 9, 16, 0, tzinfo=timezone.utc)}
    users = {1: {"name": "Tunde Bello", "nickname": ""}, 2: {"name": "Chukwuemeka Obi", "nickname": "Emeka"}}
    claims = [
        {"user_id": 1, "status": "confirmed", "stats": {"goals": 2, "assists": 0, "score": {"us": 5, "them": 3}}},
        {"user_id": 2, "status": "pending", "stats": {"goals": 1, "assists": 2, "score": {"us": 3, "them": 5}}},
    ]
    facts = collect_facts(game, {"name": "Parklane"}, claims, users)
    assert facts["score"] == "5-3"
    assert facts["goals"] == "Tunde 2, Emeka 1 (pending)"
    assert facts["assists"] == "Emeka 2 (pending)"
    assert invented_numbers(template_summary(facts), summary_facts(facts)) == []


def test_the_code_picks_a_clear_winner():
    from app.settle import decide, verdict_is_clear
    decision = decide(build_table(A, B))
    # Bayo leads in goals, goals per game and win streak; Tunde leads in nothing.
    assert decision["winner"] == "b"
    assert "Goals" in decision["leads_b"] and decision["leads_a"] == []
    assert "DECISION: Bayo wins." in facts_text("Tunde", "Bayo", "Parklane, all time", build_table(A, B))
    # The same numbers on both sides is the only time it is a draw.
    assert decide(build_table(A, A))["winner"] == "draw"
    assert verdict_is_clear("Bayo takes it with 5 goals.", "Bayo")
    assert not verdict_is_clear("Honestly this is a draw, though Bayo has 5 goals.", "Bayo")
    assert not verdict_is_clear("Tunde has the spirit.", "Bayo")


def test_numbers_must_belong_to_the_right_player():
    from app.settle import numbers_belong
    table = build_table(A, B)  # Tunde: 3 goals, streak 0. Bayo: 5 goals, streak 1.
    assert numbers_belong("Bayo wins it. Bayo has 5 goals and 1.67 goals per game.", "Tunde", "Bayo", table)
    # The 1 is Bayo's streak, not Tunde's.
    assert not numbers_belong("Tunde is still king of the current win streak with 1.", "Tunde", "Bayo", table)
    assert not numbers_belong("Tunde scored 5 goals.", "Tunde", "Bayo", table)
    # A sentence naming both players can't be checked, so it passes.
    assert numbers_belong("Bayo has 5 goals to Tunde's 3 goals.", "Tunde", "Bayo", table)
    assert numbers_belong("Tunde, keep your head up!", "Tunde", "Bayo", table)
