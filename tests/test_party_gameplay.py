"""Real journey checkpoints and event prompts preserve the selected roster."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')

import pygame
import main
from quests import MILL_QUEST
from test_mill_battle_gameplay import seed_completed_mill, seed_mill_handoff


class PartyGameplayTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'journey.json'

    def tearDown(self):pygame.quit()

    def game(self,*,title=False):
        game=main.Game(fullscreen=False,start_on_title=title,save_path=self.path,
                       settings_path=Path(self.directory.name)/'settings.json')
        game.audio.set_effects(0)
        return game

    def recruit(self,game):
        for identifier in ('mira','lucan','rhea'):
            self.assertTrue(game.recruit_party_member(identifier))
        game.party_ui.close()

    def test_roster_and_independent_resources_survive_real_save_reload_and_swaps(self):
        game=self.game()
        self.assertEqual(tuple(game.party.members),('caelan',))
        self.recruit(game)
        game.party.characters['mira'].set_current(hp=123,mp=7)
        game.party.characters['lucan'].set_current(hp=42,mp=3)
        self.assertTrue(game.set_active_party(('caelan','lucan','rhea')))
        loaded=self.game(title=True)
        self.assertTrue(loaded.begin_journey(True))
        self.assertEqual(loaded.party.active_ids,('caelan','lucan','rhea'))
        self.assertIs(loaded.attributes,loaded.party.characters['caelan'])
        self.assertEqual((loaded.party.characters['mira'].current_hp,
                          loaded.party.characters['mira'].current_mp),(123,7))
        self.assertTrue(loaded.set_active_party(('caelan','mira')))
        self.assertEqual(loaded.party.characters['lucan'].current_hp,42)
        self.assertEqual(loaded.party.characters['mira'].current_mp,7)

    def test_failed_formation_checkpoint_rolls_back_and_keeps_ui_draft(self):
        game=self.game();self.recruit(game)
        before=deepcopy(game.party.to_dict())
        game.party_ui.open()
        game.party_ui.selected_slot=2
        self.assertTrue(game.party_ui.choose_member('rhea'))
        with patch.object(game.save_store,'write',return_value=False):
            self.assertFalse(game.party_ui.confirm())
        self.assertTrue(game.party_ui.is_open)
        self.assertEqual(game.party.to_dict(),before)
        self.assertEqual(game.party_ui.formation,('caelan','mira','rhea'))
        self.assertTrue(game.party_ui.confirm())
        self.assertFalse(game.party_ui.is_open)

    def test_pending_event_selection_reopens_after_reload_and_locks_only_on_confirm(self):
        game=self.game();self.recruit(game)
        self.assertTrue(game.request_party_selection('test_gate',required=('mira',),
            unavailable=('rhea',),title='Choose companions',reason='The passage is closing.',lock_after=True))
        self.assertFalse(game.party.locked)
        loaded=self.game(title=True)
        self.assertTrue(loaded.begin_journey(True))
        self.assertTrue(loaded.party_ui.is_open)
        self.assertEqual(loaded.party_ui.prompt,'Choose companions')
        self.assertIn('mira',loaded.party.required_ids)
        self.assertFalse(loaded.party.members['rhea']['available'])
        position=loaded.player.position.copy()
        loaded.update(.3,(1,0),True)
        self.assertEqual(loaded.player.position,position)
        self.assertTrue(loaded.party_ui.confirm())
        self.assertTrue(loaded.party.locked)
        self.assertIsNone(loaded.party.pending_selection)
        again=self.game(title=True)
        self.assertTrue(again.begin_journey(True))
        self.assertTrue(again.party.locked)
        self.assertFalse(again.party_ui.is_open)
        self.assertTrue(again.end_party_event('test_gate'))
        self.assertTrue(again.party.members['rhea']['available'])

    def test_cancel_event_restores_prior_selection_and_never_calls_continuation(self):
        game=self.game();self.recruit(game)
        self.assertTrue(game.set_active_party(('caelan','lucan','rhea')))
        before=game.party.to_dict();calls=[]
        self.assertTrue(game.request_party_selection('test_gate',required=('mira',),
                                                     on_confirm=lambda:calls.append(True)))
        game.party_ui.close()
        self.assertEqual(game.party.to_dict(),before)
        self.assertEqual(calls,[])

    def test_malformed_party_cannot_load_or_replace_a_live_roster(self):
        game=self.game();self.recruit(game)
        original=game.party.to_dict()
        data=json.loads(self.path.read_text())
        data['party']['active']=['caelan','mira','lucan','rhea']
        self.path.write_text(json.dumps(data))
        self.assertIsNone(game._read_saved_journey())
        self.assertEqual(game.party.to_dict(),original)

    def test_legacy_journey_without_party_migrates_without_future_recruits(self):
        game=self.game();self.assertTrue(game.save_progress())
        data=json.loads(self.path.read_text());data.pop('party')
        self.path.write_text(json.dumps(data))
        loaded=self.game(title=True)
        self.assertTrue(loaded.begin_journey(True))
        self.assertEqual(tuple(loaded.party.members),('caelan',))

    def test_equivalent_older_attribute_schema_validates_against_party_alias(self):
        game=self.game();self.assertTrue(game.save_progress())
        data=json.loads(self.path.read_text())
        data['character_attributes']['version']=2
        self.path.write_text(json.dumps(data))
        loaded=self.game(title=True)
        self.assertTrue(loaded.begin_journey(True))
        self.assertEqual(loaded.attributes.to_dict(),loaded.party.characters['caelan'].to_dict())

    def test_later_story_can_return_mira_after_completed_mill_and_reload(self):
        game=self.game();seed_completed_mill(game)
        self.assertFalse(game.party.members['mira']['available'])
        game.party.characters['mira'].set_current(hp=85,mp=4)
        self.assertTrue(game.set_party_member_available('mira',True))
        loaded=self.game(title=True)
        self.assertTrue(loaded.begin_journey(True))
        self.assertTrue(loaded.party.members['mira']['available'])
        self.assertEqual(loaded.party.characters['mira'].current_mp,4)
        self.assertEqual(loaded.party.active_ids,('caelan',))

    def test_mill_reconciliation_requires_mira_then_retains_her_as_unavailable(self):
        game=self.game()
        seed_mill_handoff(game)
        self.assertTrue(game.quests.accept(MILL_QUEST))
        self.assertTrue(game.quests.complete_objective(MILL_QUEST,'meet_mira'))
        game._sync_story_party()
        self.assertEqual(game.party.active_ids,('caelan','mira'))
        self.assertIn('mira',game.party.required_ids)
        game.party.characters['mira'].set_current(hp=80,mp=5)
        game.mill_quest.resolved=True
        game._sync_story_party()
        self.assertEqual(game.party.active_ids,('caelan',))
        self.assertFalse(game.party.members['mira']['available'])
        self.assertEqual(game.party.members['mira']['reason'],'Working in Eldenmere.')
        self.assertEqual(game.party.characters['mira'].current_mp,5)
        # A later story may return her; the old quest must not keep dismissing her.
        self.assertTrue(game.party.set_available('mira',True))
        game._sync_story_party()
        self.assertTrue(game.party.members['mira']['available'])
        self.assertEqual(game.party.characters['mira'].current_mp,5)

    def test_no_party_operation_changes_progression_or_equipment(self):
        game=self.game()
        before=(game.lattice.to_dict(),game.character_abilities.to_dict(),game.inventory.to_dict())
        self.recruit(game)
        self.assertTrue(game.set_active_party(('caelan','lucan')))
        self.assertTrue(game.set_party_member_available('rhea',False,'Away on an errand.'))
        self.assertEqual((game.lattice.to_dict(),game.character_abilities.to_dict(),
                          game.inventory.to_dict()),before)

    def test_sanctuary_world_accepts_party_actors_without_breaking_depth_rendering(self):
        from elden_vale_sanctuary import SanctuaryReserveWorld
        game=self.game();self.recruit(game)
        world=SanctuaryReserveWorld(main.ROOT/'assets/maps/elden_vale_sanctuary/map.json')
        game.world=world
        game.player.position.update(world.data['spawn'])
        game.party_travel.update(.1)
        world.draw(game.canvas,(0,0),game.player,0,include_ui=False,
                   party_actors=game.party_travel.actors())
