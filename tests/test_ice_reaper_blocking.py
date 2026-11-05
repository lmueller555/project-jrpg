"""The first attack threatens Rhea and is stopped by a physically placed shield."""
import math
import os
from pathlib import Path
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from ice_reaper_action import IceReaperActionStage as Stage

ROOT = Path(__file__).resolve().parents[1]


class IceReaperBlockingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((480, 320))
        cls.stage = Stage(ROOT/'assets/story/ice_reaper_rescue', strict=True)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_unobstructed_attack_passes_through_rheas_body_inside_the_prison(self):
        geometry = Stage.attack_geometry()
        release, target, shield = (geometry[key] for key in ('release', 'target', 'shield'))
        rhea = Stage.actor_positions(8.8)['rhea']
        self.assertLess((target-pygame.Vector3(rhea.x, .4, rhea.z)).length(), .01)
        incoming = shield-release
        continued = release+incoming*((target.z-release.z)/incoming.z)
        self.assertLess((continued-target).length(), .01)
        self.assertLess((shield-release).cross(target-release).length(), .001)
        self.assertGreater((target-shield).dot(incoming), 0)

    def test_guard_finishes_on_enemy_side_with_shield_covering_the_line(self):
        geometry = Stage.attack_geometry()
        rhea = Stage.actor_positions(7.5)['rhea']
        lucan = Stage.actor_positions(7.5)['lucan']
        self.assertLess(lucan.z, rhea.z)
        self.assertLess(abs(lucan.x-rhea.x), .9)
        self.assertGreater(pygame.Vector3(Stage.camera(8.5).position).distance_to(lucan),
                           pygame.Vector3(Stage.camera(8.5).position).distance_to(rhea))
        forward = Stage.camera(8.5).basis()[2]
        self.assertGreater((lucan-rhea).dot(forward), .5)
        self.assertEqual(lucan, geometry['lucan'])
        self.assertLess(abs(geometry['shield'].x-lucan.x), .65)
        self.assertLess(abs(geometry['shield'].z-lucan.z), .7)
        self.assertGreater(geometry['shield'].y, 1.2)
        self.assertLess(geometry['shield'].y, 1.9)
        # The raised shield remains within an arm plus shield-center reach
        # from a kneeling shoulder, rather than floating above the actor.
        shoulder = lucan+pygame.Vector3(0, 1., 0)
        self.assertLess(geometry['shield'].distance_to(shoulder), 1.05)

    def test_rescue_view_has_a_readable_diagonal_toward_rhea(self):
        camera = Stage.camera(8.5)
        start, end = (camera.project(point) for point in
                      (Stage.first_shard_release(), Stage.first_shard_target()))
        dx, dy = end[0]-start[0], end[1]-start[1]
        self.assertLess(dx, 0)
        self.assertGreater(dy, 0)
        angle = math.degrees(math.atan2(dy, -dx))
        self.assertGreater(angle, 25)
        self.assertLess(angle, 50)

    def test_tip_arrives_at_the_shield_without_moving_the_target(self):
        contact = Stage.first_shard_shield_contact()
        distances = [Stage.first_shard_tip(time).distance_to(contact)
                     for time in (6.86, 7.2, 7.5, 8, 8.5, 8.9, 9.)]
        self.assertEqual(distances, sorted(distances, reverse=True))
        self.assertLess(distances[-1], .001)
        self.assertGreater(contact.distance_to(Stage.first_shard_target()), .5)

    def test_contact_falls_inside_the_authored_forward_shield_face(self):
        # These polygons trace the actual wooden/gold board in the final brace
        # and first impact drawings.  Merely hitting near Lucan's body is not
        # enough: the collision must be inside the visible shield surface.
        cases = (
            (8.99, [(79,51),(84,51),(88,54),(89,61),(87,70),(83,76),
                    (78,82),(74,79),(76,70),(76,60),(76,55)]),
            (9.0, [(79,51),(84,51),(88,54),(89,61),(87,70),(83,76),
                   (78,82),(74,79),(76,70),(76,60),(76,55)]),
        )
        for time, polygon in cases:
            with self.subTest(time=time):
                camera = Stage.camera(time)
                position = Stage.actor_positions(time)['lucan']
                foot = camera.project(position)
                contact = camera.project(Stage.first_shard_shield_contact())
                action, local, duration = self.stage._action('lucan', time)
                image, data = self.stage._sequence('lucan', action, local, duration,
                                                  camera, position, time=time)
                scale = camera.focal*1.85/foot[2]/data['body_pixels']
                point = (round(data['anchor'][0]+(contact[0]-foot[0])/scale),
                         round(data['anchor'][1]+(contact[1]-foot[1])/scale))
                face = pygame.Surface(image.get_size())
                face.fill('black')
                pygame.draw.polygon(face, 'white', polygon)
                self.assertEqual(face.get_at(point)[:3], (255,255,255))
                self.assertGreater(image.get_at(point).a, 200)

    def test_rendered_shard_tip_does_not_extend_half_a_shard_past_contact(self):
        camera = Stage.camera(8.99)
        point = Stage.first_shard_shield_contact()
        target = Stage.first_shard_target()
        projected = pygame.Vector2(camera.project(point)[:2])
        direction = pygame.Vector2(camera.project(target)[:2])-projected
        direction = direction.normalize()
        canvas = pygame.Surface((480, 320))
        canvas.fill('black')
        self.stage._draw_shard(canvas, camera, point, target, tip=True)
        mask = pygame.mask.from_threshold(canvas, (0, 0, 0), (1, 1, 1, 255))
        mask.invert()
        samples = [pygame.Vector2(x, y) for x in range(480) for y in range(320)
                   if mask.get_at((x, y))]
        self.assertTrue(samples)
        self.assertLess(max((pixel-projected).dot(direction) for pixel in samples), 3)
        self.assertLess(min(pixel.distance_to(projected) for pixel in samples), 4)


if __name__ == '__main__':
    unittest.main()
