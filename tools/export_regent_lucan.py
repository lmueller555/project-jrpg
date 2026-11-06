"""Register approved Lucan travel drawings for the regent's cinematic.

Ground cells are sampled from retained adult cinematic travel drawings, rather
than enlarged overworld rasters. The two bird-camera drawings have their own
retained source and keep the existing aerial cast's registration.
No existing character, pose, portrait or camera plate is repainted.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/regent_arrival/actors/lucan'
GROUND = ROOT/'assets/story/regent_arrival/actors'
AERIAL = ROOT/'assets/story/regent_aerial/actors'


def sha(data):return hashlib.sha256(data).hexdigest()


def encoded(image):
    stream = io.BytesIO();image.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def json_bytes(value):return (json.dumps(value, indent=2)+'\n').encode()


def registered(image, bounds, origin, scale, canvas=(80,96), anchor=(40,92)):
    """One uniform source scale around the approved body/ground registration."""
    image = image.convert('RGBA')
    image.putalpha(image.getchannel('A').point(lambda value:255 if value >= 128 else 0))
    crop = image.crop(bounds)
    crop = crop.resize((round(crop.width*scale), round(crop.height*scale)), Image.Resampling.NEAREST)
    offset = (round(anchor[0]-(origin[0]-bounds[0])*scale),
              round(anchor[1]-(origin[1]-bounds[1])*scale))
    if (min(offset) < 0 or offset[0]+crop.width > canvas[0]
            or offset[1]+crop.height > canvas[1]):
        raise ValueError('Lucan drawing exceeds its registered canvas')
    output = Image.new('RGBA', canvas);output.alpha_composite(crop, offset)
    return output


def ground_outputs():
    outputs = {};poses = {};loops = {};registrations = {}
    recipe_path = SOURCE/'travel_source.json'
    recipe = json.loads(recipe_path.read_text())
    source_path = SOURCE/recipe['source']
    if sha(source_path.read_bytes()) != recipe['source_sha256']:
        raise ValueError('Lucan cinematic travel original changed')
    sources = {source_path.relative_to(ROOT).as_posix():sha(source_path.read_bytes()),
               recipe_path.relative_to(ROOT).as_posix():sha(recipe_path.read_bytes())}
    for filename,expected in recipe['references'].items():
        if sha((ROOT/filename).read_bytes()) != expected:
            raise ValueError('Approved Lucan or cinematic cast reference changed')
        sources[filename] = expected
    image = Image.open(source_path).convert('RGBA')
    image.putalpha(image.getchannel('A').point(lambda value:255 if value >= recipe['alpha_threshold'] else 0))
    for direction,record in recipe['directions'].items():
        drawings = [record['standing'],*record['frames']]
        scale = 80/max(cell['bounds'][3]-cell['bounds'][1] for cell in drawings)
        for index,cell in enumerate(drawings):
            filename = f'stand_{direction}.png' if index == 0 else f'walk_{direction}_{index-1}.png'
            outputs['lucan/'+filename] = encoded(registered(image,cell['bounds'],cell['anchor'],scale))
            registrations[filename] = {'source':source_path.relative_to(ROOT).as_posix(),
                'bounds':cell['bounds'],'source_anchor':cell['anchor'],'scale':scale}
        poses['stand_'+direction] = f'stand_{direction}.png'
        loops['walk_'+direction] = [{'file':f'walk_{direction}_{i}.png','duration_ms':140,
                                     'phase':phase} for i,phase in enumerate(recipe['phases'])]
    # The gate's diagonal uses the closest existing rear direction. It is an
    # explicit view alias, not a distorted or synthetic extra body drawing.
    loops['walk_left_back'] = loops['walk_back']
    poses['turn_left_back'] = poses['stand_back']
    manifest = {'version':1,'canvas':[80,96],'anchor':[40,92],
        'poses':poses,'loops':loops,
        'gaits':{key:{'stride_pixels':32} for key in loops},
        'source':'imagegen-authored cinematic travel poses matching approved tall Lucan identity and adult regent cast proportions; registered nearest export',
        'view_aliases':{'walk_left_back':'walk_back','turn_left_back':'stand_back'}}
    outputs['lucan/animation.json'] = json_bytes(manifest)
    outputs['lucan/provenance.json'] = json_bytes({'version':1,
        'exporter':'tools/export_regent_lucan.py','sources':sources,'registrations':registrations,
        'exports':{name:sha(data) for name,data in outputs.items()},
        'notes':['No approved source or existing cinematic actor pixels were changed.',
                 'Ten new travel drawings reuse the approved adult cinematic identity, not chibi overworld proportions.',
                 'Four distinct authored stride drawings per direction; no limb morphs or synthetic extra phases.',
                 'A shared body scale and row foot baseline retain natural stride rise.',
                 'Rear-quarter route uses the explicitly recorded closest rear-view alias.']})
    return outputs, sources


def aerial_outputs():
    source_path = SOURCE/'aerial_generated.png'
    recipe_path = SOURCE/'aerial_source.json'
    recipe = json.loads(recipe_path.read_text())
    if sha(source_path.read_bytes()) != recipe['source_sha256']:
        raise ValueError('Lucan aerial original changed')
    image = Image.open(source_path).convert('RGBA');outputs = {};poses = {}
    for pose,record in recipe['poses'].items():
        scale = record['height']/(record['bounds'][3]-record['bounds'][1])
        anchor = ((record['bounds'][0]+record['bounds'][2])/2,record['bounds'][3])
        outputs['lucan/'+pose+'.png'] = encoded(registered(image,record['bounds'],anchor,scale,
                                                          canvas=(48,64),anchor=(24,56)))
        poses[pose] = pose+'.png'
    outputs['lucan/animation.json'] = json_bytes({'version':1,'canvas':[48,64],
        'anchor':[24,56],'poses':poses,'loops':{},'overhead_facing':'north',
        'oblique_facing':'northwest','source':'imagegen-authored camera-specific Lucan travel poses; approved identity, lowered shield and low-carried sword',
        'source_recipe':recipe_path.relative_to(ROOT).as_posix()})
    outputs['lucan/provenance.json'] = json_bytes({'version':1,
        'exporter':'tools/export_regent_lucan.py',
        'sources':{source_path.relative_to(ROOT).as_posix():sha(source_path.read_bytes()),
                   recipe_path.relative_to(ROOT).as_posix():sha(recipe_path.read_bytes())},
        'exports':{name:sha(data) for name,data in outputs.items()}})
    return outputs


def main():
    ground,_ = ground_outputs();aerial = aerial_outputs()
    for directory,outputs in ((GROUND,ground),(AERIAL,aerial)):
        for name,data in outputs.items():
            path = directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    print(f'Exported {len(ground)} ground and {len(aerial)} aerial Lucan files')


if __name__ == '__main__':main()
