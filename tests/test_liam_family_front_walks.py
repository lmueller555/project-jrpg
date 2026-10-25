"""Exported motion contracts: faces, scale, boots, paw support and GIF playback."""
import hashlib
import json
from pathlib import Path
import unittest

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
IDS=('liam','liam_mother','liam_father','daisy')
HEIGHTS={'liam':26,'liam_mother':34,'liam_father':34,'daisy':24}


def read(path):return json.loads(path.read_text())
def rgba(color):return tuple(bytes.fromhex(color[1:]))+(255,)


class FamilyFrontWalks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packs={}
        for identity in IDS:
            folder=ROOT/f'assets/characters/{identity}/walk_front'
            meta=read(folder/'animation.json')
            cls.packs[identity]=(folder,meta,[Image.open(folder/r['file']).convert('RGBA') for r in meta['frames']])

    def test_four_unique_frames_palette_scale_baseline_and_timing(self):
        for identity,(folder,meta,frames) in self.packs.items():
            palette=read(folder.parent/'palette.json')
            allowed={rgba(c) for colors in palette['materials'].values() for c in colors}|{rgba(c) for c in palette['eyes'].values()}
            self.assertEqual(len(frames),4);self.assertEqual(len({f.tobytes() for f in frames}),4)
            self.assertEqual([r['duration_ms'] for r in meta['frames']],[140]*4)
            self.assertEqual(meta['duration_ms'],560)
            self.assertEqual(meta['rest_visible_height_px'],HEIGHTS[identity])
            recipe=read(folder/'recipe.json')
            self.assertEqual(recipe['approved_idle_sha256'],hashlib.sha256((folder.parent/'idle_front.png').read_bytes()).hexdigest())
            for frame,record in zip(frames,meta['frames']):
                dy=record['upper_body_offset'][1]
                self.assertEqual(frame.size,(32 if identity=='daisy' else 24,36))
                self.assertEqual(frame.getbbox()[1::2],(35-HEIGHTS[identity]+dy,35))
                self.assertEqual(set(frame.getchannel('A').tobytes()),{0,255})
                self.assertTrue(all(not p[3] or p in allowed for p in getattr(frame,'get_flattened_data',frame.getdata)()))

    def test_human_face_neck_and_shoulders_keep_the_approved_translation(self):
        for identity in IDS[:-1]:
            folder,meta,frames=self.packs[identity];idle=Image.open(folder.parent/'idle_front.png').convert('RGBA')
            recipe=read(folder/'recipe.json');head_end=recipe['head_rows'][1]
            x0,y0,w,h=recipe['torso_rect']
            for frame,record in zip(frames,meta['frames']):
                dy=record['upper_body_offset'][1]
                self.assertEqual(record['shoulder_offset'],[0,dy])
                for y in range(36):
                    for x in range(24):
                        p=idle.getpixel((x,y))
                        if p[3] and (y<head_end or x0<=x<x0+w and y0<=y<y0+h):
                            self.assertEqual(frame.getpixel((x,y+dy)),p,(identity,record['phase'],x,y))

    def test_mother_apron_and_both_boots_remain_visible_in_every_phase(self):
        folder,meta,frames=self.packs['liam_mother'];palette=read(folder.parent/'palette.json')
        linen={rgba(c) for c in palette['materials']['linen']}
        leather={rgba(c) for c in palette['materials']['leather']}
        for frame,record in zip(frames,meta['frames']):
            self.assertGreater(sum(frame.getpixel((x,y)) in linen for y in range(21,29) for x in range(7,17)),30)
            for left,right in ((0,12),(12,24)):
                self.assertGreater(sum(frame.getpixel((x,y)) in leather for y in range(record['hem_row']+1,35) for x in range(left,right)),0)
        self.assertEqual([r['hem_row'] for r in meta['frames']],[31,30,31,30])

    def test_daisy_walk_is_four_beats_with_three_supporting_paws(self):
        folder,meta,frames=self.packs['daisy']
        order=[]
        for frame,record in zip(frames,meta['frames']):
            swing=[name for name,leg in record['legs'].items() if not leg['planted']]
            self.assertEqual(len(swing),1);order.extend(swing)
            self.assertEqual(sum(p['planted'] for p in record['legs'].values()),3)
            for name,leg in record['legs'].items():
                expected_floor=32 if name.startswith('hind') else 34
                self.assertEqual(leg['toe'][1],expected_floor if leg['planted'] else expected_floor-2)
                path=next(p for p in record['layers_from_repo_root'] if p.endswith(f'_{name}.png'))
                paw=Image.open(ROOT/path).convert('RGBA')
                self.assertEqual(paw.getpixel(tuple(leg['toe']))[3],255,(name,record['phase']))
            # There is always an actual front paw touching the ground plane.
            self.assertIsNotNone(frame.getchannel('A').crop((0,34,32,35)).getbbox())
        self.assertEqual(order,['hind_left','fore_left','hind_right','fore_right'])

    def test_daisy_face_and_chest_markings_move_with_her_body(self):
        folder,meta,frames=self.packs['daisy'];idle=Image.open(folder.parent/'idle_front.png').convert('RGBA')
        for frame,record in zip(frames,meta['frames']):
            dy=record['upper_body_offset'][1]
            for y in range(11,27):
                for x in range(13,21):
                    p=idle.getpixel((x,y))
                    if p[3]:self.assertEqual(frame.getpixel((x,y+dy)),p,(record['phase'],x,y))
        child=self.packs['liam'][2]
        for dog,boy in zip(frames,child):self.assertEqual(dog.getbbox()[1]-boy.getbbox()[1],2)

    def test_native_sheets_and_source_layers_reconstruct_every_frame(self):
        for identity,(folder,meta,frames) in self.packs.items():
            sheet=Image.open(folder/meta['image']).convert('RGBA')
            for frame,record in zip(frames,meta['frames']):
                x,y,w,h=record['rect'];self.assertEqual(sheet.crop((x,y,x+w,y+h)).tobytes(),frame.tobytes())
                combined=Image.new('RGBA',frame.size)
                for path in record['layers_from_repo_root']:combined.alpha_composite(Image.open(ROOT/path).convert('RGBA'))
                self.assertEqual(combined.tobytes(),frame.tobytes())

    def test_individual_and_synchronized_gifs_decode_at_exact_native_colors(self):
        review=ROOT/'docs/reviews/liam_family_front_walks'
        for identity,(folder,meta,frames) in self.packs.items():
            with Image.open(review/f'{identity}.gif') as gif:
                self.assertEqual(gif.n_frames,4);self.assertEqual(gif.info['loop'],0)
                for i,frame in enumerate(frames):
                    gif.seek(i);self.assertEqual(gif.info['duration'],140)
                    x=24+(32-frame.width)//2*20
                    # Row 35 is transparent padding; the review's floor guide
                    # lies there, below every sprite pixel.
                    actual=gif.convert('RGB').crop((x,104,x+frame.width*20,104+700))
                    expected=Image.new('RGB',frame.size,'#e8edf2');expected.paste(frame,(0,0),frame)
                    self.assertEqual(actual.tobytes(),expected.crop((0,0,frame.width,35)).resize(actual.size,Image.Resampling.NEAREST).tobytes())
        with Image.open(review/'all_front_walks.gif') as gif:
            self.assertEqual(gif.n_frames,4);self.assertEqual(gif.info['loop'],0)
            for i in range(4):
                gif.seek(i);self.assertEqual(gif.info['duration'],140)
                for column,identity in enumerate(IDS):
                    frame=self.packs[identity][2][i]
                    x=24+column*352+(32-frame.width)//2*10
                    actual=gif.convert('RGB').crop((x,104,x+frame.width*10,104+350))
                    expected=Image.new('RGB',frame.size,'#e8edf2');expected.paste(frame,(0,0),frame)
                    self.assertEqual(actual.tobytes(),expected.crop((0,0,frame.width,35)).resize(actual.size,Image.Resampling.NEAREST).tobytes())


if __name__=='__main__':unittest.main()
