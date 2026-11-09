"""Actual Game input retains an acknowledged gem seating and accessible prose."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from main import Game
from ui_style import Painter


class ElementalFocusPresentationTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(fullscreen=False, start_on_title=True, save_path=None, settings_path=None)
        self.addCleanup(pygame.quit)
        self.game.on_title = False
        self.game.opening.stage = 'done'
        self.game.opening_fade = self.game.transfer_cooldown = 0
        self.game.audio.set_music(0);self.game.audio.set_effects(0)
        self.assertTrue(self.game.character_abilities.acquire_weapon('caelan', 'caelan_gearblade'))
        self.assertTrue(self.game.character_abilities.grant_gem('fire'))
        self.assertTrue(self.game.character_abilities.learn_ability('caelan', 'flame_edge'))
        self.owner = self.game.elemental_bosses
        state = self.owner.to_dict()
        state['bosses']['embravyr'].update(discovered=True, intro_seen=True,
                                          defeated=True, pending_acquisition=True)
        state['victory_order'] = ['embravyr']
        self.assertTrue(self.owner.restore(state))

    def key(self, value):
        self.assertTrue(self.game.handle_events([
            pygame.event.Event(pygame.KEYDOWN, key=value, repeat=False),
            pygame.event.Event(pygame.KEYUP, key=value)]))

    def read_all(self):
        for _ in range(40):
            if not self.game.social.active:return
            self.key(pygame.K_SPACE)
        self.fail('The focus dialogue did not finish')

    def test_native_installation_and_labels_fit_above_measured_prose_at_both_text_sizes(self):
        self.assertTrue(self.owner._present_acquisition())
        self.game.draw()
        for text_scale in (1, 1.5):
            with self.subTest(text_scale=text_scale):
                self.game.audio.text_scale = text_scale
                self.game.social.refresh_layout()
                for _ in range(40):
                    self.game.draw()
                    recorded = []
                    original = Painter.text

                    def text(painter, label, *args, **kwargs):
                        bounds = original(painter, label, *args, **kwargs)
                        recorded.append((label, bounds))
                        return bounds

                    with patch.object(Painter, 'text', text):
                        panel = self.owner.draw_ui(self.game.ui_surface)
                    prose = self.game.social.bubble.layout().panel
                    self.assertFalse(panel.colliderect(prose), (panel, prose))
                    for label, bounds in recorded:
                        self.assertTrue(panel.contains(bounds), (label, bounds, panel))
                    if self.game.social.page_index == len(self.game.social.pages)-1:break
                    self.key(pygame.K_SPACE)
                self.assertTrue(self.game.social.active)
                # Rewind reading only to examine layout at another text scale;
                # no gameplay progression or animation clock is modified.
                self.game.social.page_index = 0

    def test_fast_acknowledgment_cannot_skip_the_seat_or_activate_world_inputs(self):
        self.assertTrue(self.owner._present_acquisition())
        before = tuple(self.game.player.position)
        self.read_all()
        self.assertTrue(self.owner.acquisition_active)
        self.assertTrue(self.owner.locks_player)
        self.assertTrue(self.owner.bosses['embravyr']['pending_acquisition'])
        self.key(pygame.K_i)
        self.assertFalse(self.game.inventory_ui.is_open)
        self.game.update(.5, (1, 0), False)
        self.assertEqual(tuple(self.game.player.position), before)
        self.assertTrue(self.owner.acquisition_active)
        self.game.update(.6, (1, 0), False)
        self.assertEqual(tuple(self.game.player.position), before)
        self.assertFalse(self.owner.acquisition_active)
        self.assertFalse(self.owner.bosses['embravyr']['pending_acquisition'])
        self.assertIn('fire', self.game.character_abilities.owned_gems())
        self.assertIn('flame_edge', self.game.character_abilities.known_abilities())

    def test_failed_presentation_checkpoint_requeues_without_granting_again(self):
        self.assertTrue(self.owner._present_acquisition())
        self.read_all()
        before = self.game.inventory.to_dict(), self.game.character_abilities.to_dict()
        with patch.object(self.owner, '_checkpoint', return_value=False):
            self.game.update(1.2, (0, 0), False)
        self.assertFalse(self.owner.acquisition_active)
        self.assertTrue(self.owner.bosses['embravyr']['pending_acquisition'])
        self.assertEqual((self.game.inventory.to_dict(), self.game.character_abilities.to_dict()), before)
        self.assertTrue(self.owner._present_acquisition())


if __name__ == '__main__':unittest.main()
