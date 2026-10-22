"""Build exact palette variants of the approved male NPC front idle."""

import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
NPCS = ROOT / "assets/characters/npcs"
SOURCE = ROOT / "assets/source/characters/npcs/male_01"


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def rgba(value):
    return (*bytes.fromhex(value[1:]), 255)


def preview(sprite):
    canvas = Image.new("RGB", sprite.size, "#e8edf2")
    canvas.paste(sprite, mask=sprite.getchannel("A"))
    return canvas.resize((576, 864), Image.Resampling.NEAREST)


def main():
    config = json.loads((SOURCE / "palette_variants.json").read_text())
    base = Image.open(SOURCE / config["source"]).convert("RGBA")
    palette = json.loads((SOURCE / config["source_palette"]).read_text())["materials"]
    entries = [("01: Brown / moss / tan", "Approved", base)]
    rects = []
    sheet = Image.new("RGBA", (72, 36))
    sheet.paste(base, (0, 0))
    for index, variant in enumerate(config["variants"], start=1):
        output = NPCS / f"male_{variant['variant']:02}"
        output.mkdir(parents=True, exist_ok=True)
        metadata_path = output / "idle_front.json"
        status = json.loads(metadata_path.read_text())["status"] if metadata_path.exists() else "draft"
        sprite = base.copy()
        # Regions prevent shared brown source colors on the belt, boots and
        # clothing from changing when a hair shade is replaced.
        for material, replacements in variant["materials"].items():
            x0, y0, width, height = config["material_regions"][material]
            mapping = {rgba(palette[material][shade]): rgba(color)
                       for shade, color in replacements.items()}
            for shade, aliases in config.get("shade_aliases", {}).get(material, {}).items():
                for color in aliases:
                    mapping[rgba(color)] = rgba(replacements[shade])
            for y in range(y0, y0 + height):
                for x in range(x0, x0 + width):
                    old = base.getpixel((x, y))
                    if old in mapping:
                        sprite.putpixel((x, y), mapping[old])
        sprite.save(output / "idle_front.png")
        preview(sprite).save(output / "idle_front_review.png")
        write_json(output / "palette.json", {
            "status": status, "source_palette": "../male_01/palette.json",
            "material_overrides": variant["materials"],
            "regions": config["material_regions"],
            "shade_aliases": config["shade_aliases"],
            "other_pixels": "unchanged from approved male_01",
        })
        write_json(output / "idle_front.json", {
            "character": variant["character"], "animation": "idle.front",
            "variant": variant["variant"], "design_status": status, "status": status,
            "image": "idle_front.png", "frame_size": [24, 36],
            "rect": [0, 0, 24, 36], "foot_anchor": [12, 34],
            "palette": "palette.json", "source": "../male_01/idle_front.png",
            "recipe": "../../../source/characters/npcs/male_01/palette_variants.json",
            "review": {"image": "idle_front_review.png", "scale": 24, "background": "#e8edf2"},
        })
        sheet.paste(sprite, (index*24, 0))
        entries.append((f"{variant['variant']:02}: {variant['label']}",
                        "Approved" if status == "approved" else "Draft for review", sprite))

    sheet.save(NPCS / "male_variants.png")
    board = Image.new("RGB", (1152, 668), "#e8edf2")
    draw = ImageDraw.Draw(board)
    for index, (label, status, sprite) in enumerate(entries):
        x = index*384
        enlarged = sprite.resize((384, 576), Image.Resampling.NEAREST)
        board.paste(enlarged, (x, 8), enlarged)
        draw.text((x+16, 600), label, fill="#1a0e16", font_size=18)
        draw.text((x+16, 630), status, fill="#455531", font_size=18)
        rects.append({"variant": index+1, "status": "approved" if status == "Approved" else "draft",
                      "rect": [index*24, 0, 24, 36],
                      "image": f"male_{index+1:02}/idle_front.png"})
    board.save(NPCS / "male_variants_review.png")
    write_json(NPCS / "male_variants.json", {
        "image": "male_variants.png", "frame_size": [24, 36],
        "foot_anchor": [12, 34], "variants": rects,
        "review": {"image": "male_variants_review.png", "scale": 16},
    })


if __name__ == "__main__":
    main()
