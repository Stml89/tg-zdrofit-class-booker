"""Script to generate badge images for milestones using Pillow."""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math

BADGES_DIR = Path(__file__).parent.parent / "assets" / "badges"
BADGES_DIR.mkdir(parents=True, exist_ok=True)

# Badge configurations: count -> (title, color_scheme, emoji)
BADGE_CONFIGS = {
    10: ("First Milestone", ("#CD7F32", "#8B4513"), "🥉"),
    20: ("Dedicated", ("#C0C0C0", "#708090"), "🛡️"),
    30: ("Warrior", ("#FFD700", "#B8860B"), "⚔️"),
    40: ("Iron Will", ("#E5E4E2", "#4A4A4A"), "🏋️"),
    50: ("Half Century Hero", ("#00CED1", "#008B8B"), "🏆"),
    100: ("Centurion", ("#FFD700", "#FF8C00"), "⚔️"),
    150: ("Legend", ("#9B59B6", "#6C3483"), "👑"),
    200: ("Unstoppable", ("#FF4500", "#8B0000"), "🌟"),
}


def draw_star(draw, center_x, center_y, radius, points, color, outline_color):
    """Draw a star shape."""
    coords = []
    for i in range(points * 2):
        angle = math.pi / 2 + (i * math.pi / points)
        r = radius if i % 2 == 0 else radius * 0.4
        x = center_x + r * math.cos(angle)
        y = center_y - r * math.sin(angle)
        coords.append((x, y))
    draw.polygon(coords, fill=color, outline=outline_color)


def generate_badge(count: int, title: str, colors: tuple, emoji: str):
    """Generate a badge image."""
    width, height = 400, 400
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    primary, secondary = colors

    # Draw circular background
    margin = 20
    draw.ellipse(
        [margin, margin, width - margin, height - margin],
        fill=primary,
        outline=secondary,
        width=6,
    )

    # Inner circle
    inner_margin = 50
    draw.ellipse(
        [inner_margin, inner_margin, width - inner_margin, height - inner_margin],
        fill=secondary,
        outline=primary,
        width=3,
    )

    # Draw decorative star in center background
    draw_star(draw, width // 2, height // 2 - 10, 80, 8, primary, secondary)

    # Try to use a font, fall back to default
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except (OSError, IOError):
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except (OSError, IOError):
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

    # Draw count number
    count_text = str(count)
    bbox = draw.textbbox((0, 0), count_text, font=font_large)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((width - text_w) // 2, height // 2 - 50),
        count_text,
        fill="white",
        font=font_large,
    )

    # Draw "CLASSES" text
    classes_text = "CLASSES"
    bbox = draw.textbbox((0, 0), classes_text, font=font_small)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((width - text_w) // 2, height // 2 + 10),
        classes_text,
        fill="white",
        font=font_small,
    )

    # Draw title at bottom
    bbox = draw.textbbox((0, 0), title, font=font_medium)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((width - text_w) // 2, height - 80),
        title,
        fill="white",
        font=font_medium,
    )

    return img


def generate_dynamic_badge():
    """Generate a generic dynamic badge for milestones > 200."""
    width, height = 400, 400
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Purple-gold gradient-like effect
    primary = "#9B59B6"
    secondary = "#F39C12"

    draw.ellipse([20, 20, 380, 380], fill=primary, outline=secondary, width=6)
    draw.ellipse([50, 50, 350, 350], fill=secondary, outline=primary, width=3)
    draw_star(draw, 200, 190, 80, 8, primary, secondary)

    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except (OSError, IOError):
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except (OSError, IOError):
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

    # Draw "TITAN" text
    text = "TITAN"
    bbox = draw.textbbox((0, 0), text, font=font_large)
    text_w = bbox[2] - bbox[0]
    draw.text(((400 - text_w) // 2, 160), text, fill="white", font=font_large)

    text2 = "ACHIEVEMENT"
    bbox = draw.textbbox((0, 0), text2, font=font_small)
    text_w = bbox[2] - bbox[0]
    draw.text(((400 - text_w) // 2, 220), text2, fill="white", font=font_small)

    text3 = "UNLOCKED"
    bbox = draw.textbbox((0, 0), text3, font=font_small)
    text_w = bbox[2] - bbox[0]
    draw.text(((400 - text_w) // 2, 320), text3, fill="white", font=font_small)

    return img


def main():
    """Generate all badge images."""
    print(f"Generating badges in {BADGES_DIR}")

    for count, (title, colors, emoji) in BADGE_CONFIGS.items():
        img = generate_badge(count, title, colors, emoji)
        filename = f"badge_{count:03d}.png"
        img.save(BADGES_DIR / filename)
        print(f"  ✓ {filename} ({title})")

    # Generate dynamic badge
    img = generate_dynamic_badge()
    img.save(BADGES_DIR / "badge_dynamic.png")
    print("  ✓ badge_dynamic.png (Titan)")

    print("Done!")


if __name__ == "__main__":
    main()
