"""Photo checks that need no database: file types and Telegram's sizes."""

from app.bot import pick_sizes
from app.photos import sniff


def test_sniff_knows_real_image_types():
    assert sniff(b"\xff\xd8\xff\xe0" + b"0" * 20) == "image/jpeg"
    assert sniff(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert sniff(b"\x89PNG\r\n\x1a\n" + b"0" * 8) == "image/png"


def test_sniff_refuses_everything_else():
    assert sniff(b"<svg onload=alert(1)>") is None
    assert sniff(b"GIF89a") is None
    assert sniff(b"RIFF\x00\x00\x00\x00WAVEfmt ") is None  # a sound file, not WebP
    assert sniff(b"") is None


def size(file_id, width, height):
    return {"file_id": file_id, "width": width, "height": height}


def test_telegram_sizes_mid_for_gallery_small_for_thumb():
    # What Telegram usually sends for one photo: 90, 320, 800 and 1280 wide.
    sizes = [size("s", 90, 67), size("m", 320, 240), size("x", 800, 600), size("y", 1280, 960)]
    assert pick_sizes(sizes) == ("x", "m")


def test_telegram_sizes_when_the_photo_is_small():
    assert pick_sizes([size("s", 90, 90), size("m", 320, 320)]) == ("m", "m")
    assert pick_sizes([size("only", 200, 150)]) == ("only", "only")
    # No mid-size version: the gallery takes the big one, never the tiny one.
    assert pick_sizes([size("s", 90, 60), size("y", 1280, 853)]) == ("y", "y")
