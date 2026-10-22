"""Assemble a front walk from shared pose masks and character-specific parts.

Run with the assets virtualenv: python tools/build_character_walk.py mira
Add --refresh-template to extract masks from the approved Caelan references.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageColor


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
    layer.paste(image.crop((x, y, x + w, y + h)), (x, y))
    return layer


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


def on_background(image, scale):
    background = Image.new("RGBA", image.size, (232, 237, 242, 255))
    return Image.alpha_composite(background, image).convert("RGB").resize(
        (image.width * scale, image.height * scale), Image.Resampling.NEAREST
    )


def build(recipe_path, refresh):
    recipe = read_json(recipe_path)
    config_path = (recipe_path.parent / recipe["template"]).resolve()
    template = read_json(config_path)
    if refresh:
        extract_template(config_path, template)
    if not recipe["shared_leg_costume"]:
        raise ValueError("This recipe requires matching trousers/boots for shared leg art")
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
    previews[0].save(recipe_path.parent / "walk_front_preview.gif", save_all=True,
                     append_images=previews[1:], duration=[f["duration_ms"] for f in template["frames"]],
                     loop=0, disposal=2, optimize=False)
    comparisons[0].save(recipe_path.parent / "shared_motion_comparison.gif", save_all=True,
                         append_images=comparisons[1:], duration=[f["duration_ms"] for f in template["frames"]],
                         loop=0, disposal=2, optimize=False)
    write_json(recipe_path.parent / "animation.json", {
        "character": recipe["character"], "animation": "walk.front", "status": recipe["approval_status"],
        "image": "spritesheet.png", "frame_size": template["frame_size"],
        "foot_anchor": template["foot_anchor"], "loop": True, "frames": metadata,
        "template": recipe["template"], "recipe": recipe_path.name,
        "offsets_baked_into_pixels": True,
        "review": {"gif": "walk_front_preview.gif", "scale": 20, "background": "#e8edf2"}
    })
    print(f"Built {recipe['character']}: {len(frames)} frames using {template['id']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("character", help="Character asset directory, e.g. mira")
    parser.add_argument("--refresh-template", action="store_true")
    args = parser.parse_args()
    if not args.character.isascii() or not args.character.isidentifier():
        parser.error("Use an ASCII character directory name without path separators")
    build(ROOT / "assets" / "characters" / args.character / "walk_front" / "recipe.json", args.refresh_template)
