from engine.grassland_autotile import (
    N,E,S,W,NE,SE,SW,NW,CANONICAL_MASKS,canonical,dirt_mask,mapped_asset_id
)
import pytest

def test_exactly_47_unique_canonical_masks():
    assert len(CANONICAL_MASKS)==47
    assert len(set(CANONICAL_MASKS))==47
    assert all(canonical(m)==m for m in CANONICAL_MASKS)

def test_illegal_diagonals_are_removed():
    assert canonical(NE)==0
    assert canonical(N|NE)==N
    assert canonical(N|E|NE)==N|E|NE
    assert canonical(255)==255

def test_inside_corner_vs_solid():
    assert canonical(N|E|S|W)==15
    assert canonical(255)==255
    assert canonical(255 & ~NW)==127

def test_outside_corners():
    rows=["ggg","gpg","ggg"]
    assert dirt_mask(rows,1,1)==0
    rows=["ggg","gpp","gpp"]
    assert dirt_mask(rows,1,1)==E|S|SE

def test_repeated_tiles_are_deterministic():
    rows=["ppppp"]*5
    assert dirt_mask(rows,2,2)==255
    assert dirt_mask(rows,2,2)==dirt_mask(rows,3,2)

def test_mapping_rejects_unverified_source_slots():
    with pytest.raises(ValueError):
        mapped_asset_id(0)
    with pytest.raises(ValueError):
        mapped_asset_id(0, {0:"terrain.grassland.transition.source_slot_01"})

def test_invalid_input():
    with pytest.raises(ValueError):
        canonical(-1)
    with pytest.raises(ValueError):
        canonical(256)
    with pytest.raises(ValueError):
        canonical(True)
