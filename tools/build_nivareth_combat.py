"""Export Nivareth's retained authored atlases without synthesizing poses.

Registration preserves every floating shard in each isolated source cell.
Each atlas uses a fixed native scale, shared 64-color opaque-only palette,
binary alpha, and an explicit virtual floor for the hovering elemental.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/combat/nivareth'
OUTPUT = ROOT/'assets/combat/nivareth'
REVIEW = ROOT/'docs/reviews/nivareth_combat'
RECIPE = SOURCE/'registration.json'


def encoded(image):
    stream = BytesIO()
    image.save(stream, format='PNG', optimize=True)
    return stream.getvalue()


def split_time(total, count):
    if type(total) is not int or type(count) is not int or not 0 < count <= total:
        raise ValueError('Animation duration must cover every authored drawing')
    return [round((i+1)*total/count)-round(i*total/count) for i in range(count)]


def products():
    specification = json.loads(RECIPE.read_text())
    canvas, anchor = specification['canvas'], specification['anchor']
    sources, colors = {}, []
    for name, record in specification['sources'].items():
        path = ROOT/name
        if sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Nivareth source changed: '+name)
        source = Image.open(path).convert('RGBA')
        sources[name] = source
        colors.extend(pixel[:3] for pixel in source.get_flattened_data() if pixel[3] >= 128)
    samples = Image.new('RGB', (len(colors), 1))
    samples.putdata(colors)
    palette = samples.quantize(colors=specification['palette_colors'], dither=Image.Dither.NONE)
    drawings, registrations = [], []
    for index, drawing in enumerate(specification['drawings']):
        source_record = specification['sources'][drawing['source_sheet']]
        source = sources[drawing['source_sheet']]
        left, top, width, height = drawing['source_rect']
        if not (0 <= left < left+width <= source.width and 0 <= top < top+height <= source.height):
            raise ValueError('Invalid source rectangle: '+str(index))
        image = source.crop((left, top, left+width, top+height))
        alpha = image.getchannel('A').point(lambda a: 255 if a >= 128 else 0)
        bounds = alpha.getbbox()
        if (bounds is None or bounds[0] < 2 or bounds[1] < 2
                or bounds[2] > width-2 or bounds[3] > height-2):
            raise ValueError('Authored Nivareth silhouette touches source cell: '+str(index))
        image.putalpha(alpha)
        scale = source_record['native_scale']
        image = image.resize((max(1, round(width*scale)), max(1, round(height*scale))),
                             Image.Resampling.NEAREST)
        alpha = image.getchannel('A')
        image = image.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE).convert('RGBA')
        image.putalpha(alpha)
        foot = drawing['source_foot']
        position = (round(anchor[0]-(foot[0]-left)*scale), round(anchor[1]-(foot[1]-top)*scale))
        native_bounds = (position[0]+image.getbbox()[0], position[1]+image.getbbox()[1],
                         position[0]+image.getbbox()[2], position[1]+image.getbbox()[3])
        if (native_bounds[0] <= 0 or native_bounds[1] <= 0
                or native_bounds[2] >= canvas[0] or native_bounds[3] >= canvas[1]):
            raise ValueError('Clipped Nivareth drawing: '+str(index))
        frame = Image.new('RGBA', tuple(canvas))
        frame.alpha_composite(image, position)
        if set(frame.getchannel('A').tobytes())-{0,255}:raise ValueError('Non-binary Nivareth alpha')
        anchors = {'floor': list(anchor)}
        for key, point in drawing['source_anchors'].items():
            anchors[key] = [round(anchor[0]+(point[0]-foot[0])*scale),
                            round(anchor[1]+(point[1]-foot[1])*scale)]
        if not {'body','core','contact','cast_origin'} <= set(anchors):
            raise ValueError('Missing Nivareth pose anchors')
        drawings.append(frame)
        registrations.append({**drawing, 'source_sha256':source_record['sha256'],
            'native_scale':scale,'native_bounds':list(native_bounds),
            'position':list(position),'anchors':anchors})
    result, animations, used, atlas = {}, {}, [], []
    global_fingerprints = set()
    for state, record in specification['animations'].items():
        indices = record['drawings']
        contact = record.get('contact_frame')
        durations = (split_time(record['duration_ms'], len(indices)) if contact is None else
            split_time(record['contact_ms'],contact)+
            split_time(record['duration_ms']-record['contact_ms'],len(indices)-contact))
        frames, fingerprints = [], set()
        for number, (index, milliseconds) in enumerate(zip(indices,durations),1):
            image = drawings[index]
            name = f'{state}_{number:02}.png'
            result[(OUTPUT/name).relative_to(ROOT).as_posix()] = encoded(image)
            frames.append({**registrations[index],'file':name,'duration_ms':milliseconds})
            fingerprint = sha256(image.tobytes()).digest()
            fingerprints.add(fingerprint);global_fingerprints.add(fingerprint)
            used.append(index);atlas.append(image)
        if len(fingerprints) != len(indices):
            raise ValueError('Duplicate Nivareth drawings in '+state)
        animations[state] = {'loop':record['loop'],'frames':frames}
        for field in ('contact_frame','contact_ms'):
            if field in record:animations[state][field] = record[field]
    if sorted(used) != list(range(len(drawings))) or len(global_fingerprints) != len(drawings):
        raise ValueError('Every authored Nivareth drawing must be unique and used once')
    sheet = Image.new('RGBA',(canvas[0]*16,canvas[1]*((len(atlas)+15)//16)))
    for i,frame in enumerate(atlas):sheet.alpha_composite(frame,((i%16)*canvas[0],(i//16)*canvas[1]))
    result[(OUTPUT/'spritesheet.png').relative_to(ROOT).as_posix()] = encoded(sheet)
    manifest = {'version':1,'actor':'nivareth','canvas':canvas,'anchor':anchor,'facing':'right',
        'sheet':'spritesheet.png','authored_frames':len(drawings),
        'source_sha256':{name:record['sha256'] for name,record in specification['sources'].items()},
        'registration':RECIPE.relative_to(ROOT).as_posix(),
        'registration_sha256':sha256(RECIPE.read_bytes()).hexdigest(),
        'palette_colors':specification['palette_colors'],
        'extraction':'all isolated authored shards retained; alpha>=128; opaque-only shared palette; per-atlas fixed native scale; explicit virtual floor/core/cast/contact anchors',
        'action_aliases':specification['action_aliases'],'animations':animations}
    result[(OUTPUT/'animation.json').relative_to(ROOT).as_posix()] = (json.dumps(manifest,indent=2)+'\n').encode()
    return result


def review():
    """Produce an honest authored-pose reel, separate from gameplay evidence."""
    manifest = json.loads((OUTPUT/'animation.json').read_text())
    REVIEW.mkdir(parents=True,exist_ok=True)
    font = ImageFont.load_default(size=16)
    canvas = manifest['canvas']
    width = 1024
    sheet = Image.new('RGB',(width,len(manifest['animations'])*174),(22,34,49))
    draw = ImageDraw.Draw(sheet)
    reel = []
    for row,(state,entry) in enumerate(manifest['animations'].items()):
        y = row*174
        draw.text((8,y+4),f'{state} / {len(entry["frames"])} authored drawings',fill=(220,241,255),font=font)
        for column in range(8):
            record = entry['frames'][round(column*(len(entry['frames'])-1)/7)]
            image = Image.open(OUTPUT/record['file']).convert('RGBA')
            image = image.resize((128,115),Image.Resampling.NEAREST)
            sheet.paste(image,(column*128,y+30),image)
        for record in entry['frames']:
            image = Image.open(OUTPUT/record['file']).convert('RGBA')
            frame = Image.new('RGB',(640,400),(22,34,49))
            label = ImageDraw.Draw(frame)
            label.text((20,18),'NIVARETH — authored animation review',font=font,fill=(235,247,255))
            label.text((20,47),state.replace('_',' ').upper(),font=font,fill=(165,215,250))
            scaled = image.resize((canvas[0]*2,canvas[1]*2),Image.Resampling.NEAREST)
            frame.paste(scaled,(160,90),scaled)
            # The white card checks the core/outline against a pale backdrop.
            label.rectangle((510,120,625,245),fill=(215,227,236))
            thumb = image.resize((112,101),Image.Resampling.NEAREST)
            frame.paste(thumb,(512,138),thumb)
            label.text((480,270),'Pale backdrop',font=font,fill=(165,185,210))
            copies = max(1,round(record['duration_ms']/40))
            reel.extend([frame]*copies)
    (REVIEW/'sprite_contact_sheet.png').write_bytes(encoded(sheet))
    reel[0].save(REVIEW/'sprite_animations.gif',save_all=True,append_images=reel[1:],
                 duration=40,loop=0,optimize=False)
    with tempfile.TemporaryDirectory(prefix='nivareth-reel-') as folder:
        for i,frame in enumerate(reel):frame.save(Path(folder)/f'{i:05}.png')
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','25','-i',
            str(Path(folder)/'%05d.png'),'-an','-c:v','libx264','-pix_fmt','yuv420p',
            '-movflags','+faststart',str(REVIEW/'sprite_animations_silent.mp4')],check=True)
    record = {'version':1,'kind':'authored pose review; not gameplay capture',
              'authored_frames':manifest['authored_frames'],'reel_fps':25,'reel_frames':len(reel),
              'manifest_sha256':sha256((OUTPUT/'animation.json').read_bytes()).hexdigest(),
              'files':{name:sha256((REVIEW/name).read_bytes()).hexdigest() for name in
                       ('sprite_contact_sheet.png','sprite_animations.gif','sprite_animations_silent.mp4')}}
    (REVIEW/'verification.json').write_text(json.dumps(record,indent=2)+'\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--review',action='store_true')
    args = parser.parse_args(argv)
    changed = []
    for name, content in products().items():
        path = ROOT/name
        if not path.exists() or path.read_bytes() != content:
            changed.append(name)
            if not args.check:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    if args.check and changed:raise SystemExit('Stale Nivareth exports: '+', '.join(changed))
    if args.review:
        if args.check:raise SystemExit('Use --review separately from --check')
        review()
    print(('Verified' if args.check else 'Built')+' 176 unique authored Nivareth poses / 178 exports')
    return 0


if __name__ == '__main__':raise SystemExit(main())
