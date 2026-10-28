"""Display-resolution UI, persistent readability and real input integration."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import main
from quests import OPENING_QUEST
from ui_style import Painter


class UIIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings = Path(self.directory.name)/'settings.json'
        self.game = main.Game(fullscreen=False, start_on_title=False,
                              settings_path=self.settings)
        self.game.audio.set_music(0)
        self.game.audio.set_effects(0)
        pygame.event.clear()

    def tearDown(self):
        pygame.quit()

    def key(self, key):
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=key, repeat=False))
        self.assertTrue(self.game.handle_events())

    def point(self, logical):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return (round((width-480*scale)//2+logical[0]*scale),
                round((height-320*scale)//2+logical[1]*scale))

    def click(self, logical):
        point = self.point(logical)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        self.assertTrue(self.game.handle_events())

    def offer(self):
        self.game.world = self.game._scene_by_id('sanctuary_dining')
        self.game.player.position.update(288, 231)
        self.game.player.facing = 'back'
        self.game.camera.reset()
        actor = next(actor for actor in self.game.persistent_npcs
                     if actor.data['id'] == 'mother_serene')
        self.assertTrue(self.game.social.start(actor))
        self.assertTrue(self.game.social.active)

    def reach_choice(self):
        for _ in range(80):
            if self.game.social.choosing:
                return
            self.assertTrue(self.game.social.active)
            self.click((1, 1))
        self.fail('Opening quest offer did not reach its explicit response')

    def test_gameplay_ui_draws_text_at_display_resolution_separately_from_world(self):
        self.game.window = pygame.display.set_mode((1920, 1080))
        targets = []
        original = Painter.text

        def record(painter, *args, **kwargs):
            targets.append(painter.canvas)
            return original(painter, *args, **kwargs)

        with patch.object(Painter, 'text', record):
            self.game.draw()
        self.assertTrue(targets)
        self.assertEqual(self.game.canvas.get_size(), (480, 320))
        self.assertEqual(self.game.ui_surface.get_size(), (1440, 960))
        self.assertTrue(all(target is not self.game.canvas for target in targets))
        font = self.game.ui.painter(self.game.ui_surface).font('body')
        self.assertGreaterEqual(font.actual.get_height(), 27)
        letters = font.actual.render('I l 1 O 0 rn m — “Caelan?”', True, '#f8f0d9')
        # Partial alpha comes from smooth glyph edges drawn at output size.
        self.assertTrue(any(0 < letters.get_at((x, y)).a < 255
                            for y in range(letters.get_height())
                            for x in range(letters.get_width())))

    def test_readability_and_motion_preferences_survive_a_new_game_instance(self):
        self.game.audio.set_text_scale(1.5)
        self.game.audio.set_reduced_motion(True)
        self.game.audio.set_tracker_visible(False)
        restored = main.Game(fullscreen=False, start_on_title=False,
                             settings_path=self.settings)
        self.assertEqual(restored.audio.text_scale, 1.5)
        self.assertTrue(restored.audio.reduced_motion)
        self.assertFalse(restored.audio.tracker_visible)
        self.assertEqual(restored.audio.music_volume, 0)
        self.assertEqual(restored.audio.effects_volume, 0)
        self.assertFalse(Path(self.directory.name, 'journey.json').exists())

    def test_larger_quest_choices_remain_visible_and_clickable_after_resize(self):
        self.game.audio.set_text_scale(1.5)
        self.offer()
        self.reach_choice()
        for size in ((480, 320), (960, 640), (1440, 810), (1920, 1080)):
            with self.subTest(size=size):
                self.game.window = pygame.display.set_mode(size)
                self.game.draw()
                rectangles = self.game.social.choice_rects
                self.assertEqual(len(rectangles), 2)
                for rect in rectangles:
                    self.assertTrue(pygame.Rect(0, 0, 480, 320).contains(rect))
                self.assertFalse(rectangles[0].colliderect(rectangles[1]))
                self.click((1, 1))
                self.assertTrue(self.game.social.choosing)
                self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')
        self.click(self.game.social.choice_rects[0].center)
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'active')
        self.assertFalse(self.game.social.active)

    def test_changing_readability_during_live_dialogue_preserves_quest_and_movement(self):
        self.offer()
        self.game.audio.set_text_scale(1.5)
        self.game.draw()
        initial = self.game.player.position.copy()
        for _ in range(4):
            self.game.update(1/60, (1, 0), False)
        self.assertGreater(self.game.player.position.x, initial.x)
        self.assertTrue(self.game.social.active)
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')
        self.reach_choice()
        self.click(self.game.social.choice_rects[1].center)
        self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')
        self.assertFalse(self.game.social.active)

    def test_pause_overlays_return_without_clickthrough_or_world_progress(self):
        self.offer()
        page = self.game.social.page_index
        for label, flag in (('Characters', 'status'), ('Aether Lattice', 'lattice'),
                            ('Journal', 'journal'), ('Map', 'map')):
            with self.subTest(overlay=label):
                self.key(pygame.K_ESCAPE)
                row = self.game.pause.options.index(label)
                self.click(self.game.pause.rows[row].center)
                self.assertEqual(self.game.pause.overlay, flag)
                self.assertTrue(self.game.pause.is_open)
                self.game.draw()
                clock = self.game.elapsed_ms
                position = self.game.player.position.copy()
                self.game.update(2, (1, 0), True)
                self.assertEqual(self.game.elapsed_ms, clock)
                self.assertEqual(self.game.player.position, position)
                # A second click queued behind the overlay-close key must not
                # activate Resume on the menu that was hidden beneath it.
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN,
                                                    key=pygame.K_ESCAPE, repeat=False))
                point = self.point(self.game.pause.rows[0].center)
                for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
                self.assertTrue(self.game.handle_events())
                self.assertIsNone(self.game.pause.overlay)
                self.assertTrue(self.game.pause.is_open)
                self.assertEqual(self.game.social.page_index, page)
                self.key(pygame.K_ESCAPE)
                self.assertFalse(self.game.pause.is_open)

    def test_settings_keyboard_shortcuts_and_slider_drag_use_real_event_routing(self):
        self.game.audio.set_music(.6)
        self.key(pygame.K_ESCAPE)
        self.click(self.game.pause.rows[self.game.pause.options.index('Settings')].center)
        self.assertTrue(self.game.pause.settings)
        self.game.pause.selected = 1
        self.key(pygame.K_MINUS)
        self.assertAlmostEqual(self.game.audio.music_volume, .5)
        self.key(pygame.K_EQUALS)
        self.assertAlmostEqual(self.game.audio.music_volume, .6)
        self.assertEqual(self.game.audio.effects_volume, 0)
        track = self.game.pause.settings_panel.slider_rects[1]
        start = self.point((track.left+track.width*.2, track.centery))
        finish = self.point((track.left+track.width*.8, track.centery))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=start))
        pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=finish,
                                            rel=(finish[0]-start[0], 0), buttons=(1, 0, 0)))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=finish))
        self.assertTrue(self.game.handle_events())
        self.assertAlmostEqual(self.game.audio.music_volume, .8, delta=.01)
        self.assertEqual(self.game.audio.effects_volume, 0)

    def test_location_plaque_expires_and_reappears_for_a_new_room(self):
        self.game.update(0, (0, 0), False)
        label = self.game.location_label
        self.assertIsNotNone(label)
        self.assertGreater(self.game.location_seconds, 0)
        self.game.pause.open()
        before = self.game.location_seconds
        self.game.update(4, (0, 0), False)
        self.assertEqual(self.game.location_seconds, before)
        self.game.pause.close()
        self.game.update(4, (0, 0), False)
        self.assertEqual(self.game.location_seconds, 0)
        self.game.world = self.game._scene_by_id('sanctuary_bedroom')
        self.game.player.position.update(self.game.world.data['spawn'])
        self.game.update(0, (0, 0), False)
        self.assertNotEqual(self.game.location_label, label)
        self.assertGreater(self.game.location_seconds, 0)

    def test_wake_cue_survives_text_and_display_reflow_without_repeating_motion(self):
        self.assertTrue(self.game.begin_journey(False))
        opening = self.game.opening
        with patch.object(opening, '_queue', wraps=opening._queue) as queue:
            for _ in range(80):
                if self.game.social.page.get('cue') == 'wake_up':
                    break
                self.game.social.advance()
                self.game.update(1/60, (0, 0), False)
            else:
                self.fail('Wake dialogue never reached its physical cue')
            source = self.game.social.page['source_line']
            self.game.update(1/60, (0, 0), False)
            self.assertEqual(opening.action_name, 'wake_up')
            for size, scale in (((1920, 1080), 1.5), ((480, 320), 1.0)):
                self.game.window = pygame.display.set_mode(size)
                self.game.audio.set_text_scale(scale)
                self.game.draw()
                self.game.update(1/60, (0, 0), False)
                self.assertEqual(self.game.social.page['source_line'], source)
            for _ in range(300):
                if opening.stage == 'explore':
                    break
                if self.game.social.scripted:
                    self.game.social.advance()
                self.game.update(1/60, (0, 0), False)
            self.assertEqual(opening.stage, 'explore')
            self.assertFalse(self.game.social.locked)
            self.assertFalse(hasattr(self.game.player, 'story_sprite'))
            wake_actions = [call for call in queue.call_args_list if call.args[0] == 'wake_up']
            self.assertEqual(len(wake_actions), 1)
            self.assertEqual(self.game.quests.status(OPENING_QUEST), 'available')


if __name__ == '__main__':
    unittest.main()
