from pathlib import Path
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


class LegRevisionTests(unittest.TestCase):
    def test_approved_upper_body_is_pixel_identical(self):
        for i in range(16):
            current=Image.open(ROOT/f'assets/characters/iselin/walk_right/frame_{i+1:02}.png').convert('RGBA')
            approved=Image.open(ROOT/f'assets/source/characters/iselin/walk_right/redrawn/leg_revision/approved_{i+1:02}.png').convert('RGBA')
            self.assertEqual(current.crop((0,0,42,46)).tobytes(),approved.crop((0,0,42,46)).tobytes())

    def test_contact_to_support_progresses_instead_of_lingering_then_snapping(self):
        for start in (1,9):
            positions=[]
            for i in range(start,start+5):
                im=Image.open(ROOT/f'assets/characters/iselin/walk_right/frame_{i:02}.png').convert('RGBA')
                y=im.getbbox()[3]-1
                groups=[]
                for x in range(42):
                    if not im.getpixel((x,y))[3]:continue
                    if not groups or x>groups[-1][-1]+1:groups.append([])
                    groups[-1].append(x)
                positions.append(sum(groups[-1])/len(groups[-1]))
            deltas=[a-b for a,b in zip(positions,positions[1:])]
            self.assertTrue(all(0<d<=8 for d in deltas),positions)
            self.assertGreater(positions[0]-positions[-1],14)
