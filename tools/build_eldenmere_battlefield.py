"""Mechanically export imagegen-authored Eldenmere battle scenery.

No scenery is painted here. The complete source panorama is resized with nearest
neighbour sampling. The isolated grass cutout is alpha-trimmed and resized;
thresholding its alpha removes generation fringes at native sprite resolution.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/combat/eldenmere"
BACKGROUND_SOURCE = ROOT / "assets/source/combat/eldenmere_background_generated.png"
GRASS_SOURCE = ROOT / "assets/source/combat/eldenmere_grass_generated.png"
CANVAS = (480, 320)
GRASS_SIZE = (24, 12)


def source_record(path: Path) -> dict:
    with Image.open(path) as image:
        dimensions = list(image.size)
    return {
        "file": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "dimensions": dimensions,
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with Image.open(BACKGROUND_SOURCE) as image:
        image.convert("RGB").resize(CANVAS, Image.Resampling.NEAREST).save(
            OUTPUT / "background.png"
        )
    with Image.open(GRASS_SOURCE) as image:
        grass = image.convert("RGBA")
        alpha = grass.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
        bounds = alpha.getbbox()
        if bounds is None:
            raise ValueError("Generated grass source has no opaque pixels")
        grass.putalpha(alpha)
        grass.crop(bounds).resize(GRASS_SIZE, Image.Resampling.NEAREST).save(
            OUTPUT / "grass.png"
        )
    metadata = {
        "id": "eldenmere_well_green",
        "canvas": list(CANVAS),
        "background": "background.png",
        "grass": "grass.png",
        "grass_size": list(GRASS_SIZE),
        "sources": {
            "background": source_record(BACKGROUND_SOURCE),
            "grass": source_record(GRASS_SOURCE),
        },
        "exporter": "tools/build_eldenmere_battlefield.py",
        "world_map": "eldenmere.playable",
        "encounter_position": [336, 900],
        "well_position": [528, 864],
        "notes": [
            "View across the village green west of Eldenmere's well.",
            "Quiet central fighting lane; foreground accents stay at the outer edges.",
            "No festival-state props, river or mill in this local view.",
        ],
    }
    (OUTPUT / "scene.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
