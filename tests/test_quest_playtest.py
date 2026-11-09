"""Quest starts use real controllers without reading or writing a journey."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from pathlib import Path
import tempfile
import unittest

import pygame

from main import Game
from mill_quest import MillQuest
from regent_arrival import RegentArrival
from regent_quest import RegentQuest
from lantern_quest import LanternQuest
from quests import QuestLog
from quest_playtest import QUEST_ORDER, prepare_quest, quest_entries


class QuestPlaytestStarts(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.display.set_mode((960, 640))
        self.games = []

    def tearDown(self):
        for game in self.games:
            game.regent_arrival.reset()
            game.music.stop()
        pygame.quit()

    def game(self, **kwargs):
        game = Game(fullscreen=False, start_on_title=False,
                    _preview_window=pygame.Surface((960, 600)),
                    _quest_playtest=True, **kwargs)
        game.audio.set_music(0)
        game.audio.set_effects(0)
        self.games.append(game)
        return game

    def test_catalogue_covers_all_registered_quests_without_duplicate_titles(self):
        quests = QuestLog()
        entries = quest_entries(quests)
        self.assertEqual(tuple(entry.id for entry in entries), tuple(quests.definitions))
        self.assertEqual([entry.name for entry in entries],
                         [record['title'] for record in quests.definitions.values()])
        self.assertIn('In development', entries[2].chapter)
        self.assertIn('test-only', entries[3].description)

    def test_all_starts_are_available_before_acceptance_with_consistent_controllers(self):
        for index, identifier in enumerate(QUEST_ORDER):
            with self.subTest(quest=identifier):
                game = self.game()
                prepare_quest(game, identifier)
                self.assertFalse(game._is_gallery_preview)
                self.assertTrue(game._is_quest_playtest)
                self.assertFalse(game.save_store.enabled)
                self.assertFalse(game.audio.store.enabled)
                self.assertFalse(game.has_saved_journey)
                self.assertTrue(game.world.can_stand(game.player.position))
                self.assertEqual(game.quests.states[identifier]['completed_objectives'], [])
                for other_index, other in enumerate(QUEST_ORDER):
                    self.assertEqual(game.quests.status(other),
                                     'completed' if other_index < index else
                                     'available' if other_index == index else 'locked')
                snapshot = {'quests': game.quests.to_dict(),
                            'mill_quest': game.mill_quest.to_dict(),
                            'regent_arrival': game.regent_arrival.to_dict(),
                            'regent_quest': game.regent_quest.to_dict(),
                            'lantern_quest': game.lantern_quest.to_dict()}
                self.assertTrue(MillQuest.valid_journey(snapshot))
                self.assertTrue(RegentArrival.valid_journey(snapshot))
                self.assertTrue(RegentQuest.valid_journey(snapshot))
                self.assertTrue(LanternQuest.valid_journey(snapshot))
                self.assertFalse(game.save_progress())
                game.update(.05, (0, 0), False)
                self.assertEqual(game.quests.status(identifier), 'available')

    def test_prerequisites_use_tools_without_forcing_an_optional_failed_spell(self):
        game = self.game()
        prepare_quest(game, 'CH01_MQ02')
        self.assertEqual(game.venn_visit.method, 'tools')
        self.assertFalse(game.venn_visit.magicks_failed)
        self.assertNotIn('CH01_MQ01_VENN_MAGICKS_FAILED', game.social.flags)
        self.assertFalse(game.mill_quest.legacy_bypass)
        self.assertEqual(game.party.active_ids, ('caelan',))
        self.assertFalse(game.inventory.quantity('caelan_gearblade'))

    def test_later_starts_have_modern_mill_receipts_weapon_and_earned_exp(self):
        for identifier in ('CH01_MQ03', 'CH01_MQ04'):
            with self.subTest(quest=identifier):
                game = self.game()
                prepare_quest(game, identifier)
                self.assertFalse(game.mill_quest.legacy_bypass)
                self.assertTrue(game.mill_quest.encounter_cleared)
                self.assertTrue(game.mill_quest.cups_placed)
                self.assertTrue(game.battle_rewards.has_receipt('mq02:ridgeback_tusker'))
                self.assertEqual(game.inventory.quantity('caelan_gearblade'), 1)
                self.assertGreater(game.character_progression['caelan'].total_xp, 0)
                self.assertGreater(game.character_progression['mira'].total_xp, 0)
                self.assertFalse(game.party.members['mira']['available'])
                self.assertEqual(game.party.active_ids, ('caelan',))

    def test_regent_start_includes_arrival_while_lantern_uses_an_explicit_test_bridge(self):
        game = self.game()
        prepare_quest(game, 'CH01_MQ03')
        self.assertTrue(game.regent_arrival.active)
        self.assertEqual(game.regent_arrival.state, 'pending')
        self.assertEqual(game.regent_quest.stage, 'idle')
        other = self.game()
        prepare_quest(other, 'CH01_MQ04')
        self.assertFalse(other.regent_arrival.active)
        self.assertEqual(other.regent_arrival.state, 'seen')
        self.assertEqual(other.regent_quest.stage, 'done')
        self.assertEqual(other.lantern_quest.stage, 'idle')

    def test_bad_ids_and_existing_journeys_are_explicit_errors(self):
        game = self.game()
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            prepare_quest(game, 'CH01_MQ99')
        prepare_quest(game, 'CH01_MQ02')
        with self.assertRaisesRegex(ValueError, 'fresh'):
            prepare_quest(game, 'CH01_MQ02')
        normal = Game(fullscreen=False, start_on_title=False)
        self.games.append(normal)
        with self.assertRaisesRegex(ValueError, 'temporary'):
            prepare_quest(normal, 'CH01_MQ01')

    def test_embedded_playtests_ignore_even_explicit_real_save_and_settings_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            journey, settings = Path(folder)/'journey.json', Path(folder)/'settings.json'
            journey.write_bytes(b'normal journey must never be opened')
            settings.write_bytes(b'normal settings must never be opened')
            game = self.game(save_path=journey, settings_path=settings)
            prepare_quest(game, 'CH01_MQ04')
            game.audio.set_text_scale(1.5)
            game.audio.set_music(.4)
            game.save_progress()
            self.assertIsNone(game.save_error)
            self.assertEqual(journey.read_bytes(), b'normal journey must never be opened')
            self.assertEqual(settings.read_bytes(), b'normal settings must never be opened')


if __name__ == '__main__':
    unittest.main()
