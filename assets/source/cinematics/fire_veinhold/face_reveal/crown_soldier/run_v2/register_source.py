"""Register complete ImageGen drawings; no anatomy synthesis or part movement.

Run from the repo root with the project Python. Whole-source fixed density is
chosen from eyes/neck/belt model measurements, never occupied/foot bounds.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ACTOR = HERE.parent
SCALE = .60


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locate(image, template, guess, radius):
    """FFT NCC locates existing painted marks without modifying them."""
    h, w = template.shape
    x, y = guess
    left, top = round(x-w/2-radius), round(y-h/2-radius)
    patch = image[top:round(y+h/2+radius), left:round(x+w/2+radius)]
    ph, pw = patch.shape
    centered = template-template.mean()
    size = (1 << (ph+h-2).bit_length(), 1 << (pw+w-2).bit_length())
    product = np.fft.rfft2(patch, s=size)*np.fft.rfft2(centered[::-1, ::-1], s=size)
    corr = np.fft.irfft2(product, s=size)[h-1:ph, w-1:pw]
    def sums(values):
        integral = np.pad(values, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        return integral[h:, w:]-integral[:-h, w:]-integral[h:, :-w]+integral[:-h, :-w]
    energy = np.maximum(1e-6, sums(patch*patch)-sums(patch)**2/(h*w))
    scores = corr/np.sqrt(energy*np.sum(centered*centered))
    iy, ix = np.unravel_index(scores.argmax(), scores.shape)
    return [float(left+ix+w/2), float(top+iy+h/2)], float(scores[iy, ix])


def recoil(index):
    # Modest source registration offset. Compression/flight remains in the
    # complete drawing; no runtime bob and no planted-foot normalization.
    values = (0., 5., -6., -3., 0., 5., -6., -3., 0.)
    k, fraction = divmod(index, 6)
    amount = (1-math.cos(math.pi*fraction/6))/2
    return values[k]*(1-amount)+values[k+1]*amount


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--partial', action='store_true')
    args = parser.parse_args()
    paths = [HERE/f'frame_{i:02d}.png' for i in range(48)]
    if not args.partial and not all(p.exists() for p in paths):
        raise SystemExit('All48 complete source drawings are required')
    ref = np.asarray(Image.open(paths[0]).convert('L'), dtype=np.float64)
    templates = {
        'eyes': (ref[161:213, 510:610], [560., 187.], 90),
        'neck': (ref[280:326, 523:601], [562., 303.], 100),
        'belt': (ref[549:621, 535:611], [573., 585.], 110),
    }
    selected, report = [], []
    sheet = Image.new('RGB', (8*240, 6*344), '#162438')
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        if not path.exists():
            continue
        master = Image.open(path).convert('RGBA')
        pixels = np.asarray(master.convert('L'), dtype=np.float64)
        landmarks, scores = {}, {}
        for label, (template, guess, radius) in templates.items():
            landmarks[label], scores[label] = locate(pixels, template, guess, radius)
        eyes = landmarks['eyes']
        origin = [384-eyes[0]*SCALE, 188+recoil(index)-eyes[1]*SCALE]
        record = {
            'source': f'run_v2/{path.name}', 'cell': [0, 0, *master.size],
            'scale': SCALE, 'origin': origin, 'landmarks': landmarks,
            'landmark_match_scores': scores,
            'authored_weight_offset_y': recoil(index),
            'notes': 'Complete individually image-authored frontal figure. '
                     'Fixed whole-source density; eyes register the source '
                     'translation and independently measured neck/buckle '
                     'check model continuity. No body-part transforms, face '
                     'pastes, occupied-bound fitting or interpolated anatomy.'}
        metadata = HERE/f'frame_{index:02d}_generation.json'
        if metadata.exists():
            record['generation_id'] = json.loads(metadata.read_text())['generation_id']
        selected.append(record)
        report.append({'frame': index, 'source_landmarks': landmarks,
                       'scores': scores, 'origin': origin,
                       'eyes_to_neck': (landmarks['neck'][1]-eyes[1])*SCALE,
                       'eyes_to_belt': (landmarks['belt'][1]-eyes[1])*SCALE})
        # Mechanical review rendering uses the same whole-figure registration.
        a = np.array(master)
        a[:, :, 3][a[:, :, 3] <= 16] = 0
        cropped = Image.fromarray(a)
        shown = Image.new('RGBA', (768, 1024))
        size = (round(master.width*SCALE), round(master.height*SCALE))
        sampled = cropped.convert('RGBa').resize(size, Image.Resampling.LANCZOS).convert('RGBA')
        shown.alpha_composite(sampled, tuple(round(v) for v in origin))
        small = shown.resize((240, 320), Image.Resampling.LANCZOS)
        x, y = index % 8*240, index//8*344
        sheet.paste(small, (x, y), small)
        draw.text((x+4, y+322), f'{index:02d} / {index/60:.3f}s', fill='white')
    prefix = 'partial_' if args.partial else ''
    (HERE/f'{prefix}registration_report.json').write_text(json.dumps(report, indent=2)+'\n')
    sheet.save(HERE/f'{prefix}registered_contact_sheet.jpg', quality=92)
    if args.partial:
        print(json.dumps(report, indent=2))
        return
    sources = [p for p in sorted(HERE.glob('*')) if p.is_file()
               and (p.name.startswith(('frame_', 'key_')) or '_authoring_guide' in p.name
                    or p.name in ('keys.png', 'keys_prompt.txt',
                    'arm_forward_authoring_guide.png', 'register_source.py'))]
    profile = {
        'version': 1, 'actor': 'crown_soldier', 'canvas': [768, 1024],
        'anchor': [384, 960], 'cycle_ms': 800, 'alpha_floor': 16,
        'contacts': [{'frame': 0, 'foot': 'near'}, {'frame': 24, 'foot': 'far'}],
        'near': 'anatomical_right', 'far': 'anatomical_left',
        'approval_state': 'internally_reviewed_for_ingame_review',
        'construction': 'Forty-eight complete individually ImageGen-authored '
                        'front-facing running drawings; key/body/weapon '
                        'and intermediate motion reviewed separately. '
                        'No rigged, warped, blended or duplicate-pose filling.',
        'registration': 'Fixed0.60 whole-source density, calibrated against the '
                        'previous bank eyes-to-belt torso scale, measured eyes/neck/belt '
                        'landmarks and modest authored recoil, never occupied '
                        'bounds or foot fitting. No pasted head/limbs.',
        'source_sha256': {f'run_v2/{p.name}': digest(p) for p in sources},
        'frames': selected,
    }
    (ACTOR/'source_art_48.json').write_text(json.dumps(profile, indent=2)+'\n')
    print(json.dumps({'frames': len(selected), 'profile': str(ACTOR/'source_art_48.json')}))


if __name__ == '__main__':
    main()
