"""Apply approved female NPC palettes to approved walks without changing poses."""

import argparse
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw

from build_character_walk import (
    ROOT, blank, build_direction_board, on_background, read_json, rgba, write_json,
)


NPCS = ROOT / "assets/characters/npcs"
SOURCE = ROOT / "assets/source/characters/npcs/female_01"
DIRECTIONS = ("front", "left", "right", "back")


def color_replacements(palette, variant):
    # These named ramps have unique colors. Apply across the whole frame so
    # raised shoulders, swinging sleeves and shifted skirts all recolor.
    replacements = {}
    for material, shades in variant["materials"].items():
        for shade, color in shades.items():
            old = palette[material][shade]
            if any(old in colors.values() for name, colors in palette.items() if name != material):
                raise ValueError(f"Ambiguous material color: {old}")
            replacements[old] = color
    replacements[palette["eyes"]["iris"]] = variant["iris_color"]
    return replacements


def recolor(image, replacements):
    mapping = {rgba(old): rgba(new) for old, new in replacements.items()}
    result = image.convert("RGBA")
    result.putdata([mapping.get(pixel, pixel) for pixel in result.get_flattened_data()])
    return result


def save_loop(path, images, durations):
    images[0].save(path, save_all=True, append_images=images[1:],
                   duration=durations, loop=0, disposal=2, optimize=False)


def build_variants(direction):
    base_pack = NPCS / "female_01" / f"walk_{direction}"
    base_recipe = read_json(base_pack / "recipe.json")
    base_meta = read_json(base_pack / "animation.json")
    if base_recipe["approval_status"] != "approved" or base_meta["status"] != "approved":
        raise ValueError("The base walk must be approved before deriving palette variants")
    config = read_json(SOURCE / "palette_variants.json")
    palette = read_json(NPCS / "female_01/palette.json")["materials"]
    for variant in config["variants"]:
        number = variant["variant"]
        pack = NPCS / f"female_{number:02}" / f"walk_{direction}"
        pack.mkdir(parents=True, exist_ok=True)
        recipe_path = pack / "recipe.json"
        status = read_json(recipe_path)["approval_status"] if recipe_path.exists() else "draft"
        replacements = color_replacements(palette, variant)
        recipe = deepcopy(base_recipe)
        recipe.update({
            "character": variant["character"], "approval_status": status,
            "parts_directory": f"../../../../source/characters/npcs/female_{number:02}/walk_{direction}/parts",
            "base_animation": f"../../female_01/walk_{direction}/animation.json",
            "palette_variant_source": "../../../../source/characters/npcs/female_01/palette_variants.json",
            "material_replacements": replacements,
            "build_tool": "tools/build_female_npc_walk_variants.py",
        })
        for shade, color in variant["materials"]["dress"].items():
            recipe["palette"][f"fabric_{shade}"] = color
        write_json(recipe_path, recipe)
        parts_dir = (pack / recipe["parts_directory"]).resolve()
        parts_dir.mkdir(parents=True, exist_ok=True)
        for source in (base_pack / base_recipe["parts_directory"]).resolve().glob("*.png"):
            recolor(Image.open(source), replacements).save(parts_dir / source.name)
        frames, records = [], []
        idle_eyes = read_json(pack.parent / f"idle_{direction}.json")["eyes"]
        for source in base_meta["frames"]:
            frame = recolor(Image.open(base_pack / source["file"]), replacements)
            frame.save(pack / source["file"])
            frames.append(frame)
            record = deepcopy(source)
            record["layers_from_repo_root"] = [
                path.replace("/female_01/", f"/female_{number:02}/")
                for path in source["layers_from_repo_root"]]
            eyes = deepcopy(idle_eyes)
            dx, dy = source["upper_body_offset"]
            eyes["top_pixels"] = [[x+dx, y+dy] for x, y in eyes["top_pixels"]]
            eyes["visible"] = bool(eyes["top_pixels"])
            record["eyes"] = eyes
            records.append(record)
        sheet = blank((96, 36))
        for index, frame in enumerate(frames):
            sheet.paste(frame, (index*24, 0))
        sheet.save(pack / "spritesheet.png")
        on_background(sheet, 12).save(pack / "frames_review.png")
        durations = [frame["duration_ms"] for frame in records]
        save_loop(pack / f"walk_{direction}_preview.gif", [on_background(f, 20) for f in frames], durations)
        metadata = deepcopy(base_meta)
        metadata.update({
            "character": variant["character"], "variant": number, "status": status,
            "frames": records, "palette": "../palette.json",
            "base_animation": recipe["base_animation"],
            "palette_variant_source": recipe["palette_variant_source"],
        })
        write_json(pack / "animation.json", metadata)
    build_direction_comparison(direction, config)


def build_direction_comparison(direction, config):
    base_meta = read_json(NPCS / f"female_01/walk_{direction}/animation.json")
    labels = [config["base_label"]+" / Blue eyes"] + [
        v["label"]+f" / {v['eye_name']} eyes" for v in config["variants"]]
    sheet, records = blank((96, 108)), []
    for row, number in enumerate((1, 2, 3)):
        pack = NPCS / f"female_{number:02}" / f"walk_{direction}"
        meta = read_json(pack / "animation.json")
        sheet.paste(Image.open(pack / "spritesheet.png").convert("RGBA"), (0, row*36))
        records.append({"variant": number, "row": row, "status": meta["status"],
                        "animation": f"female_{number:02}/walk_{direction}/animation.json"})
    boards = []
    for phase in base_meta["frames"]:
        board = Image.new("RGB", (1152, 668), "#e8edf2")
        draw = ImageDraw.Draw(board)
        for col, record in enumerate(records):
            frame = Image.open(NPCS / Path(record["animation"]).parent / phase["file"]).convert("RGBA")
            board.paste(on_background(frame, 16), (col*384, 8))
            draw.text((col*384+12, 600), labels[col], fill="#1a0e16", font_size=17)
            draw.text((col*384+12, 630), f"{direction.title()} ({record['status']})", fill="#455531", font_size=18)
        boards.append(board)
    stem = f"female_walk_{direction}_variants"
    durations = [frame["duration_ms"] for frame in base_meta["frames"]]
    sheet.save(NPCS / f"{stem}.png")
    boards[0].save(NPCS / f"{stem}_review.png")
    save_loop(NPCS / f"{stem}_review.gif", boards, durations)
    write_json(NPCS / f"{stem}.json", {
        "animation": f"walk.{direction}", "image": f"{stem}.png", "frame_size": [24, 36],
        "foot_anchor": base_meta["foot_anchor"], "loop": True, "variants": records,
        "frames": [{"column": i, "duration_ms": f["duration_ms"], "phase": f["phase"],
                    "upper_body_offset": f["upper_body_offset"]} for i, f in enumerate(base_meta["frames"])],
        "review": {"gif": f"{stem}_review.gif", "image": f"{stem}_review.png", "columns": [1, 2, 3], "scale": 16},
    })


def build_grid():
    labels = ("01: Blue / blue eyes", "02: Sage / green eyes", "03: Plum / hazel eyes")
    sheet, records = blank((96, 432)), []
    for row, direction in enumerate(DIRECTIONS):
        for col, number in enumerate((1, 2, 3)):
            pack = NPCS / f"female_{number:02}" / f"walk_{direction}"
            meta = read_json(pack / "animation.json")
            sheet.paste(Image.open(pack / "spritesheet.png").convert("RGBA"), (0, (row*3+col)*36))
            records.append({"direction": direction, "variant": number, "status": meta["status"],
                            "animation": f"female_{number:02}/walk_{direction}/animation.json",
                            "frames": [{"rect": [i*24, (row*3+col)*36, 24, 36],
                                        "duration_ms": frame["duration_ms"]}
                                       for i, frame in enumerate(meta["frames"])]})
    boards = []
    for phase in range(1, 5):
        board = Image.new("RGB", (864, 1952), "#e8edf2")
        draw = ImageDraw.Draw(board)
        for row, direction in enumerate(DIRECTIONS):
            for col, number in enumerate((1, 2, 3)):
                record = records[row*3+col]
                pack = NPCS / Path(record["animation"]).parent
                frame = Image.open(pack / f"frame_{phase:02}.png").convert("RGBA")
                board.paste(on_background(frame, 12), (col*288, row*488+32))
                draw.text((col*288+12, row*488+8), labels[col], fill="#1a0e16", font_size=18)
                draw.text((col*288+12, row*488+468), f"{direction.title()} ({record['status']})",
                          fill="#455531", font_size=16)
        boards.append(board)
    stem = "female_walk_all_variants"
    durations = [f["duration_ms"] for f in read_json(NPCS / "female_01/walk_front/animation.json")["frames"]]
    sheet.save(NPCS / f"{stem}.png")
    boards[0].save(NPCS / f"{stem}_review.png")
    save_loop(NPCS / f"{stem}_review.gif", boards, durations)
    write_json(NPCS / f"{stem}.json", {
        "image": f"{stem}.png", "frame_size": [24, 36], "foot_anchor": [12, 34],
        "loop": True, "animations": records,
        "review": {"gif": f"{stem}_review.gif", "image": f"{stem}_review.png",
                   "rows": list(DIRECTIONS), "columns": [1, 2, 3], "scale": 12},
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", choices=(*DIRECTIONS, "all"), default="front")
    args = parser.parse_args()
    for direction in DIRECTIONS if args.direction == "all" else (args.direction,):
        build_variants(direction)
    if args.direction == "all":
        for number in (2, 3):
            build_direction_board(f"npcs/female_{number:02}")
        build_grid()
    print(f"Built female NPC walk palettes: {args.direction}")
