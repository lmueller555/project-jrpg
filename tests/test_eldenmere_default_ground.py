import json
from pathlib import Path
from engine.eldenmere_ground import ground_sprite_id

ROOT=Path(__file__).resolve().parents[1]

def test_default_eldenmere_uses_canonical_terrain():
    source=(ROOT/"main.py").read_text()
    assert "self.draw_grassland_ground(" in source
    assert "JRPG_GRASSLAND_BLOB47" not in source
    assert "self.grassland_preview" not in source

def test_legacy_grass_and_path_assets_are_unregistered():
    doc=json.loads((ROOT/"assets/manifests/assets.json").read_text())
    assert "terrain.grass" not in doc["assets"]
    assert "terrain.path" not in doc["assets"]
    assert all(f"terrain.grassland.blob.grass_{i:02d}" in doc["assets"] for i in range(1,9))
    assert all(f"terrain.grassland.blob.dirt_{i:02d}" in doc["assets"] for i in range(1,9))

def test_eldenmere_map_and_collision_materials_still_resolve():
    world=json.loads((ROOT/"maps/towns/eldenmere.json").read_text())
    for y,row in enumerate(world["tiles"]):
        for x,char in enumerate(row):
            value=ground_sprite_id(world["tiles"],x,y)
            if char in ("g","p"):
                assert value is not None
            else:
                assert value is None
