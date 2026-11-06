"""Export the reserve's authored ground-foot geometry and standard scene metadata.

The retained clean plate supplies the artwork. This builder only exports the
monochrome navigation mask and metadata, with every point registered to the
approved reference image before its uniform native scale.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/maps/elden_vale_sanctuary/recipe.json'
OUT = ROOT/'assets/maps/elden_vale_sanctuary'


def products():
    recipe = json.loads(SOURCE.read_text())
    art = json.loads((ROOT/recipe['art_manifest']).read_text())
    scale = recipe['scale']
    def point(p):return tuple(round(v*scale) for v in p)
    def polygon(p):return [point(v) for v in p]
    def rectangle(r):
        x,y,w,h = r
        return (*point((x,y)),*point((x+w,y+h)))
    mask = Image.new('L',tuple(recipe['size_pixels']),255)
    draw = ImageDraw.Draw(mask)
    for area in recipe['walk_areas']:
        draw.polygon(polygon(area['polygon']),fill=0)
    for path in recipe['paths']:
        vertices = polygon(path['points']);width = round(path['width']*scale)
        draw.line(vertices,fill=0,width=width,joint='curve')
        radius = width//2
        for x,y in vertices:draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=0)
    for solid in recipe['solid_rects']:draw.rectangle(rectangle(solid['rect']),fill=255)
    for solid in recipe['solid_polygons']:draw.polygon(polygon(solid['polygon']),fill=255)
    # The visible doorway is a real traversable threshold. The hall walls on
    # either side remain solid, including when the interior has not been loaded.
    draw.rectangle(rectangle(recipe['door_clearance']['rect']),fill=0)
    collision = BytesIO();mask.convert('RGB').save(collision,format='PNG')
    scene = {key:recipe[key] for key in ('id','name','size_pixels','spawn','reserve_exit',
              'hall_approach','landmarks','public_approaches','loop_waypoints',
              'blocked_probes','confluence_motes','doors')}
    scene.update(kind='reserve',tile_size=24,size_tiles=[v//24 for v in recipe['size_pixels']],
                 player_probe_size=[24,12],player_draw_anchor=[12,30],
                 ground_frames=[art['ground']],ground_frame_duration_ms=1000,
                 collision=(OUT/'collision.png').relative_to(ROOT).as_posix(),
                 entities=art['entities'],foreground=[],overview=art['overview'],
                 npcs=[],world_links=[],
                 build={'tool':'tools/build_elden_vale_sanctuary.py',
                        'source_recipe':SOURCE.relative_to(ROOT).as_posix(),
                        'source_recipe_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                        'art_manifest':recipe['art_manifest'],
                        'art_manifest_sha256':hashlib.sha256((ROOT/recipe['art_manifest']).read_bytes()).hexdigest()})
    return {'map.json':(json.dumps(scene,indent=2,ensure_ascii=False)+'\n').encode(),
            'collision.png':collision.getvalue()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true');args = parser.parse_args()
    exports = products()
    if args.check:
        stale = [p for p,body in exports.items() if not (OUT/p).exists() or (OUT/p).read_bytes()!=body]
        if stale:raise SystemExit('Stale sanctuary geometry: '+', '.join(stale))
        print('Verified sanctuary reserve map and ground-foot collision.');return
    OUT.mkdir(parents=True,exist_ok=True)
    for name,body in exports.items():(OUT/name).write_bytes(body)
    print('Exported sanctuary reserve map and ground-foot collision.')


if __name__=='__main__':main()
