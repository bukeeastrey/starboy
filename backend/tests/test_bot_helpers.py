"""Small pieces of the Telegram bot that need no database or network."""

from datetime import timedelta

from app import botgames, botmenu, botmore, flows, pictures


def test_parse_time_understands_how_people_type_times():
    assert botgames.parse_time("5pm") == "17:00"
    assert botgames.parse_time("5:30 PM") == "17:30"
    assert botgames.parse_time("7.30am") == "07:30"
    assert botgames.parse_time("17:30") == "17:30"
    assert botgames.parse_time("12am") == "00:00"
    assert botgames.parse_time("12pm") == "12:00"


def test_parse_time_refuses_unclear_times():
    assert botgames.parse_time("5") is None        # morning or evening?
    assert botgames.parse_time("25:00") is None
    assert botgames.parse_time("13pm") is None
    assert botgames.parse_time("5:75pm") is None
    assert botgames.parse_time("evening") is None


def test_clock_labels():
    assert [botgames.clock(t) for t in ("07:00", "17:00", "07:30", "00:00", "12:00")] == ["7am", "5pm", "7:30am", "12am", "12pm"]


def test_calendar_only_offers_days_from_today():
    today = botgames.today()
    grid = botgames.month_grid(f"{today:%Y-%m}")
    assert [label for label, _ in grid[1]] == ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    days = {label: action for row in grid[2:] for label, action in row}
    assert days[str(today.day)] == f"ng:d:{today}"                 # today can be picked
    yesterday = today - timedelta(days=1)
    if yesterday.month == today.month:
        assert str(yesterday.day) not in days                      # yesterday shows as a dot
    assert all(len(row) == 7 for row in grid[2:])                  # every week has 7 cells
    assert all(len(action.encode()) <= 64 for row in grid for _, action in row)  # Telegram's limit


def test_every_menu_button_has_an_action():
    for row in botmenu.MENU_ROWS:
        for label in row:
            assert botmenu.action_for(label), label
    assert botmenu.action_for("/newgame") == "newgame"
    assert botmenu.action_for("/mygames@starboy_soccerbot") == "mygames"
    assert botmenu.action_for("we won 5-3") is None
    assert botmenu.action_for("/start") is None  # handled before the menu


def test_back_and_cancel_are_on_every_step():
    assert flows.nav("ng") == [("⬅️ Back", "ng:back"), ("✖️ Cancel", "x")]
    assert flows.nav("ng", back=False) == [("✖️ Cancel", "x")]
    flow = {"step": "a", "history": []}
    flows.go(flow, "b")
    flows.go(flow, "c")
    assert flows.back(flow) and flow["step"] == "b"
    assert flows.back(flow) and flow["step"] == "a"
    assert not flows.back(flow)  # already at the first step


def test_versus_table_lines_up():
    table = [{"label": "Goals", "a": "5", "b": "3"}, {"label": "Goals per game", "a": "1.67", "b": "1"}]
    lines = botmore.versus_table({"a": "Ada", "b": "Bola"}, table).split("\n")
    assert len({len(line.rstrip()) <= 35 for line in lines}) == 1
    assert "Goals per game" in lines[2] and lines[2].strip().startswith("1.67")


def test_pictures_are_real_pngs_of_the_right_size():
    from io import BytesIO
    from PIL import Image
    poster = Image.open(BytesIO(pictures.poster("Parklane Football Pitch", "Sat 10 Oct, 5:00 pm", ["Tunde", "Emeka"])))
    assert poster.size == (1080, 1920) and poster.format == "PNG"
    card = Image.open(BytesIO(pictures.player_card(
        "A Very Long Name Indeed Okonkwo", "", "Anywhere", "abc", [("GLS", 0)] * 6, [], None, 0)))
    assert card.size == (900, 1360)
