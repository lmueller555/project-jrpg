"""Export complete painted frontal running drawings with measured registration.

Artwork owns anatomy, poses, overlap and cloth. This exporter only crops the
recorded source cells, samples each whole figure uniformly, and registers it.
Run --actor while reviewing a single bank, then export/check all three banks.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/fire_veinhold/face_reveal'
OUTPUT = ROOT/'assets/story/fire_veinhold_opening/shot07/characters'
REVIEW = ROOT/'docs/reviews/veinhold_motion_continuity'
ACTORS = ('lucan', 'iselin', 'crown_soldier')


def _json(data):
    return (json.dumps(data, indent=2)+'\n').encode()


def _png(image):
    stream = BytesIO()
    image.save(stream, format='PNG', compress_level=6)
    return stream.getvalue()


def _write(path, data, check):
    if check:
        if not path.is_file() or path.read_bytes() != data:
            raise ValueError('Stale complete-drawing export: '+str(path.relative_to(ROOT)))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def _point(value):
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(type(v) in (int, float) and math.isfinite(v) for v in value))


def build_actor(actor, check=False):
    folder = SOURCE/actor
    profile = folder/'source_art_48.json'
    data = json.loads(profile.read_text())
    canvas, anchor = data.get('canvas'), data.get('anchor')
    count, cycle = len(data.get('frames', [])), data.get('cycle_ms')
    alpha_floor = data.get('alpha_floor', 16)
    if (data.get('version') != 1 or data.get('actor') != actor
            or canvas not in ([768,1024], [1024,1024]) or not _point(anchor)
            or not 0 < anchor[0] < canvas[0] or not 0 < anchor[1] < canvas[1]
            or count < 8 or count > 64 or count % 2
            or type(alpha_floor) is not int or not 0 <= alpha_floor <= 32
            or type(cycle) not in (int, float) or not math.isfinite(cycle) or cycle <= 0
            or data.get('contacts') != [{'frame':0,'foot':'near'}, {'frame':count//2,'foot':'far'}]):
        raise ValueError('Expected a registered complete two-step source profile for '+actor)
    frame_ms = cycle/count
    images, hashes, animation, registrations, drawings = {}, {}, [], [], []
    hashes[profile.relative_to(ROOT).as_posix()] = sha256(profile.read_bytes()).hexdigest()
    for name, expected in data.get('source_sha256', {}).items():
        source = (folder/name).resolve()
        if not source.is_relative_to(folder.resolve()) or not source.is_file():
            raise ValueError('Missing or unconfined authored source: '+name)
        actual = sha256(source.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('Authored source changed after registration: '+name)
        hashes[source.relative_to(ROOT).as_posix()] = actual
    for index, record in enumerate(data['frames']):
        name = record.get('source')
        if not isinstance(name, str) or Path(name).is_absolute():
            raise ValueError('Running source paths must be relative to the actor folder')
        path = (folder/name).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file():
            raise ValueError('Running source leaves or is missing from its actor folder')
        if path not in images:
            images[path] = Image.open(path).convert('RGBA')
            hashes[path.relative_to(ROOT).as_posix()] = sha256(path.read_bytes()).hexdigest()
        master = images[path]
        cell = record.get('cell')
        if (not isinstance(cell, list) or len(cell) != 4 or any(type(v) is not int for v in cell)
                or not 0 <= cell[0] < cell[2] <= master.width
                or not 0 <= cell[1] < cell[3] <= master.height):
            raise ValueError(f'Invalid {actor} source cell {index}')
        scale, origin = record.get('scale'), record.get('origin')
        if (type(scale) not in (int, float) or not math.isfinite(scale) or not 0 < scale <= 4
                or not _point(origin)):
            raise ValueError(f'Invalid {actor} whole-drawing registration {index}')
        crop = master.crop(tuple(cell))
        if crop.getchannel('A').getextrema()[0] > alpha_floor:
            raise ValueError(f'Complete drawing needs a transparent background {actor}:{index}')
        # Generated masters can contain vivid hidden RGB in near-transparent
        # hair-edge pixels. Discard only the documented low-opacity fringe;
        # preserve the original master and all substantive painted anatomy.
        crop.putalpha(crop.getchannel('A').point(lambda alpha:0 if alpha <= alpha_floor else alpha))
        size = (max(1, round(crop.width*scale)), max(1, round(crop.height*scale)))
        # Premultiplied-alpha sampling prevents hidden RGB from coloring edges.
        sampled = crop.convert('RGBa').resize(size, Image.Resampling.LANCZOS).convert('RGBA')
        applied_origin = (round(origin[0]), round(origin[1]))
        solid = sampled.getchannel('A').point(lambda alpha:255 if alpha >= 16 else 0)
        bounds = solid.getbbox()
        if bounds is None:
            raise ValueError(f'Empty complete drawing {actor}:{index}')
        placed_bounds = [bounds[0]+applied_origin[0], bounds[1]+applied_origin[1],
                         bounds[2]+applied_origin[0], bounds[3]+applied_origin[1]]
        if min(placed_bounds[:2]) < 0 or max(placed_bounds[::2]) > canvas[0] or max(placed_bounds[1::2]) > canvas[1]:
            raise ValueError(f'Whole drawing clips its canvas {actor}:{index}: {placed_bounds}')
        frame = Image.new('RGBA', tuple(canvas))
        frame.alpha_composite(sampled, applied_origin)
        filename = f'frame_{index:02d}.png'
        pixels = _png(frame)
        _write(OUTPUT/actor/filename, pixels, check)
        source_landmarks = record.get('landmarks', {})
        if not isinstance(source_landmarks, dict):
            raise ValueError('Landmarks must be named source-cell points or null when hidden')
        landmarks = {}
        for label, point in source_landmarks.items():
            if point is None:
                landmarks[label] = None
            elif _point(point):
                landmarks[label] = [round(point[i]*scale+applied_origin[i], 4) for i in (0,1)]
            else:
                raise ValueError(f'Invalid source-cell landmark {actor}:{index}:{label}')
        animation.append({'file':filename, 'duration_ms':frame_ms, 'landmarks':landmarks,
                          'notes':record.get('notes', '')})
        registrations.append({'frame':index, 'source':name, 'cell':cell, 'scale':scale,
            'requested_origin':origin, 'applied_origin':list(applied_origin), 'sample_size':list(size),
            'source_cell_landmarks':source_landmarks, 'exported_landmarks':landmarks,
            'opaque_bounds':placed_bounds, 'sha256':sha256(pixels).hexdigest()})
        drawings.append(frame)
    manifest = {'version':1, 'actor':actor, 'canvas':canvas, 'anchor':anchor,
                'duration_ms':cycle, 'fps':count*1000/cycle, 'loop':True, 'contacts':data['contacts'],
                'landmark_space':'Exported artwork pixels; null means occluded/unmeasured.',
                'frames':animation}
    _write(OUTPUT/actor/'animation.json', _json(manifest), check)
    provenance = {'version':1, 'exporter':'tools/export_prologue_faces.py',
        'exporter_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'construction':'Complete image-authored drawings; recorded cell crops and uniform whole-figure sampling/registration only.',
        'alpha_floor':alpha_floor,
        'source_landmark_space':'Source-cell pixels, before uniform scaling and whole-figure translation.',
        'source_sha256':hashes, 'registrations':registrations}
    _write(OUTPUT/actor/'provenance.json', _json(provenance), check)
    # Whole-figure previews are uniformly reduced; the face sheet retains
    # source-resolution facial pixels. Individual runtime PNGs remain native.
    rows = math.ceil(count/4)
    thumbnail_width = canvas[0]//2
    sheet = Image.new('RGB', (thumbnail_width*4,536*rows), '#152235')
    faces = Image.new('RGB', (320*4,344*rows), '#152235')
    text, face_text = ImageDraw.Draw(sheet), ImageDraw.Draw(faces)
    for index, frame in enumerate(drawings):
        x, y = (index%4)*thumbnail_width, (index//4)*536
        small = frame.convert('RGBa').resize((thumbnail_width,512), Image.Resampling.LANCZOS).convert('RGBA')
        sheet.paste(small, (x,y), small)
        text.text((x+8,y+514), f'{index:02d} / {index*frame_ms/1000:.3f}s', fill='white')
        fx, fy = (index%4)*320, (index//4)*344
        face = frame.crop((round(anchor[0])-160,24,round(anchor[0])+160,344))
        faces.paste(face, (fx,fy), face)
        face_text.text((fx+8,fy+322), f'{index:02d}', fill='white')
    stream = BytesIO()
    sheet.save(stream, format='JPEG', quality=94, subsampling=0)
    _write(REVIEW/f'{actor}_drawn_contact_sheet.jpg', stream.getvalue(), check)
    _write(REVIEW/f'{actor}_faces_contact_sheet.png', _png(faces), check)
    print(f'{actor}: {count} complete poses, {cycle} ms; registration and alpha exports match.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actor', choices=ACTORS)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name in ((args.actor,) if args.actor else ACTORS):
        build_actor(name, args.check)
