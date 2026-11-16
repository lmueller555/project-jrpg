"""Explicit density boundary for Caelan's rebuilt story poses.

World.image stays a raw immutable source loader. Only registered scene art is
normalized here; other actors and separately owned props retain their own banks.
"""
from functools import lru_cache
import json
from pathlib import Path
from rendering import load_art, record_art
ROOT=Path(__file__).resolve().parent
@lru_cache(maxsize=1)
def records():
    data=json.loads((ROOT/'assets/characters/caelan/scene_actions.json').read_text())
    return {r['file']:r for r in data['outputs']}
def image(world,path):
    record=records().get(path)
    return load_art(world,path,record) if record else world.image(path)
def frame(sheet,rect,metadata):
    """Atlas rects are artwork units; anchors and contacts remain logical."""
    return record_art(sheet.subsurface(rect).copy(),{'artwork_pixels_per_world_pixel':metadata.get('artwork_pixels_per_world_pixel',1)})
