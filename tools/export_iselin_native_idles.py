"""Export the staged native-density idle review from complete authored drawings.

Only hard-alpha extraction, uniform whole-drawing sampling and registration are
performed here. The character drawings belong to the retained imagegen source.
The four idles are user-approved; live activation is a separate integration.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/source/characters/iselin/native_idles/turnaround.png"
OUTPUT = ROOT / "assets/characters/iselin/native_idles"
DIRECTIONS = ("front", "left", "right", "back")


def encoded(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def json_bytes(value):
    return (json.dumps(value, indent=2) + "\n").encode()


def products():
    source = Image.open(SOURCE).convert("RGBA")
    if source.size != (2048, 768):
        raise ValueError("Unexpected authored sheet dimensions")
    source.putalpha(source.getchannel("A").point(lambda a: 255 if a >= 220 else 0))
    cells = [source.crop((index * 512, 0, (index + 1) * 512, 768))
             for index in range(4)]
    bounds = [cell.getbbox() for cell in cells]
    if any(bound is None for bound in bounds):
        raise ValueError("An authored idle is empty")
    # A single crown/sole interval and scale serve all four complete drawings.
    top = min(bound[1] for bound in bounds)
    bottom = max(bound[3] for bound in bounds)
    scale = 34 / (bottom - top)
    outputs = {}
    records = {}
    for direction, cell, bound in zip(DIRECTIONS, cells, bounds):
        crop = cell.crop((bound[0], top, bound[2], bottom))
        size = (round(crop.width * scale), 34)
        if size[0] > 22:
            raise ValueError("Authored silhouette would clip: " + direction)
        origin = (round(12 - size[0] / 2), 1)
        frame = Image.new("RGBA", (24, 36))
        # Composite onto an empty frame to keep invisible storage transparent.
        frame.alpha_composite(crop.resize(size, Image.Resampling.NEAREST), origin)
        outputs[OUTPUT / f"idle_{direction}.png"] = encoded(frame)
        records[direction] = {
            "source_cell": [DIRECTIONS.index(direction) * 512, 0, 512, 768],
            "opaque_bounds_in_cell": list(bound),
            "registered_source_crop": [bound[0], top, bound[2], bottom],
            "rounded_sample_size": list(size),
            "destination_origin": list(origin),
            "occupied_bounds": list(frame.getbbox()),
        }
    outputs[OUTPUT / "animation.json"] = json_bytes({
        "idles": {direction: f"assets/characters/iselin/native_idles/idle_{direction}.png"
                  for direction in DIRECTIONS},
        "walks": {},
        "status": "user-approved idles; not bound to live regent",
        "frame_size": [24, 36],
        "draw_anchor": [12, 30],
        "foot_anchor": [12, 34],
        "artwork_pixels_per_world_pixel": 1,
    })
    outputs[SOURCE.parent / "registration.json"] = json_bytes({
        "generation_tool": "image_gen.imagegen",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": sha256(SOURCE.read_bytes()).hexdigest(),
        "references": [
            "assets/characters/caelan/idle_front.png",
            "assets/characters/mira/idle_front.png",
            "assets/characters/iselin/idle_front_42x72.png",
            "assets/characters/iselin/idle_left_42x72.png",
            "assets/characters/iselin/idle_back_42x72.png",
        ],
        "construction": "Four complete newly authored low-resolution drawings; no mirrored profiles or detached anatomy.",
        "design": "White hair and blue eyes; blue/silver royal coat; mantle anatomical right, forward braid anatomical left.",
        "export": "Alpha >=220; common crown/sole interval; one uniform source scale; nearest-neighbor registration only.",
        "source_scale": scale,
        "frame_size": [24, 36],
        "draw_anchor": [12, 30],
        "foot_anchor": [12, 34],
        "collision_probe": [8, 4],
        "status": "user-approved idles; live HD bank preserved pending integration",
        "records": records,
        "exports": {str(path.relative_to(ROOT)): sha256(data).hexdigest()
                    for path, data in outputs.items()},
    })
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = products()
    changed = [str(path.relative_to(ROOT)) for path, data in outputs.items()
               if not path.exists() or path.read_bytes() != data]
    if args.check:
        if changed:
            raise SystemExit("Stale native Iselin idle exports: " + ", ".join(changed))
        print("Native Iselin idle exports match the retained source.")
        return
    for path, data in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print("Exported four staged 24x36 Iselin idles and registration metadata.")


if __name__ == "__main__":
    main()
