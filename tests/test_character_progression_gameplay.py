"""Traditional EXP save ownership, migration and fresh-journey baselines."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from leveling import MAX_TOTAL_XP, character_ids, character_stats
from main import Game


class CharacterProgressionGameplayTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='character-exp-save-')
        self.addCleanup(temporary.cleanup)
        self.addCleanup(pygame.quit)
        self.directory = Path(temporary.name)
        self.path = self.directory / 'journey.json'
        self.game = self.make_game()

    def make_game(self, title=False):
        game = Game(window_size=(960, 640), fullscreen=False,
                    start_on_title=title, save_path=self.path,
                    settings_path=self.directory / 'settings.json')
        game.audio.set_music(0)
        game.audio.set_effects(0)
        pygame.event.clear()
        return game

    def test_fresh_game_uses_all_approved_starting_profiles(self):
        for identifier in character_ids():
            with self.subTest(character=identifier):
                attributes = self.game.party.characters[identifier]
                self.assertEqual({key: attributes.base_value(key)
                                  for key in attributes.definitions},
                                 character_stats(identifier, 1))
                self.assertEqual(attributes.current_hp, attributes.value('hp'))
                self.assertEqual(attributes.current_mp, attributes.value('mp'))
                self.assertEqual(self.game.character_progression.level(identifier), 1)

    def test_continue_retunes_old_guest_profile_once_without_healing_or_erasing_exp(self):
        game = self.game
        attributes = game.party.characters['mira']
        attributes._attributes = dict(zip(attributes.definitions,
            (300, 30, 20, 12, 12, 18, 14, 12, 16, 12, 10)))
        attributes.set_current(hp=211, mp=7)
        game.character_progression.records['mira'].award_xp(100)
        self.assertTrue(game.save_progress())
        restored = self.make_game(title=True)
        self.assertTrue(restored.begin_journey(True), restored.save_error)
        mira = restored.party.characters['mira']
        self.assertEqual(mira.to_dict()['attributes'], character_stats('mira', 1))
        self.assertEqual((mira.current_hp, mira.current_mp), (106, 7))
        self.assertEqual(restored.character_progression['mira'].total_xp, 100)
        self.assertTrue(restored.save_progress())
        again = self.make_game(title=True)
        self.assertTrue(again.begin_journey(True), again.save_error)
        self.assertEqual(again.party.characters['mira'].to_dict(), mira.to_dict())

    def test_progression_changes_are_in_checkpoint_signature_and_continue(self):
        game = self.game
        game.attributes.set_current(hp=47, mp=7)
        signature = game._progress_signature()
        plan = game.character_progression.preview(700, ['caelan'], {'caelan': 47})
        self.assertTrue(game.character_progression.apply(plan))
        self.assertNotEqual(signature, game._progress_signature())
        self.assertEqual((game.attributes.current_hp, game.attributes.current_mp), (47, 7))
        self.assertTrue(game.save_progress())
        expected_levels = game.character_progression.to_dict()
        expected_party = game.party.to_dict()
        restored = self.make_game(title=True)
        self.assertTrue(restored.has_saved_journey, restored.save_error)
        self.assertTrue(restored.begin_journey(True), restored.save_error)
        self.assertEqual(restored.character_progression.to_dict(), expected_levels)
        self.assertEqual(restored.party.to_dict(), expected_party)
        self.assertIs(restored.party.characters['caelan'], restored.attributes)
        self.assertIs(restored.character_progression.party, restored.party)

    def test_old_save_import_preserves_stats_resources_and_does_not_invent_exp(self):
        game = self.game
        self.assertTrue(game.attributes.apply_growth({'hp': 77, 'str': 9}))
        game.attributes.set_current(hp=23, mp=6)
        self.assertTrue(game.save_progress())
        data = json.loads(self.path.read_text())
        data.pop('character_levels')
        # An older companion profile is a preserved baseline, not a reason
        # to infer a level or replace the character with the new-game profile.
        data['party']['characters']['mira']['attributes']['hp'] = 300
        data['party']['characters']['mira']['current_hp'] = 211
        self.path.write_text(json.dumps(data))
        original = self.path.read_bytes()
        restored = self.make_game(title=True)
        self.assertTrue(restored.has_saved_journey, restored.save_error)
        self.assertEqual(self.path.read_bytes(), original, 'Title validation is read-only')
        self.assertTrue(restored.begin_journey(True), restored.save_error)
        self.assertEqual(restored.attributes.to_dict(), data['character_attributes'])
        self.assertEqual(restored.party.characters['mira'].to_dict(),
                         data['party']['characters']['mira'])
        self.assertTrue(all(record.total_xp == 0
                            for record in restored.character_progression.records.values()))
        self.assertIn('character_levels', json.loads(self.path.read_text()))

    def test_malformed_exp_records_cannot_mutate_live_state_or_saved_file(self):
        self.assertTrue(self.game.save_progress())
        saved = json.loads(self.path.read_text())
        mutations = (
            lambda r: r['characters']['caelan'].update(total_xp=True),
            lambda r: r['characters']['caelan'].update(total_xp=-1),
            lambda r: r['characters']['caelan'].update(total_xp=MAX_TOTAL_XP + 1),
            lambda r: r['characters']['mira'].update(character_id='caelan'),
            lambda r: r['characters'].pop('edran'),
            lambda r: r.update(extra='unrecognized'),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)):
                data = deepcopy(saved)
                mutation(data['character_levels'])
                self.path.write_text(json.dumps(data))
                original = self.path.read_bytes()
                restored = self.make_game(title=True)
                self.assertFalse(restored.has_saved_journey)
                self.assertEqual(self.path.read_bytes(), original)
                self.assertTrue(all(record.total_xp == 0
                                    for record in restored.character_progression.records.values()))

    def test_new_journey_resets_exp_and_uses_a_new_party_owner(self):
        game = self.game
        plan = game.character_progression.preview(700, ['caelan'], {'caelan': 140})
        self.assertTrue(game.character_progression.apply(plan))
        old_party = game.party
        self.assertTrue(game.begin_journey(False, show_cinematic=False))
        self.assertIsNot(game.party, old_party)
        self.assertIs(game.character_progression.party, game.party)
        self.assertEqual(game.character_progression.level('caelan'), 1)
        self.assertEqual(game.attributes.base_value('hp'), character_stats('caelan', 1)['hp'])


if __name__ == '__main__':
    unittest.main()
