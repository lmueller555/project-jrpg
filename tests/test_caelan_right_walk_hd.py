"""Review-pack export contracts and the motion defects found during Iselin work."""
from pathlib import Path
import hashlib
import json
import unittest
from PIL import Image,ImageSequence

ROOT=Path(__file__).resolve().parents[1]
BANK=ROOT/'assets/characters/caelan/review_hd/walk_right'
SOURCE=ROOT/'assets/source/characters/caelan/walk_right_hd_review'


class CaelanRightWalkReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((BANK/'animation.json').read_text())
        cls.frames=[Image.open(BANK/r['file']).convert('RGBA') for r in cls.data['frames']]

    def test_sixteen_complete_unique_frames_preserve_density_alpha_and_padding(self):
        self.assertEqual(len(self.frames),16)
        self.assertEqual(len({im.tobytes() for im in self.frames}),16)
        for frame in self.frames:
            self.assertEqual(frame.size,(48,72))
            self.assertLessEqual(set(frame.getchannel('A').get_flattened_data()),{0,255})
            left,top,right,bottom=frame.getbbox()
            self.assertTrue(left>0 and top>0 and right<48 and bottom<72)
        self.assertEqual(self.data['logical_size'],[24,36])
        self.assertFalse(self.data['runtime_integration'])

    def test_body_scale_is_shared_and_actual_head_and_support_heights_are_stable(self):
        self.assertEqual(len({r['uniform_scale'] for r in self.data['frames']}),1)
        crowns=[];heights=[]
        for frame,record in zip(self.frames,self.data['frames']):
            crown=frame.crop((0,0,48,24)).getbbox()[1]
            self.assertEqual(crown,record['head_crown_y']);crowns.append(crown)
            lo,hi=record['support_window']
            ground=max(y for y in range(65,72) for x in range(lo,hi) if frame.getpixel((x,y))[3])
            self.assertEqual(ground,record['support_ground_interval'][1]);heights.append(ground)
        # Asset-specific export regression bounds, not an anatomical gait rule.
        self.assertLessEqual(max(crowns)-min(crowns),1)
        self.assertLessEqual(max(heights)-min(heights),2)
        for i in range(16):self.assertLessEqual(abs(crowns[i]-crowns[(i+1)%16]),1)

    def test_support_progression_advances_backwards_in_both_half_cycles(self):
        for start in (0,8):
            contacts=self.data['frames'][start:start+8]
            xs=[r['support_ground_interval'][2] for r in contacts]
            self.assertGreater(xs[0]-xs[-1],12)
            # Rolling heel-to-toe contact may advance the visible edge slightly;
            # it must not reset far ahead during the same support half-cycle.
            self.assertLessEqual(max(b-a for a,b in zip(xs,xs[1:])),3)

    def test_cycle_and_saved_normal_slow_gif_timings_are_correct(self):
        self.assertEqual([r['duration_ms'] for r in self.data['frames']],[35]*16)
        self.assertEqual(self.data['cycle_ms'],560)
        with Image.open(ROOT/'docs/reviews/caelan_right_walk_hd/preview.gif') as gif:
            times=[frame.info['duration'] for frame in ImageSequence.Iterator(gif)]
        self.assertEqual(times,[30,40]*16)
        self.assertEqual(sum(times),1120)

    def test_sheet_reconstructs_every_exact_frame_and_sources_are_retained(self):
        with Image.open(BANK/'spritesheet.png') as sheet:
            for index,frame in enumerate(self.frames):
                self.assertEqual(sheet.crop((index*48,0,(index+1)*48,72)).tobytes(),frame.tobytes())
        for file,digest in self.data['source_hashes'].items():
            self.assertEqual(hashlib.sha256((SOURCE/file).read_bytes()).hexdigest(),digest)

    def test_approved_idle_is_preserved_as_the_appearance_reference(self):
        idle=ROOT/'assets/characters/caelan/review_hd/idles/idle_right.png'
        self.assertEqual(hashlib.sha256(idle.read_bytes()).hexdigest(),self.data['approved_idle_sha256'])
        status=json.loads((idle.parent/'idles.json').read_text())
        self.assertEqual(status['status'],'approved')

    def test_local_arm_correction_preserves_the_other_fifteen_exact_drawings(self):
        protected=json.loads((SOURCE/'protected_frames.json').read_text())
        self.assertEqual(len(protected),15)
        for file,digest in protected.items():
            self.assertEqual(hashlib.sha256((BANK/file).read_bytes()).hexdigest(),digest)
