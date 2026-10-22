"""Build female NPC idle palettes and directional review comparisons."""

from copy import deepcopy
from pathlib import Path
import argparse
import json

from PIL import Image, ImageDraw

from build_npc_palette_variants import recolor, preview, write_json, rgba


ROOT = Path(__file__).resolve().parents[1]
NPCS = ROOT / "assets/characters/npcs"
SOURCE = ROOT / "assets/source/characters/npcs/female_01"


def read_json(path):
    return json.loads(path.read_text())


def build_front():
    config = read_json(SOURCE / "palette_variants.json")
    base = Image.open(SOURCE / config["source"]).convert("RGBA")
    palette = read_json(SOURCE / config["source_palette"])["materials"]
    base_meta = read_json(SOURCE / config["source_metadata"])
    layers = read_json(SOURCE / "export.json")["layers"]
    entries = [(config["base_label"], base_meta, base)]
    for variant in config["variants"]:
        number = variant["variant"]
        folder = NPCS / f"female_{number:02}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "idle_front.json"
        status = read_json(path)["status"] if path.exists() else "draft"
        sprite = recolor(base, palette, variant, config)
        eyes = deepcopy(base_meta["eyes"])
        eyes.update({"iris_color": variant["iris_color"], "iris_name": variant["eye_name"]})
        for x, y in eyes["top_pixels"]:
            sprite.putpixel((x, y), rgba(eyes["pupil_color"]))
            sprite.putpixel((x, y+eyes["iris_offset_y"]), rgba(eyes["iris_color"]))
        sprite.save(folder / "idle_front.png")
        preview(sprite).save(folder / "idle_front_review.png")
        materials = deepcopy(palette)
        materials.update(variant["materials"])
        materials["eyes"]["iris"] = eyes["iris_color"]
        write_json(folder / "palette.json", {
            "status": status, "materials": materials, "source_palette": "../female_01/palette.json",
            "regions": config["material_regions"], "eye_feature": eyes,
        })
        metadata = deepcopy(base_meta)
        metadata.update({
            "character": variant["character"], "variant": number,
            "design_status": status, "status": status, "eyes": eyes,
            "source": "../female_01/idle_front.png",
            "recipe": "../../../source/characters/npcs/female_01/palette_variants.json",
        })
        metadata.pop("export_recipe", None)
        metadata["layers"] = []
        part_dir = ROOT / "assets/source/characters/npcs" / f"female_{number:02}" / "layers"
        part_dir.mkdir(parents=True, exist_ok=True)
        for name, definition in layers.items():
            y0, y1 = definition["rows"]
            layer = Image.new("RGBA", (24, 36))
            layer.paste(sprite.crop((0, y0, 24, y1)), (0, y0))
            layer.save(part_dir / f"{name}.png")
            metadata["layers"].append(f"../../../source/characters/npcs/female_{number:02}/layers/{name}.png")
        write_json(path, metadata)
        entries.append((variant["label"], metadata, sprite))

    sheet = Image.new("RGBA", (72, 36))
    board = Image.new("RGB", (1152, 708), "#e8edf2")
    eye_board = Image.new("RGB", (768, 240), "#e8edf2")
    draw, eye_draw = ImageDraw.Draw(board), ImageDraw.Draw(eye_board)
    records = []
    for col, (label, metadata, sprite) in enumerate(entries):
        sheet.paste(sprite, (col*24, 0))
        background = Image.new("RGB", (24, 36), "#e8edf2")
        background.paste(sprite, mask=sprite.getchannel("A"))
        board.paste(background.resize((384, 576), Image.Resampling.NEAREST), (col*384, 8))
        draw.text((col*384+16, 600), label, fill="#1a0e16", font_size=18)
        eye_label = metadata["eyes"]["iris_name"] + " eyes"
        draw.text((col*384+16, 630), eye_label, fill="#1a0e16", font_size=18)
        draw.text((col*384+16, 660), metadata["status"].capitalize(), fill="#455531", font_size=18)
        face = background.crop((8, 7, 16, 13)).resize((256, 192), Image.Resampling.NEAREST)
        eye_board.paste(face, (col*256, 8))
        eye_draw.text((col*256+24, 208), eye_label, fill="#1a0e16", font_size=20)
        records.append({"variant": col+1, "status": metadata["status"],
                        "rect": [col*24, 0, 24, 36], "metadata": f"female_{col+1:02}/idle_front.json",
                        "eyes": metadata["eyes"]})
    sheet.save(NPCS / "female_variants.png")
    board.save(NPCS / "female_variants_review.png")
    eye_board.save(NPCS / "female_eyes_review.png")
    write_json(NPCS / "female_variants.json", {
        "image": "female_variants.png", "frame_size": [24, 36], "foot_anchor": [12, 34],
        "variants": records, "review": {"image": "female_variants_review.png", "scale": 16,
                                           "eyes": "female_eyes_review.png", "eye_scale": 32},
    })


def build_direction(direction):
    config = read_json(SOURCE / "palette_variants.json")
    base = Image.open(NPCS / "female_01" / f"idle_{direction}.png").convert("RGBA")
    base_meta = read_json(NPCS / "female_01" / f"idle_{direction}.json")
    palette = read_json(SOURCE / config["source_palette"])["materials"]
    layers = read_json(SOURCE / "export.json")["layers"]
    for variant in config["variants"]:
        number = variant["variant"]
        folder = NPCS / f"female_{number:02}"
        path = folder / f"idle_{direction}.json"
        status = read_json(path)["status"] if path.exists() else "draft"
        sprite = recolor(base, palette, variant, config)
        eyes = deepcopy(base_meta["eyes"])
        if eyes["visible"]:
            eyes.update(iris_color=variant["iris_color"], iris_name=variant["eye_name"])
            for x, y in eyes["top_pixels"]:
                sprite.putpixel((x, y), rgba(eyes["pupil_color"]))
                sprite.putpixel((x, y+eyes["iris_offset_y"]), rgba(eyes["iris_color"]))
        sprite.save(folder / f"idle_{direction}.png")
        preview(sprite).save(folder / f"idle_{direction}_review.png")
        metadata = deepcopy(base_meta)
        metadata.update({
            "character": variant["character"], "variant": number,
            "design_status": status, "status": status, "eyes": eyes,
            "source": f"../female_01/idle_{direction}.png",
            "recipe": "../../../source/characters/npcs/female_01/palette_variants.json",
        })
        metadata.pop("export_recipe", None)
        metadata["layers"] = []
        part_dir = ROOT / "assets/source/characters/npcs" / f"female_{number:02}" / "directions/layers" / direction
        part_dir.mkdir(parents=True, exist_ok=True)
        for name, definition in layers.items():
            y0, y1 = definition["rows"]
            layer = Image.new("RGBA", (24, 36))
            layer.paste(sprite.crop((0, y0, 24, y1)), (0, y0))
            layer.save(part_dir / f"{name}.png")
            metadata["layers"].append(
                f"../../../source/characters/npcs/female_{number:02}/directions/layers/{direction}/{name}.png")
        write_json(path, metadata)


def build_direction_sheets():
    config = read_json(SOURCE / "palette_variants.json")
    labels = [config["base_label"]] + [v["label"] for v in config["variants"]]
    directions = ("front", "left", "right", "back")
    sheet = Image.new("RGBA", (96, 108))
    board = Image.new("RGB", (1152, 1488), "#e8edf2")
    eye_board = Image.new("RGB", (960, 480), "#e8edf2")
    eye_draw = ImageDraw.Draw(eye_board)
    records = []
    for row, label in enumerate(labels):
        folder = NPCS / f"female_{row+1:02}"
        row_sheet = Image.new("RGBA", (96, 36))
        row_board = Image.new("RGB", (1152, 496), "#e8edf2")
        draw = ImageDraw.Draw(row_board)
        draw.text((16, 8), label, fill="#1a0e16", font_size=20)
        frames = []
        for col, direction in enumerate(directions):
            sprite = Image.open(folder / f"idle_{direction}.png").convert("RGBA")
            meta = read_json(folder / f"idle_{direction}.json")
            row_sheet.paste(sprite, (col*24, 0))
            background = Image.new("RGB", (24, 36), "#e8edf2")
            background.paste(sprite, mask=sprite.getchannel("A"))
            row_board.paste(background.resize((288, 432), Image.Resampling.NEAREST), (col*288, 36))
            draw.text((col*288+12, 472), f"{direction.capitalize()} - {meta['status']}",
                      fill="#1a0e16", font_size=16)
            frames.append({"direction": direction, "rect": [col*24, 0, 24, 36],
                           "metadata": f"idle_{direction}.json", "status": meta["status"]})
            if direction in ("left", "right"):
                eye_row = col-1
                crop = background.crop((7, 7, 17, 13)).resize((320, 192), Image.Resampling.NEAREST)
                eye_board.paste(crop, (row*320, eye_row*240+8))
                eye_draw.text((row*320+12, eye_row*240+208),
                              f"{meta['eyes']['iris_name']} / {direction}", fill="#1a0e16", font_size=20)
        row_sheet.save(folder / "idle_directions.png")
        row_board.save(folder / "idle_directions_review.png")
        write_json(folder / "idle_directions.json", {
            "image": "idle_directions.png", "frame_size": [24, 36], "foot_anchor": [12, 34],
            "frames": frames, "review": {"image": "idle_directions_review.png", "scale": 12},
        })
        sheet.paste(row_sheet, (0, row*36))
        board.paste(row_board, (0, row*496))
        for frame in frames:
            record = deepcopy(frame)
            record["variant"] = row+1
            record["rect"][1] = row*36
            record["metadata"] = f"female_{row+1:02}/{frame['metadata']}"
            records.append(record)
    sheet.save(NPCS / "female_idle_directions.png")
    board.save(NPCS / "female_idle_directions_review.png")
    eye_board.save(NPCS / "female_profile_eyes_review.png")
    write_json(NPCS / "female_idle_directions.json", {
        "image": "female_idle_directions.png", "frame_size": [24, 36], "foot_anchor": [12, 34],
        "frames": records, "review": {"image": "female_idle_directions_review.png", "scale": 12,
                                     "profile_eyes": "female_profile_eyes_review.png", "eye_scale": 32},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", choices=("front", "left", "right", "back", "all"), default="front")
    direction = parser.parse_args().direction
    if direction in ("front", "all"):
        build_front()
    if direction == "all":
        for facing in ("left", "right", "back"):
            build_direction(facing)
        build_direction_sheets()
    elif direction != "front":
        build_direction(direction)


if __name__ == "__main__":
    main()
