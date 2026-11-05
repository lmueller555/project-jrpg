"""Register authored facial expressions and the compact winter outfit sprite.

The expression drawings already authored for Rhea are transferred into a fixed
facial mask on her winter body. Hair, shawl, anatomy, staff and alpha remain
identical across expressions. The opening sprite comes from the approved
compact combat-style wardrobe drawing, not a deformation of the large sprite.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/story/rhea_winter'
SOURCE = OUT/'rested/front.png'
OLD = ROOT/'assets/story/rhea_scene_awakening_study/frames'
NAMES = ('neutral_closed', 'strain_begin', 'strain_mid', 'strain_peak',
         'opening_01', 'opening_02', 'angry_open', 'angry_hold')
TIMES = (0., .45, .75, 1.03, 1.3, 1.43, 1.57, 1.8)
OPENNESS = (0., 0., 0., 0., .25, .6, 1., 1.)
# Final native face registration is measured against rested/front.png.
FACE = (56, 44, 64, 51)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def opening():
    """Isolate the approved compact front drawing above the next sheet row."""
    source = ROOT/'assets/source/cinematics/rhea_winter/approved_wardrobe.png'
    sheet = Image.open(source).convert('RGBA')
    # This review sheet is not a uniform animation grid: the larger drawings
    # begin at y434, before the nominal 512px row boundary. Keep the complete
    # first figure (including the staff at x379) and exclude that second row.
    source_box = (0, 0, 512, 400)
    tile = sheet.crop(source_box)
    alpha = tile.getchannel('A').point(lambda value: 255 if value >= 140 else 0)
    tile.putalpha(alpha)
    bounds = tile.getbbox()
    if bounds is None:
        raise ValueError('Empty compact winter candidate')
    pixels = np.asarray(tile)
    occupied = pixels[:,:,3] > 0
    rows = np.flatnonzero(occupied.any(axis=1))
    if not np.all(np.diff(rows) == 1):
        raise ValueError('Opening crop contains separated figure fragments')
    yy = np.indices(occupied.shape)[0]
    rgb = pixels[:,:,:3].astype(float)
    boots = (occupied & (yy >= bounds[3]-24)
             & (rgb[:,:,0] > rgb[:,:,1]*1.1)
             & (rgb[:,:,1] > rgb[:,:,2]*1.08))
    _, foot_x = np.where(boots)
    if not len(foot_x):
        raise ValueError('Opening sprite has no registered boot pixels')
    foot_center = float((foot_x.min()+foot_x.max())/2)
    sprite = tile.crop(bounds)
    # Combat Rhea's existing feet are at (32,54), with 41 native body pixels.
    scale = 41/sprite.height
    size = tuple(max(1, round(value*scale)) for value in sprite.size)
    sprite = sprite.resize(size, Image.Resampling.NEAREST)
    frame = Image.new('RGBA', (64,64))
    offset = (32-round((foot_center-bounds[0])*scale), 54-size[1]+1)
    frame.alpha_composite(sprite, offset)
    frame.save(OUT/'opening.png', optimize=True)
    return dict(file='opening.png', canvas=[64,64], anchor=[32,54],
                source=str(source.relative_to(ROOT)), source_sha256=sha(source),
                source_crop=list(source_box), subject_bounds=list(bounds),
                source_foot_center=foot_center, offset=list(offset),
                sha256=sha(OUT/'opening.png'))


def build():
    folder = OUT/'awakening'
    folder.mkdir(parents=True, exist_ok=True)
    base = np.array(Image.open(SOURCE).convert('RGBA'))
    x0,y0,x1,y1 = FACE
    mask = np.zeros(base.shape[:2], dtype=bool)
    mask[y0:y1, x0:x1] = True
    palette = np.unique(base[base[:,:,3]>0,:3].reshape(-1,3), axis=0).astype(np.int32)
    records, verification, drawings = {}, {}, set()
    contact = Image.new('RGB', (128*4*3, 150*2*3), '#14212c')
    labels = ImageDraw.Draw(contact)
    for index,name in enumerate(NAMES):
        old = Image.open(OLD/(name+'.png')).convert('RGBA')
        patch = old.crop((58,44,65,51)).resize((x1-x0,y1-y0), Image.Resampling.NEAREST)
        pixels = np.asarray(patch)[:,:,:3].astype(np.int32)
        distance = ((pixels[:,:,None,:]-palette[None,None,:,:])**2).sum(axis=3)
        registered = palette[distance.argmin(axis=2)].astype(np.uint8)
        result = base.copy()
        result[y0:y1,x0:x1,:3] = registered
        assert np.array_equal(result[~mask],base[~mask])
        assert np.array_equal(result[:,:,3],base[:,:,3])
        path = folder/(name+'.png')
        frame = Image.fromarray(result)
        frame.save(path, optimize=True)
        drawings.add(result.tobytes())
        eyes = [[x0+(1.5/7)*(x1-x0), y0+(2/7)*(y1-y0)],
                [x0+(5.5/7)*(x1-x0), y0+(2/7)*(y1-y0)]]
        records[name] = dict(file='awakening/'+name+'.png', eyes=eyes,
                             openness=OPENNESS[index], start=TIMES[index])
        verification[name] = dict(sha256=sha(path),
            protected_pixels_unchanged=True, source_expression=sha(OLD/(name+'.png')))
        pos = (index%4*384,index//4*450)
        enlarged = frame.resize((384,384),Image.Resampling.NEAREST)
        contact.paste(enlarged,pos,enlarged)
        labels.text((pos[0]+8,pos[1]+392),name,fill='white')
    if len(drawings) != 8:
        raise ValueError('Expression registration collapsed distinct authored drawings')
    manifest = dict(canvas=[128,128], anchor=[64,116], body_pixels=82,
        source=str(SOURCE.relative_to(ROOT)), source_sha256=sha(SOURCE),
        frames=records, sequence=list(NAMES),
        facial_mask_rows={str(y):[x0,x1-1] for y in range(y0,y1)},
        operation='Nearest registration of existing image_gen-authored facial drawings into the winter face mask; no body or cloth deformation.',
        verification=verification)
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    contact.save(folder/'contact_sheet.png',optimize=True)
    record = opening()
    (OUT/'opening_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(expressions=len(drawings),opening=record['file'],face=FACE)))


if __name__ == '__main__':
    build()
