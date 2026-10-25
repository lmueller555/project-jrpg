"""Four-pose run contracts across all new directions and their review GIFs."""
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_liam_daisy_run_prototypes import review_panel
from build_liam_family_front_walks import rgba,blank
from test_liam_daisy_run_prototypes import reachable

REVIEW=ROOT/'docs/reviews/liam_daisy_directional_runs'
DIRECTIONS=('front','right','back')
ALL_DIRECTIONS=('front','left','right','back')


def read(path):return json.loads(path.read_text())
def pixels(im):return list(getattr(im,'get_flattened_data',im.getdata)())


class DirectionalRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packs={}
        for who in ('liam','daisy'):
            for direction in DIRECTIONS:
                path=ROOT/f'assets/characters/{who}/run_{direction}';meta=read(path/'animation.json')
                cls.packs[who,direction]=(path,meta,[Image.open(path/f['file']).convert('RGBA') for f in meta['frames']])

    def test_approved_left_runs_all_walks_and_idles_are_unchanged(self):
        manifest=read(REVIEW/'animations.json')
        self.assertEqual(manifest['new_directions'],list(DIRECTIONS))
        protected=manifest['protected_inputs_sha256']
        for who in ('liam','daisy'):
            self.assertEqual(read(ROOT/f'assets/characters/{who}/run_left/animation.json')['status'],'approved')
            for name in ('animation.json','recipe.json','frame_01.png','spritesheet.png'):
                self.assertIn(f'assets/characters/{who}/run_left/{name}',protected)
            for direction in ALL_DIRECTIONS:
                self.assertIn(f'assets/characters/{who}/idle_{direction}.png',protected)
                self.assertIn(f'assets/characters/{who}/walk_{direction}/animation.json',protected)
        for relative,expected in protected.items():
            self.assertEqual(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest(),expected,relative)

    def test_four_unique_native_frames_palette_bounds_and_timing(self):
        for (who,di),(path,meta,frames) in self.packs.items():
            with self.subTest(character=who,direction=di):
                self.assertEqual(meta['frame_size'],[24 if who=='liam' else 40,36])
                self.assertEqual(meta['foot_anchor'],[12 if who=='liam' else 20,34])
                self.assertEqual(meta['duration_ms'],400);self.assertEqual(len(frames),4)
                self.assertEqual(len({im.tobytes() for im in frames}),4)
                self.assertEqual([f['duration_ms'] for f in meta['frames']],[100]*4)
                p=read(path.parent/'palette.json')
                allowed={rgba(c) for ramp in p['materials'].values() for c in ramp}|{rgba(c) for c in p['eyes'].values()}
                for im in frames:
                    self.assertEqual(set(im.getchannel('A').tobytes()),{0,255})
                    self.assertTrue(all(not p[3] or p in allowed for p in pixels(im)))
                    l,t,r,b=im.getbbox()
                    self.assertGreater(l,0);self.assertGreater(t,0)
                    self.assertLess(r,im.width);self.assertLessEqual(b,35)
                recipe=read(path/'recipe.json')
                self.assertEqual(recipe['approved_idle_sha256'],hashlib.sha256((path.parent/f'idle_{di}.png').read_bytes()).hexdigest())

    def test_support_and_flight_follow_the_approved_gaits(self):
        for (who,di),(path,meta,frames) in self.packs.items():
            self.assertEqual([f['airborne'] for f in meta['frames']],
                             [False,True,False,True] if who=='liam' else [False,False,False,True])
            template=read(ROOT/meta['template'])
            self.assertEqual(template['frames'],[{k:v for k,v in f.items() if k not in ('file','rect','layers_from_repo_root')} for f in meta['frames']])
            for record,im in zip(meta['frames'],frames):
                self.assertEqual(record['upper_body_offset'],record['shoulder_offset'])
                self.assertEqual(not record['supporting_legs'],record['airborne'])
                if record['airborne']:
                    self.assertLessEqual(im.getbbox()[3],33)
                    for name,joints in record['legs'].items():
                        floor=record.get('contact_rows',{}).get(name,34)
                        self.assertLess(joints[-1][1],floor)
                for name in record['supporting_legs']:
                    floor=record.get('contact_rows',{}).get(name,32 if who=='daisy' and name.endswith('left') else 34)
                    self.assertEqual(record['legs'][name][-1][1],floor)
                    layername=name if who=='daisy' else name+'_leg'
                    relative=next(p for p in record['layers_from_repo_root'] if p.endswith('_'+layername+'.png'))
                    leg=Image.open(ROOT/relative).convert('RGBA')
                    self.assertTrue(leg.getpixel(tuple(record['legs'][name][-1]))[3])

    def test_liam_head_neck_collar_and_bent_elbows(self):
        for di in DIRECTIONS:
            path,meta,frames=self.packs['liam',di]
            idle=Image.open(path.parent/f'idle_{di}.png').convert('RGBA');recipe=read(path/'recipe.json')
            for record,im in zip(meta['frames'],frames):
                dx,dy=record['upper_body_offset']
                x0,y0,w,h=recipe['collar_rect']
                for y in range(23):
                    for x in range(24):
                        p=idle.getpixel((x,y))
                        if p[3] and (y<21 or x0<=x<x0+w and y0<=y<y0+h):
                            self.assertEqual(im.getpixel((x+dx,y+dy)),p,('liam',di,record['phase'],x,y))
                for shoulder,elbow,hand in record['arms'].values():
                    self.assertLessEqual(math.dist(shoulder,elbow),4)
                    self.assertLessEqual(math.dist(elbow,hand),4)
                    a=[shoulder[i]-elbow[i] for i in (0,1)];b=[hand[i]-elbow[i] for i in (0,1)]
                    self.assertNotEqual(a[0]*b[1]-a[1]*b[0],0)

    def test_eyes_and_daisy_directional_face_markings(self):
        for (who,di),(path,meta,frames) in self.packs.items():
            palette=read(path.parent/'palette.json');landmarks=read(path.parent/f'idle_{di}.json')['eyes']['top_pixels']
            idle=Image.open(path.parent/f'idle_{di}.png').convert('RGBA')
            for record,im in zip(meta['frames'],frames):
                dx,dy=record['upper_body_offset']
                self.assertEqual(pixels(im).count(rgba(palette['eyes']['iris'])),len(landmarks),(who,di,record['phase']))
                for x,y in landmarks:
                    self.assertEqual(im.getpixel((x+dx,y+dy)),rgba(palette['eyes']['pupil']))
                    self.assertEqual(im.getpixel((x+dx,y+dy+1)),rgba(palette['eyes']['iris']))
                if who=='daisy':
                    box={'front':(13,11,20,21),'right':(24,12,32,20),'back':(9,11,14,15)}[di]
                    x,y,r,b=box
                    self.assertEqual(im.crop((x+dx,y+dy,r+dx,b+dy)).tobytes(),idle.crop(box).tobytes())
        left=Image.open(ROOT/'assets/characters/daisy/run_left/frame_01.png').convert('RGBA')
        right=self.packs['daisy','right'][2][0]
        self.assertNotEqual(right.tobytes(),left.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes())
        # Her white right hip remains distinct from the large dark left patch.
        def white_count(path):
            layer=Image.open(path).convert('RGBA')
            return sum(p in {rgba(c) for c in ('#c5c5bd','#eee8d9','#fff4df')} for p in pixels(layer))
        for i,record in enumerate(self.packs['daisy','right'][1]['frames'],1):
            p=ROOT/next(p for p in record['layers_from_repo_root'] if p.endswith('_body.png'))
            l=ROOT/f'assets/source/characters/daisy/run_left/parts/frame_{i:02}_body.png'
            self.assertGreater(white_count(p),white_count(l))

    def test_daisy_ear_and_tail_roots_stay_attached(self):
        for di in DIRECTIONS:
            path,meta,frames=self.packs['daisy',di];recipe=read(path/'recipe.json')
            idle=Image.open(path.parent/f'idle_{di}.png').convert('RGBA')
            tip_positions=[]
            for record in meta['frames']:
                dy=record['upper_body_offset'][1]
                for side,pivot in recipe['ear_pivots_native'].items():
                    layer=Image.open(ROOT/next(p for p in record['layers_from_repo_root'] if p.endswith('_ear_'+side+'.png'))).convert('RGBA')
                    root=(pivot[0]+4,pivot[1]+dy)
                    self.assertEqual(layer.getpixel(root),idle.getpixel(tuple(pivot)),(di,side,record['phase']))
                    self.assertGreater(len(reachable(layer,root)),3)
                    tip_positions.append((side,layer.getbbox()[3]-root[1]))
                tail=Image.open(ROOT/next(p for p in record['layers_from_repo_root'] if p.endswith('_tail.png'))).convert('RGBA')
                x,y=recipe['tail_pivot_native'];root=(x+4-record.get('body_width_delta',0) if di=='right' else x+4,y+dy)
                self.assertTrue(tail.getpixel(root)[3],(di,record['phase']))
                self.assertLess(min(yy for xx,yy in reachable(tail,root)),root[1]-4,(di,record['phase']))
            self.assertGreater(len(set(tip_positions)),2)

    def test_native_strips_and_layers_reconstruct_every_frame(self):
        for (who,di),(path,meta,frames) in self.packs.items():
            sheet=Image.open(path/'spritesheet.png').convert('RGBA')
            for record,im in zip(meta['frames'],frames):
                merged=blank(im.size)
                for relative in record['layers_from_repo_root']:merged.alpha_composite(Image.open(ROOT/relative).convert('RGBA'))
                self.assertEqual(merged.tobytes(),im.tobytes())
                x,y,w,h=record['rect'];self.assertEqual(sheet.crop((x,y,x+w,y+h)).tobytes(),im.tobytes())

    def test_enlarged_looping_gifs_preserve_exact_pixels_and_timing(self):
        for who in ('liam','daisy'):
            for suffix,duration in (('',100),('_slow',300)):
                sub='4 frames | 100 ms per frame | left approved; other views for review' if duration==100 else 'Slow motion | 300 ms per frame | left approved; other views for review'
                with Image.open(REVIEW/f'{who}_all_directions{suffix}.gif') as gif:
                    self.assertEqual(gif.n_frames,4);self.assertEqual(gif.info['loop'],0)
                    for i in range(4):
                        gif.seek(i);self.assertEqual(gif.info['duration'],duration)
                        sprites=[Image.open(ROOT/f'assets/characters/{who}/run_{d}/frame_{i+1:02}.png').convert('RGBA') for d in ALL_DIRECTIONS]
                        expected=review_panel(sprites,[d.title() for d in ALL_DIRECTIONS],f'{who.title()} / all running directions',sub,10)
                        self.assertEqual(gif.convert('RGB').tobytes(),expected.tobytes())


if __name__=='__main__':unittest.main()
