import io
import random
import time

from PIL import Image, ImageDraw, ImageFont, ImageFilter

CAPTCHA_LENGTH = 6
CAPTCHA_EXPIRY_SECONDS = 300
CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

_captcha_store: dict[str, dict] = {}


def generate_captcha_text() -> str:
    return "".join(random.choices(CHARSET, k=CAPTCHA_LENGTH))


_cached_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    global _cached_font
    if _cached_font is not None:
        return _cached_font
    font_paths = ["arial.ttf", "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for path in font_paths:
        try:
            _cached_font = ImageFont.truetype(path, size)
            return _cached_font
        except (IOError, OSError):
            continue
    _cached_font = ImageFont.load_default()
    return _cached_font


def generate_captcha_image(text: str) -> bytes:
    W, H = 200, 70
    img = Image.new("RGB", (W, H), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    font = _get_font(36)

    for i, char in enumerate(text):
        char_img = Image.new("RGBA", (40, 50), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        color = (random.randint(0, 80), random.randint(0, 80), random.randint(0, 80))
        char_draw.text((5, 5), char, font=font, fill=color)
        char_img = char_img.rotate(random.randint(-25, 25), expand=False, fillcolor=(0, 0, 0, 0))
        x = 20 + i * 28 + random.randint(-3, 3)
        y = random.randint(8, 18)
        img.paste(char_img, (x, y), char_img)

    for _ in range(3):
        x1, y1 = random.randint(0, W), random.randint(0, H)
        x2, y2 = random.randint(0, W), random.randint(0, H)
        draw.line([(x1, y1), (x2, y2)], fill=(180, 180, 180), width=1)

    for _ in range(100):
        x, y = random.randint(0, W - 1), random.randint(0, H - 1)
        draw.point((x, y), fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)))

    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def store_captcha(captcha_id: str, text: str) -> None:
    _captcha_store[captcha_id] = {"text": text, "created_at": time.time()}


def verify_captcha(captcha_id: str, user_input: str) -> bool:
    entry = _captcha_store.pop(captcha_id, None)
    if entry is None:
        return False
    if time.time() - entry["created_at"] > CAPTCHA_EXPIRY_SECONDS:
        return False
    return entry["text"].upper() == user_input.strip().upper()


def cleanup_expired_captchas() -> None:
    now = time.time()
    expired = [k for k, v in _captcha_store.items() if now - v["created_at"] > CAPTCHA_EXPIRY_SECONDS]
    for k in expired:
        _captcha_store.pop(k, None)