"""Guard the user-approved art, support/flight and reproducible layered exports."""
import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/characters/caelan/run_left'
SOURCE=ROOT/'assets/source/characters/caelan/run_left'
REVIEW=ROOT/'docs/reviews/caelan_left_run'

class CaelanLeftRunTests(unittest.TestCase):
    def test_matches_approved_frames_and_preserves_existing_art(self):
        approval=json.loads((REVIEW/'approval.json').read_text())
        for name,digest in approval['approved_frames_sha256'].items():
            self.assertEqual(hashlib.sha256((PACK/name).read_bytes()).hexdigest(),digest,name)
        for name,digest in approval['protected_inputs_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)

    def test_native_palette_support_flight_and_source_reconstruction(self):
        meta=json.loads((PACK/'animation.json').read_text())
        self.assertEqual(meta['status'],'approved')
        self.assertEqual(meta['foot_anchor'],[12,34])
        self.assertEqual([f['duration_ms'] for f in meta['frames']],[100]*4)
        palette=set(Image.open(PACK.parent/'idle_left.png').convert('RGBA').get_flattened_data())
        strip=Image.open(PACK/'spritesheet.png')
        for i,record in enumerate(meta['frames']):
            im=Image.open(PACK/record['file']).convert('RGBA')
            self.assertEqual(im.size,(24,36))
            self.assertEqual(set(im.getchannel('A').tobytes()),{0,255})
            self.assertTrue(all(not c[3] or c in palette for c in im.get_flattened_data()))
            self.assertEqual(im.getbbox()[3],32 if record['airborne'] else 35)
            rebuilt=Image.new('RGBA',im.size)
            for name in ['far_arm','far_leg','near_leg','torso','near_arm','head']:
                rebuilt.alpha_composite(Image.open(SOURCE/f'frame_{i+1:02}'/(name+'.png')))
            self.assertEqual(rebuilt.tobytes(),im.tobytes())
            self.assertEqual(strip.crop((i*24,0,(i+1)*24,36)).tobytes(),im.tobytes())

    def test_review_clocks(self):
        for filename,total in [('walk-vs-run.gif',2800),('walk-vs-run-slow.gif',1400)]:
            with Image.open(REVIEW/filename) as gif:
                elapsed=0
                for index in range(gif.n_frames):
                    gif.seek(index);elapsed+=gif.info['duration']
                self.assertEqual(elapsed,total)

if __name__=='__main__':unittest.main()
