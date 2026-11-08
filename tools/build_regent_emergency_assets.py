"""Export the injured Crown worker using registered native villager pixels.

The character keeps the original head, clothing material and boot registration.
Authored wraps, dust and guarded poses are separate derived assets. No shared
actor or scene is changed by this builder.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/story/regent_emergency/recipe.json'
OUTPUT = ROOT/'assets/story/regent_emergency'
DIRECTIONS = ('front', 'back', 'left', 'right')


def png(image):
    stream = BytesIO();image.save(stream, format='PNG');return stream.getvalue()


def injured(source, direction, palette, *, alarm=False):
    """Lean only the upper body, leaving actual contact boots in place."""
    source = source.convert('RGBA')
    image = source.copy()
    image.paste((0,0,0,0), (0,0,24,29))
    lean = -1 if direction == 'left' else 1 if direction == 'right' else 0
    image.alpha_composite(source.crop((0,0,24,28)), (lean,1))
    draw = ImageDraw.Draw(image)
    # A small forehead dressing leaves the eyes and established face readable.
    if direction == 'front':
        draw.line((7,10,11,10), fill=palette['bandage_shadow'])
        draw.line((7,9,11,9), fill=palette['bandage'])
        draw.point((8,9), fill=palette['bandage_light'])
        draw.point((15,14), fill=palette['small_wound'])
        arm=(16,22,18,24);dust=((7,21),(8,24),(12,26),(16,19))
        # The injured worker guards his ribs with the free hand.
        draw.line((13,23,11,24), fill=palette['skin'])
    elif direction == 'back':
        draw.line((7,10,11,10), fill=palette['bandage_shadow'])
        arm=(5,22,7,24);dust=((9,20),(10,23),(15,25),(6,25))
    elif direction == 'left':
        draw.line((8,9,10,9), fill=palette['bandage'])
        arm=(8,22,10,24);dust=((10,19),(11,23),(13,25))
    else:
        draw.line((12,9,14,9), fill=palette['bandage'])
        arm=(13,22,15,24);dust=((12,20),(14,25),(10,24))
    draw.rectangle(arm, fill=palette['bandage_shadow'])
    draw.line((arm[0],arm[1]+1,arm[2],arm[1]+1), fill=palette['bandage'])
    draw.point((arm[0],arm[1]), fill=palette['bandage_light'])
    for index, point in enumerate(dust):
        if image.getpixel(point)[3]:
            draw.point(point, fill=palette['dust'] if index%2 else palette['dust_shadow'])
    if alarm and direction == 'front':
        draw.line((9,23,11,25,14,23), fill=palette['skin'])
        draw.point((12,22), fill=palette['bandage'])
    return image


def resting(idle, palette):
    """Seated knees and boots fit the existing spare bench, on a24×36 canvas."""
    image = idle.copy()
    image.paste((0,0,0,0), (0,27,24,36))
    draw = ImageDraw.Draw(image)
    draw.polygon(((7,26),(16,26),(19,29),(17,31),(9,29),(5,30),(4,28)),
                 fill=palette['pants_shadow'])
    draw.line((7,27,11,28,17,28), fill=palette['pants'], width=2)
    draw.line((6,29,7,32), fill=palette['pants'])
    draw.line((17,29,18,32), fill=palette['pants'])
    draw.line((5,33,8,33), fill=palette['boot'], width=2)
    draw.line((17,33,20,33), fill=palette['boot'], width=2)
    return image


def products():
    recipe = json.loads(SOURCE.read_text())
    for record in recipe['sources']:
        if sha256((ROOT/record['path']).read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Survivor reference changed: '+record['path'])
    output = {};images = {};root = ROOT/recipe['source_sprite_root']
    def export(name, image):
        output[OUTPUT/name] = png(image)
        images[name] = image
        return (OUTPUT/name).relative_to(ROOT).as_posix()
    idles = {};walks = {}
    for direction in DIRECTIONS:
        idle = injured(Image.open(root/f'idle_{direction}.png'), direction, recipe['palette'])
        idles[direction] = export(f'idle_{direction}.png', idle)
        frames = [export(f'walk_{direction}/frame_{index:02}.png', injured(
            Image.open(root/f'walk_{direction}/frame_{index+1:02}.png'), direction, recipe['palette']))
            for index in range(4)]
        walks[direction] = [frames[index] for index in recipe['walk_order']]
    alarm = injured(Image.open(root/'idle_front.png'), 'front', recipe['palette'], alarm=True)
    poses = {'alarm_front':export('poses/alarm_front.png', alarm),
             'rest_front':export('poses/rest_front.png', resting(images['idle_front.png'], recipe['palette']))}
    aid = Image.open(ROOT/'assets/characters/serene/idle_left.png').convert('RGBA')
    aid_draw = ImageDraw.Draw(aid)
    aid_draw.line((8,21,5,23,3,23), fill=recipe['palette']['skin'], width=2)
    aid_draw.rectangle((0,23,3,25), fill=recipe['palette']['bandage_shadow'])
    aid_draw.line((0,23,3,23), fill=recipe['palette']['bandage_light'])
    poses['serene_aid_left'] = export('poses/serene_aid_left.png', aid)
    portrait = Image.open(ROOT/recipe['source_portrait']).convert('RGB')
    painter = ImageDraw.Draw(portrait)
    painter.polygon(((22,26),(29,25),(30,28),(23,29)), fill=recipe['palette']['bandage_shadow'])
    painter.line((23,26,29,26), fill=recipe['palette']['bandage'], width=2)
    painter.point((24,26), fill=recipe['palette']['bandage_light'])
    # Lift the inner brows and part the lips: the same face is visibly shaken
    # and short of breath, instead of retaining the source's relaxed smile.
    painter.line(((27,30),(30,28),(33,28)), fill='#60412f')
    painter.line(((39,28),(42,29),(44,30)), fill='#60412f')
    painter.rectangle((33,43,40,46), fill=portrait.getpixel((38,42)))
    painter.polygon(((35,44),(37,43),(39,44),(39,46),(37,47),(35,46)),fill='#75432f')
    painter.line((36,47,38,47),fill='#ca8050')
    painter.line((49,33,49,35), fill='#d8d9bb')
    painter.line((46,43,48,45), fill=recipe['palette']['dust_shadow'])
    painter.line((28,63,32,65), fill=recipe['palette']['dust'])
    portrait_path = export('portrait.png', portrait)
    # Social's standard portrait registry resolves files in this shared folder;
    # this is a new derivative, never a replacement for its approved source.
    output[ROOT/'assets/portraits/eldenmere/regent_survivor.png'] = png(portrait)
    animation = {'id':recipe['id'],'status':recipe['status'],
                 'frame_size':recipe['frame_size'],'draw_anchor':recipe['draw_anchor'],
                 'foot_anchor':recipe['foot_anchor'],'probe_size':recipe['probe_size'],
                 'idles':idles,'walks':walks,'poses':poses,'portrait':portrait_path,
                 'frame_duration_ms':recipe['frame_duration_ms'],
                 'source_recipe':SOURCE.relative_to(ROOT).as_posix(),
                 'source_recipe_sha256':sha256(SOURCE.read_bytes()).hexdigest(),
                 'source_assets':recipe['sources']}
    output[OUTPUT/'animation.json'] = (json.dumps(animation,indent=2)+'\n').encode()
    board = Image.new('RGB',(1152,660),'#23483b');draw=ImageDraw.Draw(board)
    font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'),20)
    small = ImageFont.truetype(str(ROOT/'assets/ui/fonts/DejaVuSans.ttf'),16)
    draw.text((20,12),'MQ03 survivor / native injured Crown worker /24×36 source scale',font=font,fill='#e3e8d6')
    hero = Image.open(ROOT/'assets/characters/caelan/idle_front.png').convert('RGBA')
    for index,direction in enumerate(DIRECTIONS):
        x=24+index*190;y=60
        for image,dx in ((hero,0),(images[f'idle_{direction}.png'],80)):
            board.paste(image.resize((96,144),Image.Resampling.NEAREST),(x+dx,y),
                        image.resize((96,144),Image.Resampling.NEAREST))
        draw.text((x,y+154),direction.title(),font=small,fill='#d6e1d3')
    board.paste(portrait.resize((216,216),Image.Resampling.NEAREST),(900,48))
    draw.text((24,254),'Limp: source-contact poses retained; hurt-side support held longer',font=font,fill='#e3e8d6')
    for index,frame in enumerate(walks['front']):
        im=images[str(Path(frame).relative_to(OUTPUT.relative_to(ROOT)))]
        scaled=im.resize((96,144),Image.Resampling.NEAREST)
        board.paste(scaled,(24+index*140,300),scaled)
        draw.text((24+index*140,450),str(index+1),font=small,fill='#d6e1d3')
    draw.text((24,504),'Alarm, registered bench-rest and Serene cloth-preparation poses',font=font,fill='#e3e8d6')
    for index,name in enumerate(('poses/alarm_front.png','poses/rest_front.png','poses/serene_aid_left.png')):
        im=images[name];scaled=im.resize((72,108),Image.Resampling.NEAREST)
        board.paste(scaled,(24+index*150,536),scaled)
    export('materials_review.png',board)
    return output


def build(check=False):
    for path,body in products().items():
        if check:
            if not path.is_file() or path.read_bytes()!=body:
                raise ValueError('Stale emergency actor export: '+str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
    print(('Verified' if check else 'Built')+' native MQ03 emergency survivor assets')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
