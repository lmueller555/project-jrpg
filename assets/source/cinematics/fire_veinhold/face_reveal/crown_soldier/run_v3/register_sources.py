"""Register complete Crown run drawings; never construct or edit anatomy.

ImageGen owns every revised complete figure. This tool only measures painted
landmarks, samples each whole source uniformly, and records registration.
Authoring guides and diagnostic reference images never become sprite pixels.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ACTOR = HERE.parent
NEW_DENSITY = .70
CACHE_VERSION = 1


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def locate(image, template, guess, radius):
    h, w = template.shape
    x, y = guess
    left, top = round(x-w/2-radius), round(y-h/2-radius)
    crop = image[top:round(y+h/2+radius), left:round(x+w/2+radius)]
    ch, cw = crop.shape
    centered = template-template.mean()
    size = (1 << (ch+h-2).bit_length(), 1 << (cw+w-2).bit_length())
    product = np.fft.rfft2(crop, s=size)*np.fft.rfft2(centered[::-1, ::-1], s=size)
    corr = np.fft.irfft2(product, s=size)[h-1:ch, w-1:cw]
    def sums(a):
        v = np.pad(a, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        return v[h:, w:]-v[:-h, w:]-v[h:, :-w]+v[:-h, :-w]
    energy = np.maximum(1e-6, sums(crop*crop)-sums(crop)**2/(h*w))
    scores = corr/np.sqrt(energy*np.sum(centered*centered))
    iy, ix = np.unravel_index(scores.argmax(), scores.shape)
    return [float(left+ix+w/2), float(top+iy+h/2)], float(scores[iy, ix])


def sample(master, scale, origin):
    master = master.copy()
    master.putalpha(master.getchannel('A').point(lambda a: 0 if a <= 16 else a))
    size = (round(master.width*scale), round(master.height*scale))
    sampled = master.convert('RGBa').resize(size, Image.Resampling.LANCZOS).convert('RGBA')
    bounds = sampled.getchannel('A').point(lambda a: 255 if a >= 16 else 0).getbbox()
    applied = tuple(round(v) for v in origin)
    placed = [bounds[0]+applied[0], bounds[1]+applied[1],
              bounds[2]+applied[0], bounds[3]+applied[1]]
    canvas = Image.new('RGBA', (768, 1024))
    canvas.alpha_composite(sampled, applied)
    return canvas, placed


def baseline_frame(rec):
    master = Image.open(ACTOR/rec['source']).convert('RGBA').crop(tuple(rec['cell']))
    return sample(master, rec['scale'], rec['origin'])[0]


def measure(master, baseline, old):
    # One source density for all new masters, calibrated from the first body
    # keys. No occupied-bound, foot-height or per-pose scale normalization.
    size = (round(master.width*NEW_DENSITY), round(master.height*NEW_DENSITY))
    measured = master.resize(size, Image.Resampling.LANCZOS)
    pixels = np.asarray(measured.convert('L'), dtype=np.float64)
    oldpoints = {k: [p[j]*old['scale']+round(old['origin'][j]) for j in (0, 1)]
                 for k, p in old['landmarks'].items() if p is not None}
    eyes = oldpoints['eyes']
    facebox = (round(eyes[0]-48), round(eyes[1]-26),
               round(eyes[0]+48), round(eyes[1]+68))
    template = np.asarray(baseline.crop(facebox).convert('L'), dtype=np.float64)
    center = [(facebox[j]+facebox[j+2])/2 for j in (0, 1)]
    match, score = locate(pixels, template, center, 100)
    foundeyes = [match[j]+eyes[j]-center[j] for j in (0, 1)]
    points = {'eyes': [round(v/NEW_DENSITY, 5) for v in foundeyes]}
    scores = {'eyes': round(score, 6)}
    for label in ('neck', 'belt'):
        q = oldpoints[label]
        box = (round(q[0]-28), round(q[1]-25), round(q[0]+28), round(q[1]+25))
        template = np.asarray(baseline.crop(box).convert('L'), dtype=np.float64)
        guess = [foundeyes[j]+q[j]-eyes[j] for j in (0, 1)]
        point, found = locate(pixels, template, guess, 55)
        points[label] = [round(v/NEW_DENSITY, 5) for v in point]
        scores[label] = round(found, 6)
    origin = [round(eyes[j]-points['eyes'][j]*NEW_DENSITY, 5) for j in (0, 1)]
    return {'scale': NEW_DENSITY, 'origin': origin,
            'landmarks': points, 'landmark_match_scores': scores}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--partial', action='store_true', help='Measure present sources without publishing a profile')
    parser.add_argument('--force-measure', action='store_true')
    args = parser.parse_args()
    selection_path = HERE/'selected_sources.json'
    selection = json.loads(selection_path.read_text())
    selected = {int(k): v for k, v in selection['frames'].items()}
    if not args.partial and set(selected) != set(range(48)):
        raise SystemExit('All 48 selected complete sources are required before publishing')
    baseline_path = HERE/'history/baseline_profile_48.json'
    baseline = json.loads(baseline_path.read_text())
    cachepath = HERE/'measurement_cache.json'
    cache = json.loads(cachepath.read_text()) if cachepath.exists() else {}
    frames, report, hashes = [], [], {}
    diagnostics = Path('/tmp/crown_v3_registered')
    diagnostics.mkdir(exist_ok=True)
    bounds_folder = HERE/'authoring_bounds'
    bounds_folder.mkdir(exist_ok=True)
    sheet = Image.new('RGB', (8*240, 6*344), '#162438')
    draw = ImageDraw.Draw(sheet)
    for i, entry in sorted(selected.items()):
        path = HERE/entry['source_master']
        actual = digest(path)
        if actual != entry['source_sha256']:
            raise ValueError(f'Selected master changed: {i}')
        old = baseline['frames'][i]
        master = Image.open(path).convert('RGBA')
        if entry['kind'] == 'retained':
            rec = {k: v for k, v in old.items()}
            rec['source'] = 'run_v3/'+entry['source_master']
        else:
            key = str(i)
            stamp = {'source_sha256': actual, 'baseline_profile_sha256': digest(baseline_path),
                     'version': CACHE_VERSION, 'density': NEW_DENSITY}
            cached = cache.get(key)
            if args.force_measure or not cached or cached.get('stamp') != stamp:
                cached = {'stamp': stamp, 'registration': measure(master, baseline_frame(old), old)}
                cache[key] = cached
            rec = {'source': 'run_v3/'+entry['source_master'],
                   'cell': [0, 0, *master.size], **cached['registration'],
                   'generation_id': entry['generation_id'],
                   'notes': 'Complete ImageGen-authored leg-continuity repair with the corresponding approved '
                            'upper-body action as reference. Whole source sampled uniformly and registered by '
                            'painted body landmarks only; no old pixels, part transforms or interpolated anatomy.'}
        canvas, placed = sample(master, rec['scale'], rec['origin'])
        canonical = {k: [round(v[j]*rec['scale']+round(rec['origin'][j]), 4) for j in (0, 1)]
                     for k, v in rec['landmarks'].items() if v is not None}
        frames.append(rec)
        row = {'frame': i, 'source': rec['source'], 'source_sha256': actual,
               'scale': rec['scale'], 'origin': rec['origin'],
               'source_landmarks': rec['landmarks'], 'canonical_landmarks': canonical,
               'match_scores': rec.get('landmark_match_scores', {}), 'opaque_bounds': placed}
        report.append(row)
        canvas.save(diagnostics/f'frame_{i:02d}.png')
        canonical_hash = sha256(canvas.tobytes()).hexdigest()
        bound = bounds_folder/f'frame_{i:02d}_{canonical_hash[:12]}.png'
        if not bound.exists():
            canvas.save(bound)
        row['authoring_bound'] = bound.relative_to(HERE).as_posix()
        small = canvas.convert('RGBa').resize((240, 320), Image.Resampling.LANCZOS).convert('RGBA')
        x, y = i % 8*240, i//8*344
        sheet.paste(small, (x, y), small)
        draw.text((x+4, y+322), f'{i:02d} / {i/60:.3f}s', fill='white')
        hashes[rec['source']] = actual
    cachepath.write_text(json.dumps(cache, indent=2)+'\n')
    (HERE/'registration_report.json').write_text(json.dumps(report, indent=2)+'\n')
    sheet.save('/tmp/crown_v3_current_contact_sheet.jpg', quality=95)
    if not args.partial:
        for extra in (selection_path, baseline_path, Path(__file__)):
            hashes['run_v3/'+extra.relative_to(HERE).as_posix()] = digest(extra)
        for entry in selected.values():
            for ref in entry.get('referenced_image_paths', []):
                source = Path(ref)
                if source.is_relative_to(ACTOR) and source.is_file():
                    hashes[source.relative_to(ACTOR).as_posix()] = digest(source)
        profile = {'version': 1, 'actor': 'crown_soldier', 'canvas': [768, 1024],
                   'anchor': [384, 960], 'cycle_ms': 800, 'alpha_floor': 16,
                   'contacts': [{'frame': 0, 'foot': 'near'}, {'frame': 24, 'foot': 'far'}],
                   'near': 'anatomical_right', 'far': 'anatomical_left',
                   'approval_state': 'implemented_for_ingame_review',
                   'construction': 'Forty-eight complete painted figures: four retained approved contact/recovery '
                                   'drawings and forty-four ImageGen-authored leg-continuity repairs. '
                                   'No detached rigs, pose warps, pixel restoration or crossfaded anatomy.',
                   'registration': 'Fixed 0.70 whole-source density for new masters, calibrated against the approved '
                                   'body model; measured eyes/neck/belt locate each complete drawing. '
                                   'Retained raw keys keep their original 0.60 density and registration. '
                                   'No occupied-height or foot fitting.',
                   'source_sha256': hashes, 'frames': frames}
        (ACTOR/'source_art_48.json').write_text(json.dumps(profile, indent=2)+'\n')
    print(json.dumps({'selected': len(selected), 'published': not args.partial,
                      'clipped': [r['frame'] for r in report if min(r['opaque_bounds'][:2]) < 0
                                  or r['opaque_bounds'][2] > 768 or r['opaque_bounds'][3] > 1024]}))


if __name__ == '__main__':
    main()
