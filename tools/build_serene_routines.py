"""Build Serene's planted-foot sanctuary work loops from approved sprite parts.

The 24x36 body is registered on a 48x48 transparent action canvas.  The extra
room belongs to articulated hands and small work props; Serene's approved head,
mantle, planted lower body, palette and foot position remain unchanged.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/source/characters/serene/routines"
OUTPUT = ROOT / "assets/characters/serene/routines"
SERENE_SOURCE = ROOT / "assets/source/characters/serene"
SERENE_OUTPUT = ROOT / "assets/characters/serene"
BODY_OFFSET = (12, 6)
BACKGROUND = "#e8edf2"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def rgba(hex_color: str) -> tuple[int, int, int, int]:
    value = hex_color.removeprefix("#")
    return tuple(bytes.fromhex(value)) + (255,)


def opened(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def blank(size: tuple[int, int] = (48, 48)) -> Image.Image:
    return Image.new("RGBA", size)


def point_on_canvas(point: list[int] | tuple[int, int]) -> tuple[int, int]:
    return point[0] + BODY_OFFSET[0], point[1] + BODY_OFFSET[1]


def approved_body_parts(direction: str) -> tuple[Image.Image, Image.Image, Image.Image]:
    """Return lower torso, mantle and head without approved idle/walk arms."""
    parts = SERENE_SOURCE / f"walk_{direction}/parts"
    idle_layers = SERENE_SOURCE / f"idle_{direction}_layers"
    lower = blank((24, 36))
    lower.alpha_composite(opened(idle_layers / "legs_and_boots.png"))
    lower.alpha_composite(opened(parts / "frame_01_skirt_and_apron.png"))
    lower.alpha_composite(opened(parts / "bodice.png"))
    return lower, opened(parts / "shoulder_mantle.png"), opened(parts / "head.png")


def draw_arm(image: Image.Image, points: list[list[int]], materials: dict) -> None:
    """Draw a three-joint sleeve, linen cuff and hand at native-pixel scale."""
    shoulder, elbow, hand = [point_on_canvas(point) for point in points]
    draw = ImageDraw.Draw(image)
    outline = rgba(materials["outline"][0])
    sage_base = rgba(materials["sage"][1])
    sage_light = rgba(materials["sage"][2])
    linen_base = rgba(materials["linen"][1])
    linen_light = rgba(materials["linen"][2])
    skin_shadow = rgba(materials["skin"][1])
    skin_base = rgba(materials["skin"][0])

    draw.line((shoulder, elbow, hand), fill=outline, width=4, joint="curve")
    draw.line((shoulder, elbow), fill=sage_base, width=3)
    draw.line(
        ((shoulder[0], shoulder[1] - 1), (elbow[0], elbow[1] - 1)),
        fill=sage_light,
        width=1,
    )
    cuff = (
        round(elbow[0] + (hand[0] - elbow[0]) * 0.62),
        round(elbow[1] + (hand[1] - elbow[1]) * 0.62),
    )
    draw.line((elbow, cuff), fill=linen_base, width=3)
    if cuff != elbow:
        draw.point((cuff[0], cuff[1] - 1), fill=linen_light)
    draw.line((cuff, hand), fill=skin_shadow, width=2)
    draw.point(hand, fill=skin_base)


def draw_provision_jar(image: Image.Image, prop: dict, colors: dict, materials: dict) -> None:
    x, y = point_on_canvas(prop["anchor"])
    draw = ImageDraw.Draw(image)
    outline = rgba(materials["outline"][0])
    draw.rectangle((x + 1, y, x + 3, y + 1), fill=outline)
    draw.rectangle((x, y + 1, x + 4, y + 5), fill=outline)
    draw.rectangle((x + 1, y + 2, x + 3, y + 4), fill=rgba(colors["amber"]))
    draw.point((x + 1, y + 2), fill=rgba(colors["amber_shadow"]))
    draw.line((x + 1, y + 3, x + 3, y + 3), fill=rgba(colors["parchment"]))
    draw.point((x + 2, y + 3), fill=rgba(colors["ink"]))


def draw_list(image: Image.Image, prop: dict, colors: dict, materials: dict) -> None:
    x, y = point_on_canvas(prop["anchor"])
    draw = ImageDraw.Draw(image)
    outline = rgba(materials["outline"][0])
    draw.polygon(((x, y), (x + 6, y), (x + 6, y + 6), (x + 5, y + 7), (x, y + 7)), fill=outline)
    draw.rectangle((x + 1, y + 1, x + 5, y + 6), fill=rgba(colors["parchment"]))
    draw.line((x + 2, y + 2, x + 4, y + 2), fill=rgba(colors["ink"]))
    draw.line((x + 2, y + 4, x + 5, y + 4), fill=rgba(colors["ink"]))
    draw.point((x + 1, y + 1), fill=rgba(colors["parchment_light"]))
    draw.point((x + 5, y + 6), fill=rgba(colors["parchment_shadow"]))
    if prop.get("state") == "checked":
        draw.line((x + 2, y + 5, x + 3, y + 6, x + 5, y + 3), fill=rgba(colors["ember"]))


def draw_poker(image: Image.Image, prop: dict, colors: dict, materials: dict) -> None:
    grip = point_on_canvas(prop["grip"])
    tip = point_on_canvas(prop["tip"])
    draw = ImageDraw.Draw(image)
    outline = rgba(materials["outline"][0])
    metal = rgba(colors["metal"])
    leather = rgba(materials["leather"][1])
    draw.line((grip, tip), fill=outline, width=2)
    draw.line((grip, tip), fill=metal, width=1)
    length = max(1.0, math.dist(grip, tip))
    handle_end = (
        round(grip[0] + (tip[0] - grip[0]) * min(4.0 / length, 0.45)),
        round(grip[1] + (tip[1] - grip[1]) * min(4.0 / length, 0.45)),
    )
    draw.line((grip, handle_end), fill=leather, width=2)
    draw.point(tip, fill=rgba(colors["ember"]) if prop.get("sparks") else metal)
    spark_offsets = ((-1, -2), (2, -1), (1, -3))
    for dx, dy in spark_offsets[: prop.get("sparks", 0)]:
        draw.point((tip[0] + dx, tip[1] + dy), fill=rgba(colors["ember"]))


def draw_linen(image: Image.Image, prop: dict, colors: dict, materials: dict) -> None:
    x, y = point_on_canvas(prop["anchor"])
    state = prop["state"]
    width, height = {"folded": (5, 4), "half": (9, 4), "open": (15, 5)}[state]
    draw = ImageDraw.Draw(image)
    outline = rgba(materials["outline"][0])
    draw.polygon(
        ((x, y), (x + width - 2, y), (x + width - 1, y + 1),
         (x + width - 1, y + height - 1), (x, y + height - 1)),
        fill=outline,
    )
    draw.rectangle((x + 1, y + 1, x + width - 2, y + height - 2), fill=rgba(colors["parchment"]))
    draw.line((x + 1, y + 1, x + width - 3, y + 1), fill=rgba(colors["parchment_light"]))
    draw.line((x + 1, y + height - 2, x + width - 2, y + height - 2), fill=rgba(colors["parchment_shadow"]))
    if state != "folded":
        fold_x = x + width // 2
        draw.line((fold_x, y + 1, fold_x, y + height - 2), fill=rgba(colors["parchment_shadow"]))


PROP_DRAWERS = {
    "provision_jar": draw_provision_jar,
    "list": draw_list,
    "poker": draw_poker,
    "linen": draw_linen,
}


def render_frame(
    direction: str,
    frame_spec: dict,
    materials: dict,
    prop_colors: dict,
) -> Image.Image:
    lower, mantle, head = approved_body_parts(direction)
    image = blank()
    image.alpha_composite(lower, BODY_OFFSET)

    prop_layer = blank()
    prop = frame_spec["prop"]
    PROP_DRAWERS[prop["kind"]](prop_layer, prop, prop_colors, materials)
    image.alpha_composite(prop_layer)

    arm_layer = blank()
    for points in frame_spec["arms"]:
        draw_arm(arm_layer, points, materials)
    image.alpha_composite(arm_layer)

    # Approved upper-body pixels cover the articulated shoulder seams.
    image.alpha_composite(mantle, BODY_OFFSET)
    image.alpha_composite(head, BODY_OFFSET)
    return image


def on_background(image: Image.Image, scale: int) -> Image.Image:
    background = Image.new("RGB", image.size, BACKGROUND)
    background.paste(image, (0, 0), image)
    return background.resize(
        (image.width * scale, image.height * scale), Image.Resampling.NEAREST
    )


def export_action(
    name: str,
    action_spec: dict,
    materials: dict,
    prop_colors: dict,
) -> tuple[list[dict], dict]:
    action_root = OUTPUT / name
    action_root.mkdir(parents=True, exist_ok=True)
    for stale in action_root.glob("frame_*.png"):
        stale.unlink()

    frames: list[Image.Image] = []
    records: list[dict] = []
    for index, frame_spec in enumerate(action_spec["frames"], start=1):
        frame = render_frame(action_spec["facing"], frame_spec, materials, prop_colors)
        if frame.size != (48, 48):
            raise AssertionError(f"{name} frame {index} is not 48x48")
        if set(frame.getchannel("A").tobytes()) != {0, 255}:
            raise AssertionError(f"{name} frame {index} has soft alpha")
        filename = f"frame_{index:02}.png"
        frame.save(action_root / filename)
        frames.append(frame)
        records.append(
            {
                "file": f"{name}/{filename}",
                "duration_ms": frame_spec["duration_ms"],
                "phase": frame_spec["phase"],
                "hands": [arm[-1] for arm in frame_spec["arms"]],
                "prop": frame_spec["prop"],
            }
        )

    # The first and final settle frames deliberately match for a clean loop.
    if frames[0].tobytes() != frames[-1].tobytes():
        raise AssertionError(f"{name} does not close on an identical settle frame")

    sheet = blank((48 * len(frames), 48))
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, (index * 48, 0))
    sheet.save(action_root / "spritesheet.png")

    columns = min(6, len(frames))
    rows = math.ceil(len(frames) / columns)
    review = Image.new("RGB", (columns * 48, rows * 48), BACKGROUND)
    for index, frame in enumerate(frames):
        tile = Image.new("RGB", (48, 48), BACKGROUND)
        tile.paste(frame, (0, 0), frame)
        review.paste(tile, ((index % columns) * 48, (index // columns) * 48))
    review.resize(
        (review.width * 6, review.height * 6), Image.Resampling.NEAREST
    ).save(action_root / "frames_review.png")

    previews = [on_background(frame, 8) for frame in frames]
    durations = [record["duration_ms"] for record in records]
    previews[0].save(
        action_root / "preview.gif",
        save_all=True,
        append_images=previews[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )

    runtime_frames = [
        {"file": record["file"], "duration_ms": record["duration_ms"]}
        for record in records
    ]
    rich_record = {
        "facing": action_spec["facing"],
        "loop": True,
        "duration_ms": sum(durations),
        "description": action_spec["description"],
        "frames": records,
        "review": {
            "gif": f"{name}/preview.gif",
            "sheet": f"{name}/frames_review.png",
            "scale": 8,
            "background": BACKGROUND,
        },
    }
    return runtime_frames, rich_record


def build() -> None:
    recipe = read_json(SOURCE / "recipe.json")
    palette = read_json(SERENE_OUTPUT / "palette.json")
    materials = palette["materials"]
    OUTPUT.mkdir(parents=True, exist_ok=True)

    runtime_actions: dict[str, list[dict]] = {}
    animations: dict[str, dict] = {}
    for name, action_spec in recipe["actions"].items():
        runtime_actions[name], animations[name] = export_action(
            name, action_spec, materials, recipe["prop_palette"]
        )

    # A compact board shows the most descriptive frame from every loop.
    representative = {
        "sort_provisions": 4,
        "consult_list": 6,
        "tend_hearth": 5,
        "arrange_hall": 5,
    }
    board = Image.new("RGB", (48 * len(representative), 48), BACKGROUND)
    for column, (name, index) in enumerate(representative.items()):
        frame = opened(OUTPUT / name / f"frame_{index:02}.png")
        tile = Image.new("RGB", (48, 48), BACKGROUND)
        tile.paste(frame, (0, 0), frame)
        board.paste(tile, (column * 48, 0))
    board.resize((board.width * 8, board.height * 8), Image.Resampling.NEAREST).save(
        OUTPUT / "routines_review.png"
    )

    manifest = {
        "id": recipe["id"],
        "status": recipe["status"],
        "character": recipe["character"],
        "frame_size": recipe["action_canvas"],
        "action_canvas": recipe["action_canvas"],
        "body_frame_size": recipe["body_frame_size"],
        "body_offset": recipe["body_offset"],
        "draw_anchor": recipe["draw_anchor"],
        "foot_anchor": recipe["foot_anchor"],
        "actions": runtime_actions,
        "animations": animations,
        "source_recipe": "../../../source/characters/serene/routines/recipe.json",
        "approved_inputs": {
            "palette": "assets/characters/serene/palette.json",
            "back_parts": "assets/source/characters/serene/walk_back/parts",
            "back_idle_layers": "assets/source/characters/serene/idle_back_layers",
        },
        "review": {
            "image": "routines_review.png",
            "columns": list(representative),
            "scale": 8,
            "background": BACKGROUND,
        },
    }
    write_json(OUTPUT / "animations.json", manifest)
    counts = ", ".join(f"{name}={len(frames)}" for name, frames in runtime_actions.items())
    print(f"Built Serene sanctuary routines ({counts}); approved appearance and planted feet retained.")


if __name__ == "__main__":
    build()
