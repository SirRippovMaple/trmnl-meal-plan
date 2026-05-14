import os
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

W, H = 800, 480
PAD_X = 36
PAD_Y = 26

_FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
}


def _font(key: str, size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES[key]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def render_png(data: dict) -> bytes:
    img = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(img)

    f_meal = _font("bold", 20)
    f_day = _font("regular", 13)
    f_item = _font("regular", 20)
    f_footer = _font("regular", 13)

    meal_type = data["meal_type"].upper()
    day = data["day"].upper()
    week_date = data["week_date"]

    # Header row: meal type left, day right
    draw.text((PAD_X, PAD_Y), meal_type, font=f_meal, fill=0)
    day_w = int(draw.textlength(day, font=f_day))
    draw.text((W - PAD_X - day_w, PAD_Y + 5), day, font=f_day, fill=0)

    # Heavy divider under header
    div1_y = PAD_Y + 38
    draw.line([(PAD_X, div1_y), (W - PAD_X, div1_y)], fill=0, width=2)

    # Footer divider position (anchor from bottom)
    div2_y = H - PAD_Y - 30
    footer_y = div2_y + 10

    # Items or error message
    items_top = div1_y + 18
    items_bottom = div2_y - 10
    available_h = items_bottom - items_top

    if data.get("error"):
        draw.text((PAD_X, items_top + 20), data["error"], font=f_item, fill=0)
    else:
        items = data["items"]
        row_h = max(30, available_h // max(len(items), 1))
        row_h = min(row_h, 42)
        y = items_top + (available_h - row_h * len(items)) // 2  # vertically centre

        max_text_w = W - PAD_X * 2
        for item in items:
            text = f"• {item['food']} ({item['qty']})"
            # Truncate if too wide
            while draw.textlength(text, font=f_item) > max_text_w and len(text) > 10:
                text = text[:-2]
            if not text.endswith(")"):
                text = text.rstrip() + "…"
            draw.text((PAD_X, y), text, font=f_item, fill=0)
            y += row_h

    # Light divider above footer
    draw.line([(PAD_X, div2_y), (W - PAD_X, div2_y)], fill=0, width=1)

    # Footer: title left, macros centre, date right
    draw.text((PAD_X, footer_y), "KETO MEAL PLAN", font=f_footer, fill=0)

    if not data.get("error") and data.get("macros"):
        m = data["macros"]
        macros_str = f"{m['kcal']} kcal  |  {m['p']}g P  |  {m['f']}g F  |  {m['nc']}g NC"
        macros_w = int(draw.textlength(macros_str, font=f_footer))
        draw.text(((W - macros_w) // 2, footer_y), macros_str, font=f_footer, fill=0)

    date_w = int(draw.textlength(week_date, font=f_footer))
    draw.text((W - PAD_X - date_w, footer_y), week_date, font=f_footer, fill=0)

    buf = BytesIO()
    img.convert("1", dither=Image.Dither.NONE).save(buf, format="PNG")
    return buf.getvalue()
