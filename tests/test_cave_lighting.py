"""Cave light reaches scenery and actors, but cannot cross solid rock."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import pygame

from sanctuary_cave_world import CaveLighting


class CaveLightingTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.display.set_mode((480, 320))
        self.addCleanup(pygame.quit)

    def field(self, wall=False):
        blocked = pygame.Mask((480, 320))
        if wall:
            # A wall spanning the scene separates two otherwise open rooms.
            blocked.draw(pygame.Mask((24, 320), fill=True), (120, 0))
        world = NS(size=(480, 320), blocked=blocked, data={'cave':{'lights':[
            {'position':[64, 160], 'radius':200, 'phase':0,
             'color':[150, 220, 245]}]}})
        return CaveLighting(world)

    @staticmethod
    def render(field, clock, *, camera=(0, 0), reduced=False):
        canvas = pygame.Surface((480, 320));canvas.fill((180, 180, 180))
        # A colored actor-shaped patch gets exactly the same world illumination.
        pygame.draw.rect(canvas, (210, 150, 90), (84, 144, 12, 24))
        field.apply(canvas, camera, clock, reduced_motion=reduced)
        return canvas

    def test_six_second_breath_lights_floor_and_actor_and_repeats(self):
        field = self.field()
        trough = self.render(field, 0)
        peak = self.render(field, 3000)
        self.assertGreater(sum(peak.get_at((92, 180))[:3]),
                           sum(trough.get_at((92, 180))[:3]))
        self.assertGreater(sum(peak.get_at((90, 155))[:3]),
                           sum(trough.get_at((90, 155))[:3]))
        self.assertEqual(pygame.image.tobytes(trough, 'RGB'),
                         pygame.image.tobytes(self.render(field, 6000), 'RGB'))
        self.assertTrue(all(value > 0 for value in trough.get_at((420, 280))[:3]),
                        'Unlit paths retain a readable ambient level')

    def test_wall_face_catches_light_but_floor_in_adjacent_room_does_not(self):
        field = self.field(wall=True)
        peak = self.render(field, 3000)
        baseline = self.render(CaveLighting(NS(size=(480,320),
            blocked=field.world.blocked, data={'cave':{'lights':[]}})), 3000)
        self.assertGreater(sum(peak.get_at((126,160))[:3]),
                           sum(baseline.get_at((126,160))[:3]))
        for point in ((146,160),(160,160),(200,160)):
            self.assertEqual(peak.get_at(point), baseline.get_at(point))

    def test_reduced_motion_is_static_and_cache_reused_across_camera_and_clock(self):
        field = self.field()
        first = self.render(field, 0, reduced=True)
        cached = tuple(id(frame) for frame in field._cache[0]['frames'])
        later = self.render(field, 27653, reduced=True)
        self.assertEqual(pygame.image.tobytes(first, 'RGB'),
                         pygame.image.tobytes(later, 'RGB'))
        self.render(field, 3500, camera=(20, 0))
        self.assertEqual(tuple(id(frame) for frame in field._cache[0]['frames']), cached)
        self.assertEqual(field.snapshot()['cached_frames'], field.LEVELS)
        self.render(field, 0, camera=(800, 0))
        self.assertEqual(field.snapshot()['visible_sources'], 0)

    def test_prewarm_builds_all_fields_before_walking_and_daylight_stays_steady(self):
        field = self.field()
        field.sources[0]['steady'] = True
        field.prewarm()
        self.assertEqual(field.snapshot()['cached_sources'], len(field.sources))
        self.assertGreater(field.snapshot()['cache_bytes'], 0)
        with patch.object(field, '_build', side_effect=AssertionError('Cold field during walking')):
            first = self.render(field, 0)
            later = self.render(field, 3000, camera=(0, 0))
        self.assertEqual(pygame.image.tobytes(first, 'RGB'),
                         pygame.image.tobytes(later, 'RGB'))
        field.sources = field.sources*(field.MAX_CACHED+1)
        with self.assertRaisesRegex(ValueError, 'budget'):field.prewarm()

    def test_self_emission_lights_wall_tips_without_repainting_foreground_actors(self):
        field = self.field(wall=True)
        mask = pygame.Surface((12, 24), pygame.SRCALPHA)
        mask.fill((255,255,255,0))
        pygame.draw.rect(mask, (255,255,255,255), (4,2,4,20))
        def draw(pulse, emit=True):
            target = pygame.Surface((480,320));target.fill((120,160,190))
            # The actor overlaps the emissive silhouette in front of the wall.
            pygame.draw.rect(target, (230,40,20), (124,36,4,4))
            field.apply(target, (0,0), 0,
                        emissions=[(mask,(120,20),pulse)] if emit else [])
            return target
        dark = draw(0,False);trough = draw(0);peak = draw(1)
        point = (125,24)
        self.assertGreater(sum(trough.get_at(point)[:3]),sum(dark.get_at(point)[:3]))
        self.assertGreater(sum(peak.get_at(point)[:3]),sum(trough.get_at(point)[:3]))
        self.assertEqual(peak.get_at((121,24)),dark.get_at((121,24)),
                         'Transparent margins never become halos through rock')
        red, green, blue = peak.get_at((125,37))[:3]
        self.assertGreater(red, green*3)
        self.assertGreater(red, blue*3,
                           'Foreground actor pixels retain their own color and depth')


if __name__ == '__main__':unittest.main()
