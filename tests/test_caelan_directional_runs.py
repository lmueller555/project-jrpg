"""Guard reviewed directional runs, source reconstruction and support/flight."""
import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/characters/caelan'
SOURCE=ROOT/'assets/source/characters/caelan'
REVIEW=ROOT/'docs/reviews/caelan_directional_runs'

class CaelanDirectionalRunTests(unittest.TestCase):
    def test_approved_frames_and_protected_art(self):
        data=json.loads((REVIEW/'approval.json').read_text())
        for name,digest in data['approved_frames_sha256'].items():
            self.assertEqual(hashlib.sha256((BASE/name).read_bytes()).hexdigest(),digest,name)
        for name,digest in data['protected_inputs_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)

    def test_native_frames_flight_palette_and_reconstruction(self):
        for direction in ['front','right','back']:
            pack=BASE/f'run_{direction}'
            meta=json.loads((pack/'animation.json').read_text())
            self.assertEqual(meta['status'],'approved')
            self.assertEqual(meta['frame_size'],[24,36])
            self.assertEqual(meta['foot_anchor'],[12,34])
            self.assertEqual([r['duration_ms'] for r in meta['frames']],[100]*4)
            self.assertEqual([r['airborne'] for r in meta['frames']],[False,True,False,True])
            palette=set(Image.open(BASE/f'idle_{direction}.png').convert('RGBA').get_flattened_data())
            strip=Image.open(pack/'spritesheet.png');seen=set()
            for i,r in enumerate(meta['frames']):
                im=Image.open(pack/r['file']).convert('RGBA');seen.add(im.tobytes())
                self.assertEqual(im.size,(24,36))
                self.assertEqual(set(im.getchannel('A').tobytes()),{0,255})
                self.assertTrue(all(not c[3] or c in palette for c in im.get_flattened_data()))
                if r['airborne']:self.assertLessEqual(im.getbbox()[3],33)
                else:self.assertEqual(im.getbbox()[3],35)
                rebuilt=Image.new('RGBA',im.size)
                for layer in r['layer_order']:
                    layer_strip=Image.open(SOURCE/f'run_{direction}'/(layer+'.png'))
                    rebuilt.alpha_composite(layer_strip.crop((24*i,0,24*(i+1),36)))
                self.assertEqual(rebuilt.tobytes(),im.tobytes())
                self.assertEqual(strip.crop((24*i,0,24*(i+1),36)).tobytes(),im.tobytes())
            self.assertEqual(len(seen),4)

    def test_review_clocks(self):
        for name,hold in [('all-directions.gif',100),('all-directions-slow.gif',350)]:
            with Image.open(REVIEW/name) as gif:
                self.assertEqual(gif.n_frames,4)
                for i in range(4):
                    gif.seek(i);self.assertEqual(gif.info['duration'],hold)

if __name__=='__main__':unittest.main()
