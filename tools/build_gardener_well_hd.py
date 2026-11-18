"""Export the staged gardener performance; no anatomy generator or live writes.

New action frames are complete image-authored drawings. Existing four-frame
travel bodies remain explicitly labelled compatibility art; their gait is not
redrawn or retimed by this pack. Only canonical rigid pail artwork is rotated.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
RECIPE='assets/source/characters/npcs/female_02/gardener_well_hd/recipe.json'
PACK='assets/characters/npcs/female_02/gardener_well_hd'


def document(value):return (json.dumps(value,indent=2)+'\n').encode()
def digest(raw):return sha256(raw).hexdigest()


def image(path):
    with Image.open(path) as source:return source.convert('RGBA')


def products():
    raw=(ROOT/RECIPE).read_bytes();recipe=json.loads(raw);source=(ROOT/RECIPE).parent
    if recipe['status']!='staged' or recipe['runtime_activation'] or recipe['artwork_pixels_per_world_pixel']!=2:
        raise ValueError('This exporter owns staged native gardener artwork only')
    contract=recipe['mechanism_contract'];contract_raw=(source/contract['file']).read_bytes()
    if digest(contract_raw)!=contract['sha256']:raise ValueError('Mechanism reference changed without review')
    for meta in recipe['source_metadata']:
        if digest((source/meta['file']).read_bytes())!=meta['sha256']:raise ValueError('Authored extraction metadata changed')
    output={};exports=[]
    def png(file,im,role):
        if Path(file).is_absolute() or '..' in Path(file).parts:raise ValueError('Export leaves pack')
        path=PACK+'/'+file
        if path in output:raise ValueError('Duplicate export')
        stream=BytesIO();im.save(stream,format='PNG');data=stream.getvalue();output[path]=data
        exports.append({'file':file,'sha256':digest(data),'artwork_size':list(im.size),'role':role})
        return file
    poses=deepcopy(recipe['poses'])
    for name,pose in poses.items():
        path=ROOT/pose['source_file'] if pose['source_file'].startswith('assets/') else source/pose['source_file']
        data=path.read_bytes()
        if digest(data)!=pose['source_sha256']:raise ValueError('Authored frame changed: '+name)
        im=image(path)
        if pose.get('source_density',2)==1:
            im=im.resize(tuple(v*2 for v in im.size),Image.Resampling.NEAREST)
        if im.size!=(96,96):raise ValueError('Action canvas changed: '+name)
        if set(im.getchannel('A').tobytes())-{0,255}:raise ValueError('Action edges must be hard alpha')
        if im.getbbox() is None:raise ValueError('Empty action drawing')
        pose.update(logical_size=[48,48],artwork_size=[96,96],artwork_pixels_per_world_pixel=2,
                    draw_anchor_logical=recipe['draw_anchor_logical'],foot_anchor_logical=recipe['foot_anchor_logical'])
        png(pose['file'],im,'complete_action_pose')
    for clip in recipe['clips'].values():
        if not clip['frames'] or any(name not in poses for name in clip['frames']):raise ValueError('Unresolved clip frame')
    pailbank=json.loads((ROOT/recipe['canonical_pail_bank']).read_text());pailroot=(ROOT/recipe['canonical_pail_bank']).parent
    interior=image(pailroot/pailbank['pail']['masks']['interior']).convert('L')
    source_grip=tuple(v*2 for v in pailbank['pail']['grip_logical']);pivot=(32,16);pail_variants=[]
    for angle in recipe['pail_angles']:
        a=math.radians(angle)
        # PIL's positive angle rotates counterclockwise in artwork space.
        def transform(point):
            dx,dy=point[0]-source_grip[0],point[1]-source_grip[1]
            return [pivot[0]+dx*math.cos(a)+dy*math.sin(a),pivot[1]-dx*math.sin(a)+dy*math.cos(a)]
        mask=Image.new('L',(64,64));mask.paste(interior,(round(pivot[0]-source_grip[0]),round(pivot[1]-source_grip[1])))
        mask=mask.rotate(angle,resample=Image.Resampling.NEAREST,center=pivot)
        maskfile=png(f'pails/interior_{angle}.png',mask,'rigid_pail_interior_mask')
        for record in pailbank['pail']['variants']:
            im=image(pailroot/record['file']);canvas=Image.new('RGBA',(64,64));canvas.alpha_composite(im,(round(pivot[0]-source_grip[0]),round(pivot[1]-source_grip[1])))
            canvas=canvas.rotate(angle,resample=Image.Resampling.NEAREST,center=pivot)
            bounds=canvas.getbbox()
            if bounds is None or min(bounds)<1 or bounds[2]>=64 or bounds[3]>=64:raise ValueError('Rigid pail clipping')
            file=png(f'pails/angle_{angle}_fill_{record["units"]}.png',canvas,'canonical_rigid_pail_variant')
            edge=(6,17) if angle>0 else (18,17)
            pail_variants.append({'angle':angle,'units':record['units'],'file':file,'logical_size':[32,32],
                                  'artwork_size':[64,64],'grip_logical':[16,8],'interior_mask':maskfile,
                                  'stream_origin_logical':[v/2 for v in transform(edge)],'source_file':str((pailroot/record['file']).relative_to(ROOT)),
                                  'source_sha256':digest((pailroot/record['file']).read_bytes())})
    manifest={'version':1,'id':recipe['id'],'integration_status':'staged','runtime_activation':False,
              'visual_approval':'pending_user_review','artwork_pixels_per_world_pixel':2,
              'logical_size':[48,48],'artwork_size':[96,96],'draw_anchor_logical':recipe['draw_anchor_logical'],
              'foot_anchor_logical':recipe['foot_anchor_logical'],'poses':poses,'clips':recipe['clips'],
              'pails':{'variants':pail_variants,'canonical_bank':recipe['canonical_pail_bank'],
                       'canonical_bank_sha256':digest((ROOT/recipe['canonical_pail_bank']).read_bytes()),'capacity_units':6},
              'source_recipe':RECIPE,'source_recipe_sha256':digest(raw),'sources':recipe['source_metadata'],
              'mechanism_contract':contract,'travel_policy':recipe['travel_policy'],
              'exporter':'tools/build_gardener_well_hd.py','exporter_sha256':digest(Path(__file__).read_bytes()),
              'exports':exports,'limits':'Staged visual performance only. PR4 owns live routine selection, navigation, water accounting, lifecycle and saving. Compatibility travel bodies retain existing gait.'}
    output[PACK+'/animations.json']=document(manifest)
    return output


def build(check=False):
    output=products();stale=[p for p,b in output.items() if not (ROOT/p).is_file() or (ROOT/p).read_bytes()!=b]
    if check and stale:raise SystemExit('Stale gardener performance exports: '+', '.join(stale))
    if not check:
        for p,b in output.items():
            path=ROOT/p
            if not path.is_file() or path.read_bytes()!=b:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)
    print(f'{len(output)} staged gardener exports '+('verified' if check else 'built'))
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');build(parser.parse_args().check)
