"""Dormant child bedrest artwork contract; never activates the old base actor."""
from pathlib import Path
import json,unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
class VennChildBedrestNative(unittest.TestCase):
 def test_dormant_art_has_native_density_fixed_support_and_eye_only_blink(self):
  p=ROOT/'assets/characters/named_hd/venn_child/bedrest';meta=json.loads((p/'animation.json').read_text());self.assertEqual(meta['artwork_pixels_per_world_pixel'],2);self.assertEqual(meta['draw_anchor'],[24,24]);self.assertEqual(meta['story_position_world'],[60,112]);self.assertEqual(meta['story_sort_y'],167);self.assertEqual([f['duration_ms'] for f in meta['frames']],[4640,160]);a=Image.open(p/'rest_head.png').convert('RGBA');b=Image.open(p/'rest_blink.png').convert('RGBA');self.assertEqual(a.size,(48,72));self.assertEqual(a.getchannel('A').tobytes(),b.getchannel('A').tobytes());changed=[(x,y) for y in range(72) for x in range(48) if a.getpixel((x,y))!=b.getpixel((x,y))];self.assertTrue(changed);self.assertTrue(all(19<=x<=28 and 21<=y<=22 for x,y in changed))
