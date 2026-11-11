"""Old journeys migrate to Mira's wearable rig without restoring a bot actor."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

from main import Game
from test_mill_battle_gameplay import seed_completed_mill


LEGACY_LOADOUT = {'version': 1, 'loadouts': {
    'mira': {'bot_id': 'rivet', 'ability_id': 'piston_jab'}}}
STARTING_RIG = frozenset({'arm_rig', 'charged_bolt', 'bulwark', 'repair_pulse',
                          'impact_bolt', 'arc_discharge'})


class RetiredBotGameplayTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='retired-bot-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory/'journey.json'
        self.games = []

    def tearDown(self):
        for game in self.games:
            game.opening_audio.reset();game.regional_audio.reset();game.music.stop()
        self.games.clear();pygame.quit()

    def game(self, title=False):
        game = Game(window_size=(960, 640), fullscreen=False,
            start_on_title=title, save_path=self.path,
            settings_path=self.directory/'settings.json')
        self.games.append(game)
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        pygame.event.clear()
        return game

    def test_new_journey_has_starting_rig_but_neither_recruits_mira_nor_serializes_bots(self):
        game = self.game()
        self.assertNotIn('mira', game.party.active_ids)
        self.assertEqual(game.character_abilities.known_abilities('mira'), STARTING_RIG)
        self.assertEqual(game.mira_rig.allocation, {'weapons': 2, 'protection': 2, 'support': 2})
        self.assertTrue(game.save_progress())
        payload = json.loads(self.path.read_text())
        self.assertNotIn('bot_loadouts', payload)
        self.assertEqual(payload['mira_rig']['allocation'],
            {'weapons': 2, 'protection': 2, 'support': 2})
        game.world = game.town
        game.player.position.update(game.combat.position+(0, 24))
        self.assertTrue(game.combat.interact())
        self.assertEqual([member.identifier for member in game.combat.model.party], ['player'])
        self.assertFalse(hasattr(game.combat.model, 'bots'))
        self.assertEqual(len(game.combat.model.party), 1)

    def test_known_legacy_loadout_migrates_without_changing_inventory_or_earned_progress(self):
        game = self.game();seed_completed_mill(game)
        saved = json.loads(self.path.read_text())
        saved.pop('mira_rig', None)
        saved['bot_loadouts'] = deepcopy(LEGACY_LOADOUT)
        raw = json.dumps(saved)
        self.path.write_text(raw)
        resumed = self.game(title=True)
        self.assertTrue(resumed.has_saved_journey, resumed.save_error)
        self.assertEqual(self.path.read_text(), raw)
        self.assertTrue(resumed.begin_journey(True))
        self.assertEqual(resumed.mira_rig.allocation, {'weapons': 2, 'protection': 2, 'support': 2})
        self.assertEqual(resumed.character_abilities.known_abilities('mira'), STARTING_RIG)
        self.assertEqual(resumed.inventory.to_dict(), saved['inventory'])
        self.assertEqual(resumed.character_progression.to_dict(), saved['character_levels'])
        self.assertEqual(resumed.battle_rewards.to_dict(), saved['battle_rewards'])
        current = json.loads(self.path.read_text())
        self.assertNotIn('bot_loadouts', current)
        self.assertEqual(current['mira_rig']['allocation'],
            {'weapons': 2, 'protection': 2, 'support': 2})

    def test_unknown_or_malformed_retired_loadouts_do_not_overwrite_the_journey(self):
        game = self.game();seed_completed_mill(game)
        saved = json.loads(self.path.read_text())
        unknown_ability = deepcopy(LEGACY_LOADOUT)
        unknown_ability['loadouts']['mira']['ability_id'] = 'unknown_ability'
        future_bot = deepcopy(LEGACY_LOADOUT)
        future_bot['loadouts']['mira']['bot_id'] = 'future_bot'
        for state in (None, {}, {'version': True, 'loadouts': LEGACY_LOADOUT['loadouts']},
                      unknown_ability, future_bot):
            with self.subTest(state=state):
                payload = deepcopy(saved);payload['bot_loadouts'] = state
                raw = json.dumps(payload);self.path.write_text(raw)
                resumed = self.game(title=True)
                self.assertFalse(resumed.has_saved_journey)
                self.assertIsNotNone(resumed.save_error)
                self.assertFalse(resumed.begin_journey(True))
                self.assertEqual(self.path.read_text(), raw)


if __name__ == '__main__':unittest.main()
