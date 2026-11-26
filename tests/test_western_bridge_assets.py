"""Bridge art preserves the clear road, destroyed gap and depth registration."""
import json
from pathlib import Path
import unittest

from PIL import Image

from tools.build_western_bridge_assets import SOURCE, TARGET, products


ROOT = Path(__file__).resolve().parents[1]


class WesternBridgeAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((TARGET/'art.json').read_text())

    def image(self, phase, layer):
        record = self.manifest['phases'][phase][layer]
        return Image.open(ROOT/record['image']).convert('RGBA')

    def test_export_reproduces_every_registered_file_without_mutating_sources(self):
        before = {path: path.read_bytes() for path in SOURCE.iterdir() if path.is_file()}
        for path, raw in products().items():
            self.assertEqual(path.read_bytes(), raw, path)
        self.assertEqual(before, {path: path.read_bytes() for path in before})

    def test_all_phase_layers_share_anchor_canvas_and_depth_contract(self):
        self.assertEqual(self.manifest['canvas'], [288, 144])
        self.assertEqual(self.manifest['anchor'], [144, 94])
        self.assertEqual((self.manifest['deck_top_px'], self.manifest['deck_bottom_px']), (34, 106))
        for phase in ('intact', 'destroyed', 'restored'):
            for layer in ('deck', 'far', 'near'):
                with self.subTest(phase=phase, layer=layer):
                    record = self.manifest['phases'][phase][layer]
                    self.assertEqual(record['foot_anchor'], [144, 94])
                    self.assertEqual(self.image(phase, layer).size, (288, 144))
                    self.assertIsNotNone(self.image(phase, layer).getbbox())
                    if layer != 'deck':
                        self.assertEqual(record['sort_offset'], -60 if layer == 'far' else 14)

    def test_intact_and_restored_have_a_full_72_pixel_clear_paved_road(self):
        for phase in ('intact', 'restored'):
            with self.subTest(phase=phase):
                deck = self.image(phase, 'deck')
                self.assertEqual(deck.getchannel('A').crop((0, 34, 288, 106)).getextrema(), (255, 255))
                self.assertEqual(deck.getbbox(), (0, 34, 288, 106))
                for layer in ('far', 'near'):
                    self.assertIsNone(self.image(phase, layer).crop((0, 34, 288, 106)).getbbox())

    def test_destroyed_gap_is_transparent_through_deck_and_both_rails(self):
        for layer in ('deck', 'far', 'near'):
            image = self.image('destroyed', layer)
            self.assertIsNone(image.crop((107, 0, 181, 144)).getbbox(), layer)
            self.assertIsNotNone(image.crop((0, 0, 107, 144)).getbbox(), layer)
            self.assertIsNotNone(image.crop((181, 0, 288, 144)).getbbox(), layer)

    def test_exports_use_only_native_reference_colours_and_binary_alpha(self):
        reference = Image.open(SOURCE/'destroyed_reference.png').convert('RGBA')
        palette = {pixel[:3] for _, pixel in reference.getcolors(288*144) if pixel[3] == 255}
        for phase in self.manifest['phases']:
            for layer in ('deck', 'far', 'near'):
                with self.subTest(phase=phase, layer=layer):
                    image = self.image(phase, layer)
                    self.assertLessEqual({alpha for _, alpha in image.getchannel('A').getcolors(288*144)},
                                         {0, 255})
                    self.assertLessEqual({pixel[:3] for _, pixel in image.getcolors(288*144)
                                          if pixel[3] == 255}, palette)


if __name__ == '__main__':
    unittest.main()
