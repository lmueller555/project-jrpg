"""Attribute checkpoints, legacy journeys and fresh-game isolation."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import main
from character_attributes import CharacterAttributes
from quests import OPENING_QUEST


class CharacterAttributesGameplayTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name)/'journey.json'

    def tearDown(self):
        pygame.quit()

    def game(self, title=False):
        game = main.Game(fullscreen=False, start_on_title=title, save_path=self.path)
        game.audio.set_music(0)
        game.audio.set_effects(0)
        pygame.event.clear()
        return game

    def test_new_game_has_balanced_full_resources_and_checkpoints_attributes(self):
        game = self.game(title=True)
        self.assertTrue(game.begin_journey())
        expected = CharacterAttributes('caelan').to_dict()
        self.assertEqual(game.attributes.to_dict(), expected)
        self.assertEqual(expected['attributes']['hp'], 140)
        self.assertEqual(expected['attributes']['mp'], 30)
        self.assertEqual({value for key, value in expected['attributes'].items()
                          if key not in ('hp', 'mp')}, {10})
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['character_attributes'], expected)
        self.assertEqual(game.opening.stage, 'wake')
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')

    def test_continue_restores_attributes_and_depleted_resources_without_mutating_title(self):
        game = self.game()
        self.assertTrue(game.accept_quest(OPENING_QUEST))
        game.social.flags.add('attribute_round_trip')
        attributes = game.attributes.to_dict()
        attributes['attributes'].update(mag=13, spr=17)
        attributes.update(current_hp=113, current_mp=17)
        self.assertTrue(game.attributes.restore(attributes))
        self.assertTrue(game.save_progress())
        saved = json.loads(self.path.read_text())
        restored = self.game(title=True)
        self.assertTrue(restored.has_saved_journey)
        self.assertEqual(restored.attributes.to_dict(), CharacterAttributes('caelan').to_dict())
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.attributes.to_dict(), attributes)
        self.assertEqual(restored.quests.to_dict(), saved['quests'])
        self.assertEqual(restored.inventory.to_dict(), saved['inventory'])
        self.assertIn('attribute_round_trip', restored.social.flags)

    def test_legacy_continue_initializes_baseline_and_preserves_story_progress(self):
        game = self.game()
        self.assertTrue(game.accept_quest(OPENING_QUEST))
        game.social.flags.add('legacy_attribute_test')
        self.assertTrue(game.save_progress())
        legacy = json.loads(self.path.read_text())
        legacy.pop('character_attributes')
        self.path.write_text(json.dumps(legacy))
        restored = self.game(title=True)
        self.assertTrue(restored.attributes.set_current(hp=1, mp=0))
        self.assertTrue(restored.begin_journey(True))
        expected = CharacterAttributes('caelan').to_dict()
        self.assertEqual(restored.attributes.to_dict(), expected)
        self.assertEqual(restored.quests.to_dict(), legacy['quests'])
        self.assertEqual(restored.inventory.to_dict(), legacy['inventory'])
        self.assertEqual(sorted(restored.social.flags), legacy['dialogue_flags'])
        self.assertEqual(json.loads(self.path.read_text())['character_attributes'], expected)
        self.assertIsNone(restored.quest_ui.current_notice)

    def test_invalid_attribute_record_rejects_continue_without_overwriting_save(self):
        game = self.game()
        self.assertTrue(game.save_progress())
        original = json.loads(self.path.read_text())
        cases = []
        malformed = copy.deepcopy(original)
        malformed['character_attributes']['attributes'].pop('spr')
        cases.append(malformed)
        malformed = copy.deepcopy(original)
        malformed['character_attributes']['current_mp'] = 31
        cases.append(malformed)
        for malformed in cases:
            with self.subTest(record=malformed['character_attributes']):
                raw = json.dumps(malformed)
                self.path.write_text(raw)
                restored = self.game(title=True)
                self.assertFalse(restored.has_saved_journey)
                self.assertIsNotNone(restored.save_error)
                self.assertFalse(restored.begin_journey(True))
                self.assertEqual(self.path.read_text(), raw)
                self.assertEqual(restored.attributes.to_dict(), CharacterAttributes('caelan').to_dict())

    def test_new_game_resets_saved_growth_and_current_resources(self):
        game = self.game()
        attributes = game.attributes.to_dict()
        attributes['attributes'].update(hp=400, mp=50, spr=20)
        attributes.update(current_hp=0, current_mp=0)
        self.assertTrue(game.attributes.restore(attributes))
        self.assertTrue(game.save_progress())
        self.assertTrue(game.begin_journey(True))
        self.assertEqual(game.attributes.current_hp, 0)
        self.assertEqual(game.attributes.value('spr'), 20)
        self.assertTrue(game.begin_journey())
        self.assertEqual(game.attributes.to_dict(), CharacterAttributes('caelan').to_dict())
        self.assertEqual(game.opening.stage, 'wake')
        self.assertEqual(game.quests.status(OPENING_QUEST), 'available')

    def test_attribute_resource_change_participates_in_automatic_checkpoint(self):
        game = self.game()
        self.assertTrue(game.save_progress())
        before = game._progress_signature()
        self.assertTrue(game.attributes.set_current(hp=125, mp=21))
        self.assertNotEqual(game._progress_signature(), before)
        game.update(0, (0, 0), False)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['character_attributes']['current_hp'], 125)
        self.assertEqual(saved['character_attributes']['current_mp'], 21)

    def test_original_300_hp_save_rebalances_only_when_continued(self):
        game = self.game()
        self.assertTrue(game.accept_quest(OPENING_QUEST))
        game.social.flags.add('health_rebalance')
        self.assertTrue(game.save_progress())
        original = json.loads(self.path.read_text())
        record = original['character_attributes']
        record.update(version=1, current_hp=150, current_mp=12)
        record['attributes'].update(hp=300, mag=13, spr=17)
        raw = json.dumps(original)
        self.path.write_text(raw)
        restored = self.game(title=True)
        self.assertTrue(restored.has_saved_journey)
        self.assertEqual(self.path.read_text(), raw)
        self.assertEqual(restored.attributes.value('hp'), 140)
        self.assertEqual(restored.attributes.current_hp, 140)
        self.assertTrue(restored.begin_journey(True))
        self.assertEqual(restored.attributes.value('hp'), 140)
        self.assertEqual(restored.attributes.current_hp, 70)
        self.assertEqual(restored.attributes.current_mp, 12)
        self.assertEqual(restored.attributes.value('mag'), 13)
        self.assertEqual(restored.attributes.value('spr'), 17)
        self.assertEqual(restored.quests.to_dict(), original['quests'])
        self.assertEqual(restored.inventory.to_dict(), original['inventory'])
        self.assertEqual(sorted(restored.social.flags), original['dialogue_flags'])
        migrated = json.loads(self.path.read_text())['character_attributes']
        self.assertEqual(migrated['version'], 3)
        second = self.game(title=True)
        self.assertTrue(second.begin_journey(True))
        self.assertEqual(second.attributes.to_dict(), migrated)


if __name__ == '__main__':
    unittest.main()
