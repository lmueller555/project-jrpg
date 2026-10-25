"""Scene framing, reversible dialogue transitions and deterministic easing."""
import math
from types import SimpleNamespace
import unittest

from camera_director import CameraDirector


class CameraDirectorTests(unittest.TestCase):
    def game(self, size=(432, 336), point=(132, 228), stage='disabled', focus=None):
        opening = SimpleNamespace(stage=stage, focus=focus)
        opening.camera_focus = lambda: opening.focus
        return SimpleNamespace(
            world=SimpleNamespace(size=size),
            player=SimpleNamespace(position=point), opening=opening,
            social=SimpleNamespace(locked=False, actor=None, script_identifier=None))

    def test_authored_breakfast_shot_does_not_change_when_textbox_toggles(self):
        game = self.game(stage='breakfast', focus=(210, 185))
        camera = CameraDirector(game)
        camera.reset()
        self.assertEqual(camera.position(), (-24, 83))
        for locked in (True, False, True, False):
            game.social.locked = locked
            camera.update(.2)
            self.assertEqual(camera.position(), (-24, 83))
            self.assertEqual(camera.framing_height, 204)
        self.assertTrue(camera.settled)

    def test_wake_to_free_control_eases_without_a_camera_cut(self):
        game = self.game(size=(288, 336), point=(60, 186), stage='wake', focus=(74, 150))
        camera = CameraDirector(game)
        camera.reset()
        self.assertEqual(camera.position(), (-96, 48))
        game.opening.stage, game.opening.focus = 'explore', None
        camera.update(1/60)
        self.assertTrue(16 < camera.position()[1] < 48)
        self.assertTrue(204 < camera.framing_height < 320)
        for _ in range(24):
            camera.update(1/60)
        self.assertEqual(camera.position(), (-96, 16))
        self.assertTrue(camera.settled)

    def test_ease_is_frame_partition_independent_and_never_overshoots(self):
        game_a = self.game(size=(1536, 1344), point=(384, 312))
        game_b = self.game(size=(1536, 1344), point=(384, 312))
        a, b = CameraDirector(game_a), CameraDirector(game_b)
        a.reset(); b.reset()
        game_a.player.position = game_b.player.position = (584, 412)
        a.update(.3)
        for _ in range(18):
            b.update(1/60)
            self.assertTrue(144 <= b.position()[0] <= 344)
            self.assertTrue(152 <= b.position()[1] <= 252)
        self.assertEqual(a.position(), b.position())
        self.assertAlmostEqual(a._point[0], b._point[0], places=9)
        self.assertAlmostEqual(a._point[1], b._point[1], places=9)

    def test_room_change_is_one_intentional_cut(self):
        game = self.game(size=(1536, 1344), point=(1000, 900))
        camera = CameraDirector(game)
        camera.reset()
        game.world = SimpleNamespace(size=(288, 336))
        game.player.position = (60, 186)
        game.opening.stage, game.opening.focus = 'wake', (74, 150)
        self.assertEqual(camera.position(), (-96, 48))
        camera.update(.2)
        self.assertEqual(camera.position(), (-96, 48))

    def test_small_world_centering_and_both_axis_bounds(self):
        game = self.game(size=(200, 160), point=(10, 10))
        camera = CameraDirector(game)
        camera.reset()
        self.assertEqual(camera.position(), (-140, -80))
        for point in ((-100, -100), (2000, 2000)):
            game.world = SimpleNamespace(size=(1536, 1344))
            game.player.position = point
            camera.reset()
            x, y = camera.position()
            self.assertTrue(0 <= x <= 1056)
            self.assertTrue(0 <= y <= 1024)

    def test_bedroom_inspection_holds_existing_useful_composition(self):
        game = self.game(size=(288, 336), point=(60, 186))
        camera = CameraDirector(game)
        camera.reset()
        before = camera.position()
        game.social.locked = True
        game.social.script_identifier = 'bedroom_inspect_bed'
        for _ in range(20):
            camera.update(1/60)
        self.assertEqual(camera.position(), before)
        self.assertEqual(camera.framing_height, 320)
        game.social.locked = False
        game.social.script_identifier = None
        camera.update(.3)
        self.assertEqual(camera.position(), before)

    def test_inspection_in_a_small_centered_room_does_not_recenter_it(self):
        game = self.game(size=(200, 160), point=(100, 80))
        camera = CameraDirector(game)
        camera.reset()
        before = camera.position()
        game.social.locked = True
        game.social.script_identifier = 'bedroom_inspect_books'
        camera.update(.3)
        self.assertEqual(camera.position(), before)
        self.assertEqual(camera.framing_height, 320)

    def test_inspection_exposes_a_player_previously_below_the_textbox(self):
        game = self.game(size=(432, 336), point=(216, 300))
        camera = CameraDirector(game)
        camera.reset()
        self.assertEqual(camera.position(), (-24, 16))
        game.social.locked = True
        game.social.script_identifier = 'bedroom_inspect_test'
        camera.update(1/60)
        self.assertTrue(16 < camera.position()[1] < 110)
        camera.update(.4)
        self.assertLessEqual(game.player.position[1]-camera.position()[1], 191)

    def test_assignment_free_roaming_does_not_stay_fixed_on_serene(self):
        game = self.game(stage='assignment', focus=(228, 198))
        camera = CameraDirector(game)
        camera.reset()
        self.assertEqual(camera.position(), (-24, 16))
        game.social.locked = True
        camera.update(.4)
        self.assertEqual(camera.position(), (-24, 96))

    def test_conversation_centers_participants_and_eases_both_directions(self):
        game = self.game(point=(288, 231))
        camera = CameraDirector(game)
        camera.reset()
        game.social.locked = True
        game.social.actor = SimpleNamespace(position=(288, 214))
        camera.update(1/60)
        self.assertTrue(16 < camera.position()[1] < 108)
        camera.update(.4)
        self.assertTrue(camera.settled)
        game.social.locked = False
        game.social.actor = None
        previous = camera.position()[1]
        camera.update(1/60)
        self.assertTrue(16 < camera.position()[1] < previous)

    def test_resize_is_not_part_of_camera_coordinates_and_invalid_dt_is_rejected(self):
        game = self.game(stage='breakfast', focus=(210, 185))
        camera = CameraDirector(game)
        camera.reset()
        for size in ((960, 640), (1920, 1080), (800, 800)):
            game.window = SimpleNamespace(size=size)
            camera.update(.1)
            self.assertEqual(camera.position(), (-24, 83))
        for value in (-1, math.nan, math.inf):
            with self.assertRaises(ValueError):
                camera.update(value)


if __name__ == '__main__':
    unittest.main()
