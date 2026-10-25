"""Check four-pose running, flight, attached secondary motion and review clocks."""
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

REVIEW=ROOT/'docs/reviews/liam_daisy_run_prototypes'


def read(path):return json.loads(path.read_text())
def pixels(im):return list(getattr(im,'get_flattened_data',im.getdata)())


def reachable(layer,root):
    seen={tuple(root)};pending=list(seen)
    while pending:
        x,y=pending.pop()
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                xx,yy=x+dx,y+dy
                if (xx,yy) not in seen and 0<=xx<layer.width and 0<=yy<layer.height and layer.getpixel((xx,yy))[3]:
                    seen.add((xx,yy));pending.append((xx,yy))
    return seen


class RunPrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packs={}
        for who in ('liam','daisy'):
            path=ROOT/f'assets/characters/{who}/run_left'
            meta=read(path/'animation.json')
            cls.packs[who]=(path,meta,[Image.open(path/f['file']).convert('RGBA') for f in meta['frames']])

    def test_approved_idles_and_all_four_walks_are_unchanged(self):
        protected=read(REVIEW/'animations.json')['protected_inputs_sha256']
        for who in self.packs:
            self.assertIn(f'assets/characters/{who}/idle_left.png',protected)
            self.assertIn(f'assets/characters/{who}/palette.json',protected)
            for direction in ('front','left','right','back'):
                self.assertIn(f'assets/characters/{who}/walk_{direction}/animation.json',protected)
        for path,expected in protected.items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),expected,path)

    def test_four_unique_poses_native_palette_hard_alpha_and_clear_bounds(self):
        for who,(path,meta,frames) in self.packs.items():
            palette=read(path.parent/'palette.json')
            allowed={rgba(c) for ramp in palette['materials'].values() for c in ramp}|{rgba(c) for c in palette['eyes'].values()}
            self.assertEqual(len(frames),4)
            self.assertEqual(len({f.tobytes() for f in frames}),4)
            self.assertEqual(meta['frame_size'],[24 if who=='liam' else 40,36])
            self.assertEqual(meta['foot_anchor'],[12 if who=='liam' else 20,34])
            self.assertEqual(meta['duration_ms'],400)
            self.assertEqual([f['duration_ms'] for f in meta['frames']],[100]*4)
            for frame in frames:
                self.assertEqual(set(frame.getchannel('A').tobytes()),{0,255})
                self.assertTrue(all(not p[3] or p in allowed for p in pixels(frame)))
                left,top,right,bottom=frame.getbbox()
                self.assertGreater(left,0);self.assertLess(right,frame.width)
                self.assertGreater(top,0);self.assertLessEqual(bottom,35)

    def test_ground_contacts_and_real_airborne_poses(self):
        for who,(path,meta,frames) in self.packs.items():
            expected=[False,True,False,True] if who=='liam' else [False,False,False,True]
            self.assertEqual([f['airborne'] for f in meta['frames']],expected)
            template=read(ROOT/meta['template'])
            self.assertEqual(template['frames'],[{k:v for k,v in f.items() if k not in ('file','rect','layers_from_repo_root')} for f in meta['frames']])
            for record,frame in zip(meta['frames'],frames):
                support=record['supporting_legs']
                self.assertEqual(not support,record['airborne'])
                if record['airborne']:
                    self.assertLessEqual(frame.getbbox()[3],33)
                    self.assertFalse(frame.getchannel('A').crop((0,33,frame.width,36)).getbbox())
                else:
                    self.assertEqual(frame.getbbox()[3],35)
                    for name in support:
                        toe=record['legs'][name][-1]
                        self.assertEqual(toe[1],32 if who=='daisy' and name.endswith('right') else 34)
                        layername=name if who=='daisy' else name+'_leg'
                        relative=next(p for p in record['layers_from_repo_root'] if p.endswith('_'+layername+'.png'))
                        leg=Image.open(ROOT/relative).convert('RGBA')
                        self.assertTrue(leg.getpixel(tuple(toe))[3])

    def test_liam_face_neck_and_collar_travel_together_with_bent_limbs(self):
        path,meta,frames=self.packs['liam']
        idle=Image.open(path.parent/'idle_left.png').convert('RGBA')
        for record,frame in zip(meta['frames'],frames):
            dx,dy=record['upper_body_offset']
            self.assertEqual(record['shoulder_offset'],[dx,dy])
            for y in range(23):
                for x in range(24):
                    p=idle.getpixel((x,y))
                    if p[3] and (y<21 or 10<=x<15):
                        self.assertEqual(frame.getpixel((x+dx,y+dy)),p,(record['phase'],x,y))
            for shoulder,elbow,hand in record['arms'].values():
                self.assertLessEqual(math.dist(shoulder,elbow),4)
                self.assertLessEqual(math.dist(elbow,hand),4)
                a=[shoulder[i]-elbow[i] for i in (0,1)]
                b=[hand[i]-elbow[i] for i in (0,1)]
                self.assertNotEqual(a[0]*b[1]-a[1]*b[0],0)
            if not record['airborne']:
                hip,_,toe=record['legs']['near']
                shoulder,_,hand=record['arms']['near']
                self.assertLess((toe[0]-hip[0])*(hand[0]-shoulder[0]),0)

    def test_daisy_face_and_spotted_body_come_from_approved_native_art(self):
        path,meta,frames=self.packs['daisy'];idle=Image.open(path.parent/'idle_left.png').convert('RGBA')
        iris=rgba(read(path.parent/'palette.json')['eyes']['iris'])
        for record,frame in zip(meta['frames'],frames):
            dx,dy=record['upper_body_offset']
            self.assertEqual(frame.crop((1+dx,12+dy,8+dx,20+dy)).tobytes(),idle.crop((1,12,8,20)).tobytes())
            self.assertEqual(pixels(frame).count(iris),1)
            self.assertEqual(frame.getpixel((5+dx,18+dy)),iris)
            bodypath=next(p for p in record['layers_from_repo_root'] if p.endswith('_body.png'))
            body=Image.open(ROOT/bodypath).convert('RGBA')
            self.assertGreater(pixels(body).count(rgba('#25272b')),5)
            # Width changes are tiny native-pixel torso compression/extension.
            self.assertIn(record['body_width_delta'],(-1,1,2))

    def test_daisy_ears_and_tail_have_attached_hinges_and_follow_through(self):
        path,meta,frames=self.packs['daisy'];idle=Image.open(path.parent/'idle_left.png').convert('RGBA')
        ear_shapes=[];tail_shapes=[]
        for record in meta['frames']:
            dy=record['upper_body_offset'][1];stretch=record['body_width_delta']
            ear=Image.open(ROOT/next(p for p in record['layers_from_repo_root'] if p.endswith('_ear.png'))).convert('RGBA')
            tail=Image.open(ROOT/next(p for p in record['layers_from_repo_root'] if p.endswith('_tail.png'))).convert('RGBA')
            eroot=(14,16+dy);troot=(27+stretch,24+dy)
            self.assertEqual(ear.getpixel(eroot),idle.getpixel((10,16)))
            self.assertEqual(tail.getpixel(troot),idle.getpixel((23,24)))
            self.assertGreater(len(reachable(ear,eroot)),5)
            self.assertLess(min(y for x,y in reachable(tail,troot)),troot[1]-5)
            ear_shapes.append((ear.getbbox()[3]-eroot[1],record['ear_tip_offset'][1]))
            tail_shapes.append(tuple(record['tail_tip_offset']))
        self.assertGreater(len(set(ear_shapes)),2)
        self.assertGreater(len(set(tail_shapes)),2)

    def test_retained_source_layers_and_native_strips_reconstruct_frames(self):
        for who,(path,meta,frames) in self.packs.items():
            strip=Image.open(path/'spritesheet.png').convert('RGBA')
            for record,frame in zip(meta['frames'],frames):
                merged=blank(frame.size)
                for relative in record['layers_from_repo_root']:
                    merged.alpha_composite(Image.open(ROOT/relative).convert('RGBA'))
                self.assertEqual(merged.tobytes(),frame.tobytes())
                x,y,w,h=record['rect']
                self.assertEqual(strip.crop((x,y,x+w,y+h)).tobytes(),frame.tobytes())

    def test_review_gifs_decode_exactly_at_normal_and_slow_speeds(self):
        for who,(_,meta,frames) in self.packs.items():
            for suffix,duration in (('',100),('_slow',300)):
                with Image.open(REVIEW/f'{who}_run{suffix}.gif') as gif:
                    self.assertEqual(gif.n_frames,4);self.assertEqual(gif.info['loop'],0)
                    for i,frame in enumerate(frames):
                        gif.seek(i);self.assertEqual(gif.info['duration'],duration)
                        expected=review_panel([frame],[who.title()],f'{who.title()} / left-facing run',
                                              '4 frames | 100 ms per frame | prototype for review' if duration==100 else
                                              'Slow motion | 300 ms per frame | same four poses',16)
                        self.assertEqual(gif.convert('RGB').tobytes(),expected.tobytes())

    def test_comparison_preserves_walk_and_run_clocks_independently(self):
        walking={who:[Image.open(ROOT/f'assets/characters/{who}/walk_left/frame_{i:02}.png').convert('RGBA') for i in range(1,5)] for who in self.packs}
        elapsed=0
        with Image.open(REVIEW/'walk_run_comparison.gif') as gif:
            self.assertEqual(gif.info['loop'],0)
            for i in range(gif.n_frames):
                gif.seek(i);duration=gif.info['duration']
                # A GIF may combine adjacent identical 20ms samples.
                for tick in range(elapsed,elapsed+duration,20):
                    sprites=[sprite for who in self.packs for sprite in (walking[who][tick//140%4],self.packs[who][2][tick//100%4])]
                    expected=review_panel(sprites,['Liam / walk','Liam / run','Daisy / walk','Daisy / run'],
                                          'Approved walks and running prototypes','Independent clocks | walk 140 ms/frame; run 100 ms/frame',8)
                    self.assertEqual(gif.convert('RGB').tobytes(),expected.tobytes(),tick)
                elapsed+=duration
        self.assertEqual(elapsed,2800)


if __name__=='__main__':unittest.main()
