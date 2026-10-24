"""Pose Mira's approved appearance parts for a readable outdoor repair routine.

Only new work assets are exported; approved idles, walks and bench stay intact.
"""
from pathlib import Path
import json

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/characters/mira/work_bench'
OUTPUT = ROOT / 'assets/characters/mira/work_bench'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def blank(size=(24, 36)):
    return Image.new('RGBA', size)


def region(image, box):
    result = blank()
    result.paste(image.crop(box), box[:2])
    return result


def arm(image, points, palette, cuff=True):
    """Explicit articulated sleeve, elbow and hand poses in native pixels."""
    d = ImageDraw.Draw(image)
    shoulder, elbow, hand = map(tuple, points)
    d.line((shoulder, elbow, hand), fill=palette['outline'], width=5)
    d.line((shoulder, elbow), fill=palette['fabric_base'], width=3)
    d.line((elbow, hand), fill=palette['skin_shadow'], width=3)
    d.line((elbow, hand), fill=palette['skin_base'], width=1)
    x, y = elbow
    if cuff:
        d.line((x-1, y-1, x+1, y-1), fill=palette['fabric_light'], width=2)
    x, y = hand
    d.rectangle((x-1, y-1, x+1, y+1), fill=palette['skin_base'])


def build():
    recipe = read(SOURCE / 'recipe.json')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    parts_dir = SOURCE / 'parts'
    parts_dir.mkdir(exist_ok=True)
    left = Image.open(ROOT / recipe['head_source']).convert('RGBA')
    back = Image.open(ROOT / recipe['body_source']).convert('RGBA')
    head = region(left, (0, 0, 24, 17))
    legs = region(back, (0, 26, 24, 36))
    waist = region(back, (8, 21, 16, 26))
    pouch = region(left, (7, 22, 11, 26))
    for name, image in [('head', head), ('legs', legs), ('waist', waist), ('pouch', pouch)]:
        image.save(parts_dir / f'{name}.png')
    palette = read(ROOT / 'assets/characters/mira/walk_left/recipe.json')['palette']
    palette.update(tool_dark='#485354', tool_light='#b8c9c6', brass='#b69652')
    frames = {}
    for name, pose in recipe['poses'].items():
        image = blank()
        image.alpha_composite(legs)
        image.alpha_composite(waist)
        image.alpha_composite(pouch)
        dx, dy = pose['lean']
        # Shoulder and head share the lean, preserving the neckline.
        torso = blank()
        d = ImageDraw.Draw(torso)
        d.polygon([(8,17),(14,17),(16,21),(15,22),(8,22)], fill=palette['outline'])
        d.polygon([(8,17),(14,17),(15,20),(14,21),(9,21)], fill=palette['fabric_base'])
        d.line((9,17,13,17), fill=palette['fabric_light'], width=2)
        d.line((13,19,14,21), fill=palette['fabric_shadow'])
        image.alpha_composite(torso, (dx, dy))
        # Far hand steadies the fitting; near hand visibly operates the wrench.
        arms = blank()
        arm(arms, pose['steady_arm'], palette)
        arm(arms, pose['working_arm'], palette)
        arms.save(parts_dir / f'{name}_arms.png')
        image.alpha_composite(arms)
        image.alpha_composite(head, (dx, dy))
        # Tool remains in front of the hand, with a small skin grip over it.
        tool = blank()
        d = ImageDraw.Draw(tool)
        pivot = tuple(pose['tool_pivot'])
        grip = tuple(pose['working_arm'][-1])
        d.line((pivot, grip), fill=palette['tool_dark'], width=3)
        d.line((pivot, grip), fill=palette['tool_light'], width=1)
        x,y = pivot
        d.line((x-2,y-1,x-2,y+1,x,y+2,x+2,y+1,x+2,y-1), fill=palette['tool_dark'], width=1)
        d.line((x-1,y,x,y+1,x+1,y), fill=palette['tool_light'])
        x,y = grip
        d.line((x-1,y,x+1,y), fill=palette['skin_base'])
        tool.save(parts_dir / f'{name}_tool.png')
        image.alpha_composite(tool)
        image.save(OUTPUT / f'{name}.png')
        frames[name] = image
    # A separate small repair fitting sits on the existing, unchanged bench.
    for phase, offset in enumerate((0, 1, 0, -1)):
        part = blank((12, 9))
        d = ImageDraw.Draw(part)
        d.rectangle((1,6,10,8), fill='#485354')
        d.line((2,6,9,6), fill='#b8c9c6')
        d.rectangle((3,1,8,6), fill='#735b36')
        d.polygon([(4,0),(7,0),(7,1),(9,2),(9,4),(8,5),(7,7),(4,7),(3,5),(2,4),(2,2),(4,1)], fill='#b69652')
        d.rectangle((4,2,7,5), fill='#735b36')
        d.line((5,2,6,2), fill='#e2c68a')
        # Testing turns the bright three-pixel handle through a broad arc.
        end=(8,1) if offset>0 else (2,1) if offset<0 else (6,3)
        d.line((5,4,*end), fill='#b8c9c6', width=1)
        d.point(end, fill='#e2c68a')
        part.save(OUTPUT / f'fitting_{phase}.png')
    sequence = []
    for step in recipe['sequence']:
        sequence.append({**step, 'file':step['pose']+'.png', 'fitting_file':f"fitting_{step.get('fitting_phase',0)}.png"})
    animation = {
        'id':'mira.work_bench', 'status':recipe['status'], 'frame_size':[24,36],
        'foot_anchor':[12,34], 'draw_anchor':[12,30], 'loop':True,
        'duration_ms':sum(s['duration_ms'] for s in sequence),
        'frames':sequence, 'source_recipe':'../../../source/characters/mira/work_bench/recipe.json',
        'station':recipe['station'], 'fitting_position':recipe['fitting_position'],
    }
    write(OUTPUT / 'animation.json', animation)
    # Native sprite sheet and enlarged opaque pose contact sheet.
    names = list(frames)
    sheet = blank((24*len(names),36))
    review = Image.new('RGB',(24*len(names),40),'#e8edf2')
    for i,name in enumerate(names):
        sheet.alpha_composite(frames[name],(i*24,0))
        review.paste(frames[name],(i*24,2),frames[name])
    sheet.save(OUTPUT/'spritesheet.png')
    review.resize((review.width*6,240),Image.Resampling.NEAREST).save(OUTPUT/'poses_review.png')
    print(f"Built Mira bench routine: {len(names)} poses, {animation['duration_ms']} ms")


if __name__=='__main__':build()
