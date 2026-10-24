"""Verify Tomas's exported motion, height, landmarks and review playback."""
import json
import unittest
from pathlib import Path

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/characters/tomas/walk_front'


class TomasFrontWalk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((OUT/'animation.json').read_text())
        cls.idle=Image.open(OUT/'../idle_front.png').convert('RGBA')
        cls.frames=[Image.open(OUT/record['file']).convert('RGBA') for record in cls.meta['frames']]
        cls.template_path=(OUT/cls.meta['template']).resolve()
        cls.template=json.loads(cls.template_path.read_text())

    def test_native_palette_height_and_baseline(self):
        palette=json.loads((OUT/'../palette.json').read_text())
        colors={tuple(bytes.fromhex(c[1:]))+(255,) for ramp in palette['materials'].values() for c in ramp}
        colors.update(tuple(bytes.fromhex(c[1:]))+(255,) for c in palette['eyes'].values())
        self.assertEqual(self.meta['foot_anchor'],[12,34])
        self.assertEqual(self.meta['rest_visible_height_px'],32)
        for image,phase in zip(self.frames,self.template['frames'],strict=True):
            reference=Image.open(self.template_path.parent/phase['reference']).convert('RGBA')
            dy=phase['upper_body_offset'][1]
            self.assertEqual(image.size,(24,36))
            self.assertEqual(image.getbbox()[1::2],(3+dy,35))
            self.assertEqual(image.getbbox()[1]-reference.getbbox()[1],2)
            self.assertEqual(set(image.getchannel('A').tobytes()),{0,255})
            for y in range(36):
                for x in range(24):
                    pixel=image.getpixel((x,y))
                    if pixel[3]:self.assertIn(pixel,colors)

    def test_shared_stride_and_timing(self):
        self.assertEqual(len(self.frames),4)
        self.assertEqual(len({f.tobytes() for f in self.frames}),4)
        self.assertEqual([r['duration_ms'] for r in self.meta['frames']],[140]*4)
        self.assertEqual([r['upper_body_offset'] for r in self.meta['frames']],[[0,0],[0,-1],[0,0],[0,-1]])
        for image,record,phase in zip(self.frames,self.meta['frames'],self.template['frames'],strict=True):
            reference=Image.open(self.template_path.parent/phase['reference']).convert('RGBA')
            self.assertEqual(record['phase'],phase['phase'])
            self.assertEqual(image.getchannel('A').crop((0,26,24,35)).tobytes(),
                             reference.getchannel('A').crop((0,26,24,35)).tobytes())

    def test_face_neck_shoulders_and_cuffs(self):
        for image,record in zip(self.frames,self.meta['frames'],strict=True):
            dy=record['upper_body_offset'][1]
            self.assertEqual(record['shoulder_offset'],record['upper_body_offset'])
            for y in range(21):
                for x in range(24):
                    approved=self.idle.getpixel((x,y))
                    if approved[3] and (y<15 or 9<=x<15):
                        self.assertEqual(image.getpixel((x,y+dy)),approved)
            for x,y in [(10,11),(13,11)]:
                self.assertEqual(image.getpixel((x,y+dy)),(26,14,22,255))
                self.assertEqual(image.getpixel((x,y+dy+1)),(78,121,80,255))
            for side in ('left','right'):
                path=next(p for p in record['layers_from_repo_root'] if p.endswith(f'_{side}_arm.png'))
                arm=Image.open(ROOT/path).convert('RGBA')
                self.assertEqual(arm.getbbox()[1],16+dy)
                self.assertTrue(any(arm.getpixel((x,y))==(251,238,208,255)
                                    for y in range(36) for x in range(24)))

    def test_patch_moves_on_anatomical_left_leg_only(self):
        patch=(139,129,113,255)
        trouser={(53,42,41,255),(81,65,59,255),(116,96,80,255)}
        positions=[]
        for image,record in zip(self.frames,self.meta['frames'],strict=True):
            points={(x,y) for y in range(36) for x in range(24) if image.getpixel((x,y))==patch}
            self.assertEqual(points,{tuple(p) for p in record['patch_pixels']})
            self.assertTrue(points)
            self.assertTrue(all(x>=12 and 26<=y<31 for x,y in points))
            legs_path=next(p for p in record['layers_from_repo_root'] if p.endswith('_legs.png'))
            legs=Image.open(ROOT/legs_path).convert('RGBA')
            for point in points:self.assertIn(legs.getpixel(point),trouser)
            positions.append(frozenset(points))
        self.assertEqual(len(set(positions)),4)

    def test_sheet_and_layers_reconstruct_frames(self):
        sheet=Image.open(OUT/self.meta['image']).convert('RGBA')
        self.assertEqual(sheet.size,(96,36))
        for i,(image,record) in enumerate(zip(self.frames,self.meta['frames'],strict=True)):
            self.assertEqual(sheet.crop((i*24,0,i*24+24,36)).tobytes(),image.tobytes())
            combined=Image.new('RGBA',(24,36))
            for path in record['layers_from_repo_root']:
                combined.alpha_composite(Image.open(ROOT/path).convert('RGBA'))
            self.assertEqual(combined.tobytes(),image.tobytes())

    def test_gifs_are_opaque_exact_loops(self):
        for filename,scale in [('walk_front_preview.gif',20),('shared_motion_comparison.gif',16)]:
            with Image.open(OUT/filename) as gif:
                self.assertEqual(gif.n_frames,4)
                self.assertEqual(gif.info['loop'],0)
                for i,image in enumerate(self.frames):
                    gif.seek(i);self.assertEqual(gif.info['duration'],140)
                    self.assertEqual(gif.convert('RGBA').getchannel('A').getextrema(),(255,255))
                    expected=Image.new('RGB',(24,36),'#e8edf2');expected.paste(image,(0,0),image)
                    x=0 if scale==20 else 384
                    self.assertEqual(gif.convert('RGB').crop((x,0,x+24*scale,36*scale)).tobytes(),
                                     expected.resize((24*scale,36*scale),Image.Resampling.NEAREST).tobytes())
                    if scale==16:
                        reference=Image.open(self.template_path.parent/self.template['frames'][i]['reference']).convert('RGBA')
                        expected=Image.new('RGB',(24,36),'#e8edf2');expected.paste(reference,(0,0),reference)
                        self.assertEqual(gif.convert('RGB').crop((0,0,384,576)).tobytes(),
                                         expected.resize((384,576),Image.Resampling.NEAREST).tobytes())


class TomasDirectionalWalks(unittest.TestCase):
    def test_directional_contract_stride_neck_and_playback(self):
        palette=json.loads((OUT/'../palette.json').read_text())
        allowed={tuple(bytes.fromhex(c[1:]))+(255,) for ramp in palette['materials'].values() for c in ramp}
        allowed.update(tuple(bytes.fromhex(c[1:]))+(255,) for c in palette['eyes'].values())
        for direction in ('left','right','back'):
            with self.subTest(direction=direction):
                root=OUT.parent/f'walk_{direction}'
                meta=json.loads((root/'animation.json').read_text())
                template_path=(root/meta['template']).resolve()
                template=json.loads(template_path.read_text())
                idle=Image.open(root/f'../idle_{direction}.png').convert('RGBA')
                sheet=Image.open(root/'spritesheet.png').convert('RGBA')
                self.assertEqual(sheet.size,(96,36))
                self.assertEqual(meta['foot_anchor'],[12,34])
                self.assertEqual(meta['rest_visible_height_px'],32)
                self.assertEqual(meta['duration_ms'],560)
                frames=[]
                for i,(record,phase) in enumerate(zip(meta['frames'],template['frames'],strict=True)):
                    image=Image.open(root/record['file']).convert('RGBA');frames.append(image)
                    reference=Image.open(template_path.parent/phase['reference']).convert('RGBA')
                    dy=phase['upper_body_offset'][1]
                    self.assertEqual(image.size,(24,36))
                    self.assertEqual(image.getbbox()[1::2],(3+dy,35))
                    self.assertEqual(image.getbbox()[1]-reference.getbbox()[1],2)
                    self.assertEqual(set(image.getchannel('A').tobytes()),{0,255})
                    self.assertEqual(record['duration_ms'],140)
                    self.assertEqual(record['phase'],phase['phase'])
                    self.assertEqual(record['shoulder_offset'],phase['upper_body_offset'])
                    self.assertEqual(record['upper_body_offset'],phase['upper_body_offset'])
                    self.assertEqual(image.getchannel('A').crop((0,26,24,35)).tobytes(),
                                     reference.getchannel('A').crop((0,26,24,35)).tobytes())
                    for y in range(36):
                        for x in range(24):
                            pixel=image.getpixel((x,y))
                            if pixel[3]:self.assertIn(pixel,allowed)
                            approved=idle.getpixel((x,y))
                            collar={'left':(10,15),'right':(9,14),'back':(9,15)}[direction]
                            if approved[3] and (y<15 or (15<=y<17 and collar[0]<=x<collar[1])):
                                self.assertEqual(image.getpixel((x,y+dy)),approved)
                    self.assertEqual(len(record['eyes']),0 if direction=='back' else 1)
                    for x,y in record['eyes']:
                        self.assertEqual(image.getpixel((x,y)),(26,14,22,255))
                        self.assertEqual(image.getpixel((x,y+1)),(78,121,80,255))
                    if direction=='back':
                        self.assertNotIn((78,121,80,255),[image.getpixel((x,y)) for y in range(36) for x in range(24)])
                    combined=Image.new('RGBA',(24,36))
                    for path in record['layers_from_repo_root']:
                        combined.alpha_composite(Image.open(ROOT/path).convert('RGBA'))
                    self.assertEqual(combined.tobytes(),image.tobytes())
                    self.assertEqual(sheet.crop((i*24,0,i*24+24,36)).tobytes(),image.tobytes())
                self.assertEqual(len({f.tobytes() for f in frames}),4)
                with Image.open(root/meta['review']['gif']) as gif:
                    self.assertEqual(gif.n_frames,4);self.assertEqual(gif.info['loop'],0)
                    self.assertEqual(gif.size,(480,720))
                    for i,image in enumerate(frames):
                        gif.seek(i);self.assertEqual(gif.info['duration'],140)
                        expected=Image.new('RGB',(24,36),'#e8edf2');expected.paste(image,(0,0),image)
                        self.assertEqual(gif.convert('RGB').tobytes(),expected.resize((480,720),Image.Resampling.NEAREST).tobytes())
                        self.assertEqual(gif.convert('RGBA').getchannel('A').getextrema(),(255,255))

    def test_left_profile_patch_follows_near_leg_and_other_views_hide_it(self):
        patch=(139,129,113,255)
        trousers={(53,42,41,255),(81,65,59,255),(116,96,80,255)}
        for direction in ('left','right','back'):
            root=OUT.parent/f'walk_{direction}'
            meta=json.loads((root/'animation.json').read_text())
            positions=[]
            for record in meta['frames']:
                image=Image.open(root/record['file']).convert('RGBA')
                points={(x,y) for y in range(36) for x in range(24) if image.getpixel((x,y))==patch}
                self.assertEqual(points,{tuple(p) for p in record['patch_pixels']})
                if direction!='left':
                    self.assertFalse(points)
                    continue
                self.assertTrue(points)
                self.assertTrue(all(26<=y<31 for x,y in points))
                path=next(p for p in record['layers_from_repo_root'] if p.endswith('_legs.png'))
                legs=Image.open(ROOT/path).convert('RGBA')
                for point in points:self.assertIn(legs.getpixel(point),trousers)
                positions.append(frozenset(points))
            if direction=='left':self.assertEqual(len(set(positions)),4)

    def test_four_direction_sheet_and_synchronized_board(self):
        root=OUT.parent
        meta=json.loads((root/'walk_directions.json').read_text())
        directions=['front','left','right','back']
        self.assertEqual([r['direction'] for r in meta['directions']],directions)
        self.assertEqual([r['status'] for r in meta['directions']],
                         [json.loads((root/f'walk_{d}/animation.json').read_text())['status'] for d in directions])
        sheet=Image.open(root/meta['image']).convert('RGBA')
        self.assertEqual(sheet.size,(96,144))
        with Image.open(root/meta['review']['gif']) as gif:
            self.assertEqual(gif.n_frames,4);self.assertEqual(gif.info['loop'],0)
            for phase in range(4):
                gif.seek(phase);self.assertEqual(gif.info['duration'],140)
                self.assertEqual(gif.convert('RGBA').getchannel('A').getextrema(),(255,255))
                for column,direction in enumerate(directions):
                    image=Image.open(root/f'walk_{direction}/frame_0{phase+1}.png').convert('RGBA')
                    self.assertEqual(sheet.crop((phase*24,column*36,phase*24+24,column*36+36)).tobytes(),image.tobytes())
                    expected=Image.new('RGB',(24,36),'#e8edf2');expected.paste(image,(0,0),image)
                    self.assertEqual(gif.convert('RGB').crop((column*288,0,column*288+288,432)).tobytes(),
                                     expected.resize((288,432),Image.Resampling.NEAREST).tobytes())


if __name__=='__main__':
    unittest.main()
