"""MQ03 owns Mira's existing roster record without changing her resources."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

import pygame

from main import Game
from quests import REGENT_QUEST
from test_mill_battle_gameplay import seed_completed_mill


class MQ03PartyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(pygame.quit)
        self.path=Path(self.directory.name)
        self.game=Game(fullscreen=False,start_on_title=False,
                       save_path=self.path/'journey.json',settings_path=self.path/'settings.json')
        self.game.audio.set_music(0);self.game.audio.set_effects(0)
        seed_completed_mill(self.game)
        self.game._sync_story_party()
        self.assertFalse(self.game.party.members['mira']['available'])

    def prepare_acknowledged_trip(self):
        game=self.game
        self.assertTrue(game.accept_quest(REGENT_QUEST))
        for objective in ('meet_visitors','accompany_visit','welcome_party'):
            self.assertTrue(game.quests.complete_objective(REGENT_QUEST,objective))
        # The runtime's dialogue acknowledgment owns this phase. This fixture
        # isolates reconciliation from the separately tested presentation path.
        game.regent_quest.stage='sanctuary_travel'

    def test_mira_rejoins_without_healing_and_mill_reconciliation_keeps_her(self):
        game=self.game
        mira=game.party.characters['mira']
        mira.set_current(hp=83,mp=4)
        before=(game.inventory.to_dict(),game.character_abilities.to_dict(),
                game.bot_loadouts.to_dict(),game.battle_rewards.to_dict())
        self.prepare_acknowledged_trip()
        for _ in range(4):self.assertTrue(game._sync_story_party())
        self.assertIs(game.party.characters['mira'],mira)
        self.assertEqual((mira.current_hp,mira.current_mp),(83,4))
        self.assertEqual(game.party.current_event_id,'mq03_sanctuary')
        self.assertEqual(game.party.active_ids,('caelan','mira'))
        self.assertEqual(game.party.required_ids,('caelan','mira'))
        self.assertNotIn('lucan',game.party.members)
        self.assertEqual(before,(game.inventory.to_dict(),game.character_abilities.to_dict(),
                                 game.bot_loadouts.to_dict(),game.battle_rewards.to_dict()))

    def test_reserved_mq03_party_event_is_validated_before_live_state_changes(self):
        game=self.game
        self.prepare_acknowledged_trip()
        self.assertTrue(game._sync_story_party())
        self.assertTrue(game.save_progress())
        valid=deepcopy(game.saved_journey)
        self.assertTrue(Game._valid_party_snapshot(valid))
        before=game.party.to_dict()
        for corrupt in ('missing_event','wrong_phase','missing_mira'):
            with self.subTest(corrupt=corrupt):
                data=deepcopy(valid)
                if corrupt=='missing_event':data['party']['event']=None
                elif corrupt=='wrong_phase':data['regent_quest']['stage']='rejoin_mira'
                else:data['party']['active']=['caelan']
                self.assertFalse(Game._valid_party_snapshot(data))
                self.assertEqual(game.party.to_dict(),before)
        # Absence is supported for real legacy journeys, but the new joined
        # phase cannot invent a replacement Mira/event/resource record.
        data=deepcopy(valid);data.pop('party')
        (self.path/'journey.json').write_text(json.dumps(data))
        self.assertIsNone(game._read_saved_journey())
        self.assertEqual(game.party.to_dict(),before)

    def test_other_party_event_cannot_be_silently_replaced_by_the_outing(self):
        game=self.game
        self.assertTrue(game.party.begin_event('other_story',required=('caelan',)))
        self.prepare_acknowledged_trip()
        before=game.party.to_dict()
        self.assertFalse(game._sync_story_party())
        self.assertEqual(game.party.to_dict(),before)


if __name__=='__main__':unittest.main()
