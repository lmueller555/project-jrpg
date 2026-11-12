"""One-time guest recruitment and legacy adoption preserve durable injuries."""
from types import SimpleNamespace as NS
import unittest

from character_attributes import CharacterAttributes
from character_progression import CharacterProgression
from leveling import CharacterLevel, character_stats, total_xp_for_level
from lucan_guest import guest_xp_excluded, initialize_lucan_guest
from party_state import PartyState
from sanctuary_arrival_party import sync_arrival_party
from sanctuary_cave import SanctuaryCave


class LucanGuestProfileTests(unittest.TestCase):
    def game(self):
        party = PartyState(CharacterAttributes())
        progression = CharacterProgression(party)
        progression.initialize_new_game()
        party.recruit('mira')
        return NS(party=party, character_progression=progression,
                  sanctuary_cave=NS(lucan_guest_initialized=False,lucan_departed=False),
                  sanctuary_arrival=NS(completed=True),
                  regent_quest=NS(stage='sanctuary_arrival_pending'),
                  combat=NS(active=False,post_phase=None,_pending=None))

    def test_new_join_starts_level_five_and_never_heals_on_reconciliation(self):
        game = self.game()
        self.assertTrue(sync_arrival_party(game))
        self.assertEqual(game.character_progression.level('lucan'), 5)
        stats = game.party.characters['lucan']
        self.assertEqual(stats._attributes, character_stats('lucan',5))
        self.assertEqual((stats.current_hp,stats.current_mp),(stats.value('hp'),stats.value('mp')))
        self.assertEqual(guest_xp_excluded(game.party),('lucan',))
        stats.set_current(hp=0,mp=0)
        before = game.party.to_dict()
        for _ in range(3):self.assertTrue(sync_arrival_party(game))
        self.assertEqual(game.party.to_dict(),before)

    def test_old_guest_adopts_profile_once_with_proportional_resources_and_ko(self):
        for conscious in (True,False):
            game=self.game();game.party.recruit('lucan',temporary=True)
            stats=game.party.characters['lucan']
            stats._attributes=character_stats('lucan',20)
            game.character_progression.records['lucan']=CharacterLevel('lucan',total_xp_for_level(20))
            old_hp,old_mp=stats.value('hp'),stats.value('mp')
            hp=old_hp//3 if conscious else 0;mp=old_mp//4
            stats.set_current(hp=hp,mp=mp)
            self.assertTrue(initialize_lucan_guest(game))
            self.assertEqual(game.character_progression.level('lucan'),5)
            expected_hp=(hp*stats.value('hp')+old_hp//2)//old_hp if hp else 0
            self.assertEqual(stats.current_hp,expected_hp)
            self.assertEqual(stats.current_mp,(mp*stats.value('mp')+old_mp//2)//old_mp)
            before=stats.to_dict()
            self.assertFalse(initialize_lucan_guest(game))
            self.assertEqual(stats.to_dict(),before)

    def test_pending_victory_and_permanent_recruitment_are_not_retuned(self):
        game=self.game();game.party.recruit('lucan',temporary=True)
        before=game.party.to_dict()
        game._lucan_guest_defer_profile=True
        self.assertFalse(initialize_lucan_guest(game))
        self.assertEqual(game.party.to_dict(),before)
        game._lucan_guest_defer_profile=False
        game.combat.active=True
        self.assertFalse(initialize_lucan_guest(game))
        self.assertEqual(game.party.to_dict(),before)
        game=self.game();game.party.recruit('lucan')
        before=game.party.to_dict()
        self.assertFalse(initialize_lucan_guest(game,new=True))
        self.assertEqual(game.party.to_dict(),before)
        self.assertEqual(guest_xp_excluded(game.party),())

    def test_departure_receipt_requires_the_completed_boss(self):
        base={'version':1,'opened':[],'lucan_guest_initialized':True,'lucan_departed':True}
        self.assertFalse(SanctuaryCave.valid_journey({'player':{'scene':'elden_vale_sanctuary'},
                                                   'sanctuary_cave':base}))
        self.assertTrue(SanctuaryCave.valid_journey({'player':{'scene':'elden_vale_sanctuary'},
            'sanctuary_cave':base,'sanctuary_boss':{'defeated':True}}))
        malformed={**base,'lucan_guest_initialized':False}
        self.assertFalse(SanctuaryCave.valid_snapshot(malformed))


if __name__=='__main__':unittest.main()
