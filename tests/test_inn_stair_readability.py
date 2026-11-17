"""Structural stair direction cues keep original landing/support registration."""
import unittest
from PIL import ImageChops, ImageStat
from tools.eldenmere_interior_architecture import _stair_art, recipe

class StairReadabilityTests(unittest.TestCase):
    def test_same_canvas_hard_alpha_and_supports(self):
        up=_stair_art(recipe()['palette'])
        down=_stair_art(recipe()['palette'],upstairs=True)
        self.assertEqual(up.size,(120,168));self.assertEqual(down.size,up.size)
        for im in (up,down):
            self.assertLessEqual(set(im.getchannel('A').getdata()),{0,255})
        for box in ((0,0,10,168),(110,0,120,168),(10,158,110,168)):
            self.assertIsNone(ImageChops.difference(up.crop(box),down.crop(box)).getbbox())
    def test_descending_well_is_visibly_recessed_without_route_chevrons(self):
        palette=recipe()['palette']
        up=_stair_art(palette);down=_stair_art(palette,upstairs=True)
        def light(im,box):return ImageStat.Stat(im.crop(box).convert('L')).mean[0]
        self.assertGreater(light(up,(24,14,96,40)),light(down,(24,14,96,40))+35)
        self.assertGreater(light(down,(24,124,96,150)),light(down,(24,14,96,40))+30)
        self.assertNotEqual(up.tobytes(),down.tobytes())
        # Former painted navigation chevrons used the bright canvas color.
        canvas=tuple(bytes.fromhex(palette['canvas_light'].lstrip('#')))+(255,)
        for im in (up,down):self.assertNotIn(canvas,set(im.getdata()))
