"""Export registered HD bowl contents and their exact matching front lips.

The room's existing ceramic bodies and logical support remain unchanged. This
small bank replaces the town composer's generic half-painted ellipse treatment.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/terrain/eldenmere/liam_home/bowls_hd'
PACK='assets/terrain/eldenmere/liam_home/bowls_hd'
ROOM='assets/maps/eldenmere/building_interiors/rooms/liam_house/map.json'
STATES=('full','half_full','empty')


def products():
    recipe=json.loads((SOURCE/'recipe.json').read_text());out={}
    def png(path,image):
        stream=BytesIO();image.save(stream,format='PNG');out[path]=stream.getvalue();return path
    size=tuple(v*2 for v in recipe['logical_size'])
    full=Image.new('L',size);ImageDraw.Draw(full).ellipse(recipe['full_content_ellipse_artwork'],fill=255)
    half=Image.new('L',size);ImageDraw.Draw(half).ellipse(recipe['half_content_ellipse_artwork'],fill=255)
    half=ImageChops.multiply(full,half)
    png(PACK+'/content_mask.png',full);png(PACK+'/half_content_mask.png',half)
    meta={'logical_size':recipe['logical_size'],'artwork_pixels_per_world_pixel':2,
          'content_mask':'content_mask.png','half_content_mask':'half_content_mask.png',
          'bowls':{},'source_recipe':(SOURCE/'recipe.json').relative_to(ROOT).as_posix()}
    for kind,master in recipe['masters'].items():
        body=Image.open(SOURCE/master).convert('RGBA')
        if body.size!=size:raise ValueError('Bowl master changed logical size')
        well=Image.new('RGBA',size,recipe['well_palette'][1]);d=ImageDraw.Draw(well)
        d.line((16,21,31,21),fill=recipe['well_palette'][0])
        d.line((18,26,29,26),fill=recipe['well_palette'][2]);well.putalpha(full)
        body.alpha_composite(well)
        lip=body.copy()
        for y in range(size[1]):
            for x in range(size[0]):
                if y<recipe['front_overlay_start_y_artwork'] or full.getpixel((x,y)):lip.putpixel((x,y),(0,0,0,0))
        lip_path=png(PACK+'/'+kind+'_front_overlay.png',lip)
        records={}
        for state in STATES:
            active=full if state=='full' else half if state=='half_full' else Image.new('L',size)
            palette=recipe[kind+'_palette'];contents=Image.new('RGBA',size,palette[0]);d=ImageDraw.Draw(contents)
            if kind=='food':
                # Small, discrete kibble clusters, not a plate of human food.
                for row,y in enumerate(range(20,28,3)):
                    for x in range(14+row%2,35,4):
                        d.rectangle((x,y,x+2,y+1),fill=palette[1]);d.point((x,y),fill=palette[2]);d.point((x+2,y+1),fill=palette[3])
            else:
                d.line((14,26,33,26),fill=palette[3]);d.line((19,24 if state=='half_full' else 21,28,24 if state=='half_full' else 21),fill=palette[1]);d.line((22,25 if state=='half_full' else 22,26,25 if state=='half_full' else 22),fill=palette[2])
            contents.putalpha(active);image=body.copy();image.alpha_composite(contents)
            path=f'assets/maps/eldenmere/town_hd/rooms/liam_house/daisy_{kind}_bowl_{state}.png'
            png(path,image)
            if state=='full':png(path.replace('_full.png','.png'),image)
            records[state]={'image':path,'fill_fraction':{'full':1,'half_full':.5,'empty':0}[state],
                            'content_pixels':sum(bool(v) for v in active.tobytes())}
        meta['bowls'][kind]={'states':records,'front_overlay':lip_path.rsplit('/',1)[-1]}
    out[PACK+'/bowls.json']=(json.dumps(meta,indent=2)+'\n').encode()
    return out,meta


def integrate(entity,data,export):
    """Bind only this existing bowl; preserve collision, depth and behavior IDs."""
    out,meta=products()
    for path,raw in out.items():
        if path.endswith('.png'):
            # Use the normal town exporter so its complete manifest stays owned.
            name=path.removeprefix('assets/maps/eldenmere/town_hd/').removesuffix('.png')
            if path.startswith('assets/maps/eldenmere/town_hd/'):
                export.png(name,Image.open(BytesIO(raw)).convert('RGBA'))
            else:export.out[path]=raw
        else:export.out[path]=raw
    record=meta['bowls'][entity['bowl_kind']]
    old=deepcopy(entity);entity['bowl_render_pack']=PACK+'/bowls.json'
    entity.update(logical_size=meta['logical_size'],artwork_pixels_per_world_pixel=2,reduced_motion_frame=0)
    entity['state_images']={state:r['image'] for state,r in record['states'].items()}
    entity['frames']=[entity['state_images'][entity['state']]]
    for state,path in old.get('state_images',{}).items():
        if not path.startswith('assets/maps/eldenmere/town_hd/'):
            data['art_replacements'][path]=export.art(entity['state_images'][state],meta['logical_size'])
    for path in old['frames']:
        if not path.startswith('assets/maps/eldenmere/town_hd/'):
            data['art_replacements'][path]=export.art(entity['state_images'][entity['state']],meta['logical_size'])


def build(check=False):
    out,meta=products();data=json.loads((ROOT/ROOM).read_text())
    # The scoped command updates only bowl bindings, never rebuilds the room.
    for entity in data['entities']:
        if not entity.get('bowl_kind'):continue
        entity['bowl_render_pack']=PACK+'/bowls.json'
        entity['state_images']={s:r['image'] for s,r in meta['bowls'][entity['bowl_kind']]['states'].items()}
        entity['frames']=[entity['state_images'][entity['state']]]
        legacy='assets/terrain/eldenmere/liam_home/bowls/'+entity['bowl_kind']
        for state,path in entity['state_images'].items():
            data['art_replacements'][legacy+'_'+state+'.png']={'file':path,'logical_size':[24,24],'artwork_pixels_per_world_pixel':2}
    out[ROOM]=(json.dumps(data,indent=2)+'\n').encode()
    manifest_path='assets/maps/eldenmere/town_hd/manifest.json'
    manifest=json.loads((ROOT/manifest_path).read_text())
    for record in manifest['exports']:
        if record['file'] in out:record['sha256']=sha256(out[record['file']]).hexdigest()
    out[manifest_path]=(json.dumps(manifest,indent=2)+'\n').encode()
    changed=[p for p,raw in out.items() if not (ROOT/p).is_file() or (ROOT/p).read_bytes()!=raw]
    if check:
        if changed:raise SystemExit('Bowl export drift: '+', '.join(changed))
    else:
        for path,raw in out.items():(ROOT/path).parent.mkdir(parents=True,exist_ok=True);(ROOT/path).write_bytes(raw)
    return changed

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    print('Registered HD bowl export:',len(build(args.check)),'changed files')
