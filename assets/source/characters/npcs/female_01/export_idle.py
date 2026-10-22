"""Export the first female NPC appearance to the game's native frame."""

import json
from pathlib import Path

from PIL import Image, ImageDraw


SOURCE = Path(__file__).resolve().parent
ASSETS = SOURCE.parents[3]
OUTPUT = ASSETS / "characters/npcs/female_01"
PALETTE = {
    "outline": {"base": "#1a0e16"},
    "hair": {"shadow": "#302329", "base": "#4b373c", "light": "#70535a"},
    "skin": {"shadow": "#eda052", "base": "#e8c49d"},
    "dress": {"shadow": "#304f70", "base": "#4d77a0", "light": "#7da5c7"},
    "leather": {"shadow": "#3d2118", "base": "#84512e", "light": "#9d6238"},
}
# Register the source appearance to head, shoulders, waist, hem and ankle rows.
BANDS = [
    (62, 602, 1, 14, ("outline", "hair", "skin")),
    (602, 780, 14, 21, ("outline", "dress", "skin")),
    (780, 813, 21, 22, ("outline", "dress", "skin")),
    (813, 1268, 22, 29, ("outline", "dress", "skin")),
    (1268, 1333, 29, 32, ("outline", "skin")),
    (1333, 1473, 32, 35, ("outline", "leather")),
]
LAYERS = {"head": (0, 14), "bodice_and_arms": (14, 22),
          "skirt_and_hands": (22, 29), "legs_and_boots": (29, 36)}


def rgb(value):
    return tuple(bytes.fromhex(value[1:]))


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((OUTPUT / "idle_front.json").read_text())
    status = metadata["status"]
    eyes = metadata["eyes"]
    PALETTE["eyes"] = {"pupil": eyes["pupil_color"], "iris": eyes["iris_color"]}
    concept = Image.open(SOURCE / "idle_front_concept.png").convert("RGBA")
    alpha = concept.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
    bounds = alpha.getbbox()
    concept.putalpha(alpha)
    native = Image.new("RGBA", (24, 36))
    for sy0, sy1, y0, y1, groups in BANDS:
        colors = [rgb(c) for group in groups for c in PALETTE[group].values()]
        band = concept.crop((bounds[0], sy0, bounds[2], sy1)).resize(
            (14, y1-y0), Image.Resampling.NEAREST)
        for y in range(band.height):
            for x in range(14):
                pixel = band.getpixel((x, y))
                if pixel[3]:
                    candidates = colors
                    # Keep the warm chin/neck shading in the skin ramp rather
                    # than letting dark source skin shading become hair color.
                    if 10 <= x+5 < 14 and 11 <= y+y0 < 14 and pixel[0] > 60:
                        candidates = [rgb(c) for c in PALETTE["skin"].values()]
                    color = min(candidates, key=lambda c: sum((a-b)**2 for a, b in zip(pixel[:3], c)))
                    native.putpixel((x+5, y+y0), (*color, 255))
    # Explicit eye landmarks keep iris recoloring separate from dark outlines.
    for x, y in eyes["top_pixels"]:
        native.putpixel((x, y), (*rgb(eyes["pupil_color"]), 255))
        native.putpixel((x, y+eyes["iris_offset_y"]), (*rgb(eyes["iris_color"]), 255))
    native.save(OUTPUT / "idle_front.png")
    background = Image.new("RGB", native.size, "#e8edf2")
    background.paste(native, mask=native.getchannel("A"))
    background.resize((576, 864), Image.Resampling.NEAREST).save(OUTPUT / "idle_front_review.png")

    comparison = Image.new("RGB", (1152, 668), "#e8edf2")
    draw = ImageDraw.Draw(comparison)
    for col, (label, path) in enumerate((
        ("Male NPC 01", ASSETS / "characters/npcs/male_01/idle_front.png"),
        (f"Female NPC 01 ({status})", OUTPUT / "idle_front.png"),
        ("Mira", ASSETS / "characters/mira/idle_front.png"),
    )):
        sprite = Image.open(path).convert("RGBA").resize((384, 576), Image.Resampling.NEAREST)
        comparison.paste(sprite, (col*384, 8), sprite)
        draw.text((col*384+24, 608), label, fill="#1a0e16", font_size=20)
    comparison.save(OUTPUT / "scale_comparison.png")

    (SOURCE / "layers").mkdir(exist_ok=True)
    for name, (y0, y1) in LAYERS.items():
        layer = Image.new("RGBA", native.size)
        layer.paste(native.crop((0, y0, 24, y1)), (0, y0))
        layer.save(SOURCE / "layers" / f"{name}.png")
    (OUTPUT / "palette.json").write_text(json.dumps({"status": status, "materials": PALETTE}, indent=2)+"\n")
    recipe = {
        "source": "idle_front_concept.png", "alpha_threshold": 128, "source_bounds": bounds,
        "frame_size": [24, 36], "occupied_rect": [5, 1, 14, 34], "foot_anchor": [12, 34],
        "resampling": "nearest", "palette": "../../../../characters/npcs/female_01/palette.json",
        "chin_skin_rect": [10, 11, 4, 3], "chin_source_red_min_exclusive": 60,
        "eyes": eyes,
        "bands": [{"source_y": [a,b], "native_y": [c,d], "materials": list(groups)}
                  for a,b,c,d,groups in BANDS],
        "layers": {name: {"image": f"layers/{name}.png", "rows": list(rows)} for name,rows in LAYERS.items()},
    }
    (SOURCE / "export.json").write_text(json.dumps(recipe, indent=2)+"\n")


if __name__ == "__main__":
    main()
