"""Explicit cutscene shots preserve bounded, full-height normal world tracking."""
import math
from types import SimpleNamespace
import unittest

from camera_director import CameraDirector


class ScriptedCameraTests(unittest.TestCase):
    def camera(self, *, size=(1536, 1344), point=(384, 312)):
        game = SimpleNamespace(world=SimpleNamespace(size=size),
                               player=SimpleNamespace(position=point))
        camera = CameraDirector(game)
        camera.reset()
        return game, camera

    def test_focus_is_a_finite_smooth_pan_then_holds_while_player_moves(self):
        game, camera = self.camera()
        start = camera.position()
        camera.focus((984, 712), duration=.8)
        self.assertEqual(camera.position(), start)
        self.assertFalse(camera.settled)
        self.assertTrue(camera.scripted)
        camera.update(.4)
        self.assertEqual(camera.position(), (444, 352))
        self.assertFalse(camera.settled)
        camera.update(.4)
        self.assertEqual(camera.position(), (744, 552))
        self.assertTrue(camera.settled)
        game.player.position = (1300, 1100)
        camera.update(20)
        self.assertEqual(camera.position(), (744, 552))
        self.assertTrue(camera.scripted)
        self.assertEqual(camera.framing_height, 320)

    def test_pan_is_partition_independent_and_never_overshoots(self):
        _, a = self.camera()
        _, b = self.camera()
        a.focus((984, 712), duration=.8)
        b.focus((984, 712), duration=.8)
        a.update(.8)
        for _ in range(48):
            b.update(1/60)
            x, y = b.position()
            self.assertTrue(144 <= x <= 744)
            self.assertTrue(152 <= y <= 552)
        self.assertEqual(a.position(), b.position())
        self.assertTrue(a.settled and b.settled)
        self.assertEqual(a._point, b._point)

    def test_release_pans_back_then_normal_tracking_resumes(self):
        game, camera = self.camera()
        camera.focus((984, 712), duration=.8)
        camera.update(.8)
        camera.release(duration=.6)
        self.assertTrue(camera.scripted)
        self.assertFalse(camera.settled)
        camera.update(.3)
        self.assertEqual(camera.position(), (444, 352))
        camera.update(.3)
        self.assertFalse(camera.scripted)
        self.assertTrue(camera.settled)
        self.assertEqual(camera.position(), (144, 152))
        game.player.position = (584, 412)
        camera.update(.1)
        self.assertTrue(144 < camera.position()[0] < 344)
        self.assertTrue(152 < camera.position()[1] < 252)

    def test_return_consumes_extra_time_as_normal_tracking(self):
        ga, a = self.camera()
        gb, b = self.camera()
        for camera in (a, b):
            camera.focus((984, 712), duration=0)
            camera.return_to_player(duration=.5)
        ga.player.position = gb.player.position = (584, 412)
        a.update(.7)
        b.update(.5)
        b.update(.2)
        self.assertFalse(a.scripted or b.scripted)
        self.assertEqual(a.position(), b.position())
        self.assertAlmostEqual(a._point[0], b._point[0], places=9)
        self.assertAlmostEqual(a._point[1], b._point[1], places=9)

    def test_framing_anchor_is_fractional_and_bounded_on_both_axes(self):
        _, camera = self.camera(size=(576, 552), point=(180, 510))
        self.assertEqual(camera.position(), (0, 232))
        camera.focus((360, 312), duration=.75, anchor=(.5, .33))
        camera.update(.75)
        self.assertEqual(camera.position(), (96, 206))
        self.assertAlmostEqual(camera._point[1], 206.4)
        self.assertEqual(camera.framing_height, 320)
        camera.focus((-1000, 2000), duration=.5)
        camera.update(.5)
        self.assertEqual(camera.position(), (0, 232))

    def test_short_rooms_stay_centered_without_zooming(self):
        _, camera = self.camera(size=(200, 160), point=(100, 80))
        camera.focus((5000, -5000), duration=.75, anchor=(.2, .8))
        self.assertEqual(camera.position(), (-140, -80))
        self.assertTrue(camera.settled)
        self.assertTrue(camera.scripted)
        camera.update(1)
        camera.return_to_player(.5)
        self.assertFalse(camera.scripted)
        self.assertEqual(camera.framing_height, 320)

    def test_world_change_clears_authored_shot_and_intentionally_cuts(self):
        game, camera = self.camera()
        camera.focus((984, 712), duration=.8)
        camera.update(.4)
        game.world = SimpleNamespace(size=(288, 336))
        game.player.position = (60, 186)
        self.assertFalse(camera.scripted)
        self.assertEqual(camera.position(), (-96, 16))
        self.assertTrue(camera.settled)
        camera.update(2)
        self.assertEqual(camera.position(), (-96, 16))

    def test_reset_clears_a_shot_in_the_same_world(self):
        _, camera = self.camera()
        camera.focus((984, 712), duration=.8)
        camera.update(.4)
        camera.reset()
        self.assertFalse(camera.scripted)
        self.assertTrue(camera.settled)
        self.assertEqual(camera.position(), (144, 152))

    def test_unchanged_request_does_not_restart_an_inflight_pan(self):
        _, camera = self.camera()
        camera.focus((984, 712), duration=.8)
        camera.update(.4)
        camera.focus((984, 712), duration=.8)
        camera.update(.4)
        self.assertTrue(camera.settled)
        self.assertEqual(camera.position(), (744, 552))

    def test_explicit_zero_duration_supports_static_accessibility_cuts(self):
        _, camera = self.camera()
        camera.focus((984, 712), duration=0)
        self.assertTrue(camera.settled)
        self.assertEqual(camera.position(), (744, 552))
        self.assertTrue(camera.scripted)
        camera.release(duration=0)
        self.assertTrue(camera.settled)
        self.assertFalse(camera.scripted)
        self.assertEqual(camera.position(), (144, 152))

    def test_explicit_cut_finishes_an_existing_focus_or_cancelled_return(self):
        _, camera = self.camera()
        camera.focus((984, 712), duration=.8)
        camera.update(.2)
        self.assertFalse(camera.settled)
        camera.focus((984, 712), duration=0)
        self.assertTrue(camera.settled)
        self.assertEqual(camera.position(), (744, 552))
        camera.return_to_player(duration=.6)
        camera.update(.2)
        self.assertTrue(camera.scripted)
        self.assertFalse(camera.settled)
        # Canceling a cutscene explicitly cuts back to the player even though
        # its normal return pan already has that same destination.
        camera.return_to_player(duration=0)
        self.assertFalse(camera.scripted)
        self.assertTrue(camera.settled)
        self.assertEqual(camera.position(), (144, 152))

    def test_unchanged_nonzero_return_preserves_its_progress(self):
        _, camera = self.camera()
        camera.focus((984, 712), duration=0)
        camera.return_to_player(duration=.6)
        camera.update(.3)
        camera.return_to_player(duration=.6)
        camera.update(.3)
        self.assertFalse(camera.scripted)
        self.assertTrue(camera.settled)
        self.assertEqual(camera.position(), (144, 152))

    def test_pause_or_zero_delta_does_not_advance_a_pan(self):
        _, camera = self.camera()
        camera.focus((984, 712), duration=.8)
        camera.update(.2)
        before = camera.position()
        camera.update(0)
        self.assertEqual(camera.position(), before)
        self.assertFalse(camera.settled)
        camera.update(.6)
        self.assertTrue(camera.settled)

    def test_invalid_points_anchors_and_durations_are_rejected(self):
        _, camera = self.camera()
        for point in ((1,), (1, 2, 3), (math.nan, 2), (1, math.inf), (True, 2), None):
            with self.subTest(point=point), self.assertRaises(ValueError):
                camera.focus(point)
        for anchor in ((-.1, .5), (.5, 1.1), (math.nan, .5), ('center', .5)):
            with self.subTest(anchor=anchor), self.assertRaises(ValueError):
                camera.focus((984, 712), anchor=anchor)
        camera.focus((984, 712), duration=.8)
        for duration in (-1, math.nan, math.inf, True, 'slow'):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                camera.focus((984, 712), duration=duration)
            with self.assertRaises(ValueError):camera.return_to_player(duration)


if __name__ == '__main__':unittest.main()
