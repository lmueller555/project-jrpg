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


if __name__ == '__main__':
    unittest.main()
