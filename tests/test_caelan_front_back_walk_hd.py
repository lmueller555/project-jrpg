"""Contracts and measured regressions for the two unmerged review cycles."""
from pathlib import Path
import hashlib
import json
import unittest
from PIL import Image, ImageSequence

ROOT=Path(__file__).resolve().parents[1]

class CaelanFrontBackWalkReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packs={}
        for direction in ('front','back'):
            bank=ROOT/f'assets/characters/caelan/review_hd/walk_{direction}'
            data=json.loads((bank/'animation.json').read_text())
            frames=[Image.open(bank/r['file']).convert('RGBA') for r in data['frames']]
            cls.packs[direction]=(bank,data,frames)

    def test_frame_contract_alpha_padding_and_unique_drawings(self):
        for bank,data,frames in self.packs.values():
            self.assertEqual(len(frames),16);self.assertEqual(len({f.tobytes() for f in frames}),16)
            self.assertEqual(data['logical_size'],[24,36]);self.assertEqual(data['draw_anchor'],[24,60])
            self.assertEqual(data['foot_anchor'],[24,68]);self.assertEqual(data['artwork_pixels_per_world_pixel'],2)
            for frame in frames:
                self.assertEqual(frame.size,(48,72))
                self.assertLessEqual(set(frame.getchannel('A').get_flattened_data()),{0,255})
                left,top,right,bottom=frame.getbbox()
                self.assertTrue(left>0 and top>0 and right<48 and bottom<72)

    def test_crown_stability_including_the_loop_seam(self):
        for bank,data,frames in self.packs.values():
            ys=[frame.crop((0,0,48,24)).getbbox()[1] for frame in frames]
            self.assertEqual(ys,[r['head_crown_y'] for r in data['frames']])
            self.assertLessEqual(max(ys)-min(ys),1)
            for a,b in zip(ys,ys[1:]+ys[:1]):self.assertLessEqual(abs(b-a),1)

    def test_boot_observations_do_not_snap_and_both_legs_progress(self):
        for bank,data,frames in self.packs.values():
            for side in (0,1):
                ys=[]
                for frame,record in zip(frames,data['frames']):
                    lo,hi,y=record['boot_observation_windows'][side]
                    actual=max(yy for x in range(lo,hi) for yy in range(52,72) if frame.getpixel((x,yy))[3])
                    self.assertEqual(actual,y);ys.append(y)
                self.assertGreaterEqual(max(ys)-min(ys),6)
                for a,b in zip(ys,ys[1:]+ys[:1]):self.assertLessEqual(abs(b-a),3)
            # Observed sole windows regress the specific large-drop defect;
            # they are not joint simulation or proof of world-ground locking.

    def test_upper_pixel_preservation_has_original_whole_drawing_provenance(self):
        for direction,(bank,data,frames) in self.packs.items():
            source=ROOT/f'assets/source/characters/caelan/walk_{direction}_hd_review'
            for frame,record in zip(frames,data['frames']):
                snapshot=Image.open(source/'upper_snapshot'/record['file']).convert('RGBA')
                region=snapshot.crop((0,0,48,48)).tobytes()
                self.assertEqual(frame.crop((0,0,48,48)).tobytes(),region)
                self.assertEqual(hashlib.sha256(region).hexdigest(),record['upper_sha256'])
                self.assertIn(record['upper_registration']['source'],data['source_hashes'])
            self.assertTrue(self.packs['front'][1]['frames'][13]['complete_pose_override'])

    def test_exact_sheet_reconstruction_and_source_hashes(self):
        for direction,(bank,data,frames) in self.packs.items():
            source=ROOT/f'assets/source/characters/caelan/walk_{direction}_hd_review'
            with Image.open(bank/'spritesheet.png') as sheet:
                for i,frame in enumerate(frames):
                    self.assertEqual(sheet.crop((i*48,0,(i+1)*48,72)).tobytes(),frame.tobytes())
            for file,digest in data['source_hashes'].items():
                self.assertEqual(hashlib.sha256((source/file).read_bytes()).hexdigest(),digest)
            palette=ROOT/'assets/source/characters/caelan/walk_right_hd_review/palette.json'
            self.assertEqual(hashlib.sha256(palette.read_bytes()).hexdigest(),data['palette_sha256'])

    def test_saved_gif_and_native_frame_cadence(self):
        for direction,(bank,data,frames) in self.packs.items():
            self.assertEqual([r['duration_ms'] for r in data['frames']],[35]*16)
            self.assertEqual(data['cycle_ms'],560)
            for file,times in [('preview.gif',[30,40]*16),('hall_preview.gif',[30,40]*8)]:
                with Image.open(ROOT/f'docs/reviews/caelan_{direction}_walk_hd'/file) as gif:
                    self.assertEqual([f.info['duration'] for f in ImageSequence.Iterator(gif)],times)

    def test_approval_and_runtime_states_are_explicit(self):
        for bank,data,frames in self.packs.values():
            self.assertEqual(data['status'],'review');self.assertEqual(data['artwork_status'],'review')
            self.assertEqual(data['design_status'],'approved');self.assertFalse(data['runtime_integration'])

    def test_approved_idles_and_side_walks_are_unchanged(self):
        source=ROOT/'assets/source/characters/caelan/walk_front_hd_review'
        for file,digest in json.loads((source/'protected_references.json').read_text()).items():
            self.assertEqual(hashlib.sha256((ROOT/file).read_bytes()).hexdigest(),digest)
        for direction,(bank,data,frames) in self.packs.items():
            idle=ROOT/f'assets/characters/caelan/review_hd/idles/idle_{direction}.png'
            self.assertEqual(hashlib.sha256(idle.read_bytes()).hexdigest(),data['approved_idle_sha256'])
