#!/usr/bin/env python3
"""Export original Elden Vale imagegen sheets to the native regional art API.

Only crops, uniform nearest-neighbour scaling, palette reduction, binary alpha
cleanup and transparent padding are used. No artwork is drawn in this script.
The source PNGs are unaltered generations; prompts and every crop are recorded
beside them so the runtime assets can be reproduced offline.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/source/terrain/overworld/elden_vale"
OUTPUT = ROOT / "assets/terrain/overworld/elden_vale"


def binary_alpha(image: Image.Image, threshold: int) -> Image.Image:
    image = image.convert("RGBA")
    image.putalpha(image.getchannel("A").point(lambda value: 255 if value >= threshold else 0))
    return image


def palette_reduce(image: Image.Image, colors: int) -> Image.Image:
    alpha = image.getchannel("A")
    result = image.convert("RGB").quantize(colors=colors, dither=Image.Dither.NONE).convert("RGBA")
    result.putalpha(alpha)
    return result


def export_image(spec: dict, recipe: dict, *, prop: bool, glint: bool = False) -> Image.Image:
    image = Image.open(SOURCE / spec["source"]).convert("RGBA").crop(spec["crop"])
    image = binary_alpha(image, recipe["alpha_threshold"])
    size = tuple(spec["size"])
    if prop:
        # Transparent source gutters are discarded. Native bounding canvases
        # remain stable, with the generated sprite centered and bottom aligned.
        bbox = image.getbbox()
        if not bbox:
            raise ValueError(f"Empty generated sprite: {spec}")
        image = image.crop(bbox)
        scale = min(size[0] / image.width, size[1] / image.height)
        scaled_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        image = image.resize(scaled_size, Image.Resampling.NEAREST)
        canvas = Image.new("RGBA", size)
        canvas.alpha_composite(image, ((size[0] - image.width) // 2, size[1] - image.height))
        image = canvas
    else:
        # Ground swatches are square; no geometric distortion is introduced.
        image = image.resize(size, Image.Resampling.NEAREST)
    image = palette_reduce(image, recipe["palette_colors"])
    if glint:
        # Extract existing generated highlights as transparent overlays. The
        # binary mask selects pixels; it does not paint or move them.
        minimum = spec["visible_rgb_min"]
        rgba = image.tobytes()
        image.putalpha(Image.frombytes("L", image.size, bytes(
            255 if all(rgba[offset + i] >= minimum[i] for i in range(3)) else 0
            for offset in range(0, len(rgba), 4)
        )))
    return binary_alpha(image, recipe["alpha_threshold"])


def build(check: bool = False) -> None:
    recipe = json.loads((SOURCE / "recipe.json").read_text())
    for source in recipe["source_records"]:
        actual = hashlib.sha256((ROOT / source["file"]).read_bytes()).hexdigest()
        if actual != source["sha256"]:
            raise ValueError(f"Unaltered generation hash differs: {source['file']}")
    manifest = {"version": 1, "tiles": {}, "props": {}}
    products: dict[Path, bytes] = {}
    for group in ("tiles", "glints", "props"):
        for key, spec in recipe[group].items():
            kind = "props" if group == "props" else "tiles"
            path = OUTPUT / kind / f"{key}.png"
            image = export_image(spec, recipe, prop=kind == "props", glint=group == "glints")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG", optimize=True)
            products[path] = buffer.getvalue()
            entry = {"image": path.relative_to(ROOT).as_posix()}
            if kind == "props":
                entry["foot_anchor"] = spec["foot_anchor"]
            manifest[kind][key] = entry
    products[OUTPUT / "art.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    differences = []
    for path, content in products.items():
        if check:
            if not path.exists() or path.read_bytes() != content:
                differences.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    if differences:
        raise SystemExit("Native art is stale: " + ", ".join(differences))
    print(f"{'Verified' if check else 'Exported'} {len(products) - 1} native art PNGs and art.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify byte-for-byte reproducible outputs")
    build(parser.parse_args().check)
