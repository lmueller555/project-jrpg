"""Settled gearblade focus survives saves without changing unlock history."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from character_abilities import CharacterAbilities
from gear_state import GEM_ORDER
from inventory import Inventory


class GearPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.inventory = Inventory()
        self.owner = CharacterAbilities(self.inventory)

    def snapshot(self):
        return (self.owner.to_dict(), self.inventory.to_dict())

    def test_water_default_preserves_the_legacy_version_one_representation(self):
        legacy = self.owner.to_dict()
        self.assertEqual(set(legacy), {'version', 'characters'})
        self.assertEqual(self.owner.active_gem(), 'water')
        self.assertTrue(self.owner.set_active_gem('fire'))
        self.assertTrue(self.owner.restore(legacy))
        self.assertEqual(self.owner.active_gem(), 'water')
        self.assertEqual(self.owner.to_dict(), legacy)
        self.assertTrue(self.owner.set_active_gem('ice'))
        self.assertTrue(self.owner.restore(None))
        self.assertEqual(self.owner.active_gem(), 'water')
        self.assertEqual(self.owner.to_dict(), legacy)

    def test_each_settled_focus_round_trips_without_transient_state(self):
        for gem in GEM_ORDER:
            with self.subTest(gem=gem):
                self.assertTrue(self.owner.set_active_gem(gem))
                saved = json.loads(json.dumps(self.owner.to_dict()))
                other = CharacterAbilities(self.inventory)
                self.assertTrue(other.restore(saved))
                self.assertEqual(other.active_gem(), gem)
                self.assertEqual(other.to_dict(), saved)
                self.assertEqual(saved.get('gear_focus', {}),
                                 {} if gem == 'water' else {'caelan': gem})
                self.assertEqual(other.known_abilities(), frozenset({'basic_magicks'}))

    def test_invalid_setters_leave_all_owners_unchanged(self):
        self.assertTrue(self.owner.set_active_gem('fire'))
        before = self.snapshot()
        for gem in (None, True, 0, [], {}, 'Fire', 'lightning', float('nan')):
            with self.subTest(gem=gem):
                self.assertFalse(self.owner.set_active_gem(gem))
                self.assertEqual(self.snapshot(), before)
        for character in (None, True, [], {}, 'missing', 'mira', 'lucan'):
            with self.subTest(character=character):
                self.assertIsNone(self.owner.active_gem(character))
                self.assertFalse(self.owner.set_active_gem('ice', character))
                self.assertEqual(self.snapshot(), before)

    def test_invalid_focus_snapshots_reject_atomically_with_pending_training(self):
        self.assertTrue(self.owner.acquire_weapon('caelan', 'caelan_gearblade',
                                                  learn_starter=False))
        self.assertTrue(self.owner.set_active_gem('nature'))
        saved = self.owner.to_dict()
        before = self.snapshot()
        invalid = (None, True, [], 'fire', {'mira': 'fire'}, {'missing': 'water'},
                   {'caelan': None}, {'caelan': []}, {'caelan': True},
                   {'caelan': 'lightning'}, {'caelan': 'Water'},
                   {'caelan': {'gem': 'fire', 'angle': 90}},
                   {'caelan': 'fire', 'hover': True})
        for focus in invalid:
            with self.subTest(focus=focus):
                bad = deepcopy(saved)
                bad['gear_focus'] = focus
                self.assertFalse(self.owner.restore(bad))
                self.assertEqual(self.snapshot(), before)
                self.assertTrue(self.owner.starter_skills_pending())

    def test_focus_preserves_deferred_lesson_and_earned_unequipped_knowledge(self):
        self.assertTrue(self.owner.acquire_weapon('caelan', 'caelan_gearblade',
                                                  learn_starter=False))
        self.assertTrue(self.owner.set_active_gem('ice'))
        saved = self.owner.to_dict()
        other = CharacterAbilities(self.inventory)
        self.assertTrue(other.restore(saved))
        self.assertTrue(other.starter_skills_pending())
        self.assertEqual(other.known_abilities(), frozenset({'basic_magicks'}))
        self.assertTrue(other.equip_weapon('caelan', None))
        self.assertEqual(other.active_gem(), 'ice')
        self.assertTrue(other.equip_weapon('caelan', 'caelan_gearblade'))
        self.assertTrue(other.learn_first_weapon_skills())
        self.assertTrue(other.set_active_gem('nature'))
        self.assertTrue(other.equip_weapon('caelan', None))
        earned = other.to_dict()
        self.assertNotIn('deferred_weapon_training', earned)
        self.assertTrue(self.owner.restore(earned))
        self.assertEqual(self.owner.active_gem(), 'nature')
        self.assertFalse(self.owner.has_weapon())
        self.assertEqual(self.owner.known_abilities(),
                         frozenset({'basic_magicks', 'aether_edge'}))
        self.assertEqual(self.inventory.quantity('caelan_gearblade'), 1)

    def test_focus_save_is_detached_and_validated_with_the_whole_journey(self):
        self.assertTrue(self.owner.set_active_gem('fire'))
        journey = {'inventory': self.inventory.to_dict(),
                   'character_abilities': self.owner.to_dict()}
        self.assertTrue(CharacterAbilities.valid_journey(journey))
        journey['character_abilities']['gear_focus']['caelan'] = 'missing'
        self.assertFalse(CharacterAbilities.valid_journey(journey))
        self.assertEqual(self.owner.active_gem(), 'fire')


class GearPersistenceGameplayTests(unittest.TestCase):
    def test_saved_focus_reaches_new_encounters_and_resumed_victory(self):
        import pygame
        from main import Game
        from test_mill_battle_gameplay import seed_completed_mill

        self.addCleanup(pygame.quit)
        with tempfile.TemporaryDirectory(prefix='gear-persistence-') as directory:
            path = Path(directory)/'journey.json'

            def new_game(title=False):
                game = Game(window_size=(960, 640), fullscreen=False,
                            start_on_title=title, save_path=path,
                            settings_path=Path(directory)/'settings.json')
                game.audio.set_music(0)
                game.audio.set_effects(0)
                pygame.event.clear()
                return game

            game = new_game()
            seed_completed_mill(game)
            self.assertTrue(game.acquire_weapon('caelan', 'caelan_gearblade'))
            self.assertTrue(game.character_abilities.set_active_gem('fire'))
            self.assertTrue(game.save_progress())
            self.assertEqual(json.loads(path.read_text())['character_abilities']['gear_focus'],
                             {'caelan': 'fire'})
            restored = new_game(True)
            self.assertTrue(restored.begin_journey(True))
            restored.opening_fade = restored.transfer_cooldown = 0
            self.assertEqual(restored.character_abilities.active_gem(), 'fire')
            restored.player.position.update(restored.combat.position+(0, 24))
            restored.player.facing = 'back'
            restored.camera.reset()
            self.assertTrue(restored.combat.interact())
            self.assertEqual(restored.combat.model.active_gem, 'fire')
            while restored.combat.transitioning:
                restored.update(.1, (0, 0), False)
            restored.combat.model.enemy.hp = 0
            restored.combat.model._result('victory')
            restored.update(0, (0, 0), False)
            self.assertEqual(restored.combat.post_phase, 'banner')
            resumed = new_game(True)
            self.assertTrue(resumed.begin_journey(True))
            self.assertTrue(resumed.combat.active)
            self.assertEqual(resumed.combat.model.active_gem, 'fire')
            self.assertIn('aether_edge', resumed.character_abilities.known_abilities())


if __name__ == '__main__':
    unittest.main()
