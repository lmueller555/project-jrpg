"""The opening presents timed prose through the game's portrait dialogue UI."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from audio_settings import AudioSettings
from opening_cinematic import OpeningCinematic, ROOT
import speech_bubble
from ui_style import Painter, UIStyle


class CinematicDialogueTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
                                    audio=AudioSettings(), _music_focused=True)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = lambda point: (point[0]/2, point[1]/2)
        self.canvas = pygame.Surface((480, 320))
        self.ui = pygame.Surface((960, 640))
        self.scene = OpeningCinematic(self.game)
        self.scene.start()

    def tearDown(self):
        pygame.quit()

    def passage(self, identifier):
        return next(record for record in self.scene.data['dialogue']
                    if record['id'] == identifier)

    def layout_at(self, elapsed):
        self.scene.elapsed = elapsed
        self.scene._layout(self.game.ui.painter(self.ui))
        return self.scene.caption_layout

    @staticmethod
    def source_words(pages):
        return ' '.join(line for page in pages for line in page).split()

    def assert_page_readable(self, painter, layout):
        self.assertTrue(pygame.Rect(0, 0, 480, 320).contains(layout.panel))
        self.assertFalse(layout.panel.colliderect(self.scene.skip_rect))
        self.assertEqual(layout.panel.width, speech_bubble.PANEL_WIDTH)
        self.assertEqual(layout.portrait.size, (48, 48))
        self.assertTrue(layout.panel.contains(layout.portrait))
        self.assertLess(layout.portrait.right, layout.text_origin[0])
        self.assertLessEqual(len(self.scene.caption_lines), speech_bubble.MAX_LINES)
        for index, line in enumerate(self.scene.caption_lines):
            size = painter.font().size(line)
            rect = pygame.Rect(layout.text_origin[0],
                               layout.text_origin[1]+index*layout.line_height, *size)
            self.assertLessEqual(size[0], speech_bubble.TEXT_WIDTH)
            self.assertTrue(layout.panel.contains(rect), (line, rect, layout.panel))

    def test_shared_renderer_uses_each_existing_portrait_without_interactive_hints(self):
        manifest = json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())
        for speaker in ('Caelan', 'Mira'):
            record = next(record for record in self.scene.data['dialogue']
                          if record['speaker'] == speaker)
            self.scene.elapsed = record['start']+.01
            with patch.object(speech_bubble, 'draw_dialogue_frame',
                              wraps=speech_bubble.draw_dialogue_frame) as frame, \
                 patch.object(speech_bubble, 'draw_dialogue_prose',
                              wraps=speech_bubble.draw_dialogue_prose) as prose, \
                 patch.object(Painter, 'text', autospec=True, side_effect=Painter.text) as text:
                self.scene.draw(self.canvas, self.ui)
            frame.assert_called_once()
            prose.assert_called_once()
            layout, portrait = frame.call_args.args[1:]
            self.assertEqual(layout.name_lines, (speaker,))
            self.assertEqual(layout.portrait_key, speaker.lower())
            expected = pygame.image.load(str(ROOT/'assets/portraits/eldenmere'/
                                              manifest['portraits'][speaker.lower()]['file'])).convert_alpha()
            self.assertEqual(pygame.image.tobytes(portrait, 'RGBA'),
                             pygame.image.tobytes(expected, 'RGBA'))
            self.assertNotIn('Click to continue', [call.args[1] for call in text.call_args_list])
            self.assertFalse(prose.call_args.kwargs.get('hint'))
            self.assertFalse(prose.call_args.kwargs.get('show_indicator', False))
            self.assertIsNone(layout.tail_side)
            self.assertFalse(layout.offscreen)

    def test_all_passages_remain_complete_and_every_page_fits_at_accessible_sizes(self):
        for size in ((480, 320), (960, 640)):
            self.ui = pygame.Surface(size)
            painter = self.game.ui.painter(self.ui)
            for scale in (1, 1.25, 1.5):
                self.game.audio.text_scale = scale
                for record in self.scene.data['dialogue']:
                    with self.subTest(size=size, scale=scale, passage=record['id']):
                        start, duration = record['start'], record['end']-record['start']
                        self.layout_at(start+.00001)
                        pages = self.scene.caption_pages
                        self.assertEqual(self.source_words(pages), record['text'].split())
                        visited = set()
                        page_visible_times = {}
                        sizes = set()
                        # Sample the actual timed presentation, including its
                        # final instant, so no tail page can silently vanish.
                        for step in range(65):
                            fraction = min(step/64, 1-1e-7)
                            layout = self.layout_at(start+duration*fraction)
                            visited.add(self.scene.caption_page_index)
                            page_visible_times.setdefault(self.scene.caption_page_index, []).append(
                                self.scene.elapsed)
                            sizes.add(layout.panel.size)
                            self.assert_page_readable(painter, layout)
                        self.assertEqual(visited, set(range(len(pages))))
                        self.assertEqual(len(sizes), 1)
                        if len(pages) > 1:
                            # An orphan ending such as 'it?' must not flash up
                            # for a fraction of a second at enlarged text sizes.
                            self.assertTrue(all(len(page) >= 2 for page in pages), pages)
                            for index, times in page_visible_times.items():
                                self.assertGreaterEqual(max(times)-min(times), 1.5,
                                                        (record['id'], index, pages[index]))

    def test_automatic_pages_receive_reading_time_and_freeze_on_pause(self):
        self.game.audio.text_scale = 1.5
        record = self.passage('small_spell')
        self.layout_at(record['start']+.001)
        pages = self.scene.caption_pages
        self.assertGreater(len(pages), 1)
        weights = [sum(len(line) for line in page) for page in pages]
        elapsed_weight = 0
        for index, weight in enumerate(weights):
            midpoint = (elapsed_weight+weight/2)/sum(weights)
            self.layout_at(record['start']+(record['end']-record['start'])*midpoint)
            self.assertEqual(self.scene.caption_page_index, index)
            self.assertEqual(self.scene.caption_lines, pages[index])
            elapsed_weight += weight
        self.scene.handle_event(pygame.event.Event(pygame.KEYDOWN,
                                                  key=pygame.K_ESCAPE, repeat=False))
        before = (self.scene.elapsed, self.scene.caption_page_index,
                  list(self.scene.caption_lines), self.scene.caption_rect.copy())
        self.scene.update(20)
        self.scene._layout(self.game.ui.painter(self.ui))
        self.assertEqual((self.scene.elapsed, self.scene.caption_page_index,
                          self.scene.caption_lines, self.scene.caption_rect), before)

    def test_panel_click_is_not_a_manual_page_advance(self):
        self.game.audio.text_scale = 1.5
        record = self.passage('small_spell')
        self.layout_at(record['start']+.1)
        before = self.scene.elapsed, self.scene.caption_page_index, list(self.scene.caption_lines)
        center = self.scene.caption_rect.center
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                                  pos=(center[0]*2, center[1]*2)))
        self.scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1))
        self.scene._layout(self.game.ui.painter(self.ui))
        self.assertEqual((self.scene.elapsed, self.scene.caption_page_index,
                          self.scene.caption_lines), before)
        self.assertTrue(self.scene.active)

    def test_display_and_text_size_reflow_do_not_advance_the_scene(self):
        record = self.passage('small_spell')
        self.layout_at(record['start']+(record['end']-record['start'])*.65)
        elapsed = self.scene.elapsed
        for size, scale in (((480, 320), 1.5), ((1440, 960), 1), ((960, 640), 1.25)):
            self.ui = pygame.Surface(size)
            self.game.audio.text_scale = scale
            self.scene._layout(self.game.ui.painter(self.ui))
            self.assertEqual(self.scene.elapsed, elapsed)
            self.assertEqual(self.scene.dialogue['id'], record['id'])
            self.assertEqual(self.source_words(self.scene.caption_pages), record['text'].split())
            self.assert_page_readable(self.game.ui.painter(self.ui), self.scene.caption_layout)


if __name__ == '__main__':
    unittest.main()
