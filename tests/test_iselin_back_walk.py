from pathlib import Path
import unittest,json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'assets/characters/iselin/walk_back'


class BackWalkTests(unittest.TestCase):
    def test_native_cycle_and_timing(self):
        meta=json.loads((BASE/'animation.json').read_text())
        self.assertEqual(sum(f['duration_ms'] for f in meta['frames']),560)
        poses=[]
        for i in range(16):
            im=Image.open(BASE/f'frame_{i+1:02}.png').convert('RGBA')
            self.assertEqual(im.size,(42,72))
            self.assertEqual(set(im.getchannel('A').tobytes()),{0,255})
            self.assertLessEqual(im.getbbox()[3],70)
            poses.append(im.tobytes())
        self.assertEqual(len(set(poses)),16)

    def test_contacts_exchange_visible_hand_and_boot_depth(self):
        def sides(index):
            im=Image.open(BASE/f'frame_{index:02}.png').convert('RGBA')
            hands=[];boots=[]
            for lo,hi in ((0,21),(21,42)):
                skin=[y for y in range(25,49) for x in range(lo,hi)
                      if (lambda p:p[3] and p[0]>130 and p[1]>80 and p[0]>p[2]*1.25)(im.getpixel((x,y)))]
                hands.append(bool(skin))
                boots.append(max(y for y in range(55,72) for x in range(lo,hi) if im.getpixel((x,y))[3]))
            return hands,boots
        hands,boots=sides(1)
        self.assertEqual(hands,[False,True])
        self.assertGreater(boots[0],boots[1])
        hands,boots=sides(9)
        self.assertEqual(hands,[True,False])
        self.assertLess(boots[0],boots[1])

    def test_right_foot_revision_preserves_surrounding_art(self):
        source=ROOT/'assets/source/characters/iselin/walk_back/redrawn/right_foot_revision'
        for i in range(1,17):
            old=Image.open(source/f'original_{i:02}.png').convert('RGBA')
            new=Image.open(ROOT/'assets/source/characters/iselin/walk_back/redrawn/body_stability_v3'/f'before_{i:02}.png').convert('RGBA')
            for box in ((0,0,42,48),(0,48,22,72),(32,48,42,72)):
                self.assertEqual(old.crop(box).tobytes(),new.crop(box).tobytes())

    def test_right_boot_has_reduced_lift_and_no_abrupt_vertical_reset(self):
        bottoms=[]
        for i in range(1,17):
            im=Image.open(BASE/f'frame_{i:02}.png').convert('RGBA')
            bottoms.append(max(y for y in range(54,72) for x in range(22,32)
                               if im.getpixel((x,y))[3]))
        self.assertGreaterEqual(min(bottoms),61)
        self.assertEqual(max(bottoms),69)
        self.assertLessEqual(max(abs(a-b) for a,b in zip(bottoms,bottoms[1:]+bottoms[:1])),3)

    def test_body_bob_and_proportions_are_stable_in_exported_pixels(self):
        crowns=[];widths=[]
        for i in range(1,17):
            im=Image.open(BASE/f'frame_{i:02}.png').convert('RGBA')
            top=im.getbbox()[1];crowns.append(top)
            head=im.getchannel('A').crop((0,top,42,top+15)).getbbox()
            widths.append(head[2]-head[0])
            belt=[]
            for y in range(25,36):
                count=sum(1 for x in range(17,25) if (lambda p:p[3] and
                    p[0]>p[1]*1.13 and p[0]>p[2]*1.03 and 30<p[0]<160 and
                    p[1]>25)(im.getpixel((x,y))))
                if count>=3:belt.append(y)
            self.assertTrue(belt,'No readable belt landmark')
            self.assertTrue(25.5<=(min(belt)+max(belt))/2-top<=27.5)
        self.assertEqual(max(crowns)-min(crowns),2)
        self.assertEqual(crowns[:8],crowns[8:])
        self.assertLessEqual(max(abs(a-b) for a,b in zip(crowns,crowns[1:]+crowns[:1])),1)
        self.assertTrue(all(16<=width<=18 for width in widths))
        self.assertLessEqual(max(abs(a-b) for a,b in zip(widths,widths[1:]+widths[:1])),1)

    def test_stable_body_keeps_reviewed_boot_pixels(self):
        source=ROOT/'assets/source/characters/iselin/walk_back/redrawn/body_stability_v3'
        for i in range(1,17):
            before=Image.open(source/f'before_{i:02}.png').convert('RGBA')
            after=Image.open(BASE/f'frame_{i:02}.png').convert('RGBA')
            self.assertEqual(before.crop((0,54,42,72)).tobytes(),
                             after.crop((0,54,42,72)).tobytes())
