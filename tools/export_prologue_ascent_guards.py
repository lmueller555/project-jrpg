"""Export complete ImageGen-authored ascent guard artwork, without pose transforms."""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/fire_veinhold/bridge_ascent/guards'
OUTPUT = ROOT/'assets/story/fire_veinhold_opening/shot08/guards'
FROZEN = (
    ('carcovian_guard_1','left_back',(0,0,600,656),(3.2,.7,.1)),
    ('carcovian_guard_2','right_mid',(0,656,600,1312),(-2.5,1.6,.1)),
    ('carcovian_guard_3','left_front',(600,0,1199,656),(1.2,3,.1)),
    ('carcovian_guard_4','right_back',(600,656,1199,1312),(-4.6,.6,.1)),
)


def png(image):
    stream=BytesIO()
    image.save(stream,format='PNG',compress_level=6)
    return stream.getvalue()


def products():
    raw_path=SOURCE/'frozen_60_master.png'
    master=Image.open(raw_path).convert('RGBA')
    if master.size!=(1199,1312):
        raise ValueError('Frozen source dimensions changed; review the full atlas before adoption')
    outputs={};frozen=[];records=[]
    for identifier,name,cell,world in FROZEN:
        image=master.crop(cell)
        image.putalpha(image.getchannel('A').point(lambda value:0 if value<=16 else value))
        name=f'frozen_{name}.png'
        payload=png(image)
        outputs[OUTPUT/name]=payload
        record={'id':identifier,'source':name,'cell':[0,0,*image.size],
                'anchor':[300,560],'art_pixels_per_metre':400,
                'world_position_metres':list(world),'view_elevation_degrees':60}
        frozen.append(record)
        records.append({**record,'source_master':'frozen_60_master.png','source_cell':list(cell),
                        'source_sha256':sha256(raw_path.read_bytes()).hexdigest(),
                        'sha256':sha256(payload).hexdigest(),
                        'registration':'Fixed 400 source pixels per metre for all four elevated frozen poses, with the ground root near supported feet. Whole-cell sampling only; no occupied-height fitting.'})
    live_path=SOURCE/'live_source_art.json'
    live=None
    if live_path.exists():
        live_source=json.loads(live_path.read_text())
        if len(live_source.get('frames',[]))!=16:
            raise ValueError('Review sixteen complete live guard poses before export')
        live={'canvas':live_source['canvas'],'anchor':live_source['anchor'],
              'art_pixels_per_metre':live_source['art_pixels_per_metre'],
              'view_elevation_degrees':live_source['view_elevation_degrees'],
              'heading_world':[0,-1,0],'cycle_ms':800,'frame_ms':50,'frames':[]}
        for index,frame in enumerate(live_source['frames']):
            path=SOURCE/frame['source'];source=Image.open(path).convert('RGBA')
            if sha256(path.read_bytes()).hexdigest()!=frame['source_sha256']:
                raise ValueError('Live source master changed: '+str(path))
            image=source.crop(tuple(frame['cell']))
            image.putalpha(image.getchannel('A').point(lambda value:0 if value<=16 else value))
            filename=f'live_{index:02d}.png';payload=png(image)
            outputs[OUTPUT/filename]=payload
            live['frames'].append({'file':filename})
            records.append({'frame':index,'source_master':frame['source'],
                            'source_cell':frame['cell'],'source_sha256':frame['source_sha256'],
                            'sha256':sha256(payload).hexdigest()})
    data={'version':1,'frozen':frozen}
    if live is not None:data['live']=live
    data['source_sha256']={path.name:sha256(payload).hexdigest()
        for path,payload in outputs.items() if path.suffix=='.png'}
    outputs[OUTPUT/'guardperformance.json']=(json.dumps(data,indent=2)+'\n').encode()
    provenance={'version':1,'exporter_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
                'alpha_floor':16,'construction':'Whole ImageGen-painted figures. Only source-cell extraction and documented alpha floor; no limb transforms, recoloring or blended anatomy.',
                'pose_mapping':'Painted frozen-stage spatial mapping: 1 left_back, 2 right_mid, 3 left_front, 4 right_back; old procedural pose indexes are not the painted layout.',
                'registrations':records}
    outputs[OUTPUT/'provenance.json']=(json.dumps(provenance,indent=2)+'\n').encode()
    return outputs


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();outputs=products()
    for path,payload in outputs.items():
        if args.check:
            if not path.exists() or path.read_bytes()!=payload:
                raise ValueError('Stale ascent guard export: '+str(path))
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
    print(f'{len(outputs)} complete guard source/export products reproduce.')


if __name__=='__main__':
    main()
