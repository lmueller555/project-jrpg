"""Check the exported animation contract and shared movement, independently of assembly."""
import json
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'assets/characters/serene/walk_front'


class SereneFrontWalk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads((OUT/'animation.json').read_text())
        cls.idle=Image.open(OUT/'../idle_front.png').convert('RGBA')
        cls.frames=[Image.open(OUT/r['file']).convert('RGBA') for r in cls.meta['frames']]
        cls.template_path=(OUT/cls.meta['template']).resolve()
        cls.template=json.loads(cls.template_path.read_text())

    def test_native_contract_and_named_palette(self):
        palette=json.loads((OUT/'../palette.json').read_text())
        colors={tuple(bytes.fromhex(c[1:]))+(255,) for ramp in palette['materials'].values() for c in ramp}
        colors.update(tuple(bytes.fromhex(c[1:]))+(255,) for c in palette['eyes'].values())
        self.assertEqual(len(self.frames),4)
        self.assertEqual(self.meta['foot_anchor'],[12,34])
        for frame in self.frames:
            self.assertEqual(frame.size,(24,36))
            self.assertEqual(set(frame.getchannel('A').tobytes()),{0,255})
            self.assertEqual(frame.getbbox()[3],35)
            for y in range(36):
                for x in range(24):
                    color=frame.getpixel((x,y))
                    if color[3]: self.assertIn(color,colors)

    def test_shared_stride_and_phase_timing(self):
        self.assertEqual([r['duration_ms'] for r in self.meta['frames']],[140]*4)
        self.assertEqual([r['upper_body_offset'] for r in self.meta['frames']],[[0,0],[0,-1],[0,0],[0,-1]])
        for frame,record,phase in zip(self.frames,self.meta['frames'],self.template['frames'],strict=True):
            self.assertEqual(record['phase'],phase['phase'])
            reference=Image.open(self.template_path.parent/phase['reference']).convert('RGBA')
            self.assertEqual(frame.getchannel('A').crop((0,29,24,35)).tobytes(),
                             reference.getchannel('A').crop((0,29,24,35)).tobytes())
        self.assertEqual(len({f.tobytes() for f in self.frames}),4)

    def test_head_shoulders_and_neck_move_together(self):
        # Every approved head/mantle pixel survives the same translation. This
        # checks the visible neck as well as metadata offsets and both eyes.
        for frame,record in zip(self.frames,self.meta['frames'],strict=True):
            dy=record['upper_body_offset'][1]
            self.assertEqual(record['shoulder_mantle_offset'],record['upper_body_offset'])
            for y in range(19):
                for x in range(24):
                    pixel=self.idle.getpixel((x,y))
                    if pixel[3]:self.assertEqual(frame.getpixel((x,y+dy)),pixel,(x,y,dy))
            for x,y in [(9,10),(14,10)]:
                self.assertEqual(frame.getpixel((x,y+dy)),(26,14,22,255))
                self.assertEqual(frame.getpixel((x,y+dy+1)),(140,96,59,255))

    def test_apron_patch_stays_visible(self):
        patch={(70,91,100,255),(112,133,139,255),(156,168,164,255)}
        def count(image):
            return sum(image.getpixel((x,y)) in patch for x in range(24) for y in range(21,29))
        expected=count(self.idle)
        self.assertGreater(expected,0)
        for frame in self.frames:self.assertEqual(count(frame),expected)

    def test_layers_and_native_sheet_reconstruct_frames(self):
        sheet=Image.open(OUT/self.meta['image']).convert('RGBA')
        self.assertEqual(sheet.size,(96,36))
        for frame,record in zip(self.frames,self.meta['frames'],strict=True):
            combined=Image.new('RGBA',(24,36))
            for file in record['layers_from_repo_root']:
                combined.alpha_composite(Image.open(ROOT/file).convert('RGBA'))
            self.assertEqual(combined.tobytes(),frame.tobytes())
            x,y,w,h=record['rect']
            self.assertEqual(sheet.crop((x,y,x+w,y+h)).tobytes(),frame.tobytes())

    def test_loop_is_opaque_pixel_exact_and_correctly_timed(self):
        gif=Image.open(OUT/self.meta['review']['gif'])
        self.addCleanup(gif.close)
        self.assertEqual(gif.n_frames,4)
        self.assertEqual(gif.info['loop'],0)
        self.assertEqual(gif.size,(480,720))
        for i,frame in enumerate(self.frames):
            gif.seek(i)
            self.assertEqual(gif.info['duration'],140)
            expected=Image.new('RGB',(24,36),'#e8edf2')
            expected.paste(frame,(0,0),frame)
            self.assertEqual(gif.convert('RGB').tobytes(),expected.resize((480,720),Image.Resampling.NEAREST).tobytes())
            self.assertEqual(gif.convert('RGBA').getchannel('A').getextrema(),(255,255))


class SereneDirectionalWalks(unittest.TestCase):
    def test_directional_stride_neck_eyes_and_exports(self):
        palette=json.loads((OUT/'../palette.json').read_text())
        colors={tuple(bytes.fromhex(c[1:]))+(255,) for ramp in palette['materials'].values() for c in ramp}
        colors.update(tuple(bytes.fromhex(c[1:]))+(255,) for c in palette['eyes'].values())
        for direction in ('left','right','back'):
            with self.subTest(direction=direction):
                root=OUT.parent/f'walk_{direction}'
                meta=json.loads((root/'animation.json').read_text())
                idle=Image.open(root/f'../idle_{direction}.png').convert('RGBA')
                template_path=(root/meta['template']).resolve()
                template=json.loads(template_path.read_text())
                sheet=Image.open(root/'spritesheet.png').convert('RGBA')
                self.assertEqual(sheet.size,(96,36))
                self.assertEqual(meta['foot_anchor'],[12,34])
                self.assertEqual(meta['duration_ms'],560)
                images=[]
                for i,(record,phase) in enumerate(zip(meta['frames'],template['frames'],strict=True)):
                    image=Image.open(root/record['file']).convert('RGBA');images.append(image)
                    self.assertEqual(image.size,(24,36))
                    self.assertEqual(set(image.getchannel('A').tobytes()),{0,255})
                    self.assertEqual(image.getbbox()[3],35)
                    self.assertEqual(record['duration_ms'],140)
                    self.assertEqual(record['phase'],phase['phase'])
                    self.assertEqual(record['upper_body_offset'],phase['upper_body_offset'])
                    self.assertEqual(record['shoulder_mantle_offset'],phase['upper_body_offset'])
                    reference=Image.open(template_path.parent/phase['reference']).convert('RGBA')
                    self.assertEqual(image.getchannel('A').crop((0,29,24,35)).tobytes(),
                                     reference.getchannel('A').crop((0,29,24,35)).tobytes())
                    dy=phase['upper_body_offset'][1]
                    mantle_bottom=20 if direction=='back' else 19
                    for y in range(36):
                        for x in range(24):
                            pixel=image.getpixel((x,y))
                            if pixel[3]:self.assertIn(pixel,colors)
                            approved=idle.getpixel((x,y))
                            if y<mantle_bottom and approved[3]:
                                self.assertEqual(image.getpixel((x,y+dy)),approved)
                    self.assertEqual(len(record['eyes']),0 if direction=='back' else 1)
                    for x,y in record['eyes']:
                        self.assertEqual(image.getpixel((x,y)),(26,14,22,255))
                        self.assertEqual(image.getpixel((x,y+1)),(140,96,59,255))
                    if direction=='back':
                        self.assertNotIn((140,96,59,255),[image.getpixel((x,y)) for y in range(36) for x in range(24)])
                    combined=Image.new('RGBA',(24,36))
                    for path in record['layers_from_repo_root']:
                        combined.alpha_composite(Image.open(ROOT/path).convert('RGBA'))
                    self.assertEqual(combined.tobytes(),image.tobytes())
                    self.assertEqual(sheet.crop((i*24,0,i*24+24,36)).tobytes(),image.tobytes())
                self.assertEqual(len({im.tobytes() for im in images}),4)
                with Image.open(root/meta['review']['gif']) as gif:
                    self.assertEqual(gif.n_frames,4)
                    self.assertEqual(gif.info['loop'],0)
                    for i,image in enumerate(images):
                        gif.seek(i);self.assertEqual(gif.info['duration'],140)
                        expected=Image.new('RGB',(24,36),'#e8edf2');expected.paste(image,(0,0),image)
                        self.assertEqual(gif.convert('RGB').tobytes(),expected.resize((480,720),Image.Resampling.NEAREST).tobytes())
                        self.assertEqual(gif.convert('RGBA').getchannel('A').getextrema(),(255,255))

    def test_profile_patch_and_back_skirt(self):
        mantle_colors={(70,91,100,255),(112,133,139,255),(156,168,164,255)}
        linen={(188,174,145,255),(222,209,174,255),(251,238,208,255)}
        for direction in ('left','right','back'):
            root=OUT.parent/f'walk_{direction}'
            meta=json.loads((root/'animation.json').read_text())
            for record in meta['frames']:
                path=next(p for p in record['layers_from_repo_root'] if p.endswith('_skirt_and_apron.png'))
                skirt=Image.open(ROOT/path).convert('RGBA')
                pixels=[skirt.getpixel((x,y)) for y in range(22,29) for x in range(24)]
                if direction=='back':
                    self.assertFalse(set(pixels)&linen)
                else:
                    self.assertTrue(set(pixels)&mantle_colors,(direction,record['file']))

    def test_synchronized_four_direction_board(self):
        root=OUT.parent
        meta=json.loads((root/'walk_directions.json').read_text())
        self.assertEqual([d['direction'] for d in meta['directions']],['front','left','right','back'])
        self.assertEqual([d['status'] for d in meta['directions']],
                         [json.loads((root/f'walk_{d}/animation.json').read_text())['status']
                          for d in ('front','left','right','back')])
        sheet=Image.open(root/meta['image']).convert('RGBA')
        self.assertEqual(sheet.size,(96,144))
        with Image.open(root/meta['review']['gif']) as gif:
            self.assertEqual(gif.n_frames,4);self.assertEqual(gif.info['loop'],0)
            for phase in range(4):
                gif.seek(phase);self.assertEqual(gif.info['duration'],140)
                self.assertEqual(gif.convert('RGBA').getchannel('A').getextrema(),(255,255))
                for column,direction in enumerate(['front','left','right','back']):
                    native=Image.open(root/f'walk_{direction}/frame_0{phase+1}.png').convert('RGBA')
                    self.assertEqual(sheet.crop((phase*24,column*36,phase*24+24,column*36+36)).tobytes(),native.tobytes())
                    expected=Image.new('RGB',(24,36),'#e8edf2');expected.paste(native,(0,0),native)
                    self.assertEqual(gif.convert('RGB').crop((column*288,0,column*288+288,432)).tobytes(),
                                     expected.resize((288,432),Image.Resampling.NEAREST).tobytes())


if __name__ == '__main__':
    unittest.main()
