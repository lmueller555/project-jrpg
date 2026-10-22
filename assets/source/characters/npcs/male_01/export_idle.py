"""Export the retained appearance concept to the game's native sprite format.

Run from the repository root with tools/requirements-assets.txt installed.
This only exports the NPC idle and review images; it does not alter references.
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw


SOURCE = Path(__file__).resolve().parent
ASSETS = SOURCE.parents[3]
OUTPUT = ASSETS / "characters/npcs/male_01"
PALETTE = {
    "outline": {"base": "#1a0e16"},
    "hair": {"shadow": "#3d2118", "base": "#71452c", "light": "#9d6238"},
    "skin": {"shadow": "#eda052", "base": "#e8c49d"},
    "shirt": {"shadow": "#455531", "base": "#6e7d43", "light": "#919b61"},
    "trousers": {"shadow": "#8c704f", "base": "#b99a6d", "light": "#d1b486"},
    "leather": {"shadow": "#573422", "base": "#84512e", "light": "#b77740"},
    "buckle": {"base": "#c48b3e"},
}


def rgb(value):
    return tuple(bytes.fromhex(value[1:]))


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    concept = Image.open(SOURCE / "idle_front_concept.png").convert("RGBA")
    alpha = concept.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
    bounds = alpha.getbbox()
    concept.putalpha(alpha)
    # Fit the same occupied 14x34 region as the approved character references.
    sampled = concept.crop(bounds).resize((14, 34), Image.Resampling.NEAREST)
    colors = [rgb(c) for material in PALETTE.values() for c in material.values()]
    native = Image.new("RGBA", (24, 36))
    for y in range(34):
        for x in range(14):
            pixel = sampled.getpixel((x, y))
            if pixel[3]:
                nearest = min(colors, key=lambda c: sum((a-b)**2 for a, b in zip(pixel[:3], c)))
                native.putpixel((x+5, y+1), (*nearest, 255))
    native.save(OUTPUT / "idle_front.png")

    background = "#e8edf2"
    review = Image.new("RGB", native.size, background)
    review.paste(native, mask=native.getchannel("A"))
    review.resize((576, 864), Image.Resampling.NEAREST).save(OUTPUT / "idle_front_review.png")

    comparison = Image.new("RGB", (960, 620), background)
    draw = ImageDraw.Draw(comparison)
    for index, (label, path) in enumerate((
        ("Caelan", ASSETS / "characters/caelan/idle_front.png"),
        ("Male NPC 01 (draft)", OUTPUT / "idle_front.png"),
        ("Mira", ASSETS / "characters/mira/idle_front.png"),
    )):
        sprite = Image.open(path).convert("RGBA").resize((384, 576), Image.Resampling.NEAREST)
        x = index*320-32
        comparison.paste(sprite, (x, 8), sprite)
        draw.text((index*320+36, 596), label, fill="#1a0e16", font_size=20)
    comparison.save(OUTPUT / "scale_comparison.png")

    palette = {"status": "draft", "materials": PALETTE}
    (OUTPUT / "palette.json").write_text(json.dumps(palette, indent=2) + "\n")
    recipe = {"source": "idle_front_concept.png", "alpha_threshold": 128,
              "source_bounds": bounds, "occupied_rect": [5, 1, 14, 34],
              "resampling": "nearest", "palette": "../../../../characters/npcs/male_01/palette.json"}
    (SOURCE / "export.json").write_text(json.dumps(recipe, indent=2) + "\n")


if __name__ == "__main__":
    main()
