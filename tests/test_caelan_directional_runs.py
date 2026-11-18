"""Current authored directional runs and retained historical approval evidence."""
import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/characters/caelan'
SOURCE=ROOT/'assets/source/characters/caelan/overworld_refresh'
REVIEW=ROOT/'docs/reviews/caelan_directional_runs'


class CaelanDirectionalRunTests(unittest.TestCase):
    def test_historical_approval_record_is_retained_without_reblessing_new_art(self):
        path=REVIEW/'approval.json'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         '8c7d02212c97e0d9a982d263673487540f4246c724f6418ce50def6a47f8a886')
        historical=json.loads(path.read_text())
        self.assertEqual(len(historical['approved_frames_sha256']),12)
        self.assertTrue(historical['protected_inputs_sha256'])

    def test_native_frames_are_registered_and_preserve_support_flight_and_cadence(self):
        registration=json.loads((SOURCE/'registration.json').read_text())
        authored={record['file'] for record in registration['source_cells']}
        for direction in ('front','right','back'):
            pack=BASE/f'run_{direction}'
            meta=json.loads((pack/'animation.json').read_text())
            self.assertEqual(meta['status'],'review')
            self.assertEqual(meta['frame_size'],[24,36])
            self.assertEqual(meta['foot_anchor'],[12,34])
            self.assertEqual([record['duration_ms'] for record in meta['frames']],[100]*4)
            self.assertEqual([record['airborne'] for record in meta['frames']],[False,True,False,True])
            strip=Image.open(pack/'spritesheet.png').convert('RGBA');seen=set()
            for index,record in enumerate(meta['frames']):
                relative=(pack/record['file']).relative_to(ROOT).as_posix()
                self.assertIn(relative,authored)
                image=Image.open(ROOT/relative).convert('RGBA');seen.add(image.tobytes())
                self.assertEqual(image.size,(24,36))
                self.assertEqual(set(image.getchannel('A').tobytes()),{0,255})
                self.assertEqual(image.getbbox()[3],32 if record['airborne'] else 35)
                self.assertEqual(strip.crop((index*24,0,(index+1)*24,36)).tobytes(),image.tobytes())
            self.assertEqual(len(seen),4)

    def test_historical_review_clocks_remain_intact(self):
        for name,hold in [('all-directions.gif',100),('all-directions-slow.gif',350)]:
            with Image.open(REVIEW/name) as gif:
                self.assertEqual(gif.n_frames,4)
                for index in range(4):
                    gif.seek(index);self.assertEqual(gif.info['duration'],hold)


if __name__=='__main__':unittest.main()
