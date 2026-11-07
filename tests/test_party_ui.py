"""Party editing is transactional, accessible and constrained by story state."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from audio_settings import AudioSettings
from character_attributes import CharacterAttributes
from party_state import PartyState
from party_ui import PartyUI
from pause_menu import PauseMenu
from ui_style import UIStyle


class PartyUITests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        self.game = SimpleNamespace(window=pygame.display.set_mode((960, 640)),
            audio=AudioSettings(), attributes=CharacterAttributes(),
            ui_surface=pygame.Surface((960, 640)), _mouse_held=False)
        self.game.audio.set_effects(0)
        self.game.ui = UIStyle(self.game)
        self.game.party = PartyState(self.game.attributes)
        self.game.set_active_party = Mock(side_effect=self.game.party.select)
        self.screen = self.game.party_ui = PartyUI(self.game)
        self.pause = PauseMenu(self.game)
        self.game.to_canvas = self.pause.to_canvas

    def tearDown(self):pygame.quit()

    def key(self, key, **extra):
        return self.screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, **extra))

    def click(self, logical):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        point = ((width-480*scale)//2+logical[0]*scale,
                 (height-320*scale)//2+logical[1]*scale)
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point))

    def recruit(self, *identifiers):
        for identifier in identifiers:self.assertTrue(self.game.party.recruit(identifier))

    def test_only_recruited_companions_appear_and_resources_are_unchanged(self):
        self.recruit('mira')
        self.game.party.characters['mira'].set_current(hp=8, mp=2)
        before = self.game.party.to_dict()
        self.screen.open();self.screen.draw(self.game.ui_surface)
        self.assertEqual(self.screen.roster, ('caelan', 'mira'))
        self.assertEqual(set(self.screen.roster_rects), {'caelan', 'mira'})
        self.assertEqual(self.screen._status('caelan')[0], 'Required')
        self.assertEqual(self.screen._status('mira')[0], 'Active')
        self.screen.close()
        self.assertEqual(self.game.party.to_dict(), before)

    def test_keyboard_selects_and_confirms_once_without_healing(self):
        self.recruit('mira', 'lucan', 'rhea')
        self.game.party.select(('caelan',))
        self.game.party.characters['mira'].set_current(hp=9, mp=3)
        confirmed = Mock()
        self.screen.open(prompt='Choose your party', on_confirm=confirmed)
        self.key(pygame.K_RETURN)  # Choose a replacement for the second slot.
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN)
        self.assertEqual(self.screen.formation, ('caelan', 'mira'))
        self.assertEqual(self.game.party.active_ids, ('caelan',))
        self.key(pygame.K_TAB);self.key(pygame.K_TAB);self.key(pygame.K_RETURN)
        self.assertEqual(self.game.party.active_ids, ('caelan', 'mira'))
        self.assertFalse(self.screen.is_open)
        self.game.set_active_party.assert_called_once_with(('caelan', 'mira'))
        confirmed.assert_called_once_with()
        self.assertEqual(self.game.party.characters['mira'].current_hp, 9)
        self.assertEqual(self.game.party.characters['mira'].current_mp, 3)

    def test_mouse_scrolls_long_reason_without_changing_the_roster_position(self):
        self.recruit('mira')
        self.game.audio.set_text_scale(1.5)
        self.game.party.set_available('mira', False, 'Mira is repairing the mill machinery. '*6)
        self.screen.open();self.screen.selected_member = 1
        self.screen.draw(self.game.ui_surface)
        self.assertGreater(self.screen.detail_max_scroll, 0)
        roster_scroll = self.screen.scroll
        self.click(self.screen.detail_down.center)
        self.assertGreater(self.screen.detail_scroll, 0)
        self.assertEqual(self.screen.scroll, roster_scroll)
        self.click(self.screen.detail_up.center)
        self.assertEqual(self.screen.detail_scroll, 0)

    def test_mouse_can_swap_active_slots_and_replace_at_the_three_member_limit(self):
        self.recruit('mira', 'lucan', 'rhea')
        self.screen.open();self.screen.draw(self.game.ui_surface)
        self.click(self.screen.slot_rects[2].center)
        self.click(self.screen.roster_rects['mira'].center)
        self.assertEqual(self.screen.formation, ('caelan', 'lucan', 'mira'))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-10))
        self.screen.draw(self.game.ui_surface)
        self.click(self.screen.roster_rects['rhea'].center)
        self.assertEqual(self.screen.formation, ('caelan', 'lucan', 'rhea'))
        self.assertEqual(self.game.party.active_ids, ('caelan', 'mira', 'lucan'))
        self.click(self.screen.confirm_rect.center)
        self.assertEqual(self.game.party.active_ids, ('caelan', 'lucan', 'rhea'))

    def test_clear_and_cancel_discard_draft_and_invoke_only_cancel_callback(self):
        self.recruit('mira')
        before = self.game.party.to_dict()
        cancelled, confirmed = Mock(), Mock()
        self.screen.open(on_cancel=cancelled, on_confirm=confirmed)
        self.screen.selected_slot = 1
        self.key(pygame.K_DELETE)
        self.assertEqual(self.screen.formation, ('caelan',))
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.game.party.to_dict(), before)
        self.game.set_active_party.assert_not_called()
        cancelled.assert_called_once_with();confirmed.assert_not_called()

    def test_required_members_cannot_be_removed_but_can_swap_other_active_slots(self):
        self.recruit('mira', 'lucan', 'rhea')
        self.game.party.begin_event('mill', required=('mira',), reason='Mira must repair the machinery.')
        self.screen.open();self.screen.selected_slot = 1
        self.assertFalse(self.screen.clear_slot())
        self.assertIn('Mira', self.screen.message)
        self.assertFalse(self.screen.choose_member('rhea'))
        self.assertIn('Mira', self.screen.message)
        self.assertTrue(self.screen.choose_member('lucan'))
        self.assertEqual(self.screen.formation, ('caelan', 'lucan', 'mira'))
        self.screen.selected_slot = 0
        self.assertFalse(self.screen.choose_member('lucan'))
        self.assertEqual(self.screen.formation[0], 'caelan')

    def test_unavailable_companion_is_inspectable_and_reason_scrolls_at_large_text(self):
        self.recruit('mira')
        reason = ('Mira is repairing the mill machinery and cannot leave the workshop until '
                  'the damaged pressure regulator, waterwheel gears, and control console '
                  'have been repaired. Return after the restoration is complete.')
        self.assertTrue(self.game.party.set_available('mira', False, reason))
        self.game.audio.set_text_scale(1.5)
        self.game.window = pygame.display.set_mode((480, 320))
        self.game.ui_surface = pygame.Surface((480, 320))
        self.screen.open();self.screen.selected_member = 1
        self.screen.draw(self.game.ui_surface)
        self.assertEqual(self.screen._status('mira')[0], 'Unavailable')
        self.assertIn(reason, self.screen._detail)
        self.assertGreater(self.screen.detail_max_scroll, 0)
        self.assertFalse(self.screen.choose_member('mira'))
        self.key(pygame.K_END)
        self.assertEqual(self.screen.detail_scroll, self.screen.detail_max_scroll)
        lines, height = self.screen._detail_lines(self.game.ui.painter(self.game.ui_surface))
        self.assertLessEqual(len(lines)*height-self.screen.detail_scroll, self.screen.detail_view.height)
        self.assertEqual(self.game.party.active_ids, ('caelan',))

    def test_selection_gate_explains_the_future_lock_before_confirmation(self):
        self.recruit('mira')
        self.assertTrue(self.game.party.begin_event('boss',required=('mira',),
            selection_pending=True,selection_title='Choose your party',lock_after=True))
        self.screen.open(prompt='Choose your party')
        self.screen.draw(self.game.ui_surface)
        self.assertIn('Confirm locks this party',self.screen._detail)
        self.assertFalse(self.game.party.locked)
        self.assertTrue(self.game.party.pending_selection)

    def test_locked_event_can_be_inspected_and_closed_without_changes(self):
        self.recruit('mira', 'lucan')
        self.game.party.begin_event('boss', locked=True, reason='The battle formation is fixed inside the arena.')
        before = self.game.party.to_dict()
        self.screen.open();self.screen.selected_slot = 2
        self.assertFalse(self.screen.clear_slot())
        self.assertFalse(self.screen.choose_member('mira'))
        self.assertFalse(self.screen.confirm())
        self.assertIn('arena', self.screen.message)
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.game.party.to_dict(), before)
        self.game.set_active_party.assert_not_called()

    def test_failed_save_keeps_draft_open_and_does_not_call_success_callback(self):
        self.recruit('mira')
        self.game.set_active_party = Mock(return_value=False)
        self.game.save_error = 'Could not write the save file.'
        callback = Mock()
        self.screen.open(on_confirm=callback);self.screen.selected_slot = 1
        self.screen.clear_slot()
        self.assertFalse(self.screen.confirm())
        self.assertTrue(self.screen.is_open)
        self.assertEqual(self.screen.formation, ('caelan',))
        self.assertEqual(self.game.party.active_ids, ('caelan', 'mira'))
        self.assertIn('save file', self.screen.message)
        callback.assert_not_called()

    def test_all_roster_entries_and_buttons_are_reachable_at_minimum_size(self):
        self.recruit('mira', 'lucan', 'rhea', 'edran')
        self.game.audio.set_text_scale(1.5)
        self.game.window = pygame.display.set_mode((480, 320))
        self.game.ui_surface = pygame.Surface((480, 320))
        self.screen.open();self.key(pygame.K_TAB)
        for _ in range(4):self.key(pygame.K_DOWN)
        self.screen.draw(self.game.ui_surface)
        self.assertEqual(self.screen.roster[self.screen.selected_member], 'edran')
        self.assertTrue(self.screen.roster_view.contains(self.screen.roster_rects['edran']))
        self.assertGreater(self.screen.scroll, 0)
        self.key(pygame.K_TAB)
        self.assertEqual(self.screen.focus, 'buttons')
        self.assertEqual(self.screen.selected_button, 2)
        for rect in (self.screen.confirm_rect, self.screen.cancel_rect, self.screen.clear_rect):
            self.assertTrue(self.screen.panel.contains(rect))
        self.assertLessEqual(self.screen.slot_rects[-1].bottom, self.screen.detail_view.top)
        self.assertLessEqual(self.screen.detail_view.bottom, self.screen.confirm_rect.top)

    def test_resize_and_text_scale_keep_selected_companion_visible(self):
        self.recruit('mira', 'lucan', 'rhea', 'edran')
        self.screen.open();self.key(pygame.K_TAB)
        for _ in range(3):self.key(pygame.K_DOWN)
        self.screen.draw(self.game.ui_surface)
        self.assertEqual(self.screen.roster[self.screen.selected_member], 'rhea')
        self.game.window = pygame.display.set_mode((480, 320))
        self.game.ui_surface = pygame.Surface((480, 320))
        self.game.audio.set_text_scale(1.5)
        self.screen.draw(self.game.ui_surface)
        self.assertTrue(self.screen.roster_view.contains(self.screen.roster_rects['rhea']))
        self.screen.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=20, pos=(300, 100)))
        self.screen.draw(self.game.ui_surface)
        self.assertEqual(self.screen.scroll, 0)
        self.assertFalse(self.screen.roster_view.contains(self.screen.roster_rects['rhea']))

    def test_pause_party_overlay_routes_input_then_returns_to_pause(self):
        self.pause.open()
        self.pause.selected = self.pause.options.index('Party')
        self.pause.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(self.pause.overlay, 'party')
        self.assertTrue(self.screen.is_open)
        self.pause.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertFalse(self.screen.is_open)
        self.assertIsNone(self.pause.overlay)
        self.assertTrue(self.pause.is_open)


if __name__ == '__main__':unittest.main()
