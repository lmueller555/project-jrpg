"""Asset contracts for the family's twelve new walking animations."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_liam_family_front_walks import blank, panel, rgba

CHARACTERS = ('liam', 'liam_mother', 'liam_father', 'daisy')
DIRECTIONS = ('left', 'right', 'back')
REVIEW = ROOT / 'docs/reviews/liam_family_directional_walks'
LABELS = ('Liam', 'Mother', 'Father', 'Daisy')


def read(path):
    return json.loads(path.read_text())


def pixels(im):
    return list(getattr(im, 'get_flattened_data', im.getdata)())


class FamilyDirectionalWalkTests(unittest.TestCase):
    def cases(self):
        for character in CHARACTERS:
            for direction in DIRECTIONS:
                base = ROOT / f'assets/characters/{character}'
                path = base / f'walk_{direction}'
                yield character, direction, base, path, read(path / 'animation.json')

    def test_approved_inputs_unchanged(self):
        manifest = read(REVIEW / 'animations.json')
        protected = manifest['protected_inputs_sha256']
        for who in CHARACTERS:
            for direction in ('front',) + DIRECTIONS:
                self.assertIn(f'assets/characters/{who}/idle_{direction}.png',protected)
            self.assertIn(f'assets/characters/{who}/walk_front/animation.json',protected)
            self.assertIn(f'assets/characters/{who}/palette.json',protected)
        for relative, expected in protected.items():
            with self.subTest(path=relative):
                self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected)
        self.assertEqual(manifest['new_directions'], list(DIRECTIONS))
        self.assertEqual(len(manifest['animations']), 4)

    def test_size_palette_height_and_timing(self):
        for who, direction, base, path, animation in self.cases():
            with self.subTest(character=who, direction=direction):
                palette = read(base / 'palette.json')
                allowed = {rgba(c) for ramp in palette['materials'].values() for c in ramp}
                allowed.update(rgba(c) for c in palette['eyes'].values())
                idle = read(base / f'idle_{direction}.json')
                frames = []
                self.assertEqual(animation['frame_size'], [32 if who == 'daisy' else 24, 36])
                self.assertEqual(animation['foot_anchor'], [16 if who == 'daisy' else 12, 34])
                self.assertEqual(animation['duration_ms'], 560)
                for i, record in enumerate(animation['frames']):
                    im = Image.open(path / record['file']).convert('RGBA'); frames.append(im.tobytes())
                    self.assertEqual(record['duration_ms'], 140)
                    self.assertEqual(record['upper_body_offset'], [0, -(i % 2)])
                    self.assertEqual(record['shoulder_offset'], record['upper_body_offset'])
                    self.assertEqual(im.getbbox()[1::2], (35-idle['visible_height_px']-(i%2), 35))
                    self.assertEqual(set(im.getchannel('A').tobytes()), {0, 255})
                    self.assertFalse(im.getchannel('A').crop((0,35,im.width,36)).getbbox())
                    self.assertTrue(all(not p[3] or p in allowed for p in pixels(im)))
                self.assertEqual(len(set(frames)), 4)
                recipe = read(path / 'recipe.json')
                self.assertEqual(recipe['approved_idle_sha256'], hashlib.sha256((base / f'idle_{direction}.png').read_bytes()).hexdigest())

    def test_human_faces_necks_and_braids_translate_with_shoulders(self):
        for who, direction, base, path, animation in self.cases():
            if who == 'daisy': continue
            idle = Image.open(base / f'idle_{direction}.png').convert('RGBA')
            recipe = read(path / 'recipe.json')
            m = read(base / 'palette.json')['materials']
            for record in animation['frames']:
                im = Image.open(path / record['file']).convert('RGBA')
                dy = record['upper_body_offset'][1]
                # The whole approved head includes chin and neck; profile arm
                # masks cannot introduce the source character's longer neck.
                for y in range(recipe['head_end']):
                    for x in range(24):
                        p = idle.getpixel((x,y))
                        if p[3]: self.assertEqual(im.getpixel((x,y+dy)), p, (who,direction,x,y))
                x,y,w,h = recipe['torso_rect']
                for yy in range(y,y+h):
                    for xx in range(x,x+w):
                        p=idle.getpixel((xx,yy))
                        if p[3]: self.assertEqual(im.getpixel((xx,yy+dy)), p, (who,direction,xx,yy))
                if who == 'liam_mother':
                    hair = {rgba(c) for c in m['hair']}
                    for yy in range(14,21):
                        for xx in range(10,17):
                            p=idle.getpixel((xx,yy))
                            if p in hair: self.assertEqual(im.getpixel((xx,yy+dy)), p)
                if direction != 'back' and who != 'liam_father':
                    x = (10 if direction=='left' else 14)
                    y = 20 if who=='liam' else 13
                    self.assertIn(im.getpixel((x,y+dy)), {rgba(c) for c in m['skin']})

    def test_eyes_and_directional_costume_details(self):
        for who, direction, base, path, animation in self.cases():
            palette = read(base / 'palette.json')
            idle_meta = read(base / f'idle_{direction}.json')
            for record in animation['frames']:
                im = Image.open(path / record['file']).convert('RGBA')
                iris = rgba(palette['eyes']['iris'])
                self.assertEqual(pixels(im).count(iris), len(idle_meta['eyes']['top_pixels']))
                for x,y in idle_meta['eyes']['top_pixels']:
                    yy=y+record['upper_body_offset'][1]
                    self.assertEqual(im.getpixel((x,yy)), rgba(palette['eyes']['pupil']))
                    self.assertEqual(im.getpixel((x,yy+1)), iris)
                if direction=='back' and who=='liam_father':
                    self.assertTrue(set(pixels(im)).isdisjoint({rgba(c) for c in palette['materials']['buckle']}))
                if who=='liam_mother':
                    # No bare calf visible under this long dress.
                    skin={rgba(c) for c in palette['materials']['skin']}
                    self.assertTrue(set(pixels(im.crop((0,28,24,36)))).isdisjoint(skin))
                    if direction=='back':
                        linen={rgba(c) for c in palette['materials']['linen']}
                        self.assertTrue(set(pixels(im.crop((0,24,24,32)))).isdisjoint(linen))

    def test_daisy_four_beat_support_and_paw_projection(self):
        order=('hind_left','fore_left','hind_right','fore_right')
        for direction in DIRECTIONS:
            base=ROOT/f'assets/characters/daisy/walk_{direction}'
            animation=read(base/'animation.json')
            template=read(ROOT/animation['template'])
            self.assertEqual(template['order'],list(order))
            for i,record in enumerate(animation['frames']):
                self.assertEqual(record['legs'],template['frames'][i]['legs'])
                self.assertEqual([n for n,leg in record['legs'].items() if not leg['planted']], [order[i]])
                self.assertEqual(sum(leg['planted'] for leg in record['legs'].values()),3)
                for name,spec in record['legs'].items():
                    layer_path=next(p for p in record['layers_from_repo_root'] if p.endswith('_'+name+'.png'))
                    layer=Image.open(ROOT/layer_path).convert('RGBA')
                    row=spec['contact_row']-(0 if spec['planted'] else 2)
                    self.assertEqual(spec['toe'][1],row)
                    self.assertEqual(layer.getbbox()[3],row+1)
                im=Image.open(base/record['file'])
                self.assertEqual(im.getbbox()[3],35)

    def test_daisy_approved_face_and_asymmetric_markings(self):
        # Keep the opposite flanks distinct rather than mirroring one view.
        signatures=[]
        for direction in DIRECTIONS:
            base=ROOT/'assets/characters/daisy'
            idle=Image.open(base/f'idle_{direction}.png').convert('RGBA')
            folder=base/f'walk_{direction}'
            animation=read(folder/'animation.json')
            signatures.append(Image.open(folder/'frame_01.png').tobytes())
            rect={'left':(13,21,22,25),'right':(10,21,19,25),'back':(8,20,18,25)}[direction]
            for record in animation['frames']:
                dy=record['upper_body_offset'][1]
                im=Image.open(folder/record['file']).convert('RGBA')
                x,y,r,b=rect
                self.assertEqual(im.crop((x,y+dy,r,b+dy)).tobytes(),idle.crop(rect).tobytes())
                # Nose/face are inherited, not stretched or redrawn.
                face={'left':(1,12,8,20),'right':(24,12,32,20),'back':(8,11,15,18)}[direction]
                x,y,r,b=face
                self.assertEqual(im.crop((x,y+dy,r,b+dy)).tobytes(),idle.crop(face).tobytes())
        self.assertNotEqual(signatures[0], Image.open(ROOT/'assets/characters/daisy/walk_right/frame_01.png').transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes())

    def test_retained_layers_and_sheet_reconstruct_every_frame(self):
        for who, direction, base, path, animation in self.cases():
            sheet=Image.open(path/'spritesheet.png').convert('RGBA')
            for record in animation['frames']:
                im=Image.open(path/record['file']).convert('RGBA')
                composite=blank(im.size)
                for relative in record['layers_from_repo_root']:
                    composite.alpha_composite(Image.open(ROOT/relative).convert('RGBA'))
                self.assertEqual(composite.tobytes(), im.tobytes())
                x,y,w,h=record['rect']
                self.assertEqual(sheet.crop((x,y,x+w,y+h)).tobytes(),im.tobytes())

    def test_review_gifs_are_looping_exact_color_and_synchronized(self):
        for direction in DIRECTIONS:
            gif=Image.open(REVIEW/f'all_{direction}_walks.gif')
            self.assertEqual(gif.n_frames,4)
            self.assertEqual(gif.info['loop'],0)
            for index in range(4):
                gif.seek(index)
                self.assertEqual(gif.info['duration'],140)
                sprites=[Image.open(ROOT/f'assets/characters/{who}/walk_{direction}/frame_{index+1:02}.png').convert('RGBA') for who in CHARACTERS]
                expected=panel(sprites,LABELS,10,f'Liam and family / {direction} walks',
                               'Shared scale and timing | 140 ms per frame | design review')
                self.assertEqual(gif.convert('RGB').tobytes(),expected.tobytes())
            gif.close()
        for who in CHARACTERS:
            gif=Image.open(REVIEW/f'{who}_all_directions.gif')
            self.assertEqual(gif.n_frames,4)
            self.assertEqual(gif.info['loop'],0)
            for i in range(4):
                gif.seek(i)
                self.assertEqual(gif.info['duration'],140)
            gif.close()


if __name__=='__main__':unittest.main()
