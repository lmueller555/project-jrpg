"""Assemble the female NPC front walk with shared strides and dress poses."""

from PIL import Image

from build_character_walk import (
    ROOT, blank, character_parts, isolated, materialize, on_background,
    read_json, rgba, shifted, write_json,
)


def skirt_pose(idle, pose, materials):
    """Fill the dress beneath the hands, then apply an authored row pose."""
    skirt = blank(idle.size)
    dress_colors = {rgba(c) for c in materials["dress"].values()}
    outline = rgba(materials["outline"]["base"])
    for y, row in enumerate(pose["skirt_rows"], start=21):
        source_y, left, right, sway = row
        for x in range(left, right):
            color = idle.getpixel((x, source_y))
            if color not in dress_colors:
                color = rgba(materials["dress"]["base"])
            if x in (left, right-1):
                color = outline
            skirt.putpixel((x+sway, y), color)
    return skirt


def legs_pose(reference, pose, materials):
    """Keep shared stride silhouettes, with bare calves and short ankle boots."""
    output = blank(reference.size)
    outlines = {rgba(c) for c in ("#1a0e16", "#1a0e17", "#2b1715")}
    source_shadows = {rgba("#573422")}
    known_colors = outlines | source_shadows | {rgba("#645450"), rgba("#8b5531")}
    for y in range(26, 35):
        for x in range(24):
            pixel = reference.getpixel((x, y))
            if not pixel[3]:
                continue
            if pixel not in known_colors:
                raise ValueError(f"Unclassified shared leg pixel: {pixel}")
            side = "left" if x < 12 else "right"
            if pixel in outlines:
                color = materials["outline"]["base"]
            elif y >= pose["boot_top_rows"][side]:
                color = materials["leather"]["shadow" if pixel in source_shadows else "base"]
            else:
                color = materials["skin"]["shadow" if pixel in source_shadows else "base"]
            output.putpixel((x, y), rgba(color))
    return output


def build():
    recipe_path = ROOT / "assets/characters/npcs/female_01/walk_front/recipe.json"
    recipe = read_json(recipe_path)
    output_dir = recipe_path.parent
    template_path = (output_dir / recipe["template"]).resolve()
    template = read_json(template_path)
    idle = Image.open(output_dir / recipe["idle"]).convert("RGBA")
    materials = read_json(output_dir / recipe["materials"])["materials"]
    parts_dir = (output_dir / recipe["parts_directory"]).resolve()
    parts_dir.mkdir(parents=True, exist_ok=True)
    parts = character_parts(idle, recipe)
    for name in ("head", "shirt"):
        parts[name].save(parts_dir / f"{name}.png")

    frames, comparisons, records = [], [], []
    for phase, pose in zip(template["frames"], recipe["costume_poses"], strict=True):
        if phase["id"] != pose["id"]:
            raise ValueError("Dress pose order must match the shared stride phases")
        frame_id = phase["id"]
        directory = template_path.parent / f"frame_{frame_id}"
        dy = phase["upper_body_offset"][1]
        legs = legs_pose(Image.open(directory / "legs.png").convert("RGBA"), pose, materials)
        skirt = skirt_pose(idle, pose, materials)
        bodice = isolated(parts["shirt"], [0, 19, 24, 2])
        upper = shifted(isolated(parts["shirt"], [0, 0, 24, 19]), dy)
        bodice = Image.alpha_composite(bodice, upper)
        if dy == -1:
            bodice = Image.alpha_composite(bodice, isolated(parts["shirt"], [0, 18, 24, 1]))
        layers = {"legs": legs, "skirt": skirt, "bodice": bodice}
        for side in ("left", "right"):
            mask = Image.open(directory / f"{side}_arm_mask.png").convert("RGBA")
            layers[f"{side}_arm"] = materialize(mask, template, recipe["palette"])
        layers["head"] = shifted(parts["head"], dy)
        image = blank(idle.size)
        layer_files = []
        for name, layer in layers.items():
            path = parts_dir / f"frame_{frame_id}_{name}.png"
            layer.save(path)
            image = Image.alpha_composite(image, layer)
            layer_files.append(str(path.relative_to(ROOT)))
        filename = f"frame_{frame_id}.png"
        image.save(output_dir / filename)
        frames.append(image)
        reference = Image.open(template_path.parent / phase["reference"]).convert("RGBA")
        comparison = blank((48, 36))
        comparison.paste(reference, (0, 0))
        comparison.paste(image, (24, 0))
        comparisons.append(on_background(comparison, 12))
        records.append({
            "file": filename, "rect": [(len(frames)-1)*24, 0, 24, 36],
            "phase": phase["phase"], "duration_ms": phase["duration_ms"],
            "upper_body_offset": phase["upper_body_offset"], "hem_row": 20+len(pose["skirt_rows"]),
            "boot_top_rows": pose["boot_top_rows"], "layers_from_repo_root": layer_files,
        })
    sheet = blank((96, 36))
    for index, image in enumerate(frames):
        sheet.paste(image, (index*24, 0))
    sheet.save(output_dir / "spritesheet.png")
    on_background(sheet, 12).save(output_dir / "frames_review.png")
    previews = [on_background(image, 20) for image in frames]
    durations = [phase["duration_ms"] for phase in template["frames"]]
    for name, images in (("walk_front_preview.gif", previews),
                         ("shared_motion_comparison.gif", comparisons)):
        images[0].save(output_dir / name, save_all=True, append_images=images[1:],
                       duration=durations, loop=0, disposal=2, optimize=False)
    write_json(output_dir / "animation.json", {
        "character": recipe["character"], "animation": "walk.front",
        "status": recipe["approval_status"], "image": "spritesheet.png", "frame_size": [24, 36],
        "foot_anchor": template["foot_anchor"], "loop": True, "frames": records,
        "template": recipe["template"], "recipe": recipe_path.name,
        "offsets_baked_into_pixels": True,
        "review": {"gif": "walk_front_preview.gif", "scale": 20, "background": "#e8edf2"},
    })
    print("Built female NPC 01: four shared-stride frames with dress-specific skirt and boots")


if __name__ == "__main__":
    build()
