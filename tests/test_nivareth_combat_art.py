"""The Ice elemental's authored drawings, registration, and real pose clock."""
from hashlib import sha256
import json
import os
from pathlib import Path
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

from PIL import Image
import pygame

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'assets/combat/nivareth'


class NivarethCombatArtTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ART/'animation.json').read_text())

    def test_all_176_frames_are_unique_opaque_pixel_art_with_complete_silhouettes(self):
        expected = {'emerge':8,'idle':16,'rime_needle':16,'glassfall':24,
                    'gather_frost':24,'charged_hold':16,'frostspire_thrust':24,
                    'settling':16,'hurt':8,'defeat':24}
        self.assertEqual({state:len(entry['frames']) for state,entry in
                          self.manifest['animations'].items()},expected)
        fingerprints, colors = set(), set()
        for state,entry in self.manifest['animations'].items():
            for record in entry['frames']:
                with self.subTest(state=state, file=record['file']):
                    image = Image.open(ART/record['file']).convert('RGBA')
                    self.assertEqual(image.size,(160,144))
                    self.assertTrue(set(image.getchannel('A').tobytes()) <= {0,255})
                    bounds = image.getbbox()
                    self.assertGreater(bounds[0],0);self.assertGreater(bounds[1],0)
                    self.assertLess(bounds[2],160);self.assertLess(bounds[3],144)
                    self.assertEqual(record['anchors']['floor'],[72,128])
                    self.assertTrue({'core','body','contact','cast_origin'} <= set(record['anchors']))
                    fingerprints.add(sha256(image.tobytes()).hexdigest())
                    colors.update(pixel[:3] for pixel in image.get_flattened_data() if pixel[3])
        self.assertEqual(len(fingerprints),176)
        self.assertLessEqual(len(colors),64)
        self.assertTrue(any(min(color)>225 for color in colors),'White core must survive palette export')

    def test_retained_sources_and_review_match_declared_provenance(self):
        recipe_path = ROOT/self.manifest['registration']
        self.assertEqual(sha256(recipe_path.read_bytes()).hexdigest(),
                         self.manifest['registration_sha256'])
        for name,digest in self.manifest['source_sha256'].items():
            self.assertEqual(sha256((ROOT/name).read_bytes()).hexdigest(),digest)
        review = ROOT/'docs/reviews/nivareth_combat'
        record = json.loads((review/'verification.json').read_text())
        self.assertEqual(record['authored_frames'],176)
        self.assertEqual(record['manifest_sha256'],sha256((ART/'animation.json').read_bytes()).hexdigest())
        for name,digest in record['files'].items():
            self.assertEqual(sha256((review/name).read_bytes()).hexdigest(),digest)

    def test_contacts_land_on_the_authored_model_boundaries(self):
        expected = {'rime_needle':450,'glassfall':800,'gather_frost':700,'frostspire_thrust':700}
        for state,contact in expected.items():
            entry = self.manifest['animations'][state]
            self.assertEqual(entry['contact_ms'],contact)
            self.assertEqual(sum(frame['duration_ms'] for frame in
                                 entry['frames'][:entry['contact_frame']]),contact)

    def test_production_sprite_loader_uses_frame_local_anchors_and_correct_contact_pose(self):
        from battle_scene import CombatSprites
        pygame.display.init();pygame.display.set_mode((1,1))
        self.addCleanup(pygame.display.quit)
        sprites = CombatSprites()
        for state in ('idle','rime_needle','glassfall','gather_frost','charged_hold',
                      'frostspire_thrust','settling','hurt','defeat','emerge'):
            for elapsed in (0,449,700,800,5000):
                image,anchor = sprites.frame('nivareth',state,elapsed)
                points = sprites.anchors('nivareth',state,elapsed)
                self.assertEqual(image.get_size(),(160,144))
                self.assertEqual(anchor,(72,128))
                self.assertEqual(points['floor'],(72,128))
                self.assertTrue({'core','contact','cast_origin'} <= set(points))


if __name__ == '__main__':unittest.main()
