"""Export generated directional appearances into native palette-bound frames."""

import json
from pathlib import Path

from PIL import Image


SOURCE = Path(__file__).resolve().parent
ASSETS = SOURCE.parents[4]
OUTPUT = ASSETS / "characters/npcs/male_01"
# Register head, shirt, belt, trousers and boots to the approved front's rows.
BANDS = [(96, 396, 1, 14), (396, 576, 14, 21), (576, 612, 21, 23),
         (612, 816, 23, 30), (816, 943, 30, 35)]
MATERIALS = [
    ("outline", "hair", "skin"),
    ("outline", "shirt", "skin"),
    ("outline", "leather", "buckle", "shirt", "skin"),
    ("outline", "trousers", "skin", "leather"),
    ("outline", "leather"),
]
SKIN_REGIONS = {
    "left": [(14, 18, 3, 8)], "right": [(6, 18, 3, 8)],
    "back": [(5, 18, 3, 8), (16, 18, 3, 8)],
}
EYES = {"left": [10, 9], "right": [14, 9]}
HAIR_ONLY_ROWS = {"left": 7, "right": 7, "back": 11}


def main():
    concept = Image.open(SOURCE / "turnaround_concept.png").convert("RGBA")
    alpha = concept.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
    concept.putalpha(alpha)
    palette = json.loads((OUTPUT / "palette.json").read_text())["materials"]
    exports = []
    for index, direction in enumerate(("left", "right", "back")):
        panel = (index*512, 0, (index+1)*512, concept.height)
        cell = concept.crop(panel)
        bounds = cell.getchannel("A").getbbox()
        width = 14 if direction == "back" else 12
        offset = (24-width)//2
        native = Image.new("RGBA", (24, 36))
        for (sy0, sy1, y0, y1), groups in zip(BANDS, MATERIALS):
            colors = [tuple(bytes.fromhex(c[1:]))
                      for group in groups for c in palette[group].values()]
            band = cell.crop((bounds[0], sy0, bounds[2], sy1)).resize(
                (width, y1-y0), Image.Resampling.NEAREST)
            for y in range(band.height):
                for x in range(band.width):
                    pixel = band.getpixel((x, y))
                    if pixel[3]:
                        candidates = colors
                        if y+y0 < HAIR_ONLY_ROWS[direction]:
                            candidates = [tuple(bytes.fromhex(c[1:]))
                                          for group in ("outline", "hair")
                                          for c in palette[group].values()]
                        for rx, ry, rw, rh in SKIN_REGIONS[direction]:
                            if rx <= x+offset < rx+rw and ry <= y+y0 < ry+rh:
                                candidates = [tuple(bytes.fromhex(c[1:]))
                                              for group in ("outline", "skin")
                                              for c in palette[group].values()]
                        color = min(candidates, key=lambda c: sum((a-b)**2 for a, b in zip(pixel[:3], c)))
                        native.putpixel((x+offset, y+y0), (*color, 255))
        # Keep each visible eye the same two-pixel height as the approved front.
        if direction in EYES:
            x, y = EYES[direction]
            native.putpixel((x, y-1), (*bytes.fromhex(palette["skin"]["base"][1:]), 255))
            for eye_y in (y, y+1):
                native.putpixel((x, eye_y), (*bytes.fromhex(palette["outline"]["base"][1:]), 255))
        native.save(OUTPUT / f"idle_{direction}.png")
        exports.append({"direction": direction, "panel": panel, "source_alpha_bounds": bounds,
                        "occupied_rect": [offset, 1, width, 34]})
    recipe = {"source": "turnaround_concept.png", "alpha_threshold": 128,
              "resampling": "nearest", "frame_size": [24, 36], "foot_anchor": [12, 34],
              "palette": "../../../../../characters/npcs/male_01/palette.json",
              "skin_regions": SKIN_REGIONS, "profile_eye_top": EYES, "eye_height": 2,
              "hair_only_rows_before": HAIR_ONLY_ROWS,
              "bands": [{"source_y": [a, b], "native_y": [c, d], "materials": groups}
                        for (a, b, c, d), groups in zip(BANDS, MATERIALS)],
              "exports": exports}
    (SOURCE / "export.json").write_text(json.dumps(recipe, indent=2)+"\n")


if __name__ == "__main__":
    main()
