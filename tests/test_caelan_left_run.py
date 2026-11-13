"""Current authored left-run contract and preserved historical review evidence."""
import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/characters/caelan/run_left'
SOURCE=ROOT/'assets/source/characters/caelan/overworld_refresh'
REVIEW=ROOT/'docs/reviews/caelan_left_run'


class CaelanLeftRunTests(unittest.TestCase):
    def test_historical_approval_record_is_retained_without_reblessing_new_art(self):
        # These hashes document the previous approved drawings, not live pixels.
        path=REVIEW/'approval.json'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         'bed40da8fe575569ed69f3ec69f6e8e01d42f38b3899398b8ac387c4563f0e1b')
        historical=json.loads(path.read_text())
        self.assertEqual(len(historical['approved_frames_sha256']),4)
        self.assertTrue(historical['protected_inputs_sha256'])

    def test_left_run_uses_registered_authored_drawings_with_support_and_flight(self):
        meta=json.loads((PACK/'animation.json').read_text())
        self.assertEqual(meta['status'],'review')
        self.assertEqual(meta['foot_anchor'],[12,34])
        self.assertEqual([frame['duration_ms'] for frame in meta['frames']],[100]*4)
        registration=json.loads((SOURCE/'registration.json').read_text())
        authored={record['file'] for record in registration['source_cells']}
        strip=Image.open(PACK/'spritesheet.png').convert('RGBA')
        seen=set()
        for index,record in enumerate(meta['frames']):
            relative=(PACK/record['file']).relative_to(ROOT).as_posix()
            self.assertIn(relative,authored)
            image=Image.open(ROOT/relative).convert('RGBA');seen.add(image.tobytes())
            self.assertEqual(image.size,(24,36))
            self.assertEqual(set(image.getchannel('A').tobytes()),{0,255})
            self.assertEqual(image.getbbox()[3],32 if record['airborne'] else 35)
            self.assertEqual(strip.crop((index*24,0,(index+1)*24,36)).tobytes(),image.tobytes())
        self.assertEqual(len(seen),4)

    def test_historical_review_clocks_remain_intact(self):
        for filename,total in [('walk-vs-run.gif',2800),('walk-vs-run-slow.gif',1400)]:
            with Image.open(REVIEW/filename) as gif:
                elapsed=0
                for index in range(gif.n_frames):
                    gif.seek(index);elapsed+=gif.info['duration']
                self.assertEqual(elapsed,total)


if __name__=='__main__':unittest.main()
