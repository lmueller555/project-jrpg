"""Packaging validation; mask mapping is intentionally not claimed."""
from pathlib import Path
import json
from PIL import Image
from tools.terrain.build_grassland_atlas import build, asset_id, ROOT

def test_atlas_dimensions_and_manifest():
    build()
    atlas=Image.open(ROOT / "assets/atlases/terrain/grassland_v1.png")
    assert atlas.size == (256,256) and atlas.mode == "RGBA"
    data=json.loads((ROOT / "assets/manifests/assets.json").read_text())
    ids=[asset_id(i) for i in range(63)]
    assert len(ids)==len(set(ids))==63
    for i,name in enumerate(ids):
        assert data["assets"][name]["rect"]==[(i%8)*32,(i//8)*32,32,32]
    assert all(name in data["assets"] for name in ids)
