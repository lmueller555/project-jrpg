"""Party-wide progression is inspectable without changing party or resources."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from audio_settings import AudioSettings
from character_attributes import CharacterAttributes
from leveling import CharacterLevel, total_xp_for_level
from party_state import PartyState
from party_ui import PartyUI
from status_ui import StatusUI
from ui_style import Painter, UIStyle


class ProgressionMenuTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
            ui_surface=pygame.Surface((960, 640)), audio=AudioSettings(),
            attributes=CharacterAttributes(), _mouse_held=False)
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.party = PartyState(self.game.attributes)
        self.game.set_active_party = Mock(side_effect=self.game.party.select)
        self.game.character_progression = SimpleNamespace(records={identifier:CharacterLevel(identifier)
            for identifier in self.game.party.known_ids})
        self.game.to_canvas = self.to_canvas
        self.status = StatusUI(self.game)
        self.party = PartyUI(self.game)

    def tearDown(self):pygame.quit()

    def to_canvas(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        point = ((point[0]-(width-480*scale)//2)/scale,
                 (point[1]-(height-320*scale)//2)/scale)
        return point if 0 <= point[0] < 480 and 0 <= point[1] < 320 else None

    def click(self, rect):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        point = (round((width-480*scale)/2+rect.centerx*scale),
                 round((height-320*scale)/2+rect.centery*scale))
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.status.handle_event(pygame.event.Event(kind, button=1, pos=point))

    def key(self, key):
        self.status.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, repeat=False))

    def set_level(self, identifier, level, extra=0):
        self.game.character_progression.records[identifier] = CharacterLevel(identifier,
            total_xp_for_level(level)+extra)

    def texts(self, draw):
        original = Painter.text
        with patch.object(Painter, 'text', autospec=True, side_effect=original) as spy:
            draw(self.game.ui_surface)
        return [str(call.args[1]) for call in spy.call_args_list]

    def test_only_recruited_companions_are_selectable_and_unavailable_can_be_inspected(self):
        self.assertFalse(self.status.select_character('mira'))
        self.assertEqual(self.status.roster, ('caelan',))
        self.assertTrue(self.game.party.recruit('mira'))
        self.assertTrue(self.game.party.set_available('mira', False, 'Repairing the mill.'))
        self.game.party.characters['mira'].set_current(hp=7, mp=3)
        self.game.party.characters['mira'].apply_growth({'mag':27})
        before = self.game.party.to_dict()
        self.status.open();self.key(pygame.K_e)
        self.assertEqual(self.status.character_id, 'mira')
        self.assertIs(self.status.attributes, self.game.party.characters['mira'])
        text = self.texts(self.status.draw)
        self.assertIn('Mira', text)
        self.assertIn(str(self.game.party.characters['mira'].value('mag')), text)
        self.assertIn('7/'+str(self.game.party.characters['mira'].value('hp')), text)
        self.click(self.status.previous_rect)
        self.assertEqual(self.status.character_id, 'caelan')
        self.click(self.status.next_rect)
        self.assertEqual(self.status.character_id, 'mira')
        self.key(pygame.K_TAB)
        self.assertEqual(self.status.selected, 'mp')
        self.assertEqual(self.status.character_id, 'mira')
        self.assertEqual(self.game.party.to_dict(), before)
        self.game.set_active_party.assert_not_called()

    def test_each_character_keeps_own_level_and_exact_exp_with_max_level_display(self):
        for identifier in ('mira', 'lucan', 'rhea', 'edran'):
            self.game.party.recruit(identifier)
        self.set_level('caelan', 5, 123)
        self.set_level('mira', 12, 78)
        self.set_level('rhea', 100)
        self.status.open()
        text = self.texts(self.status.draw)
        self.assertIn('Lv. 5', text)
        self.assertTrue(any(value.startswith('EXP 123 / ') for value in text))
        self.status.select_character('mira')
        text = self.texts(self.status.draw)
        self.assertIn('Lv. 12', text)
        self.assertTrue(any(value.startswith('EXP 78 / ') for value in text))
        self.status.select_character('rhea')
        text = self.texts(self.status.draw)
        self.assertIn('Lv. 100', text)
        self.assertIn('MAX LEVEL', text)
        self.assertFalse(any(value.startswith('EXP ') for value in text))
        self.status.reset()
        self.assertEqual(self.status.character_id, 'caelan')

    def test_party_levels_are_visible_in_active_slots_and_reserve_rows(self):
        for identifier in ('mira', 'lucan', 'rhea', 'edran'):
            self.game.party.recruit(identifier)
        self.set_level('caelan', 9)
        self.set_level('mira', 7)
        self.set_level('edran', 100)
        self.party.open()
        text = self.texts(self.party.draw)
        self.assertEqual(text.count('Lv. 9'), 2)  # Formation and roster.
        self.assertEqual(text.count('Lv. 7'), 2)
        self.party.scroll = self.party.max_scroll
        text = self.texts(self.party.draw)
        self.assertEqual(text.count('Lv. 100'), 1)  # Reserve only.
        self.assertEqual(self.game.party.active_ids, ('caelan', 'mira', 'lucan'))

    def test_progression_controls_and_exp_text_fit_all_supported_text_sizes(self):
        self.game.party.recruit('mira')
        self.set_level('mira', 99, 7897)
        self.status.open();self.status.select_character('mira')
        bounds = pygame.Rect(12, 12, 456, 296)
        for size in ((480, 320), (960, 640)):
            self.game.window = pygame.display.set_mode(size)
            self.game.ui_surface = pygame.Surface(size)
            for scale in (1.0, 1.25, 1.5):
                with self.subTest(size=size, text_scale=scale):
                    self.game.audio.set_text_scale(scale)
                    painter = self.game.ui.painter(self.game.ui_surface)
                    original = Painter.text
                    with patch.object(Painter, 'text', autospec=True, side_effect=original) as spy:
                        self.status.draw(self.game.ui_surface)
                    for call in spy.call_args_list:
                        text = str(call.args[1])
                        if text.startswith(('EXP ', 'Lv. ', 'Q/E:')):
                            point = call.args[2]
                            role = call.kwargs.get('role', 'body')
                            font = painter.font(role, call.kwargs.get('bold', False))
                            rect = pygame.Rect(point, font.size(text))
                            self.assertTrue(bounds.contains(rect), (text, rect))
                    self.assertLess(self.status.xp_bar_rect.bottom, self.status.stat_rects['str'].top)
                    self.assertTrue(bounds.contains(self.status.previous_rect))
                    self.assertTrue(bounds.contains(self.status.next_rect))
                    self.assertEqual(self.game.ui_surface.get_clip(), self.game.ui_surface.get_rect())


if __name__ == '__main__':unittest.main()
