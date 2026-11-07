"""Build the native asset-pack Sanctuary exterior, art, collision and metadata."""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw

if __package__:
    from . import build_elden_vale_sanctuary_art as art_builder
else:
    import build_elden_vale_sanctuary_art as art_builder

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/maps/elden_vale_sanctuary/recipe.json'
OUT = ROOT/'assets/maps/elden_vale_sanctuary'


def products():
    recipe=json.loads(SOURCE.read_text())
    art=json.loads(art_builder.exports()['art.json'])
    blocked=Image.new('L',tuple(recipe['size_pixels']),0)
    draw=ImageDraw.Draw(blocked)
    for record in art['collision_footprints']:
        x,y,w,h=record['rect'];draw.rectangle((x,y,x+w-1,y+h-1),fill=255)
    collision=BytesIO();blocked.convert('RGB').save(collision,format='PNG')
    keys=('id','name','size_pixels','spawn','reserve_exit','hall_approach',
          'landmarks','public_approaches','loop_waypoints','confluence_motes','doors','navigation_policy')
    scene={key:recipe[key] for key in keys}
    scene.update(kind='reserve',tile_size=24,size_tiles=[48,32],
                 player_probe_size=[24,12],player_draw_anchor=[12,30],
                 ground_frames=[art['ground']],ground_frame_duration_ms=1000,
                 collision=(OUT/'collision.png').relative_to(ROOT).as_posix(),
                 entities=art['entities'],foreground=[],overview=art['overview'],
                 npcs=[],world_links=[],
                 asset_instances=art['asset_instances'],
                 collision_footprints=art['collision_footprints'],
                 depth_samples=art['depth_samples'],cloister_bays=art['cloister_bays'],
                 blocked_probes={'hall_wall':[460,320],'tree_root':[144,276],
                                 'cloister_column':[659,331],'cave_keeper_rail':[1008,365],
                                 'survey_seam':[934,534],'south_boundary':[576,668]},
                 cave_barrier={'entity_id':'reserve_cave_keeper_rail','footprint':[972,359,72,12],
                               'public_approach':[1008,406],'inner_probe':[1008,359]},
                 build={'tool':'tools/build_elden_vale_sanctuary.py',
                        'implementation':'native_pixel_asset_packs',
                        'source_recipe':SOURCE.relative_to(ROOT).as_posix(),
                        'source_recipe_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                        'art_manifest':'assets/terrain/elden_vale_sanctuary/art.json',
                        'source_assets':art['source_assets']})
    return {'map.json':(json.dumps(scene,indent=2,ensure_ascii=False)+'\n').encode(),
            'collision.png':collision.getvalue()}


def build(check=False):
    art_builder.build(check)
    output=products()
    for name,body in output.items():
        path=OUT/name
        if check:
            if not path.is_file() or path.read_bytes()!=body:raise ValueError('Stale native Sanctuary map: '+name)
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
    print(('Verified' if check else 'Exported')+' native Sanctuary map and physical footprints')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
