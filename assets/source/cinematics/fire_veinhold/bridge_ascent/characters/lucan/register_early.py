"""Measure and register complete early ascent drawings, never individual parts.

The low-elevation source face supplies uniform drawing density. Actual eye,
neck and belt template matches remain reviewable observations. All sampling is
one uniform resize and one whole-image translation; anatomy is ImageGen art.
"""
from hashlib import sha256
import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
OLD = ROOT/'assets/story/fire_veinhold_opening/shot07/characters/lucan'
OLD_SOURCE = ROOT/'assets/source/cinematics/fire_veinhold/face_reveal/lucan'
OUTPUT = ROOT/'assets/story/fire_veinhold_opening/shot08/characters/lucan'
CANVAS = (1024, 1536)
ANCHOR = (512, 960)


def image_gray(image):
    return cv2.cvtColor(np.asarray(image.convert('RGB')), cv2.COLOR_RGB2GRAY)


def feature_match(image, reference, point, extent, search, scales):
    x, y = point
    half_x, half_y = extent
    template = image_gray(reference.crop((round(x-half_x), round(y-half_y),
                                         round(x+half_x), round(y+half_y))))
    gray = image_gray(image)
    left, top, right, bottom = search
    region = gray[top:bottom, left:right]
    best = None
    for scale in scales:
        sample = cv2.resize(template, None, fx=float(scale), fy=float(scale))
        if sample.shape[0] >= region.shape[0] or sample.shape[1] >= region.shape[1]:
            continue
        result = cv2.matchTemplate(region, sample, cv2.TM_CCOEFF_NORMED)
        _, score, _, location = cv2.minMaxLoc(result)
        if best is None or score > best['score']:
            best = {'score':float(score), 'scale':float(scale),
                    'point':[left+location[0]+sample.shape[1]/2,
                             top+location[1]+sample.shape[0]/2]}
    return best


def expected_point(old_point, elevation, name):
    # Match the inherited drawing at its original actual12.225-degree view.
    # Retain the original per-pose registration/recoil. This is a body-space
    # projection reference, not a desired hand/foot gait target.
    old_angle = math.radians(12.225)
    angle = math.radians(elevation)
    forward = .10 if name in ('eyes', 'neck') else 0.0
    z = ((960-old_point[1])/500+forward*math.sin(old_angle))/math.cos(old_angle)
    return [old_point[0]+128, 960-500*(z*math.cos(angle)-forward*math.sin(angle))]


def export_record(record):
    source = ROOT/record['source']
    if sha256(source.read_bytes()).hexdigest() != record['source_sha256']:
        raise ValueError('Changed approved raw source: '+str(source))
    image = Image.open(source).convert('RGBA').crop(tuple(record['cell']))
    if record.get('alpha_floor', 0):
        image.putalpha(image.getchannel('A').point(lambda a:0 if a <= record['alpha_floor'] else a))
    scale = record['scale']
    if scale != 1:
        image = image.convert('RGBa').resize((round(image.width*scale), round(image.height*scale)),
            Image.Resampling.LANCZOS).convert('RGBA')
    result = Image.new('RGBA', CANVAS)
    result.alpha_composite(image, tuple(round(value) for value in record['origin']))
    return result


def main():
    global OUTPUT
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--selection', type=Path, default=HERE/'early_selection.json')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    OUTPUT = args.output
    selection = json.loads(args.selection.read_text())
    profile = json.loads((OLD_SOURCE/'source_art_48.json').read_text())
    schedule = json.loads((HERE/'authoring_schedule.json').read_text())
    records = []
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for index in range(16):
        source = OLD/f'frame_{index:02d}.png'
        image = Image.open(source).convert('RGBA')
        records.append({'index':index,'gait_frame':index,
            'source':source.relative_to(ROOT).as_posix(),'source_sha256':sha256(source.read_bytes()).hexdigest(),
            'cell':[0,0,*image.size], 'scale':1.0,'origin':[128,0], 'alpha_floor':0,
            'method':'Whole approved image padded unchanged for the matched12.2–14.8degree entry.'})
    for start in sorted(int(k) for k in selection if int(k) >=16):
        source = HERE/selection[str(start)]
        master = Image.open(source).convert('RGBA')
        width, height = master.width//2, master.height//2
        for cell, index in enumerate(range(start,start+4)):
            box = [(cell%2)*width,(cell//2)*height,(cell%2+1)*width,(cell//2+1)*height]
            image = master.crop(box)
            reference = Image.open(OLD/f'frame_{index%48:02d}.png').convert('RGBA')
            original = profile['frames'][index%48]
            old_points = {name:[original['landmarks'][name][axis]*original['scale']+round(original['origin'][axis])
                               for axis in (0,1)] for name in ('eyes','neck','belt')}
            face = feature_match(image,reference,old_points['eyes'],(45,32),
                                 (100,0,width-65,min(230,height)),np.linspace(.42,.90,97))
            scale = 1/face['scale']
            rigid_scales = {24:1.17,25:1.17,26:1.17,27:1.17,28:1.28,29:1.27,30:1.26,31:1.25,32:1.15,33:1.15,34:1.15,35:1.15}
            if index in rigid_scales:
                scale = rigid_scales[index]
            matches = {'eyes':face}
            for name,extent,search in (
                ('neck',(38,24),(130,60,width-70,300)),
                ('belt',(25,28),(140,160,width-70,440))):
                matches[name] = feature_match(image,reference,old_points[name],extent,search,
                    np.linspace(face['scale']*.96,face['scale']*1.04,17))
            targets = {name:expected_point(old_points[name],schedule[index]['elevation'],name)
                       for name in old_points}
            weights = {'eyes':.65,'neck':.25,'belt':.10}
            origin = [sum(weights[name]*(targets[name][axis]-matches[name]['point'][axis]*scale)
                          for name in weights) for axis in (0,1)]
            observed = {name:[matches[name]['point'][axis]*scale+origin[axis] for axis in (0,1)]
                        for name in matches}
            records.append({'index':index,'gait_frame':index,
                'source':source.relative_to(ROOT).as_posix(), 'source_sha256':sha256(source.read_bytes()).hexdigest(),
                'cell':box,'scale':scale,'origin':origin,'alpha_floor':16,
                'view_elevation_degrees':schedule[index]['elevation'],
                'source_landmark_matches':matches,'projected_reference_landmarks':targets,
                'registered_landmarks':observed,
                'method':('Uniform whole-figure scale from inspected cranium and rigid pauldron widths; eye/neck/belt matching locates image only.' if index>=24 else 'Actual feature matching at low elevation; uniform whole-image sampling and translation only.'), 'rigid_width_observation':({'main_cranium_source_band':[120,135],'paired_pauldrons_source_band':[260,285],'source_measurement_reference':'independent_review and actual source pixel grids; no occupied-height fit'} if index>=24 else None)})
    for record in records:
        image = export_record(record)
        path = OUTPUT/f'transition_{record["index"]:03d}.png'
        image.save(path)
        record['output_sha256'] = sha256(path.read_bytes()).hexdigest()
    (HERE/'early_registration.json').write_text(json.dumps(records,indent=2)+'\n')
    partial = {'version':1,'actor':'lucan','canvas':list(CANVAS),'anchor':list(ANCHOR),
        'art_pixels_per_metre':500,'approval_state':'candidate_for_native_review',
        'transition_frames':[{'index':r['index'],'file':f'transition_{r["index"]:03d}.png',
            'gait_frame':r['gait_frame'],'source_sha256':r['source_sha256']} for r in records],
        'overhead_cycle':{'frames':[]}}
    (OUTPUT/'actorperformance.partial.json').write_text(json.dumps(partial,indent=2)+'\n')
    sheet = Image.new('RGB',(960,640*4),'#203040')
    draw = ImageDraw.Draw(sheet)
    from cinematic_bridge_ascent import actor_states_at
    for cell,index in enumerate((22,23,24,25,26,27,28,29,30,31,32,35)):
        state = actor_states_at(index/60)['runners'][0]
        figure = Image.open(OUTPUT/f'transition_{index:03d}.png').convert('RGBA')
        factor = state['scale']
        figure = figure.convert('RGBa').resize((round(figure.width*factor),round(figure.height*factor)),
            Image.Resampling.LANCZOS).convert('RGBA')
        canvas = Image.new('RGBA',(960,640),'#203040')
        root = state['ground_anchor']
        canvas.alpha_composite(figure,(round(root[0]-ANCHOR[0]*factor),round(root[1]-ANCHOR[1]*factor)))
        canvas.convert('RGB').save(f'/tmp/lucan_ascent_native_{index:03d}.png')
        canvas = canvas.convert('RGB').resize((320,213),Image.Resampling.LANCZOS)
        x,y=(cell%3)*320,(cell//3)*640
        # Larger source-registered body below each actual native picture.
        source_view = Image.open(OUTPUT/f'transition_{index:03d}.png').convert('RGBA')
        source_view.thumbnail((300,390))
        background = Image.new('RGBA',source_view.size,'#203040');background.alpha_composite(source_view)
        sheet.paste(canvas,(x,y));sheet.paste(background.convert('RGB'),(x+(320-source_view.width)//2,y+230))
        draw.text((x+8,y+215),f'{index:03d} /{index/60:.3f}s /{schedule[index]["elevation"]:.2f}deg',fill='white')
    sheet.save('/tmp/lucan_ascent_early_contact.jpg',quality=95)
    print(f'Registered {len(records)} complete drawings; candidate/native sheet /tmp/lucan_ascent_early_contact.jpg')


if __name__=='__main__':
    main()
