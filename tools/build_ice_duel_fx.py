"""Mechanically register eight authored flame drawings and rune-tip anchors."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/ice_reaper_duel/fx'
TARGET = ROOT/'assets/story/ice_reaper_duel/fx'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build():
    TARGET.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(SOURCE/'fireball_generated.png').convert('RGBA')
    if sheet.size != (1536,1024):
        raise ValueError('Flame sheet must retain its authored four-by-two grid')
    frames = []
    for index in range(8):
        x,y = index%4*384,index//4*512
        bounds = (x,y,x+384,y+512)
        frame = sheet.crop(bounds).resize((128,171),Image.Resampling.NEAREST)
        name = f'fireball_{index+1:02}.png'
        frame.save(TARGET/name,optimize=True)
        frames.append(dict(file=name,duration_ms=85,source_bounds=list(bounds),
                           sha256=digest(TARGET/name)))
    rune = ROOT/'assets/story/ice_reaper_rune/rune.json'
    meta = json.loads(rune.read_text())
    center = meta['center']
    # The large gold diamond-shaped patterns sit just inside the inner ring.
    # Use each authored spoke's diamond centre, not the circumference or a
    # random orbit. Texture X maps to world X and texture Y maps to world Z.
    normalized_radius = .78
    anchors = []
    for index in range(meta['spokes']):
        angle = math.radians(meta['spoke_start_angle_degrees'])+math.tau*index/meta['spokes']
        texture = (center[0]+math.cos(angle)*meta['outer_radius_px']*normalized_radius,
                   center[1]+math.sin(angle)*meta['outer_radius_px']*normalized_radius)
        world = (-3+math.cos(angle)*meta['world_radius']*normalized_radius,.035,
                 math.sin(angle)*meta['world_radius']*normalized_radius)
        anchors.append(dict(index=index,texture=list(texture),world=list(world),
                            ignition=25.8+index*.15))
    manifest = dict(version=1,canvas=[128,171],anchor=[64,100],core_pixels=52,
                    animations=dict(fireball=dict(loop=True,frames=frames)),
                    fireball_anchors=anchors,
                    rune_source='assets/story/ice_reaper_rune/rune.png',
                    rune_sha256=digest(ROOT/'assets/story/ice_reaper_rune/rune.png'),
                    rune_spokes=meta['spokes'],
                    source='assets/source/cinematics/ice_reaper_duel/fx/fireball_generated.png',
                    source_sha256=digest(SOURCE/'fireball_generated.png'),
                    authored=True,
                    extraction='Equal-cell extraction and nearest-neighbour registration only. Eight authored drawings; no procedural flame deformation.')
    (TARGET/'animation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(frames=len(frames),anchors=len(anchors),rune_spokes=meta['spokes'])))


if __name__ == '__main__':
    build()
