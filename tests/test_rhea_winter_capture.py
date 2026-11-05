"""The wardrobe review may change art without changing authored shot staging."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

from tools.capture_rhea_winter_cinematic import assert_close, validate_frame


class WinterCaptureTests(unittest.TestCase):
    def scene_and_reference(self):
        action = dict(shot='rune_panorama', positions={'rhea': [-3., 0., 0.]},
                      camera_position=[5., 16., -9.], camera_target=[-3., .8, 0.],
                      focal=245., world_rhea_count=1)
        stage = SimpleNamespace(telemetry=lambda _time: action,
                                last_draw_trace=[dict(actor='rhea', representation='energy_rear')])
        scene = SimpleNamespace(shot='rune_panorama', camera_position=[100., 128.],
                                camera_zoom=1., brush_progress=1., elapsed=19., action_stage=stage)
        reference = dict(shot=scene.shot, camera=list(scene.camera_position), zoom=1.,
                         brush=1., action=deepcopy(action))
        return scene, reference, action

    def test_different_rhea_art_representation_preserves_the_camera_contract(self):
        scene, reference, _ = self.scene_and_reference()
        validate_frame(scene, reference)
        scene.action_stage.last_draw_trace[0]['representation'] = 'different_authored_cloth_frame'
        validate_frame(scene, reference)

    def test_changed_camera_or_actor_position_is_rejected(self):
        scene, reference, action = self.scene_and_reference()
        action['positions']['rhea'][0] += .1
        with self.assertRaisesRegex(AssertionError, 'positions.rhea'):
            validate_frame(scene, reference)
        action['positions']['rhea'][0] -= .1
        action['camera_position'][1] += .1
        with self.assertRaisesRegex(AssertionError, 'camera_position'):
            validate_frame(scene, reference)

    def test_a_second_world_rhea_is_rejected(self):
        scene, reference, _ = self.scene_and_reference()
        scene.action_stage.last_draw_trace.append(dict(actor='rhea', representation='portrait_overlay'))
        with self.assertRaisesRegex(AssertionError, 'more than once'):
            validate_frame(scene, reference)

    def test_float_noise_is_tolerated_but_non_numeric_changes_are_not(self):
        assert_close([1., 2.+1e-10], [1., 2.])
        with self.assertRaises(AssertionError):
            assert_close('wrong_shot', 'rune_panorama')


if __name__ == '__main__':
    unittest.main()
