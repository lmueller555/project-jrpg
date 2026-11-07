"""Independent production-menu and real-Continue checks for retired progression."""
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from main import Game
from ui_style import Painter


# Generated from the real pre-removal board using legal moves and activations.
# Only the saved ledger is retained; no graph implementation is needed to load it.
PAID_LEGACY_LEDGER = {
    'version': 2, 'board_id': 'caelan_starter', 'board_version': 3,
    'characters': {'caelan': {
        'rp': 1000000, 'spent_steps': 9, 'position': 'aether_dart_01',
        'visited': ['aether_dart_01', 'blank_01', 'blank_34', 'blank_35',
                    'def_04', 'hp_01', 'hp_04', 'mp_01', 'origin', 'str_01'],
        'activated': ['aether_dart_01', 'hp_01'], 'legacy_activated': []}},
    'receipts': ['legacy:paid'],
}


class ProgressionCleanupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='progression-cleanup-test-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.path = self.directory/'journey.json'
        self.settings = self.directory/'settings.json'

    def tearDown(self):
        pygame.quit()

    def game(self, title=False):
        game = Game(window_size=(960, 640), fullscreen=False,
                    start_on_title=title, save_path=self.path,
                    settings_path=self.settings)
        game.audio.set_music(0)
        game.audio.set_effects(0)
        pygame.event.clear()
        return game

    def key(self, game, value):
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            pygame.event.post(pygame.event.Event(kind, key=value, repeat=False))
        self.assertTrue(game.handle_events())

    def labels(self, game):
        labels = []
        original = Painter.text
        def text(painter, value, *args, **kwargs):
            labels.append(str(value))
            return original(painter, value, *args, **kwargs)
        with patch.object(Painter, 'text', text):
            game.draw()
        return labels

    def test_pause_and_character_screen_expose_no_retired_progression(self):
        game = self.game()
        game.opening.restore({'version': 1, 'stage': 'disabled'})
        for field in ('lattice', 'lattice_progression', 'lattice_ui'):
            self.assertFalse(hasattr(game, field))
        self.key(game, pygame.K_ESCAPE)
        self.assertTrue(game.pause.is_open)
        self.assertEqual(game.pause.options,
                         ('Resume', 'Characters', 'Party', 'Inventory',
                          'Journal', 'Map', 'Settings', 'Quit'))
        menu = self.labels(game)
        self.key(game, pygame.K_DOWN)
        self.key(game, pygame.K_RETURN)
        self.assertTrue(game.status_ui.is_open)
        status = self.labels(game)
        self.assertIn('Characters', status)
        self.assertIn('Caelan', status)
        content = ' '.join(menu+status).lower()
        for term in ('lattice', 'attunement', 'resonance points'):
            self.assertNotIn(term, content)
        self.assertNotIn('rp', content.split())

    def test_real_continue_preserves_paid_effective_stats_skills_and_receipts_once(self):
        game = self.game()
        game.social.flags.add('progression_cleanup_preserved')
        self.assertTrue(game.inventory.add('aether_diamond', 2))
        self.assertTrue(game.save_progress())
        legacy = json.loads(self.path.read_text())
        legacy['aether_lattice'] = deepcopy(PAID_LEGACY_LEDGER)
        attributes = legacy['character_attributes']
        attributes.update(current_hp=220, current_mp=7)
        legacy['party']['characters']['caelan'] = deepcopy(attributes)
        raw = json.dumps(legacy)
        self.path.write_text(raw)

        restored = self.game(title=True)
        self.assertTrue(restored.has_saved_journey)
        self.assertEqual(self.path.read_text(), raw)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.attributes.value('hp'), 240)
        self.assertEqual((restored.attributes.current_hp, restored.attributes.current_mp),
                         (220, 7))
        self.assertIn('aether_dart', restored.character_abilities.known_abilities())
        self.assertTrue(restored.battle_rewards.has_receipt('legacy:paid'))
        self.assertEqual(restored.inventory.to_dict(), legacy['inventory'])
        self.assertEqual(restored.quests.to_dict(), legacy['quests'])
        self.assertIn('progression_cleanup_preserved', restored.social.flags)
        migrated = json.loads(self.path.read_text())
        self.assertNotIn('aether_lattice', migrated)
        self.assertEqual(migrated['party']['characters']['caelan'],
                         migrated['character_attributes'])

        again = self.game(title=True)
        self.assertTrue(again.has_saved_journey)
        self.assertTrue(again.begin_journey(True))
        self.assertEqual(again.attributes.value('hp'), 240)
        self.assertEqual(again.attributes.current_hp, 220)
        self.assertEqual(again.inventory.to_dict(), legacy['inventory'])
        self.assertEqual(again.battle_rewards.to_dict(), restored.battle_rewards.to_dict())
        self.assertIn('aether_dart', again.character_abilities.known_abilities())

    def test_old_pending_and_awarded_spoils_continue_without_lost_or_duplicate_items(self):
        for awarded in (False, True):
            with self.subTest(awarded=awarded):
                self.path.unlink(missing_ok=True)
                game = self.game()
                game.opening.restore({'version': 1, 'stage': 'disabled'})
                attributes = game.attributes.to_dict()
                attributes['attributes']['hp'] = 240
                attributes.update(current_hp=220, current_mp=7)
                self.assertTrue(game.attributes.restore(attributes))
                game.world = game.town
                game.player.position.update(game.combat.position+(0, 24))
                game.player.facing = 'back'
                game.camera.reset()
                game.opening_fade = game.transfer_cooldown = 0
                self.assertTrue(game.combat.interact(rng=random.Random(7)))
                model = game.combat.model
                for _ in range(5000):
                    if model.ended:break
                    if model.waiting_for_player:
                        self.assertTrue(model.choose_action('attack'))
                    else:game.update(.1, (0, 0), False)
                self.assertEqual(model.phase, 'victory')
                self.assertEqual(game.combat.post_phase, 'banner')
                if awarded:
                    for _ in range(200):
                        if (game.combat.post_phase == 'spoils'
                                and game.combat.spoils.awarded):break
                        game.update(.1, (0, 0), False)
                    self.assertTrue(game.combat.spoils.awarded)
                self.assertTrue(game.save_progress())
                legacy = json.loads(self.path.read_text())
                legacy['aether_lattice'] = deepcopy(PAID_LEGACY_LEDGER)
                receipt = legacy['post_battle']['receipt']
                if awarded:
                    legacy['aether_lattice']['receipts'].append(receipt)
                legacy.pop('battle_rewards')
                legacy['post_battle']['rewards']['rp'] = 20
                legacy['character_attributes']['attributes']['hp'] = 140
                legacy['party']['characters']['caelan'] = deepcopy(legacy['character_attributes'])
                old_inventory = legacy['inventory']
                self.path.write_text(json.dumps(legacy))
                before_title = self.path.read_bytes()
                resumed = self.game(title=True)
                self.assertTrue(resumed.has_saved_journey)
                self.assertEqual(self.path.read_bytes(), before_title)
                self.assertTrue(resumed.begin_journey(True))
                self.assertEqual(resumed.combat.post_phase, 'spoils')
                self.assertTrue(resumed.combat.spoils.awarded)
                self.assertEqual(resumed.inventory.quantity('aether_emerald'), 1)
                self.assertTrue(resumed.battle_rewards.has_receipt(receipt))
                self.assertTrue(resumed.battle_rewards.has_receipt('legacy:paid'))
                self.assertEqual(resumed.attributes.value('hp'), 240)
                self.assertIn('aether_dart', resumed.character_abilities.known_abilities())
                self.assertEqual(set(resumed.combat.snapshot()['rewards']), {'drops'})
                if awarded:self.assertEqual(resumed.inventory.to_dict(), old_inventory)
                for _ in range(10):resumed.update(.5, (0, 0), False)
                self.assertEqual(resumed.inventory.quantity('aether_emerald'), 1)


if __name__ == '__main__':
    unittest.main()
