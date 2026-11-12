"""Guest exclusion is part of the validated reward plan, not just its UI."""
from copy import deepcopy
import unittest

from character_attributes import CharacterAttributes
from character_progression import CharacterProgression
from party_state import PartyState


class LucanGuestProgressionTests(unittest.TestCase):
    def party(self, temporary=True):
        party = PartyState(CharacterAttributes())
        party.recruit('mira', temporary=True)
        party.recruit('lucan', temporary=temporary)
        progression = CharacterProgression(party)
        progression.initialize_new_game()
        progression.initialize_guest_level('lucan', 5)
        return party, progression

    def test_guest_gets_zero_while_all_other_survivors_receive_the_full_award(self):
        party, progression = self.party()
        active = list(party.active_ids)
        before = progression['lucan'].total_xp
        resources = [(a.current_hp, a.current_mp) for a in party.characters.values()]
        plan = progression.preview(500, active, dict.fromkeys(active, 1))
        self.assertEqual(plan['version'], 2)
        self.assertEqual(plan['guest_ids'], ['lucan'])
        self.assertTrue(progression.valid_plan(plan))
        self.assertEqual(plan['characters']['lucan']['requested_xp'], 0)
        for key in ('caelan', 'mira'):
            self.assertEqual(plan['characters'][key]['requested_xp'], 500)
        self.assertTrue(progression.apply(plan))
        self.assertEqual(progression['lucan'].total_xp, before)
        self.assertEqual(progression.level('lucan'), 5)
        self.assertEqual(resources, [(a.current_hp, a.current_mp) for a in party.characters.values()])

    def test_exclusion_cannot_be_forged_for_another_character_or_permanent_lucan(self):
        party, progression = self.party()
        active = list(party.active_ids)
        plan = progression.preview(500, active, dict.fromkeys(active, 1))
        for guests in ([], ['mira'], ['lucan', 'lucan'], ['lucan', 'mira']):
            bad = deepcopy(plan);bad['guest_ids'] = guests
            self.assertFalse(progression.valid_plan(bad))
        snapshot = party.to_dict();snapshot['members']['lucan']['temporary'] = False
        self.assertTrue(party.restore(snapshot))
        self.assertFalse(progression.matches_plan(plan))
        permanent = progression.preview(500, active, dict.fromkeys(active, 1))
        self.assertEqual(permanent['version'], 1)
        self.assertEqual(permanent['characters']['lucan']['requested_xp'], 500)

    def test_legacy_award_plans_remain_valid_for_pending_checkpoint_restoration(self):
        party, progression = self.party(temporary=False)
        active = list(party.active_ids)
        legacy = progression.preview(500, active, dict.fromkeys(active, 1))
        self.assertEqual(legacy['version'], 1)
        snapshot = party.to_dict();snapshot['members']['lucan']['temporary'] = True
        self.assertTrue(party.restore(snapshot))
        self.assertTrue(progression.valid_plan(legacy))
        self.assertTrue(progression.matches_plan(legacy))


if __name__ == '__main__':unittest.main()
