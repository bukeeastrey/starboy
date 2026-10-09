"""Pictures the bot sends: the matchday poster and the player card.

Drawn with Pillow in the same "floodlights at night" look as the website:
near-black green, chalk lines, one gold accent, Anton for the big type.
The fonts are files in app/assets/fonts (both under the Open Font License)."""

import io
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).parent / "assets" / "fonts"

NIGHT = (5, 13, 9)
TURF = (10, 26, 19)
TURF_LIT = (20, 53, 36)
CHALK = (241, 244, 238)
DIM = (154, 172, 161)
GOLD = (245, 197, 24)
RED = (255, 107, 91)
LINE = (241, 244, 238, 40)  # chalk at low opacity

# The same colours the website gives avatars (picked from the player's id).
AVATAR_COLOURS = [(14, 90, 58), (180, 69, 31), (31, 95, 180), (122, 63, 176),
                  (176, 134, 63), (31, 138, 138), (176, 63, 108), (74, 107, 31)]


@lru_cache(maxsize=64)
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """name is "Anton", "Barlow", "Barlow-SemiBold" or "Barlow-Bold"."""
    file = {"Anton": "Anton-Regular.ttf", "Barlow": "Barlow-Regular.ttf"}.get(name, f"{name}.ttf")
    return ImageFont.truetype(str(FONTS / file), size)


def spaced(draw: ImageDraw.ImageDraw, xy, text: str, fnt, fill, spacing: int, anchor: str = "ls") -> None:
    """Text with extra space between the letters (for small capital labels)."""
    x, y = xy
    if anchor[0] == "m":  # centred: start half the total width to the left
        x -= (sum(draw.textlength(ch, font=fnt) for ch in text) + spacing * (len(text) - 1)) / 2
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill, anchor="l" + anchor[1])
        x += draw.textlength(ch, font=fnt) + spacing


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> list[str]:
    """Break text into lines that fit a width."""
    lines, line = [], ""
    for word in text.split():
        longer = f"{line} {word}".strip()
        if line and draw.textlength(longer, font=fnt) > max_width:
            lines.append(line)
            line = word
        else:
            line = longer
    return lines + ([line] if line else [])


def night_sky(width: int, height: int, glow=(40, 110, 76), strength: float = 0.75) -> Image.Image:
    """The background: near-black green with a floodlight glow from the top.
    The glow is drawn tiny and stretched, which is fast and perfectly smooth."""
    small = Image.new("RGB", (48, 84), NIGHT)
    pixels = small.load()
    for y in range(84):
        for x in range(48):
            distance = math.hypot((x - 24) / 48 * width, (y + 4) / 84 * height) / (height * 0.68)
            t = max(0.0, 1 - distance) * strength
            pixels[x, y] = tuple(round(NIGHT[i] + (glow[i] - NIGHT[i]) * t) for i in range(3))
    return small.resize((width, height), Image.BICUBIC).convert("RGBA")


def _cubic(p0, p1, p2, p3, steps: int = 18) -> list[tuple[float, float]]:
    """Points along a curve (a cubic Bezier), for drawing the crest's shield."""
    points = []
    for i in range(1, steps + 1):
        t = i / steps
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
        points.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                       a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return points


def _shield(inset: float = 0.0) -> list[tuple[float, float]]:
    """The crest's outline on a 64 x 72 grid (the same path as crest.svg)."""
    if inset:  # the thin chalk line inside the rim
        return ([(32, 9.5), (52.5, 15.6), (52.5, 36)] + _cubic((52.5, 36), (52.5, 47.7), (44.5, 56.3), (32, 62))
                + _cubic((32, 62), (19.5, 56.3), (11.5, 47.7), (11.5, 36)) + [(11.5, 15.6)])
    return ([(32, 3), (58, 11), (58, 36)] + _cubic((58, 36), (58, 51), (47.5, 61.5), (32, 68))
            + _cubic((32, 68), (16.5, 61.5), (6, 51), (6, 36)) + [(6, 11)])


STAR = [(32, 17), (35.14, 26.67), (45.32, 26.67), (37.09, 32.65), (40.23, 42.33), (32, 36.35),
        (23.77, 42.33), (26.91, 32.65), (18.68, 26.67), (28.86, 26.67)]


@lru_cache(maxsize=8)
def crest(width: int) -> Image.Image:
    """The Star Boy badge, `width` pixels wide. Drawn 4x too big and shrunk,
    which gives it smooth edges."""
    scale = width / 64 * 4
    image = Image.new("RGBA", (round(64 * scale), round(72 * scale)), (0, 0, 0, 0))
    # On an RGB picture, a draw in "RGBA" mode blends see-through colours in.
    draw = ImageDraw.Draw(image, "RGBA")
    at = lambda points: [(x * scale, y * scale) for x, y in points]  # noqa: E731
    outline = at(_shield())
    draw.polygon(outline, fill=(12, 31, 22))
    draw.line(outline + [outline[0]], fill=GOLD, width=round(3 * scale), joint="curve")
    inner = at(_shield(inset=1))
    draw.line(inner + [inner[0]], fill=(241, 244, 238, 115), width=max(1, round(0.9 * scale)), joint="curve")
    draw.polygon(at(STAR), fill=GOLD)
    chalk = (241, 244, 238, 180)
    draw.line(at([(19, 49.5), (45, 49.5)]), fill=chalk, width=max(1, round(1.1 * scale)))
    draw.arc([26 * scale, 43.5 * scale, 38 * scale, 55.5 * scale], 0, 180, fill=chalk, width=max(1, round(1.1 * scale)))
    return image.resize((width, round(width * 72 / 64)), Image.LANCZOS)


def png(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.convert("RGB").save(out, "PNG", optimize=True)
    return out.getvalue()


# --- The matchday poster ------------------------------------------------------

def poster(pitch_name: str, kickoff_label: str, names: list[str], note: str = "", site: str = "") -> bytes:
    """A tall picture (1080 x 1920, the WhatsApp Status shape) announcing a game.
    `kickoff_label` is like "Sat 10 Oct, 5:00 pm"; `names` are the players who are in."""
    width, height, margin = 1080, 1920, 90
    image = night_sky(width, height)
    lines = Image.new("RGBA", image.size, (0, 0, 0, 0))
    chalk = ImageDraw.Draw(lines)
    # Pitch markings: a touchline frame, and the centre circle at the bottom.
    chalk.rectangle([40, 40, width - 40, height - 40], outline=LINE, width=3)
    chalk.arc([width / 2 - 330, height - 370, width / 2 + 330, height + 290], 180, 360, fill=LINE, width=3)
    chalk.ellipse([width / 2 - 8, height - 48, width / 2 + 8, height - 32], fill=LINE)
    image = Image.alpha_composite(image, lines).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")  # "RGBA": see-through colours blend properly

    badge = crest(128)
    image.paste(badge, (margin, 110), badge)
    draw.text((margin + 160, 212), "STAR BOY", font=font("Anton", 76), fill=CHALK, anchor="ls")

    y = 440
    spaced(draw, (margin, y), "MATCHDAY", font("Barlow-Bold", 40), GOLD, 10)

    big = font("Anton", 150)
    y += 60
    for line in wrap(draw, pitch_name.upper(), big, width - margin * 2)[:3]:
        y += 150
        draw.text((margin, y), line, font=big, fill=CHALK, anchor="ls")

    day, _, time = kickoff_label.partition(", ")
    y += 150
    draw.text((margin, y), day.upper(), font=font("Anton", 104), fill=CHALK, anchor="ls")
    y += 128
    draw.text((margin, y), time.upper(), font=font("Anton", 128), fill=GOLD, anchor="ls")

    if note:
        y += 76
        note_font = font("Barlow-SemiBold", 40)
        draw.text((margin, y), wrap(draw, note, note_font, width - margin * 2)[0], font=note_font, fill=DIM, anchor="ls")

    y += 90
    draw.rectangle([margin, y, width - margin, y + 3], fill=(241, 244, 238, 40))
    y += 70
    spaced(draw, (margin, y), f"WHO'S IN ({len(names)})", font("Barlow-Bold", 34), DIM, 8)
    name_font = font("Anton", 58)
    shown = names[:12]
    for index, name in enumerate(shown):
        column, row = index % 2, index // 2
        draw.text((margin + column * 460, y + 86 + row * 78), name.upper()[:14], font=name_font, fill=CHALK, anchor="ls")
    if len(names) > len(shown):
        draw.text((margin, y + 86 + 6 * 78), f"+{len(names) - len(shown)} MORE", font=name_font, fill=GOLD, anchor="ls")

    draw.text((width / 2, height - 190), "YOU DEY COME?", font=font("Anton", 84), fill=GOLD, anchor="ms")
    if site:
        draw.text((width / 2, height - 120), site, font=font("Barlow-SemiBold", 34), fill=DIM, anchor="ms")
    return png(image)


# --- The player card ----------------------------------------------------------

FORM_COLOURS = {"won": GOLD, "lost": RED}
FORM_LETTERS = {"won": "W", "draw": "D", "lost": "L"}


def initials(name: str) -> str:
    return "".join(word[0].upper() for word in name.split()[:2] if word)


def player_card(name: str, nickname: str, position: str, player_id: str, numbers: list[tuple[str, int]],
                form: list[str | None], played_like: str | None, games: int,
                photo: bytes | None = None) -> bytes:
    """The collector's card, as a picture (900 x 1360).
    `numbers` is six (label, value) pairs; `form` is newest-first results."""
    width, height = 900, 1360
    notch_x, notch_y = round(width * 0.13), round(height * 0.085)
    shape = [(notch_x, 0), (width - notch_x, 0), (width, notch_y), (width, height), (0, height), (0, notch_y)]

    # The face: lit turf with a gold glow at the top and a centre circle at the bottom.
    face = night_sky(width, height, glow=(120, 110, 40), strength=0.55)
    face = Image.blend(face, Image.new("RGBA", face.size, TURF + (255,)), 0.35)
    lines = Image.new("RGBA", face.size, (0, 0, 0, 0))
    ImageDraw.Draw(lines).arc([width / 2 - 320, height - 250, width / 2 + 320, height + 390], 180, 360, fill=LINE, width=3)
    face = Image.alpha_composite(face, lines).convert("RGB")
    draw = ImageDraw.Draw(face, "RGBA")

    # Top left: the position, and how many games.
    corner = "ANY" if position == "Anywhere" else position
    draw.text((70, 190), corner, font=font("Anton", 118), fill=GOLD, anchor="ls")
    draw.line([(70, 212), (70 + 150, 212)], fill=(241, 244, 238, 60), width=2)
    spaced(draw, (70, 250), f"{games} {'GAME' if games == 1 else 'GAMES'}", font("Barlow-Bold", 30), CHALK, 5)
    badge = crest(84)
    face.paste(badge, (width - 70 - 84, 96), badge)

    # The avatar: their photo if they have one, otherwise initials on their colour.
    size, cx, cy = 300, width // 2, 330
    avatar = Image.new("RGBA", (size, size), AVATAR_COLOURS[sum(ord(ch) for ch in player_id) % len(AVATAR_COLOURS)] + (255,))
    if photo:
        try:
            picture = Image.open(io.BytesIO(photo)).convert("RGBA")
            side = min(picture.size)
            left, top = (picture.width - side) // 2, (picture.height - side) // 2
            avatar = picture.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
        except Exception:
            photo = None
    if not photo:
        ImageDraw.Draw(avatar).text((size / 2, size / 2), initials(name), font=font("Anton", 124), fill=(255, 255, 255), anchor="mm")
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size * 4, size * 4], fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    draw.ellipse([cx - size / 2 - 12, cy - size / 2 - 12, cx + size / 2 + 12, cy + size / 2 + 12], fill=GOLD)
    draw.ellipse([cx - size / 2 - 6, cy - size / 2 - 6, cx + size / 2 + 6, cy + size / 2 + 6], fill=TURF)
    face.paste(avatar, (cx - size // 2, cy - size // 2), mask)
    draw = ImageDraw.Draw(face, "RGBA")

    # The name (shrunk until it fits), and the nickname.
    name_size = 92
    while name_size > 50 and draw.textlength(name.upper(), font=font("Anton", name_size)) > width - 140:
        name_size -= 4
    draw.text((cx, 590), name.upper(), font=font("Anton", name_size), fill=CHALK, anchor="ms")
    y = 600
    if nickname:
        spaced(draw, (cx, 640), f"“{nickname.upper()}”", font("Barlow-SemiBold", 30), DIM, 5, anchor="ms")
        y = 650

    # Six numbers in two columns, with a chalk line down the middle.
    top = y + 40
    draw.line([(70, top), (width - 70, top)], fill=(241, 244, 238, 60), width=2)
    draw.line([(cx, top + 26), (cx, top + 26 + 3 * 92 - 14)], fill=(241, 244, 238, 60), width=2)
    for index, (label, value) in enumerate(numbers[:6]):
        column, row = index % 2, index // 2
        x = 190 if column == 0 else cx + 130
        baseline = top + 100 + row * 92
        draw.text((x, baseline), str(value), font=font("Anton", 78), fill=CHALK, anchor="rs")
        spaced(draw, (x + 26, baseline - 6), label, font("Barlow-Bold", 32), DIM, 6)

    # The form guide: the last five results, newest on the right.
    y = top + 3 * 92 + 60
    draw.line([(70, y), (width - 70, y)], fill=(241, 244, 238, 60), width=2)
    spaced(draw, (70, y + 62), "FORM", font("Barlow-Bold", 28), DIM, 6)
    results = list(reversed(form[:5]))
    for index, result in enumerate(results):
        x0 = 200 + index * 74
        box = [x0, y + 28, x0 + 58, y + 86]
        if result in FORM_COLOURS:
            draw.ellipse(box, fill=FORM_COLOURS[result])
            ink = NIGHT
        else:
            draw.ellipse(box, outline=CHALK if result == "draw" else (241, 244, 238, 70), width=2)
            ink = CHALK if result == "draw" else DIM
        draw.text((x0 + 29, y + 58), FORM_LETTERS.get(result, "–"), font=font("Barlow-Bold", 28), fill=ink, anchor="mm")
    if not results:
        draw.text((200, y + 66), "No confirmed games yet", font=font("Barlow", 30), fill=DIM, anchor="ls")

    # The latest "You played like…" badge.
    if played_like:
        box = [70, height - 196, width - 70, height - 70]
        draw.rectangle(box, fill=(245, 197, 24, 26), outline=GOLD, width=2)
        spaced(draw, (cx, height - 150), "LAST PLAYED LIKE", font("Barlow-Bold", 24), DIM, 6, anchor="ms")
        like_size = 58
        while like_size > 34 and draw.textlength(played_like.upper(), font=font("Anton", like_size)) > width - 200:
            like_size -= 4
        draw.text((cx, height - 92), played_like.upper(), font=font("Anton", like_size), fill=GOLD, anchor="ms")

    # Cut the notched corners and put the gold frame behind the face.
    frame = 12
    card = Image.new("RGBA", (width, height), NIGHT + (255,))
    gold_mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(gold_mask).polygon(shape, fill=255)
    card.paste(Image.new("RGBA", (width, height), GOLD + (255,)), (0, 0), gold_mask)
    inner = [(notch_x + 5, frame), (width - notch_x - 5, frame), (width - frame, notch_y + 5),
             (width - frame, height - frame), (frame, height - frame), (frame, notch_y + 5)]
    face_mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(face_mask).polygon(inner, fill=255)
    card.paste(face, (0, 0), face_mask)
    return png(card)
