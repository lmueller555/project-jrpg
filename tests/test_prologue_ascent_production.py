"""Checks against the shipped picture banks, separate from visual acceptance."""
import os
import json
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
from PIL import Image

from cinematic_bridge_ascent import CinematicBridgeAscent
from cinematic_face_reveal import CinematicFaceReveal
from fire_veinhold_opening import FireVeinholdOpening


def require_cutout(path):
    """Reject full-cell mattes; this deliberately does not judge anatomy."""
    with Image.open(path) as image:
        mask = image.convert('RGBA').getchannel('A').point(lambda value:255 if value>16 else 0)
        box = mask.getbbox()
        if box is None:
            raise ValueError('Empty figure export: '+str(path))
        occupied = mask.crop(box).histogram()[255]
        coverage = occupied/((box[2]-box[0])*(box[3]-box[1]))
        # Actual human cutouts occupy well under this loose bound. The rejected
        # generated checkerboard occupies 100%, even after padded registration.
        if coverage >= .97:
            raise ValueError('Opaque cell background in figure export: '+str(path))


class AscentProductionTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960, 640))
        self.owners = []

    def tearDown(self):
        for owner in reversed(self.owners):
            if isinstance(owner, FireVeinholdOpening):
                owner.reset()
            else:
                owner.close()
        pygame.quit()

    def owner(self, factory, *args):
        value = factory(*args)
        self.owners.append(value)
        return value

    def test_actual_entry_pixels_match_the_previous_inclusive_endpoint(self):
        previous = self.owner(CinematicFaceReveal)
        current = self.owner(CinematicBridgeAscent)
        for reduced in (False, True):
            with self.subTest(reduced_motion=reduced):
                before = pygame.Surface((960, 640))
                after = pygame.Surface((960, 640))
                previous.preload(5., reduced_motion=reduced, blocking=True)
                previous.draw(before, previous.samples(5., reduced))
                current.prepare(0., reduced_motion=reduced)
                current.draw(after, current.samples(0., reduced))
                self.assertEqual(pygame.image.tobytes(before, 'RGB'),
                                 pygame.image.tobytes(after, 'RGB'))

    def test_actual_standalone_and_full_reel_share_pixels_and_clock(self):
        for reduced in (False, True):
            game = SimpleNamespace(
                audio=SimpleNamespace(reduced_motion=reduced, effects_volume=0),
                _music_focused=True, to_canvas=lambda point:point)
            complete = self.owner(FireVeinholdOpening, game)
            single = self.owner(FireVeinholdOpening, game, 'bridge_ascent')
            for seconds in (0., .4, .8, 1.2, 2.2, 4.5, 6.25, 479/60):
                with self.subTest(reduced_motion=reduced, seconds=seconds):
                    self.assertEqual(complete.state_at(47.+seconds), single.state_at(seconds))
                    self.assertEqual(
                        pygame.image.tobytes(complete.render_frame(47.+seconds), 'RGB'),
                        pygame.image.tobytes(single.render_frame(seconds), 'RGB'))
            complete.reset()
            single.reset()

    def test_retained_opaque_generation_is_rejected_by_the_cutout_gate(self):
        path = Path(__file__).parent/'fixtures/prologue_ascent_camera/rejected_opaque_cell.png'
        metadata = json.loads(path.with_suffix('.json').read_text())
        self.assertEqual(sha256(path.read_bytes()).hexdigest(),metadata['fixture_sha256'])
        with self.assertRaisesRegex(ValueError,'Opaque cell background'):
            require_cutout(path)

    def test_shipped_party_exports_have_transparent_figure_silhouettes(self):
        root = Path(__file__).resolve().parents[1]
        for actor in ('lucan','iselin','crown_soldier'):
            profile = root/f'assets/story/fire_veinhold_opening/shot08/characters/{actor}/actorperformance.json'
            data = json.loads(profile.read_text())
            files = {row.get('file',row.get('source')) for row in
                     data['transition_frames']+data['overhead_cycle']['frames']}
            for filename in sorted(files):
                with self.subTest(actor=actor,filename=filename):
                    path = (profile.parent/filename).resolve()
                    self.assertTrue(path.is_relative_to(root))
                    require_cutout(path)


if __name__ == '__main__':
    unittest.main()
