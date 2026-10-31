"""Export registered imagegen-authored arrival actors without repainting sources.

Only alpha cleanup, bounded crops, horizontal orientation and nearest resizing
are used. Original generations and prompts remain in assets/source/cinematics.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
from collections import deque
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/cinematics/regent_arrival/actors'
TARGET=ROOT/'assets/story/regent_arrival/actors'

def digest(data):return hashlib.sha256(data).hexdigest()

def clean(image):
    image=image.convert('RGBA')
    alpha=image.getchannel('A').point(lambda a:255 if a>=128 else 0)
    # Discard isolated matte specks outside the authored silhouette. This does
    # not recolor or paint any part of an actor.
    pixels=alpha.load();seen=set();w,h=alpha.size
    for y in range(h):
        for x in range(w):
            if not pixels[x,y] or (x,y) in seen:continue
            queue=deque([(x,y)]);seen.add((x,y));component=[]
            while queue:
                px,py=queue.popleft();component.append((px,py))
                for nx,ny in ((px-1,py),(px+1,py),(px,py-1),(px,py+1)):
                    if 0<=nx<w and 0<=ny<h and pixels[nx,ny] and (nx,ny) not in seen:
                        seen.add((nx,ny));queue.append((nx,ny))
            if len(component)<16:
                for px,py in component:pixels[px,py]=0
    image.putalpha(alpha)
    return image

def cell(sheet,col,row,columns=4,rows=4,row_bounds=None):
    w,h=sheet.size
    top,bottom=((row_bounds[row],row_bounds[row+1]) if row_bounds
                else (round(row*h/rows),round((row+1)*h/rows)))
    return clean(sheet.crop((round(col*w/columns),top,
                             round((col+1)*w/columns),bottom)))

def foot_center(image):
    box=image.getbbox();a=image.getchannel('A');coords=[]
    for y in range(max(box[1],box[3]-18),box[3]):
        for x in range(box[0],box[2]):
            if a.getpixel((x,y)):coords.append(x)
    return sum(coords)/len(coords),box[3]

def png(image):
    data=io.BytesIO();image.save(data,format='PNG',optimize=True);return data.getvalue()

def build():
    sheets={name:Image.open(SOURCE/(name+'_generated.png')).convert('RGBA')
            for name in ('travelers','household','caravan','walks','back_views','back_vehicle_refined')}
    # Source sheets are authored rows with unequal transparent gutters. The
    # explicit cell boundaries prevent a neighboring row's boots from entering
    # another actor's frame; no generated subject is trimmed to a uniform grid.
    row_bounds={'travelers':[0,325,635,948,1282],
                'household':[0,355,690,1022,1282],
                'walks':[0,475,887],
                'back_views':[0,555,1024],
                'back_vehicle_refined':[0,555,1024]}
    records={
      'aldric':{'height':80,'frames':{
        'stand_left':('travelers',0,0,True),'listen_left':('travelers',1,0,True),
        'gesture_left':('travelers',2,0,False),'walk_0':('travelers',3,0,False),
        'walk_1':('travelers',0,1,False),'walk_2':('travelers',1,1,False),
        'walk_3':('travelers',2,1,False),'stand_right':('travelers',3,1,False),
        'stand_back':('back_views',0,1,False),'walk_back_0':('back_views',0,1,False),
        'walk_back_1':('back_views',1,1,False),'walk_back_2':('back_views',2,1,False),
        'walk_back_3':('back_views',3,1,False)},
        'loops':{'walk_left':['walk_0','walk_1','walk_2','walk_3'],
                 'walk_back':['walk_back_0','walk_back_1','walk_back_2','walk_back_3']}},
      'guard':{'height':80,'frames':{
        'stand_right':('travelers',0,2,False),'gesture_right':('travelers',1,2,False),
        'step_0':('walks',0,0,False),'step_1':('walks',1,0,False),
        'step_2':('walks',2,0,False),'step_3':('walks',3,0,False)},
        'loops':{'step_right':['step_0','step_1','step_2','step_3']}},
      'clerk':{'height':77,'frames':{
        'stand_left':('travelers',0,3,False),'read_left':('travelers',1,3,False)},'loops':{}},
      'driver':{'height':77,'frames':{
        'stand_left':('travelers',2,3,False),'seated_left':('household',0,2,False),
        'walk_0':('household',1,2,False),'walk_1':('household',2,2,False)},
        'loops':{'walk_left':['walk_0','stand_left','walk_1','stand_left']}},
      'local':{'height':77,'frames':{
        'stand_right':('travelers',3,3,False),'talk_right':('household',3,2,False)},'loops':{}},
      'serene':{'height':78,'frames':{
        'window_left':('household',0,0,False),'stand_right':('household',1,0,False),
        'turn_right':('household',2,0,False),'walk_0':('walks',0,1,False),
        'walk_1':('walks',1,1,False),'walk_2':('walks',2,1,False),
        'walk_3':('walks',3,1,False)},
        'loops':{'walk_right':['walk_0','walk_1','walk_2','walk_3']}},
      'tomas':{'height':66,'frames':{
        'cups_left':('household',0,1,False),'cups_raised_left':('household',1,1,False),
        'stand_left':('household',2,1,False),'carry_left':('household',3,1,False)},'loops':{}}
    }
    outputs={};metadata={}
    for name,record in records.items():
        frames={pose:cell(sheets[src],col,row,row_bounds=row_bounds[src]) for pose,(src,col,row,flip) in record['frames'].items()}
        # Register each source sheet at a shared native bodily height. A seated
        # driver keeps the standing sheet's scale instead of stretching upright.
        reference=frames.get('stand_left',frames.get('stand_right',next(iter(frames.values()))))
        scale=record['height']/(reference.getbbox()[3]-reference.getbbox()[1])
        for pose,frame in frames.items():
            frame_scale=scale
            frame_source=record['frames'][pose][0]
            if frame_source in ('walks','back_views'):
                group=[f for key,f in frames.items() if record['frames'][key][0]==frame_source]
                frame_scale=record['height']/max(f.getbbox()[3]-f.getbbox()[1] for f in group)
            flip=record['frames'][pose][3]
            if flip:frame=ImageOps.mirror(frame)
            fx,fy=foot_center(frame)
            box=frame.getbbox();crop=frame.crop(box)
            size=(max(1,round(crop.width*frame_scale)),max(1,round(crop.height*frame_scale)))
            crop=crop.resize(size,Image.Resampling.NEAREST)
            sprite=Image.new('RGBA',(80,96))
            x=round(40-(fx-box[0])*frame_scale);y=92-round((fy-box[1])*frame_scale)
            if x<0 or x+crop.width>80 or y<0 or y+crop.height>96:
                raise ValueError(f'Actor {name}/{pose} exceeds registered canvas')
            sprite.alpha_composite(crop,(x,y))
            outputs[f'{name}/{pose}.png']=png(sprite)
        manifest={'version':1,'canvas':[80,96],'anchor':[40,92],
                  'poses':{pose:pose+'.png' for pose in frames if not pose.startswith('walk_') and not pose.startswith('step_')},
                  'loops':{loop:[{'file':pose+'.png','duration_ms':160 if name=='aldric' else 180} for pose in sequence]
                           for loop,sequence in record['loops'].items()},
                  'source':'imagegen-authored; deterministic crop/alpha/orientation/nearest export'}
        outputs[f'{name}/animation.json']=(json.dumps(manifest,indent=2)+'\n').encode()
        metadata[name]={'canvas':[80,96],'anchor':[40,92],'reference_height':record['height'],'scale':round(scale,6)}
    # Export four registered whole horse/wagon frames. Fixed cell crop+scale
    # keeps wagon construction and wheel centers consistent across the walk.
    wagon_frames=[cell(sheets['caravan'],col,row,2,2) for row in range(2) for col in range(2)]
    scale=280/max(frame.getbbox()[2]-frame.getbbox()[0] for frame in wagon_frames)
    boxes=[frame.getbbox() for frame in wagon_frames]
    floor=max(b[3] for b in boxes)
    left=min(b[0] for b in boxes)
    for index,frame in enumerate(wagon_frames):
        box=(left,min(b[1] for b in boxes),max(b[2] for b in boxes),floor)
        crop=frame.crop(box).resize((round((box[2]-box[0])*scale),round((box[3]-box[1])*scale)),Image.Resampling.NEAREST)
        sprite=Image.new('RGBA',(300,144));sprite.alpha_composite(crop,(10,136-crop.height))
        outputs[f'caravan/walk_{index}.png']=png(sprite)
    manifest={'version':1,'canvas':[300,144],'anchor':[150,136],
              'poses':{'parked_left':'walk_0.png','stand_left':'walk_0.png',
                       'parked_back':'walk_back_0.png'},
              'loops':{'walk_left':[{'file':f'walk_{i}.png','duration_ms':200} for i in range(4)],
                       'walk_back':[{'file':f'walk_back_{i}.png','duration_ms':200} for i in range(4)]},
              'driver_offset':[-4,-28],'driver_seated_pose':'seated_left',
              'driver_baked_poses':['walk_back','parked_back'],
              'source':'imagegen-authored horse/provision wagon; rear view includes its correctly back-facing driver'}
    backs=[cell(sheets['back_vehicle_refined'],col,0,row_bounds=row_bounds['back_vehicle_refined']) for col in range(4)]
    scale=130/max(frame.getbbox()[3]-frame.getbbox()[1] for frame in backs)
    for index,frame in enumerate(backs):
        box=frame.getbbox();crop=frame.crop(box)
        size=(round(crop.width*scale),round(crop.height*scale))
        if size[0]>110:raise ValueError('Rear caravan exceeds gate admission width')
        crop=crop.resize(size,Image.Resampling.NEAREST)
        sprite=Image.new('RGBA',(300,144));sprite.alpha_composite(crop,(150-crop.width//2,136-crop.height))
        outputs[f'caravan/walk_back_{index}.png']=png(sprite)
    outputs['caravan/animation.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    metadata['caravan']={'canvas':[300,144],'anchor':[150,136],'driver_offset':[-4,-28],
                         'rear_max_width':110,'rear_height':130,'rear_driver_baked':True}
    for col,name in enumerate(('guard','local','clerk','driver')):
        portrait=cell(sheets['household'],col,3,row_bounds=row_bounds['household'])
        box=portrait.getbbox();portrait=portrait.crop(box)
        # Preserve all head-and-shoulder art inside a common square frame.
        side=max(portrait.size);square=Image.new('RGBA',(side,side))
        square.alpha_composite(portrait,((side-portrait.width)//2,side-portrait.height))
        outputs[f'portraits/{name}.png']=png(square.resize((72,72),Image.Resampling.NEAREST))
    provenance={'version':1,'exporter':'tools/build_regent_arrival_actors.py',
      'sources':{str((SOURCE/(name+'_generated.png')).relative_to(ROOT)):digest((SOURCE/(name+'_generated.png')).read_bytes()) for name in sheets},
      'actors':metadata,'exports':{name:digest(data) for name,data in sorted(outputs.items())},
      'notes':['Original imagegen generations are retained without modification.',
               'Only alpha cleanup, bounded crops, horizontal registration and nearest resizing are applied.',
               'Human sprites are authored cinematic bodies rather than enlarged overworld sprites.',
               'Aldric has natural stride and restrained conversational poses; caravan uses four complete horse-walk frames.',
               'Supporting portraits match this cinematic cast; existing Aldric, Serene and Tomas portraits remain authoritative.']}
    outputs['provenance.json']=(json.dumps(provenance,indent=2)+'\n').encode()
    return outputs

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    outputs=build()
    if args.check:
        for name,data in outputs.items():
            path=TARGET/name
            if not path.is_file() or path.read_bytes()!=data:raise SystemExit(f'Out of date actor export: {name}')
        print(f'Verified {len(outputs)} registered actor/portrait exports')
    else:
        for name,data in outputs.items():
            path=TARGET/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        print(f'Exported {len(outputs)} registered actor/portrait files')
    return 0

if __name__=='__main__':raise SystemExit(main())
