"""Export female NPC side/back appearances to native game-sized idle frames."""

import json
from pathlib import Path

from PIL import Image


SOURCE = Path(__file__).resolve().parent
ASSETS = SOURCE.parents[4]
OUTPUT = ASSETS / "characters/npcs/female_01"
BANDS = [
    (124, 438, 1, 14, ("outline", "hair", "skin")),
    (438, 558, 14, 21, ("outline", "dress", "skin")),
    (558, 591, 21, 22, ("outline", "dress", "skin")),
    (591, 825, 22, 29, ("outline", "dress", "skin")),
    (825, 882, 29, 32, ("outline", "skin")),
    (882, 956, 32, 35, ("outline", "leather")),
]
EYES = {"left": [9, 9], "right": [14, 9]}
HAIR_HIGHLIGHTS = {"left": [[15, 10]]}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2)+"\n")


def rgb(value):
    return tuple(bytes.fromhex(value[1:]))


def main():
    palette = json.loads((OUTPUT / "palette.json").read_text())["materials"]
    front = json.loads((OUTPUT / "idle_front.json").read_text())
    layer_defs = json.loads((SOURCE.parent / "export.json").read_text())["layers"]
    concept = Image.open(SOURCE / "turnaround_concept.png").convert("RGBA")
    alpha = concept.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
    concept.putalpha(alpha)
    exports = []
    for index, direction in enumerate(("left", "right", "back")):
        panel = [index*512, 0, (index+1)*512, 1024]
        cell = concept.crop(panel)
        bounds = cell.getchannel("A").getbbox()
        width = 14 if direction == "back" else 12
        offset = (24-width)//2
        native = Image.new("RGBA", (24, 36))
        for sy0, sy1, y0, y1, groups in BANDS:
            colors = [rgb(c) for group in groups for c in palette[group].values()]
            band = cell.crop((bounds[0], sy0, bounds[2], sy1)).resize(
                (width, y1-y0), Image.Resampling.NEAREST)
            for y in range(band.height):
                for x in range(width):
                    pixel = band.getpixel((x, y))
                    if pixel[3]:
                        color = min(colors, key=lambda c: sum((a-b)**2 for a, b in zip(pixel[:3], c)))
                        native.putpixel((x+offset, y+y0), (*color, 255))
        # A bright source highlight on the bun belongs to the hair ramp.
        for point in HAIR_HIGHLIGHTS.get(direction, []):
            native.putpixel(tuple(point), (*rgb(palette["hair"]["light"]), 255))
        eyes = {"visible": False, "top_pixels": []}
        if direction in EYES:
            x, y = EYES[direction]
            # Register one pupil/iris pair to the front eye line; remove the
            # source pupil's extra upper pixel after nearest-neighbor export.
            native.putpixel((x, y-1), (*rgb(palette["skin"]["base"]), 255))
            native.putpixel((x, y), (*rgb(front["eyes"]["pupil_color"]), 255))
            native.putpixel((x, y+1), (*rgb(front["eyes"]["iris_color"]), 255))
            eyes = dict(front["eyes"], visible=True, top_pixels=[[x, y]])
        native.save(OUTPUT / f"idle_{direction}.png")
        background = Image.new("RGB", (24, 36), "#e8edf2")
        background.paste(native, mask=native.getchannel("A"))
        background.resize((576, 864), Image.Resampling.NEAREST).save(OUTPUT / f"idle_{direction}_review.png")
        meta_path = OUTPUT / f"idle_{direction}.json"
        status = json.loads(meta_path.read_text())["status"] if meta_path.exists() else "draft"
        layers = []
        part_dir = SOURCE / "layers" / direction
        part_dir.mkdir(parents=True, exist_ok=True)
        for name, definition in layer_defs.items():
            y0, y1 = definition["rows"]
            layer = Image.new("RGBA", (24, 36))
            layer.paste(native.crop((0, y0, 24, y1)), (0, y0))
            layer.save(part_dir / f"{name}.png")
            layers.append(f"../../../source/characters/npcs/female_01/directions/layers/{direction}/{name}.png")
        write_json(meta_path, {
            "character": "npc_female_01", "animation": f"idle.{direction}", "variant": 1,
            "design_status": status, "status": status, "image": f"idle_{direction}.png",
            "frame_size": [24, 36], "rect": [0, 0, 24, 36], "foot_anchor": [12, 34],
            "palette": "palette.json", "eyes": eyes, "dress": front["dress"], "layers": layers,
            "source": "../../../source/characters/npcs/female_01/directions/turnaround_concept.png",
            "export_recipe": "../../../source/characters/npcs/female_01/directions/export.json",
            "review": {"image": f"idle_{direction}_review.png", "scale": 24, "background": "#e8edf2"},
        })
        exports.append({"direction": direction, "panel": panel, "source_alpha_bounds": bounds,
                        "occupied_rect": [offset, 1, width, 34], "eyes": eyes})
    write_json(SOURCE / "export.json", {
        "source": "turnaround_concept.png", "alpha_threshold": 128, "resampling": "nearest",
        "frame_size": [24, 36], "foot_anchor": [12, 34],
        "palette": "../../../../../characters/npcs/female_01/palette.json",
        "bands": [{"source_y": [a,b], "native_y": [c,d], "materials": list(groups)}
                  for a,b,c,d,groups in BANDS],
        "profile_eye_cleanup_offset_y": -1, "hair_highlights": HAIR_HIGHLIGHTS,
        "exports": exports,
    })


if __name__ == "__main__":
    main()
