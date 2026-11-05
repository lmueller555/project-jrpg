"""Register image_gen-authored winter actions without deforming their poses.

Only equal-cell extraction, alpha thresholding, nearest pixel registration and
fixed anatomical scaling are applied. Hair and shawl motion is drawn in source
frames; no mesh, warp, rotation, or body-part deformation is performed.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/rhea_winter/actions'
OUTPUT = ROOT/'assets/story/rhea_winter/actions'
CANVAS = (128, 128)
ANCHOR = (64, 116)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract(tile, scale):
    tile = tile.convert('RGBA')
    alpha = tile.getchannel('A').point(lambda value: 255 if value >= 140 else 0)
    tile = tile.convert('RGB').quantize(colors=128, dither=Image.Dither.NONE).convert('RGBA')
    tile.putalpha(alpha)
    bounds = tile.getbbox()
    if bounds is None:
        raise ValueError('Empty authored frame')
    rgba = np.asarray(tile)
    yy, xx = np.indices(rgba.shape[:2])
    bottom = bounds[3]-1
    rgb = rgba[:, :, :3].astype(float)
    boots = (rgba[:, :, 3] > 0) & (yy >= bottom-max(3, round((bounds[3]-bounds[1])*.065)))
    brown = (rgb[:, :, 0] > rgb[:, :, 1]*1.1) & (rgb[:, :, 1] > rgb[:, :, 2]*1.08)
    if (boots & brown).sum() > 10:
        boots &= brown
    ys, xs = np.where(boots)
    footx = float((xs.min()+xs.max())/2)
    crop = tile.crop(bounds)
    size = tuple(max(1, round(value*scale)) for value in crop.size)
    crop = crop.resize(size, Image.Resampling.NEAREST)
    offset = (round(ANCHOR[0]-(footx-bounds[0])*scale),
              round(ANCHOR[1]-(bottom-bounds[1])*scale))
    if min(offset) < 0 or offset[0]+size[0] > CANVAS[0] or offset[1]+size[1] > CANVAS[1]:
        raise ValueError(f'Frame overflows existing scene registration: {offset}, {size}')
    output = Image.new('RGBA', CANVAS)
    output.alpha_composite(crop, offset)
    # Nearest sampling can round the final opaque boot row one pixel beyond
    # the analytical source-foot transform. Register the actual raster feet.
    bottom_delta = ANCHOR[1]-(output.getbbox()[3]-1)
    if bottom_delta:
        translated = Image.new('RGBA', CANVAS)
        translated.alpha_composite(output, (0, bottom_delta))
        output = translated
        offset = (offset[0], offset[1]+bottom_delta)
    return output, dict(source_bounds=list(bounds), foot=[footx, bottom],
                        scale=scale, offset=list(offset), raster_foot_y=ANCHOR[1])


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = dict(version=1, actor='rhea', canvas=list(CANVAS), anchor=list(ANCHOR),
                    body_pixels=82, animations={})
    records = []
    contact = Image.new('RGB', (128*8*2, 146*3*2), (19, 28, 37))
    draw = ImageDraw.Draw(contact)
    for row, (name, columns, rows, count, scale, angle) in enumerate((
            ('staff_sweep', 4, 2, 8, .20, 180.),
            ('cast', 3, 2, 6, .18, 0.),
            ('cast_rear', 3, 2, 6, .18, 180.))):
        source = SOURCE/(name+'_generated.png')
        sheet = Image.open(source).convert('RGBA')
        frames = []
        for index in range(count):
            col, cellrow = index % columns, index // columns
            bounds = (round(col*sheet.width/columns), round(cellrow*sheet.height/rows),
                      round((col+1)*sheet.width/columns), round((cellrow+1)*sheet.height/rows))
            frame, registration = extract(sheet.crop(bounds), scale)
            filename = f'{name}_{index+1:02}.png'
            frame.save(OUTPUT/filename, optimize=True)
            frames.append(dict(file=filename, duration_ms=100 if name=='staff_sweep' else 175))
            records.append(dict(file=filename, source=str(source.relative_to(ROOT)),
                                cell=index, cell_bounds=list(bounds), sha256=digest(OUTPUT/filename),
                                **registration))
            enlarged = frame.resize((256,256), Image.Resampling.NEAREST)
            contact.paste(enlarged, (index*256, row*292), enlarged)
            draw.text((index*256+8, row*292+262), f'{name} {index+1}', fill='white')
        manifest['animations'][name] = dict(frames=frames, view_azimuth_deg=angle, loop=False,
                                           energy_cloth=True, authored_drawings=count)
    (OUTPUT/'animation.json').write_text(json.dumps(manifest, indent=2)+'\n')
    provenance = dict(version=1, authored_with='image_gen',
        purpose='Winter-shawl casting and staff sweep with authored hair/cloth energy motion',
        operation='Equal-cell extraction; alpha threshold140;128-color registration; fixed nearest scaling and foot registration only.',
        sources={str(path.relative_to(ROOT)):digest(path) for path in sorted(SOURCE.glob('*_generated.png'))},
        records=records)
    (OUTPUT/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    contact.save(OUTPUT/'contact_sheet.png', optimize=True)
    print(json.dumps(dict(frames=len(records), canvas=CANVAS, anchor=ANCHOR)))


if __name__ == '__main__':
    build()
