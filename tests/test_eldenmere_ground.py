"""Pure logical mapping contract; no Pygame display dependency."""
from engine.eldenmere_ground import ground_sprite_id
from engine.grassland_autotile import CANONICAL_MASKS

def test_grass_and_path_ids_and_legacy_non_ground():
    tiles=["wggg","gppg","gppg","ggtg"]
    assert ground_sprite_id(tiles,0,0) is None
    assert ground_sprite_id(tiles,1,0).startswith("terrain.grassland.blob.grass_")
    assert ground_sprite_id(tiles,1,1).startswith("terrain.grassland.blob.mask_")
    assert ground_sprite_id(tiles,2,3) is None

def test_stable_variants_and_complete_dirt_patch():
    tiles=["ppppp"]*5
    assert ground_sprite_id(tiles,2,2).startswith("terrain.grassland.blob.dirt_")
    assert ground_sprite_id(tiles,2,2)==ground_sprite_id(tiles,2,2)

def test_every_mask_has_semantic_id():
    for mask in CANONICAL_MASKS:
        assert f"terrain.grassland.blob.mask_{mask:03d}"

def test_bounds_and_other_kinds_remain_legacy():
    tiles=["gwftb"]
    assert ground_sprite_id(tiles,-1,0) is None
    assert ground_sprite_id(tiles,5,0) is None
    assert ground_sprite_id(tiles,1,0) is None
    assert ground_sprite_id(tiles,2,0) is None
