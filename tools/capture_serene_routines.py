"""Capture Serene's four sanctuary work loops in their real room maps.

The action builder owns every character pixel.  This review tool only reads its
``animations.json`` export, places those exported frames at the matching map
station, and asks the game ``World`` renderer to draw the scene.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from PIL import Image, ImageDraw, ImageFont
import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import main


ANIMATIONS = ROOT / "assets/characters/serene/routines/animations.json"
BEHAVIOR = ROOT / "assets/maps/eldenmere/routines/serene.json"
ROOMS = ROOT / "assets/maps/eldenmere/building_interiors/rooms"
OUTPUT = ROOT / "docs/reviews/serene_sanctuary_routines"
FONT_FILE = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


@dataclass(frozen=True)
class ReviewSpec:
    action: str
    filename: str
    title: str
    subject: str


SPECS = (
    ReviewSpec("sort_provisions", "provisions.gif",
               "Serene / sorting provisions", "provision tables"),
    ReviewSpec("consult_list", "preparation_list.gif",
               "Serene / preparation list", "preparation list"),
    ReviewSpec("tend_hearth", "hearth.gif",
               "Serene / tending the hearth", "sanctuary hearth"),
    ReviewSpec("arrange_hall", "hall_linens.gif",
               "Serene / arranging hall linens", "mending table"),
)


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_FILE), size)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def frame_path(raw_path: str) -> Path:
    """Resolve both metadata-relative and repository-relative frame paths."""
    raw = Path(raw_path)
    candidates = [raw] if raw.is_absolute() else [ANIMATIONS.parent / raw, ROOT / raw]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    rendered = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Serene action frame {raw_path!r} was not found ({rendered})")


def validate_assets(metadata: dict) -> dict[str, list[dict]]:
    """Validate the builder contract before creating any partial reviews."""
    required_top = {"draw_anchor"}
    missing_top = sorted(required_top - metadata.keys())
    if missing_top:
        raise ValueError(f"{ANIMATIONS} is missing: {', '.join(missing_top)}")
    frame_size = metadata.get("frame_size", metadata.get("action_canvas"))
    if frame_size != [48, 48]:
        raise ValueError(f"Expected 48x48 action frames, got {frame_size!r}")

    # The asset and runtime work briefly used different collection names. Read
    # either without changing the authored files or manufacturing a fallback.
    animations = metadata.get("animations", metadata.get("actions"))
    if not isinstance(animations, dict):
        raise ValueError(f"{ANIMATIONS} needs an animations or actions object")
    missing_actions = [spec.action for spec in SPECS if spec.action not in animations]
    if missing_actions:
        raise ValueError("Serene animations are missing: " + ", ".join(missing_actions))

    resolved: dict[str, list[dict]] = {}
    for spec in SPECS:
        animation = animations[spec.action]
        frames = animation if isinstance(animation, list) else animation.get("frames", [])
        if not frames:
            raise ValueError(f"Serene animation {spec.action!r} has no frames")
        parsed = []
        for index, record in enumerate(frames, 1):
            if "file" not in record or "duration_ms" not in record:
                raise ValueError(f"{spec.action} frame {index} needs file and duration_ms")
            duration = int(record["duration_ms"])
            if duration <= 0 or duration % 10:
                raise ValueError(f"{spec.action} frame {index} has invalid GIF duration {duration}")
            parsed.append({**record, "path": frame_path(record["file"]), "duration_ms": duration})
        calculated = sum(frame["duration_ms"] for frame in parsed)
        declared = int(animation.get("duration_ms", calculated)) if isinstance(animation, dict) else calculated
        if declared != calculated:
            raise ValueError(
                f"{spec.action} duration is {declared} ms but its frames total {calculated} ms"
            )
        resolved[spec.action] = parsed
    return resolved


def validate_behavior(behavior: dict) -> dict[str, dict]:
    review = behavior.get("review")
    if not isinstance(review, dict):
        raise ValueError(f"{BEHAVIOR} needs a review object")
    result = {}
    for spec in SPECS:
        if spec.action not in review:
            raise ValueError(f"{BEHAVIOR} is missing review.{spec.action}")
        record = review[spec.action]
        for field in ("scene", "station", "camera", "size"):
            if field not in record:
                raise ValueError(f"review.{spec.action} is missing {field}")
        if len(record["station"]) != 2 or len(record["camera"]) != 2 or len(record["size"]) != 2:
            raise ValueError(f"review.{spec.action} has malformed scene geometry")
        result[spec.action] = record
    return result


def serene_record() -> dict:
    playable = read_json(main.MAP_FILE)
    records = [record for record in playable.get("persistent_npcs", [])
               if record.get("id") == "mother_serene"]
    if len(records) != 1:
        raise ValueError(f"Expected one mother_serene runtime record, found {len(records)}")
    return records[0]


def phase_at(records: list[dict], elapsed_ms: int) -> str:
    cursor = elapsed_ms % sum(record["duration_ms"] for record in records)
    for record in records:
        if cursor < record["duration_ms"]:
            phase = str(record.get("phase", "working"))
            return phase.replace("_", " ").strip().capitalize()
        cursor -= record["duration_ms"]
    return "Working"


def boundaries(records: list[dict], world: main.World) -> list[int]:
    """Preserve action timing and reveal room animation changes during holds."""
    total = sum(record["duration_ms"] for record in records)
    points = {0, total}
    cursor = 0
    for record in records:
        cursor += record["duration_ms"]
        points.add(cursor)
    intervals = {int(world.data["ground_frame_duration_ms"])}
    intervals.update(int(entity["frame_duration_ms"]) for entity in world.data["entities"])
    for interval in intervals:
        if interval <= 0:
            continue
        points.update(range(interval, total, interval))
    return sorted(points)


def crop_box(world: main.World, review: dict) -> tuple[int, int, int, int]:
    """Use the schedule's authored crop, clamped to real room pixels."""
    width, height = map(int, review["size"])
    left, top = map(int, review["camera"])
    left = max(0, min(world.size[0] - width, left))
    top = max(0, min(world.size[1] - height, top))
    return left, top, left + width, top + height


def panel(scene: Image.Image, box: tuple[int, int, int, int], title: str,
          subtitle: str, caption: str) -> Image.Image:
    crop = scene.crop(box)
    crop = crop.resize((crop.width * 4, crop.height * 4), Image.Resampling.NEAREST)
    result = Image.new("RGB", (crop.width, crop.height + 108), "#e8edf2")
    result.paste(crop, (0, 68))
    draw = ImageDraw.Draw(result)
    draw.fontmode = "1"
    draw.text((16, 8), title, font=font(22), fill="#24382f")
    draw.text((16, 37), subtitle, font=font(15), fill="#526761")
    draw.text((16, result.height - 30), caption, font=font(18), fill="#24382f")
    return result


def save_gif(path: Path, frames: list[Image.Image], durations: list[int]) -> int:
    """Encode one exact shared palette so pixel colors cannot flicker or drift."""
    def pixels(frame: Image.Image):
        # Pillow 14 replaces getdata with this spelling; retain compatibility
        # with the older Pillow versions used by some local game setups.
        method = getattr(frame, "get_flattened_data", frame.getdata)
        return method()

    colors = Counter()
    for frame in frames:
        colors.update(pixels(frame))
    if len(colors) > 256:
        raise ValueError(f"{path.name} needs {len(colors)} exact colors; GIF permits 256")
    palette = list(colors)
    lookup = {color: index for index, color in enumerate(palette)}
    rgb = [channel for color in palette for channel in color]
    rgb.extend([0] * (768 - len(rgb)))
    indexed = []
    for frame in frames:
        item = Image.new("P", frame.size)
        item.putpalette(rgb)
        item.putdata([lookup[color] for color in pixels(frame)])
        indexed.append(item)
    # Store every panel as a complete replacement frame. Some chat and code
    # review renderers sample GIF frames without compositing delta rectangles;
    # disposal=2 keeps titles, room context and the actor intact there too.
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations,
                    loop=0, disposal=2, optimize=False)
    full_extent = (0, 0, *frames[0].size)
    with Image.open(path) as exported:
        for index in range(exported.n_frames):
            exported.seek(index)
            extent = exported.tile[0][1] if exported.tile else None
            if extent != full_extent or exported.disposal_method != 2:
                raise ValueError(
                    f"{path.name} frame {index} is a delta patch: "
                    f"extent={extent}, disposal={exported.disposal_method}"
                )
    return len(colors)


def capture_one(spec: ReviewSpec, review: dict, actor_record: dict,
                records: list[dict]) -> None:
    room_path = ROOMS / review["scene"] / "map.json"
    world = main.World(room_path)
    # The review focuses on one action. Remove scheduled room actors and select
    # the action through the same RoutineNPC API used by focused runtime tests.
    world.npcs.clear()
    player = main.Player(world)
    player.position.update(-1000, -1000)
    actor = main.RoutineNPC(actor_record, world, review["scene"])
    actor.select_step(spec.action, position=review["station"], scene_id=review["scene"])
    if actor.action_id != spec.action:
        raise ValueError(f"Runtime selected {actor.action_id!r}, expected {spec.action!r}")
    # Register the same room-owned workstation props used by the playable
    # game. Their visibility follows the selected action frame's explicit
    # surface/actor ownership flag, so every handoff in the review is the
    # actual runtime handoff rather than a capture-only approximation.
    world.attach_routine_props(actor)
    world.npcs.append(actor)

    timeline = boundaries(records, world)
    durations = [end - start for start, end in zip(timeline, timeline[1:])]
    native = pygame.Surface(world.size)
    frames = []
    box = crop_box(world, review)
    for elapsed_ms in timeline[:-1]:
        actor.state_ms = elapsed_ms
        world.draw(native, (0, 0), player, elapsed_ms)
        scene = Image.frombytes("RGB", world.size, pygame.image.tobytes(native, "RGB"))
        frames.append(panel(
            scene,
            box,
            spec.title,
            f"4x native pixels | actual {world.data['name']} map",
            f"{phase_at(records, elapsed_ms)} / {spec.subject}",
        ))
    colors = save_gif(OUTPUT / spec.filename, frames, durations)
    print(
        f"{spec.filename}: {len(frames)} captures, {sum(durations)} ms, "
        f"{colors} exact colors",
        flush=True,
    )


def capture() -> None:
    if not ANIMATIONS.is_file():
        raise SystemExit(
            f"Serene routine assets are not built: missing {ANIMATIONS.relative_to(ROOT)}. "
            "Run the Serene routine asset builder first."
        )
    if not BEHAVIOR.is_file():
        raise SystemExit(
            f"Serene's sanctuary schedule is not built: missing {BEHAVIOR.relative_to(ROOT)}."
        )
    metadata = read_json(ANIMATIONS)
    behavior = read_json(BEHAVIOR)
    try:
        records = validate_assets(metadata)
        reviews = validate_behavior(behavior)
        actor_record = serene_record()
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(f"Cannot capture Serene's routines: {error}") from error

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    try:
        for spec in SPECS:
            capture_one(spec, reviews[spec.action], actor_record, records[spec.action])
    finally:
        pygame.quit()


if __name__ == "__main__":
    capture()
