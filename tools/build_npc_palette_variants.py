"""Build exact palette variants of the male NPC's directional idles."""

import argparse
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


def recolor(base, palette, variant, config):
    sprite = base.copy()
    # Regions keep brown hair replacements separate from belt/boot colors.
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
    return sprite


def build_front():
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
        sprite = recolor(base, palette, variant, config)
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


def build_direction(direction):
    config = json.loads((SOURCE / "palette_variants.json").read_text())
    config["material_regions"] = config["material_regions"] | config.get("direction_material_regions", {}).get(direction, {})
    base_path = NPCS / "male_01" / f"idle_{direction}.png"
    base = Image.open(base_path).convert("RGBA")
    palette = json.loads((NPCS / "male_01/palette.json").read_text())["materials"]
    variants = [{"variant": 1, "character": "npc_male_01", "materials": {}}] + config["variants"]
    for variant in variants:
        output = NPCS / f"male_{variant['variant']:02}"
        metadata_path = output / f"idle_{direction}.json"
        status = json.loads(metadata_path.read_text())["status"] if metadata_path.exists() else "draft"
        sprite = recolor(base, palette, variant, config)
        sprite.save(output / f"idle_{direction}.png")
        preview(sprite).save(output / f"idle_{direction}_review.png")
        metadata = {
            "character": variant["character"], "animation": f"idle.{direction}",
            "variant": variant["variant"], "design_status": status, "status": status,
            "image": f"idle_{direction}.png", "frame_size": [24, 36],
            "rect": [0, 0, 24, 36], "foot_anchor": [12, 34], "palette": "palette.json",
            "review": {"image": f"idle_{direction}_review.png", "scale": 24, "background": "#e8edf2"},
        }
        if variant["variant"] == 1:
            metadata.update({
                "source": "../../../source/characters/npcs/male_01/directions/turnaround_concept.png",
                "export_recipe": "../../../source/characters/npcs/male_01/directions/export.json",
            })
        else:
            metadata.update({"source": f"../male_01/idle_{direction}.png",
                             "recipe": "../../../source/characters/npcs/male_01/palette_variants.json",
                             "material_regions": config["material_regions"]})
        write_json(metadata_path, metadata)


def build_direction_sheets():
    directions = ("front", "left", "right", "back")
    combined = Image.new("RGBA", (96, 108))
    board = Image.new("RGB", (1152, 1488), "#e8edf2")
    variant_entries = []
    labels = ("01: Brown hair / moss shirt / tan trousers",
              "02: Black hair / rust shirt / charcoal trousers",
              "03: Gray hair / slate shirt / brown trousers")
    for row in range(3):
        output = NPCS / f"male_{row+1:02}"
        sheet = Image.new("RGBA", (96, 36))
        review = Image.new("RGB", (1152, 496), "#e8edf2")
        draw = ImageDraw.Draw(review)
        draw.text((16, 8), labels[row], fill="#1a0e16", font_size=22)
        frames = []
        for col, direction in enumerate(directions):
            sprite = Image.open(output / f"idle_{direction}.png").convert("RGBA")
            status = json.loads((output / f"idle_{direction}.json").read_text())["status"]
            sheet.paste(sprite, (col*24, 0))
            enlarged = sprite.resize((288, 432), Image.Resampling.NEAREST)
            review.paste(enlarged, (col*288, 36), enlarged)
            draw.text((col*288+20, 472), f"{direction.title()} ({status})", fill="#1a0e16", font_size=18)
            frames.append({"id": f"idle.{direction}", "rect": [col*24, 0, 24, 36],
                           "status": status, "metadata": f"idle_{direction}.json"})
        sheet.save(output / "idle_directions.png")
        review.save(output / "idle_directions_review.png")
        write_json(output / "idle_directions.json", {
            "character": f"npc_male_{row+1:02}", "image": "idle_directions.png",
            "frame_size": [24, 36], "foot_anchor": [12, 34], "frames": frames,
            "review": {"image": "idle_directions_review.png", "scale": 12},
        })
        combined.paste(sheet, (0, row*36))
        board.paste(review, (0, row*496))
        variant_entries.append({"variant": row+1, "row": row,
                                "metadata": f"male_{row+1:02}/idle_directions.json"})
    combined.save(NPCS / "male_idle_directions.png")
    board.save(NPCS / "male_idle_directions_review.png")
    write_json(NPCS / "male_idle_directions.json", {
        "image": "male_idle_directions.png", "frame_size": [24, 36],
        "foot_anchor": [12, 34], "columns": list(directions), "variants": variant_entries,
        "review": {"image": "male_idle_directions_review.png", "scale": 12},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", choices=("front", "left", "right", "back", "all"), default="front")
    args = parser.parse_args()
    if args.direction in ("front", "all"):
        build_front()
    for direction in ("left", "right", "back"):
        if args.direction in (direction, "all"):
            build_direction(direction)
    if args.direction == "all":
        build_direction_sheets()


if __name__ == "__main__":
    main()
