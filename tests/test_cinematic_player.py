"""Shared scene clocks, input and loading survive removal of the old opening."""
import math
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from audio_settings import AudioSettings
from cinematic_fixture import write_scene
from cinematic_player import CinematicPlayer
from ui_style import UIStyle


class CinematicPlayerTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        temporary = tempfile.TemporaryDirectory(prefix='cinematic-contract-')
        self.addCleanup(temporary.cleanup)
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
                                    audio=AudioSettings(), _music_focused=True)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = self.to_canvas
        self.canvas = pygame.Surface((480, 320))
        self.ui = pygame.Surface((960, 640))
        self.path = write_scene(Path(temporary.name))
        self.scene = CinematicPlayer(self.game, scene_path=self.path)

    def tearDown(self):
        pygame.quit()

    def to_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        x, y = ((point[0]-(width-480*scale)//2)/scale,
                (point[1]-(height-320*scale)//2)/scale)
        return (x, y) if 0 <= x < 480 and 0 <= y < 320 else None

    def draw(self):
        self.scene.draw(self.canvas, self.ui)

    def key(self, *, repeat=False):
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN,
                                                  key=pygame.K_ESCAPE, repeat=repeat))

    def click(self, logical):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        pos = (round((width-480*scale)//2+logical[0]*scale),
               round((height-320*scale)//2+logical[1]*scale))
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                                  button=1, pos=pos))

    def test_a_scene_path_is_required_without_a_retired_default(self):
        with self.assertRaises(TypeError):
            CinematicPlayer(self.game)
        self.assertEqual(self.scene.scene_path, self.path.resolve())
        self.assertFalse(self.scene.active)

    def test_natural_completion_releases_before_one_callback(self):
        calls = []
        self.scene.start(lambda: calls.append((self.scene.active, self.scene.paused,
                                               self.scene.finished_reason)))
        self.scene.update(self.scene.duration-1)
        self.assertTrue(self.scene.active)
        self.scene.update(1)
        self.scene.update(200)
        self.scene.skip()
        self.assertEqual(calls, [(False, False, 'completed')])

    def test_reset_discards_callback_and_start_replays_from_first_shot(self):
        calls = []
        self.scene.start(lambda: calls.append('discarded'))
        self.scene.update(50)
        self.scene.reset()
        self.scene.update(200)
        self.assertEqual(calls, [])
        self.scene.start(lambda: calls.append('replayed'))
        self.assertEqual((self.scene.elapsed, self.scene.shot, self.scene.paused),
                         (0, 'establish', False))
        self.scene.skip()
        self.assertEqual(calls, ['replayed'])

    def test_escape_freezes_camera_caption_and_rendered_layers(self):
        self.scene.start()
        self.scene.update(14)
        self.key()
        self.draw()
        image = pygame.image.tobytes(self.canvas, 'RGB')
        state = self.scene.elapsed, self.scene.camera_position, self.scene.dialogue
        self.scene.update(40)
        self.draw()
        self.assertEqual((self.scene.elapsed, self.scene.camera_position,
                          self.scene.dialogue), state)
        self.assertEqual(pygame.image.tobytes(self.canvas, 'RGB'), image)
        self.key(repeat=True)
        self.assertTrue(self.scene.paused)
        self.key()
        self.scene.update(.5)
        self.assertGreater(self.scene.elapsed, state[0])

    def test_focus_gain_preserves_manual_pause(self):
        self.scene.start()
        self.scene.update(1)
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.scene.update(3)
        self.assertEqual(self.scene.elapsed, 1)
        self.key()
        self.scene.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.scene.update(3)
        self.assertEqual(self.scene.elapsed, 1)
        self.key()
        self.scene.update(.5)
        self.assertEqual(self.scene.elapsed, 1.5)

    def test_skip_works_while_paused_and_ignores_other_clicks(self):
        calls = []
        self.scene.start(lambda: calls.append(self.scene.finished_reason))
        self.key()
        self.draw()
        self.click((20, 20))
        self.assertTrue(self.scene.active)
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1))
        self.click(self.scene.skip_rect.center)
        self.assertEqual(calls, ['skipped'])
        self.assertFalse(self.scene.paused)

    def test_letterbox_click_cannot_skip_but_scaled_button_can(self):
        self.game.window = pygame.display.set_mode((1100, 640))
        self.scene.start()
        self.draw()
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                                  button=1, pos=(20, 620)))
        self.assertTrue(self.scene.active)
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1))
        self.click(self.scene.skip_rect.center)
        self.assertFalse(self.scene.active)

    def test_camera_pan_is_bounded_and_holds_for_conversation(self):
        self.scene.start()
        self.scene.update(2)
        self.assertEqual(self.scene.camera_position, (0, 0))
        self.scene.update(2)
        self.assertEqual(self.scene.camera_position, (60, 30))
        self.scene.update(2)
        point = self.scene.camera_position.copy()
        self.scene.update(10)
        self.assertEqual(self.scene.camera_position, point)
        self.assertEqual(self.scene.shot, 'conversation')
        for elapsed in range(math.ceil(self.scene.duration)+1):
            self.scene.elapsed = elapsed
            x, y = self.scene.camera_position
            self.assertTrue(-1e-9 <= x <= 480+1e-9 and -1e-9 <= y <= 160+1e-9)

    def test_reduced_motion_uses_static_shot_crops(self):
        self.game.audio.set_reduced_motion(True)
        self.scene.elapsed = 2.1
        point = self.scene.camera_position
        self.scene.elapsed = 5.9
        self.assertEqual(point, self.scene.camera_position)
        self.assertTrue(self.scene.camera_settled)

    def test_authored_transition_runs_once_then_holds_destination(self):
        self.scene.start()
        _, _, frames, transitions = self.scene.actors[1]
        self.scene.elapsed = 12.1
        self.assertEqual(self.scene._actor_frame('mira', frames, transitions).get_at((0, 0)),
                         pygame.Color('#875755'))
        self.scene.elapsed = 12.4
        self.assertIs(self.scene._actor_frame('mira', frames, transitions), frames['sit'])
        self.game.audio.set_reduced_motion(True)
        self.scene.elapsed = 12.1
        self.assertIs(self.scene._actor_frame('mira', frames, transitions), frames['sit'])

    def test_invalid_delta_cannot_corrupt_visual_clock(self):
        self.scene.start()
        for delta in (-1, float('nan'), float('inf'), None, '4'):
            self.scene.update(delta)
        self.assertEqual(self.scene.elapsed, 0)

    def test_escaping_art_does_not_activate_a_partial_scene(self):
        self.scene.data['layers'][0]['file'] = '../outside.png'
        with self.assertRaises(ValueError):
            self.scene.start()
        self.assertFalse(self.scene.active)
        self.assertIsNone(self.scene.layers)


if __name__ == '__main__':
    unittest.main()
