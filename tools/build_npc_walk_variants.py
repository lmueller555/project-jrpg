"""Apply approved male NPC palettes to an approved directional walk recipe."""

import argparse
from copy import deepcopy
from pathlib import Path

from PIL import Image, ImageDraw

from build_character_walk import build, build_direction_board, blank, on_background, read_json, write_json


ROOT = Path(__file__).resolve().parents[1]
NPCS = ROOT / "assets/characters/npcs"
SOURCE = ROOT / "assets/source/characters/npcs/male_01"


def build_variants(direction):
    base_pack = NPCS / "male_01" / f"walk_{direction}"
    base_recipe = read_json(base_pack / "recipe.json")
    base_meta = read_json(base_pack / "animation.json")
    if base_meta["status"] != "approved" or base_recipe["approval_status"] != "approved":
        raise ValueError("The base walk must be approved before deriving palette variants")
    config = read_json(SOURCE / "palette_variants.json")
    source_palette = read_json(NPCS / "male_01/palette.json")["materials"]
    for variant in config["variants"]:
        number = variant["variant"]
        pack = NPCS / f"male_{number:02}" / f"walk_{direction}"
        pack.mkdir(parents=True, exist_ok=True)
        recipe_path = pack / "recipe.json"
        status = read_json(recipe_path)["approval_status"] if recipe_path.exists() else "draft"
        materials = variant["materials"]
        recipe = deepcopy(base_recipe)
        recipe["character"] = variant["character"]
        recipe["approval_status"] = status
        recipe["parts_directory"] = f"../../../../source/characters/npcs/male_{number:02}/walk_{direction}/parts"
        for shade in ("base", "light", "shadow"):
            recipe["palette"][f"fabric_{shade}"] = materials["shirt"][shade]
        recipe["palette"]["trousers"] = materials["trousers"]["base"]
        trousers = {old: materials["trousers"][shade]
                    for shade, old in source_palette["trousers"].items()}
        recipe["leg_palette"] = {old: trousers.get(color, color)
                                  for old, color in base_recipe["leg_palette"].items()}
        recipe["base_animation"] = f"../../male_01/walk_{direction}/animation.json"
        recipe["palette_variant_source"] = "../../../../source/characters/npcs/male_01/palette_variants.json"
        write_json(recipe_path, recipe)
        # Head, face and waist come from the already-approved palette idle.
        # The unchanged shared template supplies every pose and bob offset.
        build(recipe_path, refresh=False)

    sheet = blank((96, 108))
    records = []
    labels = ["01: Brown / moss / tan"] + [f"{v['variant']:02}: {v['label']}" for v in config["variants"]]
    for row, number in enumerate((1, 2, 3)):
        pack = NPCS / f"male_{number:02}" / f"walk_{direction}"
        meta = read_json(pack / "animation.json")
        sheet.paste(Image.open(pack / "spritesheet.png").convert("RGBA"), (0, row*36))
        records.append({"variant": number, "row": row, "status": meta["status"],
                        "animation": f"male_{number:02}/walk_{direction}/animation.json"})
    boards = []
    for phase in base_meta["frames"]:
        board = Image.new("RGB", (1152, 668), "#e8edf2")
        draw = ImageDraw.Draw(board)
        for col, record in enumerate(records):
            frame = Image.open(NPCS / Path(record["animation"]).parent / phase["file"]).convert("RGBA")
            board.paste(on_background(frame, 16), (col*384, 8))
            draw.text((col*384+16, 600), labels[col], fill="#1a0e16", font_size=18)
            draw.text((col*384+16, 630), f"{record['status'].capitalize()} ({direction})",
                      fill="#455531", font_size=18)
        boards.append(board)
    stem = f"male_walk_{direction}_variants"
    durations = [frame["duration_ms"] for frame in base_meta["frames"]]
    sheet.save(NPCS / f"{stem}.png")
    boards[0].save(NPCS / f"{stem}_review.png")
    boards[0].save(NPCS / f"{stem}_review.gif", save_all=True, append_images=boards[1:],
                   duration=durations, loop=0, disposal=2, optimize=False)
    write_json(NPCS / f"{stem}.json", {
        "animation": f"walk.{direction}", "image": f"{stem}.png", "frame_size": [24, 36],
        "foot_anchor": base_meta["foot_anchor"], "loop": True, "variants": records,
        "frames": [{"column": i, "duration_ms": frame["duration_ms"], "phase": frame["phase"],
                    "upper_body_offset": frame["upper_body_offset"]}
                   for i, frame in enumerate(base_meta["frames"])],
        "review": {"gif": f"{stem}_review.gif", "image": f"{stem}_review.png",
                   "columns": [1, 2, 3], "scale": 16},
    })


def build_all_directions_grid():
    """Compare directions as rows and palettes as columns in a shared loop."""
    directions = ("front", "left", "right", "back")
    labels = ("01: Moss / tan", "02: Rust / charcoal", "03: Slate / brown")
    frames = []
    sheet = blank((96, 432))
    records = []
    for row, direction in enumerate(directions):
        for col, number in enumerate((1, 2, 3)):
            pack = NPCS / f"male_{number:02}" / f"walk_{direction}"
            meta = read_json(pack / "animation.json")
            sheet.paste(Image.open(pack / "spritesheet.png").convert("RGBA"), (0, (row*3+col)*36))
            records.append({"direction": direction, "variant": number, "status": meta["status"],
                            "animation": f"male_{number:02}/walk_{direction}/animation.json",
                            "frames": [{"rect": [i*24, (row*3+col)*36, 24, 36],
                                        "duration_ms": frame["duration_ms"]}
                                       for i, frame in enumerate(meta["frames"])]})
    for phase in range(1, 5):
        board = Image.new("RGB", (864, 1952), "#e8edf2")
        draw = ImageDraw.Draw(board)
        for row, direction in enumerate(directions):
            for col, number in enumerate((1, 2, 3)):
                record = records[row*3+col]
                pack = NPCS / Path(record["animation"]).parent
                frame = Image.open(pack / f"frame_{phase:02}.png").convert("RGBA")
                board.paste(on_background(frame, 12), (col*288, row*488+32))
                draw.text((col*288+16, row*488+8), labels[col], fill="#1a0e16", font_size=18)
                draw.text((col*288+16, row*488+468), f"{direction.title()} ({record['status']})",
                          fill="#455531", font_size=16)
        frames.append(board)
    stem = "male_walk_all_variants"
    durations = [frame["duration_ms"] for frame in read_json(NPCS / "male_01/walk_front/animation.json")["frames"]]
    sheet.save(NPCS / f"{stem}.png")
    frames[0].save(NPCS / f"{stem}_review.png")
    frames[0].save(NPCS / f"{stem}_review.gif", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=2, optimize=False)
    write_json(NPCS / f"{stem}.json", {
        "image": f"{stem}.png", "frame_size": [24, 36], "foot_anchor": [12, 34],
        "loop": True, "animations": records,
        "review": {"gif": f"{stem}_review.gif", "image": f"{stem}_review.png",
                   "rows": list(directions), "columns": [1, 2, 3], "scale": 12},
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", choices=("front", "left", "right", "back", "all"), default="front")
    args = parser.parse_args()
    directions = ("front", "left", "right", "back") if args.direction == "all" else (args.direction,)
    for direction in directions:
        build_variants(direction)
    if args.direction == "all":
        for number in (2, 3):
            build_direction_board(f"npcs/male_{number:02}")
        build_all_directions_grid()
