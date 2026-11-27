"""Mechanical alpha matting and whole-figure landmark registration only.

Run from the repository root. Complete drawings are ImageGen-authored.
This script never changes RGB, anatomy, poses, or separate body parts.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageFilter, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
SCALE = 1.25
BATCHES = ("00_03", "04_07", "08_11", "12_15", "16_19", "20_23")
GENERATIONS = (
    "exec-df9dc99e-0e6e-4ee2-a1c7-ef2971885b8b",
    "exec-78256c16-149d-4927-87de-388c8e880bc6",
    "exec-251232ea-d6dc-4602-80dc-2a7e18bdc1bf",
    "exec-6ba63109-026c-4d48-abf1-6f97999993a0",
    "exec-aed9abfe-d689-4dab-b5b8-d39512081ccc",
    "exec-8b376504-029d-4330-b8de-07f44b3f75aa",
)
REFERENCES = ('appearance_reference.png', 'phase_06_appearance.png',
              'phase_12_appearance.png', 'phase_12_appearance.png',
              'phase_18_appearance.png', 'appearance_reference.png')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gray(image):
    return np.asarray(image.convert('L'), dtype=np.float32)


def locate(image, template, guess, radius):
    """NCC measures a painted landmark; it does not transform anatomy."""
    h, w = template.shape
    x, y = guess
    left, top = round(x-w/2-radius), round(y-h/2-radius)
    crop = image[top:round(y+h/2+radius), left:round(x+w/2+radius)]
    windows = np.lib.stride_tricks.sliding_window_view(crop, (h, w))
    mean = windows.mean(axis=(-1, -2), keepdims=True)
    centered = windows-mean
    target = template-template.mean()
    scores = (centered*target).sum(axis=(-1, -2))/np.maximum(
        1e-7, np.sqrt((centered*centered).sum(axis=(-1, -2))*(target*target).sum()))
    iy, ix = np.unravel_index(scores.argmax(), scores.shape)
    return [float(left+ix+w/2), float(top+iy+h/2)], float(scores[iy, ix])


def main():
    selected = []
    masters = []
    matte = []
    clean_images = []
    for batch, generation, reference_name in zip(BATCHES, GENERATIONS, REFERENCES):
        source = HERE/f'batch_{batch}.png'
        original = Image.open(source).convert('RGBA')
        rgba = np.array(original)
        core = Image.fromarray(np.where(rgba[:, :, 3] >= 192, 255, 0).astype('uint8'))
        retained = np.asarray(core.filter(ImageFilter.MaxFilter(5))) != 0
        cleaned = rgba.copy()
        cleaned[:, :, 3] = np.where(retained, rgba[:, :, 3], 0)
        assert np.array_equal(cleaned[:, :, :3], rgba[:, :, :3])
        target = HERE/f'batch_{batch}_alpha_clean.png'
        image = Image.fromarray(cleaned, 'RGBA')
        image.save(target)
        clean_images.append(image)
        masters.append({'source':source.name, 'selected':target.name,
            'prompt':f'batch_{batch}_prompt.txt', 'generation_id':generation,
            'tool':'image_gen.imagegen', 'transparent_background':True,
            'canvas':list(original.size), 'source_sha256':digest(source),
            'selected_sha256':digest(target),
            'references':{reference_name:digest(HERE/reference_name)}})
        matte.append({'source':source.name, 'output':target.name,
            'method':'Retain original alpha within 2 source pixels of every alpha>=192 core; set other alpha to zero. RGB exact, no component/anatomy filtering.',
            'alpha_threshold':192, 'safety_dilation_pixels':2,
            'rgb_exact':True, 'source_sha256':digest(source), 'output_sha256':digest(target)})
    reference = clean_images[0].crop((0, 0, 512, 768))
    ref = gray(reference)
    # Exposed eyes share a strong appearance reference across masters. Collar
    # steel changes with the torso angle; measure actual throat/buckle patches
    # against each master's first complete drawing rather than mistaking a
    # lower armor arc or scratched steel for the original collar/buckle.
    eye_patch = (ref[70:110, 264:304], [284.,90.])
    master_points = (
        {'neck':[284.,148.], 'belt':[289.,282.]},
        {'neck':[276.,168.], 'belt':[276.,333.]},
        {'neck':[282.,147.], 'belt':[281.,285.]},
        {'neck':[284.,147.], 'belt':[286.,282.]},
        {'neck':[284.,167.], 'belt':[284.,325.]},
        {'neck':[288.,148.], 'belt':[288.,282.]},
    )
    master_patches = []
    for image, points in zip(clean_images, master_points):
        sample = gray(image.crop((0,0,512,768)))
        patches = {'eyes':eye_patch}
        for label, point in points.items():
            x,y = [round(v) for v in point]
            patches[label] = (sample[y-16:y+16,x-18:x+18],point)
        master_patches.append(patches)
    bob = [0.,2.,3.,2.,0.,-3.,-6.,-6.,-4.,-2.,-1.,-1.]*2
    results = []
    sheet = Image.new('RGB', (4*384, 6*536), '#162438')
    draw = ImageDraw.Draw(sheet)
    for index in range(24):
        master = index//4
        slot = index % 4
        cell = [(slot % 2)*512, (slot//2)*768,
                (slot % 2+1)*512, (slot//2+1)*768]
        image = clean_images[master].crop(cell)
        pixels = gray(image)
        landmarks, scores = {}, {}
        for label, (template, guess) in master_patches[master].items():
            landmarks[label], scores[label] = locate(pixels, template, guess, 38)
        eyes = landmarks['eyes']
        origin = [384.-eyes[0]*SCALE, 188.+bob[index]-eyes[1]*SCALE]
        record = {'source':f'batch_{BATCHES[master]}_alpha_clean.png',
                  'cell':cell, 'scale':SCALE, 'origin':origin,
                  'landmarks':landmarks,
                  'notes':f'Complete frontal pose {index}; right/viewer-left sword, left/viewer-right shield. Whole-frame exposed-eye registration and authored small recoil; throat and buckle independently measured against this master.'}
        selected.append(record)
        results.append({'frame':index, 'source_cell_landmarks':landmarks,
                        'scores':scores, 'origin':origin,
                        'exported_belt':[landmarks['belt'][i]*SCALE+origin[i] for i in (0,1)],
                        'exported_eyes':[landmarks['eyes'][i]*SCALE+origin[i] for i in (0,1)]})
        shown = Image.new('RGBA', (768,1024))
        sampled = image.convert('RGBa').resize((640,960), Image.Resampling.LANCZOS).convert('RGBA')
        shown.alpha_composite(sampled, tuple(round(v) for v in origin))
        small = shown.resize((384,512), Image.Resampling.LANCZOS)
        x, y = (index%4)*384, (index//4)*536
        sheet.paste(small, (x,y), small)
        draw.text((x+7,y+514), f'{index:02d} / {index/60:.3f}s', fill='white')
    data = {'version':1, 'actor':'crown_soldier', 'canvas':[768,1024], 'anchor':[384,960],
            'cycle_ms':400, 'contacts':[{'frame':0,'foot':'near'}, {'frame':12,'foot':'far'}],
            'near':'anatomical_right', 'far':'anatomical_left',
            'construction':'Twenty-four complete image-authored frontal figures, selected from six chronological four-pose masters. No detached limb/head rigs or pixel-morphed anatomy.',
            'registration':'Fixed1.25 uniform whole-master density; exposed-eye source-cell appearance registers whole figures. Small authored whole-figure recoil follows support/flight. Visible throat and buckle points independently measured against each master document source torso foreshortening. No occupied-bound or foot normalization, no frozen/pasted face region.',
            'source_sha256':{path.name:digest(path) for path in sorted(HERE.glob('batch_*.png'))},
            'frames':selected}
    (HERE/'source_art_24.json').write_text(json.dumps(data,indent=2)+'\n')
    (HERE/'registration_report.json').write_text(json.dumps(results,indent=2)+'\n')
    (HERE/'alpha_recipe.json').write_text(json.dumps({'version':1,'derivatives':matte},indent=2)+'\n')
    (HERE/'production_generation_24.json').write_text(json.dumps({'version':1,
        'actor':'crown_soldier','active_source_selection':'source_art_24.json',
        'authored_poses':24,'cycle_ms':400,'master_layout':'2x2 complete unified frontal drawings',
        'masters':masters},indent=2)+'\n')
    sheet.save(HERE/'registered_contact_sheet.jpg', quality=91)
    print(json.dumps(results,indent=2))


if __name__ == '__main__':
    main()
