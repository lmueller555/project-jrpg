"""Register authored Rhea/Reaper duel drawings without deforming their poses.

Sources are image_gen authored. Equal-cell extraction, alpha threshold, palette
registration, fixed nearest scaling and foot placement are the only operations.
"""
from pathlib import Path
import hashlib
import json
import shutil

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/ice_reaper_duel/women'
OUTPUT = ROOT/'assets/story/ice_reaper_duel/women'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(tile):
    tile = tile.convert('RGBA')
    alpha = tile.getchannel('A').point(lambda value: 255 if value >= 140 else 0)
    tile = tile.convert('RGB').quantize(colors=128, dither=Image.Dither.NONE).convert('RGBA')
    tile.putalpha(alpha)
    return tile


def register(tile, actor, scale):
    size, anchor = ((128,128),(64,116)) if actor == 'rhea' else ((192,192),(96,172))
    pixels = np.array(tile)
    alpha = pixels[:,:,3] > 0
    bounds = tile.getbbox()
    if bounds is None:
        raise ValueError('Authored cell is empty')
    bottom = bounds[3]-1
    band = np.indices(alpha.shape)[0] >= bottom-max(3,round((bounds[3]-bounds[1])*.065))
    feet = alpha & band
    if actor == 'rhea':
        rgb = pixels[:,:,:3].astype(float)
        brown = (rgb[:,:,0]>rgb[:,:,1]*1.1)&(rgb[:,:,1]>rgb[:,:,2]*1.08)
        if (feet & brown).sum() > 10:
            feet &= brown
    ys,xs = np.where(feet)
    footx = float((xs.min()+xs.max())/2)
    cropped = tile.crop(bounds)
    dimensions = (max(1,round(cropped.width*scale)),max(1,round(cropped.height*scale)))
    cropped = cropped.resize(dimensions,Image.Resampling.NEAREST)
    offset = (round(anchor[0]-(footx-bounds[0])*scale),
              round(anchor[1]-(bottom-bounds[1])*scale))
    if offset[0] < 0 or offset[1] < 0 or offset[0]+dimensions[0] > size[0] or offset[1]+dimensions[1] > size[1]:
        raise ValueError(f'Pose exceeds registered {actor} canvas: {offset}, {dimensions}')
    output = Image.new('RGBA',size)
    output.alpha_composite(cropped,offset)
    return output,dict(content_bounds=list(bounds),foot=[footx,bottom],scale=scale,offset=list(offset))


def export(actor, filename, columns, rows, groups, scale):
    image = Image.open(SOURCE/filename).convert('RGBA')
    target = OUTPUT/actor
    target.mkdir(parents=True,exist_ok=True)
    path = target/'animation.json'
    manifest = json.loads(path.read_text()) if path.exists() else dict(version=1,actor=actor,
        canvas=[128,128] if actor=='rhea' else [192,192],
        anchor=[64,116] if actor=='rhea' else [96,172],body_pixels=82 if actor=='rhea' else 155,
        animations={})
    records=[]
    for name,indices,view in groups:
        sequence=[]
        for index,cell in enumerate(indices,1):
            col,row=cell%columns,cell//columns
            bounds=(round(col*image.width/columns),round(row*image.height/rows),
                    round((col+1)*image.width/columns),round((row+1)*image.height/rows))
            frame,registration=register(clean(image.crop(bounds)),actor,scale)
            file=f'{name}_{index:02}.png'
            frame.save(target/file,optimize=True)
            sequence.append(dict(file=file,duration_ms=70))
            records.append(dict(file=file,source=filename,cell=cell,source_bounds=list(bounds),
                                sha256=sha(target/file),**registration))
        manifest['animations'][name]=dict(frames=sequence,view_azimuth_deg=view,
            loop=name.startswith(('sword_hold','cast_')))
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    return records


def build():
    for actor in ('rhea','ice_reaper'):
        path=OUTPUT/actor/'animation.json'
        if path.exists():path.unlink()
        for old in (OUTPUT/actor).glob('*.png'):old.unlink()
    rhea=export('rhea','rhea_actions_generated.png',4,4,
        [('cast',range(8,14),0.)],.29)
    rhea+=export('rhea','rhea_sweep_corrected_generated.png',4,2,
        [('staff_sweep',range(8),180.)],.20)
    rhea+=export('rhea','rhea_cast_rear_generated.png',3,2,
        [('cast_rear',range(6),180.)],.18)
    reaper=export('ice_reaper','reaper_actions_generated.png',6,3,
        [('sword_conjure',range(6),0.),('sword_windup',range(6,12),0.),
         ('sword_charge',range(12,18),0.)],.52)
    # Nose direction in the authored turnaround determines signed camera view.
    # Right-facing profiles are the actor's left view in our projection basis.
    directions=(('front',0.),('front_left',-45.),('left',-90.),('rear_left',-135.),
                ('rear',180.),('rear_right',135.),('right',90.),('front_right',45.))
    rhea+=export('rhea','rhea_cast_views_generated.png',4,2,
        [(f'cast_hold_{name}',[index],view) for index,(name,view) in enumerate(directions)],.21)
    reaper+=export('ice_reaper','reaper_views_generated.png',4,2,
        [(f'sword_hold_{name}',[index],view) for index,(name,view) in enumerate(directions)],.38)
    portraits=OUTPUT/'portraits';portraits.mkdir(parents=True,exist_ok=True)
    # Keep the approved glowing-eye portrait intact; the dialogue UI scales it.
    portrait=Image.open(SOURCE/'rhea_portrait_generated.png')
    shutil.copyfile(SOURCE/'rhea_portrait_generated.png',portraits/'rhea_awakening.png')
    scene_portrait=ROOT/'assets/story/ice_reaper_opening/portraits/rhea_awakening.png'
    scene_portrait.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(portraits/'rhea_awakening.png',scene_portrait)
    sources={str(p.relative_to(ROOT)):sha(p) for p in sorted(SOURCE.glob('*_generated.png'))}
    references=['assets/source/companions/rhea/design_sheet.png',
        'assets/story/ice_reaper_continuity/actors/rhea/frozen_front_01.png',
        'assets/story/ice_reaper_rescue/actors/ice_reaper/recharge_06.png',
        'assets/story/ice_reaper_rescue/actors/ice_reaper/ready_rear_01.png']
    provenance=dict(version=1,authored_with='image_gen',sources=sources,
        references={name:sha(ROOT/name) for name in references},
        operation='Equal-cell extraction, alpha threshold140,128-color registration,fixed nearest scaling,foot registration only; no pose deformation or painted facial features.',
        frames=dict(rhea=rhea,ice_reaper=reaper),
        portrait=dict(file='portraits/rhea_awakening.png',canvas=list(portrait.size),sha256=sha(portraits/'rhea_awakening.png'),
                      basis='Approved image_gen portrait with green magic filling both eye sockets; copied without pixel changes'))
    (OUTPUT/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(dict(rhea_frames=len(rhea),reaper_frames=len(reaper),portrait=str(portraits/'rhea_awakening.png'))))


if __name__=='__main__':build()
