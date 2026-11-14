from pathlib import Path
import unittest
from PIL import Image,ImageOps

ROOT=Path(__file__).resolve().parents[1]


class LeftWalkTests(unittest.TestCase):
    def test_approved_foot_motion_is_preserved_without_mirroring_the_finished_costume(self):
        for i in range(16):
            left=Image.open(ROOT/f'assets/characters/iselin/walk_left/frame_{i+1:02}.png').convert('RGBA')
            right=Image.open(ROOT/f'assets/characters/iselin/walk_right/frame_{i+1:02}.png').convert('RGBA')
            guide=ImageOps.mirror(right)
            self.assertEqual(left.size,(42,72))
            self.assertEqual(left.crop((0,46,42,72)).tobytes(),guide.crop((0,46,42,72)).tobytes())
            self.assertNotEqual(left.crop((0,0,42,46)).tobytes(),guide.crop((0,0,42,46)).tobytes())

    def test_support_boot_progresses_in_both_steps(self):
        for start in (1,9):
            positions=[]
            for i in range(start,start+5):
                im=Image.open(ROOT/f'assets/characters/iselin/walk_left/frame_{i:02}.png').convert('RGBA')
                y=im.getbbox()[3]-1;groups=[]
                for x in range(42):
                    if not im.getpixel((x,y))[3]:continue
                    if not groups or x>groups[-1][-1]+1:groups.append([])
                    groups[-1].append(x)
                positions.append(sum(groups[0])/len(groups[0]))
            self.assertTrue(all(0<b-a<=8 for a,b in zip(positions,positions[1:])),positions)

    def test_frames_and_braided_tail_are_not_static(self):
        frames=[Image.open(ROOT/f'assets/characters/iselin/walk_left/frame_{i+1:02}.png').convert('RGBA') for i in range(16)]
        self.assertEqual(len({im.tobytes() for im in frames}),16)
        self.assertGreater(len({im.crop((18,23,28,41)).tobytes() for im in frames}),4)
        for im in frames:self.assertEqual(set(im.getchannel('A').tobytes()),{0,255})
