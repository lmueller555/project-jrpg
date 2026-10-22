"""Assemble walks from shared pose masks and character-specific parts.

Run with the assets virtualenv: python tools/build_character_walk.py mira
Add --refresh-template to extract masks from the approved Caelan references.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
CLEAR = (0, 0, 0, 0)


def rgba(value):
    return (*ImageColor.getrgb(value), 255)


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def blank(size):
    return Image.new("RGBA", size, CLEAR)


def isolated(image, rect):
    x, y, w, h = rect
    layer = blank(image.size)
    if w == 0 or h == 0:
        return layer
    layer.paste(image.crop((x, y, x + w, y + h)), (x, y))
    return layer


def profile_arm_masks(source, codes):
    """Retain projected sleeve/hand silhouettes without the source tabard."""
    materials = {}
    outlines = {(26, 14, 22), (26, 14, 23), (43, 23, 21)}
    for y in range(13, 25):
        for x in range(source.width):
            c = source.getpixel((x, y))
            if not c[3]:
                continue
            if c[:3] == (251, 238, 208) and y <= 20:
                materials[x, y] = "fabric_light"
            elif c[:3] == (232, 196, 157):
                materials[x, y] = "skin_base"
            elif c[:3] == (233, 159, 85):
                materials[x, y] = "skin_shadow"
            elif c[:3] == (100, 84, 80) and y <= 21:
                materials[x, y] = "skin_shadow"
    for x, y in list(materials):
        for xx, yy in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
            if 0 <= xx < source.width and 13 <= yy < 25 and (xx, yy) not in materials:
                c = source.getpixel((xx, yy))
                if c[3] and c[:3] in outlines:
                    materials[xx, yy] = "outline"
                elif c[3] and c[:3] == (211, 150, 63) and yy <= 20:
                    materials[xx, yy] = "fabric_shadow"
    # Projected arm regions can overlap the torso; their pose is already baked in.
    masks = {side: blank(source.size) for side in ("left", "right")}
    for x in range(source.width):
        ys = [y for (xx, y), material in materials.items() if xx == x and material == "fabric_light"]
        if len(ys) > 1:
            materials[x, max(ys)] = "fabric_shadow"
    for (x, y), material in materials.items():
        side = "left" if x < source.width // 2 else "right"
        masks[side].putpixel((x, y), codes[material])
    return masks


def extract_template(config_path, template):
    """Classify approved arm silhouettes into recolorable material masks."""
    codes = {key: rgba(value) for key, value in template["semantic_colors"].items()}
    outline = {(26, 14, 22), (26, 14, 23), (43, 23, 21)}
    teal = {(31, 93, 114), (36, 104, 128)}
    leather = {(87, 52, 34), (139, 85, 49), (182, 118, 68)}
    for frame in template["frames"]:
        source = Image.open(config_path.parent / frame["reference"]).convert("RGBA")
        if source.size != tuple(template["frame_size"]):
            raise ValueError("Pose reference has an unexpected frame size")
        directory = config_path.parent / ("frame_" + frame["id"])
        directory.mkdir(parents=True, exist_ok=True)
        if template.get("direction") in ("left", "right"):
            for side, mask in profile_arm_masks(source, codes).items():
                mask.save(directory / (side + "_arm_mask.png"))
            isolated(source, [0, 26, 24, 10]).save(directory / "legs.png")
            continue
        for side in ("left", "right"):
            mask = blank(source.size)
            for y in range(13, 25):
                xs = range(0, 9 if y < 19 else 8) if side == "left" else range(15 if y < 19 else 16, 24)
                for x in xs:
                    pixel = source.getpixel((x, y))
                    if not pixel[3]:
                        continue
                    color = pixel[:3]
                    # Exclude Caelan's hanging tabard from the forearm masks.
                    if y >= 19 and color in teal | {(211, 150, 63), (251, 238, 208)}:
                        continue
                    if color in outline:
                        material = "outline"
                    elif color == (251, 238, 208):
                        material = "fabric_light"
                    elif color in teal:
                        material = "fabric_base"
                    elif color == (211, 150, 63):
                        material = "fabric_shadow"
                    elif color == (232, 196, 157):
                        material = "skin_base"
                    elif color == (233, 159, 85):
                        material = "skin_shadow"
                    elif color == (100, 84, 80) or color in leather:
                        # Mira has bare forearms rather than Caelan's dark cuffs.
                        material = "skin_shadow"
                    else:
                        raise ValueError(f"Unclassified arm pixel: {color}")
                    mask.putpixel((x, y), codes[material])
            # A darker sleeve edge marks the rolled cuff.
            for x in range(source.width):
                ys = [y for y in range(source.height) if mask.getpixel((x, y)) == codes["fabric_light"]]
                if len(ys) > 1:
                    mask.putpixel((x, max(ys)), codes["fabric_shadow"])
            mask.save(directory / (side + "_arm_mask.png"))
        isolated(source, [0, 26, 24, 10]).save(directory / "legs.png")


def character_parts(idle, recipe):
    """Retain appearance pixels and fill areas previously covered by arms."""
    colors = {key: rgba(value) for key, value in recipe["palette"].items()}
    parts = {"head": isolated(idle, recipe["head_rect"])}
    shirt = blank(idle.size)
    fabric = {colors[key] for key in ("fabric_base", "fabric_light", "fabric_shadow")}
    nx, ny, nw, nh = recipe["neckline_rect"]
    x0, y0, w, h = recipe["shirt_rect"]
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            source = idle.getpixel((x, y))
            color = source if source in fabric else colors["fabric_base"]
            if nx <= x < nx + nw and ny <= y < ny + nh and source[3]:
                color = source
            shirt.putpixel((x, y), color)
    parts["shirt"] = shirt
    waist = blank(idle.size)
    if recipe.get("preserve_waist", False):
        waist = isolated(idle, recipe["waist_rect"])
    else:
        x0, y0, w, h = recipe["waist_rect"]
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                color = colors["leather"] if y < y0 + 2 else colors["trousers"]
                if x in (x0, x0 + w - 1):
                    color = colors["outline"]
                waist.putpixel((x, y), color)
    parts["waist"] = waist
    parts["pouch"] = isolated(idle, recipe["pouch_rect"])
    # Appearance references are retained independently from the posed masks.
    parts["idle_left_arm"] = isolated(idle, [0, 14, 9, 11])
    parts["idle_right_arm"] = isolated(idle, [16, 14, 8, 11])
    parts["idle_legs"] = isolated(idle, [0, 26, 24, 10])
    return parts


def materialize(mask, template, palette):
    lookup = {rgba(code): rgba(palette[name]) for name, code in template["semantic_colors"].items()}
    output = blank(mask.size)
    for y in range(mask.height):
        for x in range(mask.width):
            pixel = mask.getpixel((x, y))
            if pixel[3]:
                output.putpixel((x, y), lookup[pixel])
    return output


def shifted(layer, dy):
    output = blank(layer.size)
    output.paste(layer, (0, dy))
    return output


def recolored_legs(image, replacements):
    """Keep approved leg silhouettes while applying an explicit costume palette."""
    lookup = {rgba(source): rgba(target) for source, target in replacements.items()}
    output = blank(image.size)
    for y in range(image.height):
        for x in range(image.width):
            pixel = image.getpixel((x, y))
            if pixel[3]:
                if pixel not in lookup:
                    raise ValueError(f"Unclassified leg pixel: {pixel}")
                output.putpixel((x, y), lookup[pixel])
    return output


def on_background(image, scale):
    background = Image.new("RGBA", image.size, (232, 237, 242, 255))
    return Image.alpha_composite(background, image).convert("RGB").resize(
        (image.width * scale, image.height * scale), Image.Resampling.NEAREST
    )


def build(recipe_path, refresh):
    recipe = read_json(recipe_path)
    direction = recipe.get("direction", "front")
    config_path = (recipe_path.parent / recipe["template"]).resolve()
    template = read_json(config_path)
    if refresh:
        extract_template(config_path, template)
    if not recipe["shared_leg_costume"] and not recipe.get("leg_palette"):
        raise ValueError("Different trousers/boots require an explicit leg_palette")
    idle = Image.open(recipe_path.parent / recipe["idle"]).convert("RGBA")
    if idle.size != tuple(template["frame_size"]):
        raise ValueError("Character and template frame sizes differ")
    parts = character_parts(idle, recipe)
    part_dir = (recipe_path.parent / recipe["parts_directory"]).resolve()
    part_dir.mkdir(parents=True, exist_ok=True)
    for name, image in parts.items():
        image.save(part_dir / (name + ".png"))
    frames = []
    comparisons = []
    metadata = []
    for frame in template["frames"]:
        directory = config_path.parent / ("frame_" + frame["id"])
        dy = frame["upper_body_offset"][1]
        output = Image.open(directory / "legs.png").convert("RGBA")
        if recipe.get("leg_palette"):
            output = recolored_legs(output, recipe["leg_palette"])
            output.save(part_dir / ("frame_" + frame["id"] + "_legs.png"))
        output = Image.alpha_composite(output, parts["waist"])
        shirt = blank(idle.size)
        shirt.paste(parts["shirt"].crop((0, 19, 24, 36)), (0, 19))
        upper = isolated(parts["shirt"], [0, 0, 24, 19])
        shirt = Image.alpha_composite(shirt, shifted(upper, dy))
        if dy == -1:
            shirt.paste(parts["shirt"].crop((0, 18, 24, 19)), (0, 18))
        output = Image.alpha_composite(output, shirt)
        output = Image.alpha_composite(output, parts["pouch"])
        for side in ("left", "right"):
            mask = Image.open(directory / (side + "_arm_mask.png")).convert("RGBA")
            arm = materialize(mask, template, recipe["palette"])
            arm.save(part_dir / ("frame_" + frame["id"] + "_" + side + "_arm.png"))
            output = Image.alpha_composite(output, arm)
        output = Image.alpha_composite(output, shifted(parts["head"], dy))
        filename = "frame_" + frame["id"] + ".png"
        output.save(recipe_path.parent / filename)
        frames.append(output)
        reference = Image.open(config_path.parent / frame["reference"]).convert("RGBA")
        comparison = blank((idle.width * 2, idle.height))
        comparison.paste(reference, (0, 0))
        comparison.paste(output, (idle.width, 0))
        comparisons.append(on_background(comparison, 12))
        metadata.append({"file": filename, "rect": [(len(frames) - 1) * 24, 0, 24, 36],
                         "duration_ms": frame["duration_ms"], "phase": frame["phase"],
                         "upper_body_offset": frame["upper_body_offset"]})
    sheet = blank((idle.width * len(frames), idle.height))
    for i, image in enumerate(frames):
        sheet.paste(image, (i * idle.width, 0))
    sheet.save(recipe_path.parent / "spritesheet.png")
    on_background(sheet, 12).save(recipe_path.parent / "frames_review.png")
    previews = [on_background(image, 20) for image in frames]
    preview_name = f"walk_{direction}_preview.gif"
    previews[0].save(recipe_path.parent / preview_name, save_all=True,
                     append_images=previews[1:], duration=[f["duration_ms"] for f in template["frames"]],
                     loop=0, disposal=2, optimize=False)
    comparisons[0].save(recipe_path.parent / "shared_motion_comparison.gif", save_all=True,
                         append_images=comparisons[1:], duration=[f["duration_ms"] for f in template["frames"]],
                         loop=0, disposal=2, optimize=False)
    write_json(recipe_path.parent / "animation.json", {
        "character": recipe["character"], "animation": f"walk.{direction}", "status": recipe["approval_status"],
        "image": "spritesheet.png", "frame_size": template["frame_size"],
        "foot_anchor": template["foot_anchor"], "loop": True, "frames": metadata,
        "template": recipe["template"], "recipe": recipe_path.name,
        "offsets_baked_into_pixels": True,
        "review": {"gif": preview_name, "scale": 20, "background": "#e8edf2"}
    })
    print(f"Built {recipe['character']}: {len(frames)} frames using {template['id']}")


def build_direction_board(character):
    root = ROOT / "assets" / "characters" / character
    directions = ("front", "left", "right", "back")
    sheet = blank((96, 144))
    board_frames = []
    records = []
    font = ImageFont.load_default(size=18)
    for row, direction in enumerate(directions):
        pack = root / f"walk_{direction}"
        meta = read_json(pack / "animation.json")
        sheet.paste(Image.open(pack / "spritesheet.png").convert("RGBA"), (0, row * 36))
        records.append({"direction": direction, "status": meta["status"],
                        "animation": f"walk_{direction}/animation.json",
                        "frames": [{"rect": [i * 24, row * 36, 24, 36], "duration_ms": 140} for i in range(4)]})
    for i in range(1, 5):
        strip = blank((96, 36))
        for col, direction in enumerate(directions):
            frame = Image.open(root / f"walk_{direction}" / f"frame_0{i}.png").convert("RGBA")
            strip.paste(frame, (col * 24, 0))
        enlarged = on_background(strip, 12)
        board = Image.new("RGB", (1152, 474), (232, 237, 242))
        board.paste(enlarged, (0, 0))
        draw = ImageDraw.Draw(board)
        for col, record in enumerate(records):
            label = record["direction"].capitalize() + " (" + record["status"] + ")"
            draw.text((col * 288 + 144, 453), label, font=font, anchor="mm", fill=(38, 55, 70))
        board_frames.append(board)
    sheet.save(root / "walk_directions.png")
    board_frames[0].save(root / "walk_directions_review.png")
    board_frames[0].save(root / "walk_directions_review.gif", save_all=True,
                         append_images=board_frames[1:], duration=140, loop=0, disposal=2, optimize=False)
    write_json(root / "walk_directions.json", {
        "character": character, "image": "walk_directions.png", "frame_size": [24, 36],
        "foot_anchor": [12, 34], "directions": records,
        "review": {"gif": "walk_directions_review.gif", "columns": list(directions), "scale": 12}
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("character", help="Character asset directory, e.g. mira or npcs/male_01")
    parser.add_argument("--refresh-template", action="store_true")
    parser.add_argument("--direction", choices=("front", "left", "right", "back", "all"), default="front")
    args = parser.parse_args()
    if not all(part.isascii() and part.isidentifier() for part in args.character.split("/")):
        parser.error("Use ASCII directory names separated by /, without . or .. components")
    directions = ("front", "left", "right", "back") if args.direction == "all" else (args.direction,)
    recipes = [ROOT / "assets" / "characters" / args.character / f"walk_{d}" / "recipe.json" for d in directions]
    for recipe in recipes:
        if not recipe.is_file():
            parser.error(f"Missing character recipe: {recipe}")
    for recipe in recipes:
        build(recipe, args.refresh_template)
    if args.direction == "all":
        build_direction_board(args.character)
