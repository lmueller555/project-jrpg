"""Deterministically extract the 8x8 illustrated grassland source sheet.
This is source-slot packaging, NOT a verified 47-mask autotile lookup.
"""
from pathlib import Path
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets/source/terrain/grassland/blob47_source.png"
ATLAS = ROOT / "assets/atlases/terrain/grassland_v1.png"
MANIFEST = ROOT / "assets/manifests/assets.json"
TILE = 32
# 1254x1254 generated art sheet, not a native 256x256 source. Visual
# separators occupy several pixels between nonuniform ~156px cells.
# Cell boundaries are explicitly recorded so no separator is exported.
EDGES = (0, 156, 313, 470, 627, 784, 941, 1098, 1254)
INSET = 5

def asset_id(index):
    if index < 8:
        return f"terrain.grassland.grass.variant_{index + 1:02d}"
    if index < 16:
        return f"terrain.grassland.dirt.variant_{index - 7:02d}"
    return f"terrain.grassland.transition.source_slot_{index - 15:02d}"

def build():
    src = Image.open(SOURCE).convert("RGBA")
    if src.size != (1254, 1254):
        raise ValueError(f"Unexpected source dimensions: {src.size}")
    canvas = Image.new("RGBA", (256, 256))
    expected = {}
    for index in range(63):
        row, col = divmod(index, 8)
        left, right = EDGES[col], EDGES[col + 1]
        top, bottom = EDGES[row], EDGES[row + 1]
        if right - left <= 2 * INSET or bottom - top <= 2 * INSET:
            raise ValueError(f"Invalid source slot {index}")
        region = src.crop((left + INSET, top + INSET, right - INSET, bottom - INSET))
        tile = region.resize((TILE, TILE), Image.Resampling.NEAREST)
        x, y = col * TILE, row * TILE
        canvas.paste(tile, (x, y))
        expected[asset_id(index)] = {
            "atlas": "atlases/terrain/grassland_v1.png",
            "rect": [x, y, TILE, TILE],
            "anchor": [0, 0],
            "layer": "ground",
        }
    doc = json.loads(MANIFEST.read_text())
    for name, spec in expected.items():
        if doc["assets"].get(name) != spec:
            raise ValueError(f"Manifest differs for {name}; regenerate metadata deliberately")
    ATLAS.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(ATLAS, optimize=False)
    check = Image.open(ATLAS)
    assert check.size == (256, 256) and check.mode == "RGBA"
    assert len(expected) == 63
    print(f"Produced {ATLAS} with {len(expected)} illustrated source slots")
    print("Warning: transitions are source slots, not canonical autotile mask IDs")

if __name__ == "__main__":
    build()
