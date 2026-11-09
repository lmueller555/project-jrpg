"""Register authored gearblade water and combat drawings without pose warping.

Sources are image_gen-authored equal-cell atlases. Only alpha cleanup, uniform
nearest-neighbor scaling, palette registration and fixed foot anchoring occur.
The combat canvas has extra blade margin while retaining the original body
height and an explicit new anchor; no equipment is mirrored.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_ice_reaper_continuity_views import remove_detached_cell_bleed

SOURCE = ROOT/'assets/source/cinematics/gearblade_focus'
TARGET = ROOT/'assets/story/gearblade_focus'
REVIEW = ROOT/'docs/reviews/gearblade_focus'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract(path, columns, rows):
    sheet = Image.open(path).convert('RGBA')
    cells = []
    for row in range(rows):
        for col in range(columns):
            box = (round(col*sheet.width/columns), round(row*sheet.height/rows),
                   round((col+1)*sheet.width/columns), round((row+1)*sheet.height/rows))
            cell = sheet.crop(box)
            cell.putalpha(cell.getchannel('A').point(lambda alpha: 255 if alpha >= 140 else 0))
            cell = remove_detached_cell_bleed(cell)
            if not cell.getbbox():raise ValueError('Empty source cell')
            cells.append((cell, box))
    return cells


def brown_mask(image):
    a = np.asarray(image).astype(float)
    return ((a[:,:,3] > 0) & (a[:,:,0] > a[:,:,1]*1.12) &
            (a[:,:,1] > a[:,:,2]*1.14) & (a[:,:,0] < 215))


def body_height(image):
    ys, _ = np.where(brown_mask(image))
    return int(ys.max()-ys.min()+1)


def register(image, scale, canvas, foot_anchor):
    bounds = image.getbbox()
    mask = brown_mask(image)
    ys, xs = np.where(mask)
    bottom = int(ys.max())
    band = mask.copy()
    band[:max(bounds[1], bottom-round(body_height(image)*.14))] = False
    foot_x = float(np.median(np.where(band)[1]))
    crop = image.crop(bounds)
    resized = crop.resize((max(1,round(crop.width*scale)), max(1,round(crop.height*scale))), Image.Resampling.NEAREST)
    offset = (round(foot_anchor[0]-(foot_x-bounds[0])*scale),
              round(foot_anchor[1]-(bottom-bounds[1])*scale))
    if offset[0] < 0 or offset[1] < 0 or offset[0]+resized.width > canvas[0] or offset[1]+resized.height > canvas[1]:
        raise ValueError(f'Clipped gearblade sprite: {bounds}, {offset}, {resized.size}, {canvas}')
    alpha = resized.getchannel('A')
    resized = resized.convert('RGB').quantize(colors=192, dither=Image.Dither.NONE).convert('RGBA')
    resized.putalpha(alpha)
    frame = Image.new('RGBA', canvas)
    frame.alpha_composite(resized, offset)
    return frame, dict(source_bounds=list(bounds), source_foot=[foot_x,bottom],
                       scale=scale, registration=list(offset))


def build(*, world_only=False):
    REVIEW.mkdir(parents=True, exist_ok=True)
    records = []
    for family, source, columns, rows, canvas, anchor, foot, height in (
        ('world','water_generated.png',4,2,(40,48),(20,38),(20,42),34),
        ('combat','combat_generated.png',4,4,(64,64),(32,56),(32,56),36)):
        if world_only and family != 'world':continue
        target = TARGET/family;target.mkdir(parents=True, exist_ok=True)
        cells = extract(SOURCE/source, columns, rows)
        scale = height/body_height(cells[0][0])
        if family == 'world':
            specs = [('raise_hand',[0,1,2],650),('move_water',[3,4,5],1200),('recover',[6,7],650)]
        else:
            original = json.loads((ROOT/'assets/combat/caelan/animation.json').read_text())
            offset = 0;specs = []
            for name, entry in original['animations'].items():
                count = len(entry['frames'])
                specs.append((name,list(range(offset,offset+count)),sum(f['duration_ms'] for f in entry['frames'])))
                offset += count
        animations = {};provenance = [];contact = []
        for name, indices, duration in specs:
            frames = []
            for i,index in enumerate(indices,1):
                image,box = cells[index]
                frame,registration = register(image, scale, canvas, foot)
                filename = f'{name}_{i:02}.png';frame.save(target/filename,optimize=True)
                frame_ms = (original['animations'][name]['frames'][i-1]['duration_ms'] if family == 'combat'
                            else round(duration/len(indices)))
                frames.append(dict(file=filename,duration_ms=frame_ms))
                provenance.append(dict(file=filename,source_cell=index,source_box=list(box),sha256=sha(target/filename),**registration))
                contact.append((filename,frame))
            animations[name] = dict(frames=frames,duration_ms=duration,
                                    loop=family == 'combat' and original['animations'][name]['loop'])
        manifest = dict(version=1,canvas=list(canvas),anchor=list(anchor),body_pixels=height,
                        sequence=[name for name,_,_ in specs],duration_ms=2500 if family=='world' else None,
                        animations=animations,authored=True,
                        weapon='caelan_gearblade',facing='right' if family=='world' else 'left')
        (target/'animation.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (target/'provenance.json').write_text(json.dumps(dict(version=1,generated_with='image_gen',
            source=str((SOURCE/source).relative_to(ROOT)),source_sha256=sha(SOURCE/source),
            operation=__doc__.strip(),fixed_scale=scale,frames=provenance),indent=2)+'\n')
        sheet = Image.new('RGB',(256*4,288*((len(contact)+3)//4)),'#1c2e35');draw=ImageDraw.Draw(sheet)
        for i,(filename,frame) in enumerate(contact):
            x,y=i%4*256,i//4*288
            enlarged=frame.resize((frame.width*4,frame.height*4),Image.Resampling.NEAREST)
            sheet.paste(enlarged,(x,y),enlarged);draw.text((x+4,y+260),filename,fill='white')
        sheet.save(REVIEW/(family+'_drawings.png'),optimize=True)
        records.append(dict(family=family,frames=len(contact),scale=scale))
    print(json.dumps(records))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--world-only', action='store_true',
                        help='Rebuild the mill water-casting poses without replacing the combat atlas registration.')
    build(world_only=parser.parse_args().world_only)
