"""Boss encounter checkpoints validate independently of rendering or story actors."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from sanctuary_boss import (APPROACH, BATTLEFIELD, RECEIPT, RETREAT, SCENE_ID,
                            TRIGGER, SanctuaryBoss, valid_ticket)
from sanctuary_boss_entry import growl_samples


ROOT = Path(__file__).resolve().parents[1]


def ticket():
    return {'version': 1, 'enemy_id': 'vespermaw', 'level': 7, 'receipt': RECEIPT,
            'scene': SCENE_ID, 'position': list(APPROACH), 'facing': 'back',
            'battlefield': BATTLEFIELD, 'combat_seed': 7,
            'party_active': ['caelan', 'mira'],
            'party_resources': {'caelan': {'hp': 47, 'mp': 7}, 'mira': {'hp': 0, 'mp': 3}}}


class SanctuaryBossStateTests(unittest.TestCase):
    def pending_journey(self):
        pending = ticket()
        return {'sanctuary_boss': {'version': 1, 'defeated': False,
                                  'intro_seen': False, 'pending': pending},
                'battle_rewards': {'version': 1, 'receipts': []},
                'player': {'scene': SCENE_ID, 'position': list(APPROACH), 'facing': 'back'},
                'cave_random_encounters': {'pending': None},
                'party': {'active': pending['party_active'], 'characters': {
                    key: {'current_hp': values['hp'], 'current_mp': values['mp']}
                    for key, values in pending['party_resources'].items()}}}

    def test_old_journeys_default_unbeaten_without_mutating_input(self):
        data = {'player': {'scene': SCENE_ID}, 'battle_rewards': {'receipts': []}}
        before = deepcopy(data)
        self.assertTrue(SanctuaryBoss.valid_journey(data))
        self.assertEqual(data, before)
        state = SanctuaryBoss(None)
        self.assertTrue(state.restore())
        self.assertEqual(state.to_dict(),
                         {'version': 1, 'defeated': False, 'intro_seen': False, 'pending': None})

    def test_entry_ticket_is_detached_and_completion_is_one_way(self):
        state = SanctuaryBoss(None)
        record = self.pending_journey()['sanctuary_boss']
        self.assertTrue(state.restore(record))
        record['pending']['party_resources']['caelan']['hp'] = 999
        self.assertEqual(state.pending['party_resources']['caelan']['hp'], 47)
        detached = state.pending
        detached['position'][0] = 0
        self.assertEqual(state.pending['position'], list(APPROACH))
        self.assertTrue(state.entry_loaded())
        self.assertTrue(state.entry_loaded())
        self.assertFalse(state.mark_defeated('wrong'))
        self.assertTrue(state.mark_defeated(RECEIPT))
        self.assertFalse(state.mark_defeated(RECEIPT))
        self.assertTrue(state.finish(RECEIPT))
        self.assertTrue(state.defeated)
        self.assertIsNone(state.pending)
        self.assertFalse(state.finish(RECEIPT))

    def test_ticket_rejects_unknown_encounters_bad_resources_and_remote_positions(self):
        self.assertTrue(valid_ticket(ticket()))
        changes = [('version', True), ('enemy_id', 'cave_bat'), ('level', 6),
                   ('level', True), ('receipt', 'cave:1:1'), ('scene', 'eldenmere.playable'),
                   ('position', [288, 1660]), ('position', [float('nan'), 420]),
                   ('position', [10**1000, 420]),
                   ('battlefield', 'cave_depths'), ('combat_seed', True),
                   ('party_active', ['mira']), ('party_active', ['caelan', 'caelan'])]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                record = ticket();record[key] = value
                self.assertFalse(valid_ticket(record))
        for key, value in (('hp', -1), ('hp', True), ('hp', 10000), ('mp', 1000)):
            with self.subTest(resource=key, value=value):
                record = ticket();record['party_resources']['caelan'][key] = value
                self.assertFalse(valid_ticket(record))
        record = ticket();record['party_resources']['caelan']['hp'] = 0
        self.assertFalse(valid_ticket(record))

    def test_journey_requires_matching_entry_receipt_and_unique_encounter_owner(self):
        data = self.pending_journey()
        self.assertTrue(SanctuaryBoss.valid_journey(data))
        for field, value in (('player', None), ('party', None), ('battle_rewards', None)):
            with self.subTest(field=field):
                changed = deepcopy(data);changed[field] = value
                self.assertFalse(SanctuaryBoss.valid_journey(changed))
        changed = deepcopy(data)
        changed['cave_random_encounters']['pending'] = {'another': 'encounter'}
        self.assertFalse(SanctuaryBoss.valid_journey(changed))
        changed = deepcopy(data);changed['party']['characters']['caelan']['current_hp'] = 48
        self.assertFalse(SanctuaryBoss.valid_journey(changed))
        changed = deepcopy(data);changed['sanctuary_boss']['defeated'] = True
        self.assertFalse(SanctuaryBoss.valid_journey(changed))
        # Awarded spoils deliberately retain the original entry resources.
        data['post_battle'] = {'kind': 'cave_boss', 'stage': 'awarded',
                              'encounter': ticket(), 'party_before': ticket()['party_resources']}
        data['sanctuary_boss'].update(defeated=True, intro_seen=True)
        data['battle_rewards']['receipts'] = [RECEIPT]
        data['party']['characters']['caelan']['current_hp'] = 1
        self.assertTrue(SanctuaryBoss.valid_journey(data))
        data['sanctuary_boss']['pending'] = None
        data['post_battle'] = None
        self.assertTrue(SanctuaryBoss.valid_journey(data))

    def test_runtime_approach_matches_authored_arena(self):
        arena = json.loads((ROOT/'assets/maps/sanctuary_cave/map.json').read_text())['cave']['arena']
        for key, expected in (('approach', APPROACH), ('retreat', RETREAT), ('trigger', TRIGGER)):
            self.assertEqual(tuple(arena[key]), expected)
        self.assertEqual(arena['battlefield'], BATTLEFIELD)

    def test_original_growl_is_deterministic_bounded_stereo_with_silent_ends(self):
        samples = growl_samples(22050, 2)
        self.assertEqual(samples, growl_samples(22050, 2))
        self.assertEqual(len(samples), round(22050*1.6)*2)
        self.assertEqual(samples[0], 0)
        self.assertEqual(samples[::2], samples[1::2])
        self.assertTrue(1000 < max(samples) < 32767)
        self.assertLess(abs(samples[-1]), 10)
