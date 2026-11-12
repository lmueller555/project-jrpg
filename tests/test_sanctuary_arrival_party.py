"""An acknowledged rescue changes formation without granting resources or history."""
from copy import deepcopy
from types import SimpleNamespace as NS
from unittest.mock import patch
import unittest

from character_attributes import CharacterAttributes
from party_state import PartyState
from sanctuary_arrival_party import EVENT_ID, REQUIRED, sync_arrival_party, valid_arrival_party


class SanctuaryArrivalPartyTests(unittest.TestCase):
    def game(self, *, completed=True):
        party = PartyState(CharacterAttributes('caelan'))
        self.assertTrue(party.recruit('mira', temporary=True))
        party.characters['mira'].set_current(hp=83, mp=4)
        party.characters['lucan'].set_current(hp=71, mp=3)
        self.assertTrue(party.begin_event(EVENT_ID, required=('caelan', 'mira')))
        return NS(party=party, regent_quest=NS(stage='sanctuary_arrival_pending'),
                  sanctuary_arrival=NS(completed=completed))

    def resources(self, party):
        return {key: value.to_dict() for key, value in party.characters.items()}

    def test_prearrival_retains_the_existing_two_member_event_and_resources(self):
        game = self.game(completed=False);before = game.party.to_dict()
        self.assertIsNone(sync_arrival_party(game))
        self.assertEqual(game.party.to_dict(), before)
        self.assertNotIn('lucan', game.party.members)

    def test_completion_adds_temporary_lucan_and_preserves_every_character_object_and_resource(self):
        game = self.game();party = game.party
        objects = dict(party.characters);before = self.resources(party)
        prior = party.previous_formation()
        self.assertTrue(sync_arrival_party(game))
        self.assertEqual(party.active_ids, REQUIRED)
        self.assertEqual(party.required_ids, REQUIRED)
        self.assertTrue(party.members['lucan']['temporary'])
        self.assertEqual(party.previous_formation(), prior)
        self.assertEqual(self.resources(party), before)
        for key, value in objects.items():self.assertIs(party.characters[key], value)
        saved = party.to_dict()
        for _ in range(4):self.assertTrue(sync_arrival_party(game))
        self.assertEqual(party.to_dict(), saved)

    def test_existing_permanent_lucan_is_not_recruited_again_or_downgraded(self):
        game = self.game();party = game.party
        self.assertTrue(party.recruit('lucan'))
        before = self.resources(party)
        self.assertTrue(sync_arrival_party(game))
        self.assertFalse(party.members['lucan']['temporary'])
        self.assertEqual(self.resources(party), before)
        game.regent_quest.stage = 'done'
        self.assertIsNone(sync_arrival_party(game))
        self.assertTrue(party.members['lucan']['available'])
        self.assertFalse(party.members['lucan']['temporary'])

    def test_unrelated_event_is_not_replaced_and_failed_upgrade_is_atomic(self):
        game = self.game();party = game.party
        party.end_event(EVENT_ID);party.begin_event('other_story', required=('caelan',))
        before = party.to_dict()
        self.assertFalse(sync_arrival_party(game))
        self.assertEqual(party.to_dict(), before)
        party.end_event('other_story');party.begin_event(EVENT_ID, required=('caelan','mira'))
        before = party.to_dict()
        with patch.object(party, 'begin_event', return_value=False):
            self.assertFalse(sync_arrival_party(game))
        self.assertEqual(party.to_dict(), before)

    def test_player_formation_before_the_outing_and_later_order_are_preserved(self):
        game = self.game();party = game.party
        party.end_event(EVENT_ID)
        self.assertTrue(party.recruit('rhea'))
        self.assertTrue(party.select(('caelan','rhea','mira')))
        self.assertTrue(party.begin_event(EVENT_ID, required=('caelan','mira')))
        self.assertTrue(sync_arrival_party(game))
        self.assertEqual(party.previous_formation(), ('caelan','rhea','mira'))
        self.assertEqual(party.active_ids, REQUIRED)
        self.assertIn('rhea', party.reserve_ids)
        self.assertTrue(party.select(('caelan','lucan','mira')))
        self.assertTrue(sync_arrival_party(game))
        self.assertEqual(party.active_ids, ('caelan','lucan','mira'))

    def test_completed_scene_requires_the_trio_in_active_modern_mq03_snapshots(self):
        game = self.game()
        data = {'sanctuary_arrival': {'version':1,'beat':7,'completed':True,'cave_entered':False},
                'regent_quest': {'version':3,'stage':'sanctuary_arrival_pending'}}
        self.assertFalse(valid_arrival_party(data, game.party))
        self.assertTrue(sync_arrival_party(game))
        self.assertTrue(valid_arrival_party(data, game.party))
        game.party.end_event(EVENT_ID)
        self.assertFalse(valid_arrival_party(data, game.party))
        # An absent new scene owner is a real supported older journey.
        old = deepcopy(data);old.pop('sanctuary_arrival')
        self.assertTrue(valid_arrival_party(old, game.party))

    def test_ending_this_outing_releases_only_its_temporary_lucan(self):
        game = self.game();party = game.party
        self.assertTrue(sync_arrival_party(game))
        before = self.resources(party)
        game.regent_quest.stage = 'done'
        self.assertIsNone(sync_arrival_party(game))
        self.assertIsNone(party.event_id)
        self.assertFalse(party.members['lucan']['available'])
        self.assertNotIn('lucan', party.active_ids)
        self.assertEqual(self.resources(party), before)


if __name__ == '__main__':unittest.main()
