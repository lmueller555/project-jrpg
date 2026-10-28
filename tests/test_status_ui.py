"""Read-only status inspection, modal ownership and accessible text layout."""
import os
from types import SimpleNamespace
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from audio_settings import AudioSettings
from character_attributes import ATTRIBUTE_IDS, CharacterAttributes
from pause_menu import PauseMenu
from status_ui import StatusUI
from ui_style import UIStyle


class StatusUITests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
                                    audio=AudioSettings(), attributes=CharacterAttributes(),
                                    ui_surface=pygame.Surface((960, 640)), _mouse_held=False)
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.to_canvas = self.to_canvas
        self.screen = StatusUI(self.game)
        self.game.status_ui = self.screen
        self.pause = PauseMenu(self.game)

    def tearDown(self):pygame.quit()

    def point(self, logical):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return ((width-480*scale)//2+logical[0]*scale,
                (height-320*scale)//2+logical[1]*scale)

    def to_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        logical = ((point[0]-(width-480*scale)//2)/scale,
                   (point[1]-(height-320*scale)//2)/scale)
        return logical if 0 <= logical[0] < 480 and 0 <= logical[1] < 320 else None

    def key(self, key, **extra):
        return self.screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, **extra))

    def click(self, logical):
        point = self.point(logical)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point))

    def hover(self, logical):
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION,
                                                   pos=self.point(logical), rel=(0, 0), buttons=(0, 0, 0)))

    def test_keyboard_and_mouse_inspect_all_attributes_without_mutating_values(self):
        before = self.game.attributes.to_dict()
        self.screen.open()
        visited = []
        for _ in ATTRIBUTE_IDS:
            visited.append(self.screen.selected)
            self.key(pygame.K_TAB)
        self.assertEqual(tuple(visited), ATTRIBUTE_IDS)
        self.assertEqual(self.screen.selected, 'hp')
        self.key(pygame.K_TAB, mod=pygame.KMOD_SHIFT)
        self.assertEqual(self.screen.selected, 'lck')
        for identifier, rect in self.screen.stat_rects.items():
            self.click(rect.center)
            self.assertEqual(self.screen.selected, identifier)
        self.assertEqual(self.game.attributes.to_dict(), before)

    def test_spirit_and_magick_descriptions_remain_distinct_and_complete(self):
        self.screen.open()
        self.game.audio.set_text_scale(1.5)
        self.game.ui_surface = pygame.Surface((480, 320))
        for identifier, expected in (('spr', 'power of healing spells'),
                                     ('mag', 'power of damaging spells')):
            self.screen._select(identifier)
            painter = self.game.ui.painter(self.game.ui_surface)
            lines, height = self.screen._layout(painter)
            self.assertIn(expected, ' '.join(lines))
            self.key(pygame.K_END)
            self.assertEqual(self.screen.detail_scroll, self.screen.detail_max_scroll)
            last_bottom = self.screen.detail_view.top+len(lines)*height-self.screen.detail_scroll
            self.assertLessEqual(last_bottom, self.screen.detail_view.bottom)
        self.screen._select('mp')
        self.screen._layout(painter)
        self.assertGreater(self.screen.detail_max_scroll, 0)
        self.key(pygame.K_PAGEDOWN)
        self.assertGreater(self.screen.detail_scroll, 0)
        self.key(pygame.K_END)
        self.assertEqual(self.screen.detail_scroll, self.screen.detail_max_scroll)
        self.key(pygame.K_HOME)
        self.assertEqual(self.screen.detail_scroll, 0)

    def test_all_stat_labels_and_starting_values_fit_at_every_text_size(self):
        self.screen.open()
        for size in ((480, 320), (960, 640), (1440, 810)):
            self.game.ui_surface = pygame.Surface(size)
            for scale in (1.0, 1.25, 1.5):
                with self.subTest(size=size, scale=scale):
                    self.game.audio.set_text_scale(scale)
                    painter = self.game.ui.painter(self.game.ui_surface)
                    self.screen.draw(self.game.ui_surface)
                    for identifier, rect in self.screen.stat_rects.items():
                        self.assertTrue(pygame.Rect(12, 12, 456, 296).contains(rect))
                        label = self.game.attributes.definitions[identifier]['label']
                        if identifier in ('hp', 'mp'):
                            text = str(self.game.attributes.value(identifier))+' / '+str(self.game.attributes.value(identifier))
                            self.assertLessEqual(painter.font('small').size(text)[0], rect.width-8)
                            self.assertLessEqual(painter.font(bold=True).get_height()+painter.font('small').get_height()+11, rect.height)
                        else:
                            width = painter.font().size(label)[0]+painter.font(bold=True).size('10')[0]
                            self.assertLessEqual(width+35, rect.width)
                            self.assertLessEqual(painter.font().get_height(), rect.height)
                    self.assertEqual(self.game.ui_surface.get_clip(), self.game.ui_surface.get_rect())

    def test_pause_status_returns_to_pause_with_selection_and_no_clickthrough(self):
        self.pause.open()
        index = self.pause.options.index('Characters')
        self.pause.selected = index
        self.assertTrue(self.pause.activate())
        self.assertEqual(self.pause.overlay, 'status')
        self.assertTrue(self.screen.is_open)
        self.pause.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertFalse(self.screen.is_open)
        self.assertTrue(self.pause.is_open)
        self.assertIsNone(self.pause.overlay)
        self.assertEqual(self.pause.selected, index)

    def test_hovering_every_icon_shows_complete_bounded_tooltip_without_clicking(self):
        self.screen.open()
        before = self.game.attributes.to_dict()
        for size in ((480, 320), (960, 640), (1440, 810)):
            self.game.window = pygame.display.set_mode(size)
            scale = max(1, min(size[0]//480, size[1]//320))
            self.game.ui_surface = pygame.Surface((480*scale, 320*scale))
            for text_scale in (1.0, 1.25, 1.5):
                self.game.audio.set_text_scale(text_scale)
                self.screen.draw(self.game.ui_surface)
                painter = self.game.ui.painter(self.game.ui_surface)
                for identifier in ATTRIBUTE_IDS:
                    with self.subTest(size=size, text_scale=text_scale, attribute=identifier):
                        self.hover(self.screen.icon_rects[identifier].center)
                        tooltip = self.screen.tooltip_layout(painter)
                        self.assertEqual(tooltip['attribute'], identifier)
                        metadata = self.game.attributes.definitions[identifier]
                        self.assertEqual(' '.join(tooltip['lines']), metadata['description'])
                        self.assertIn(metadata['name'], tooltip['title'])
                        self.assertTrue(self.screen.tooltip_bounds.contains(tooltip['rect']))
                        self.assertFalse(tooltip['rect'].colliderect(self.screen.close_rect))
                        self.assertLessEqual(tooltip['rect'].bottom, 274)
                        content_height = (len(tooltip['title_lines'])*tooltip['title_height']+
                                          len(tooltip['lines'])*tooltip['line_height']+24)
                        self.assertLessEqual(content_height, tooltip['rect'].height)
                        self.screen.draw(self.game.ui_surface)
        self.assertEqual(self.screen.selected, 'hp')
        self.assertEqual(self.game.attributes.to_dict(), before)

    def test_tooltip_clears_on_pointer_leave_close_and_window_focus_loss(self):
        self.screen.open();self.screen.draw(self.game.ui_surface)
        self.hover(self.screen.icon_rects['spr'].center)
        self.assertEqual(self.screen.tooltip_layout()['attribute'], 'spr')
        self.hover((15, 290))
        self.assertIsNone(self.screen.tooltip_layout())
        self.hover(self.screen.icon_rects['mag'].center)
        self.screen.handle_event(pygame.event.Event(pygame.WINDOWLEAVE))
        self.assertIsNone(self.screen.tooltip_layout())
        self.hover(self.screen.icon_rects['hp'].center)
        self.screen.close()
        self.assertIsNone(self.screen.tooltip_layout())
        self.screen.open()
        self.assertIsNone(self.screen.tooltip_layout())

    def test_keyboard_focus_exposes_the_same_explanation_as_hover(self):
        self.screen.open()
        for identifier in ATTRIBUTE_IDS[1:]:
            self.key(pygame.K_TAB)
            tooltip = self.screen.tooltip_layout()
            self.assertEqual(tooltip['attribute'], identifier)
            expected = self.game.attributes.definitions[identifier]['description']
            self.assertEqual(' '.join(tooltip['lines']), expected)
        self.screen.draw(self.game.ui_surface)
        self.hover(self.screen.icon_rects['spr'].center)
        self.assertEqual(self.screen.tooltip_layout()['attribute'], 'spr')
        self.key(pygame.K_RIGHT)
        self.assertEqual(self.screen.tooltip_layout()['attribute'], 'hp')

    def test_letterboxed_mouse_ignores_borders_and_close_is_reachable(self):
        for size in ((1100, 750), (800, 800)):
            self.game.window = pygame.display.set_mode(size)
            self.screen.open()
            self.screen._select('spr')
            self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
            self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(0, 0)))
            self.assertEqual(self.screen.selected, 'spr')
            self.assertTrue(self.screen.is_open)
            self.click(self.screen.close_rect.center)
            self.assertFalse(self.screen.is_open)

    def test_reset_clears_inspection_state(self):
        self.screen.open();self.screen._select('spr')
        self.screen.detail_scroll = 12
        self.screen.dragging = True
        self.screen.reset()
        self.assertFalse(self.screen.is_open)
        self.assertEqual(self.screen.selected, 'hp')
        self.assertEqual(self.screen.detail_scroll, 0)
        self.assertFalse(self.screen.dragging)


if __name__ == '__main__':unittest.main()
