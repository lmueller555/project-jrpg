"""Independent guardian receipts, arena tickets and deferred focus ownership."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from elemental_bosses import (ElementalBosses, REGISTRY, SCENE_ID, definition,
                             enemy_for_receipt, valid_ticket)


ROOT = Path(__file__).resolve().parents[1]


def ticket(enemy_id='embravyr'):
    entry = definition(enemy_id)
    return {'version': 1, 'enemy_id': enemy_id, 'level': 4,
            'receipt': entry['receipt'], 'scene': SCENE_ID,
            'position': list(entry['approach']), 'facing': 'back',
            'battlefield': entry['battlefield'], 'combat_seed': 17,
            'party_active': ['caelan', 'mira'],
            'party_resources': {'caelan': {'hp': 0, 'mp': 0}, 'mira': {'hp': 73, 'mp': 2}}}


def pending_state(enemy_id='embravyr'):
    state = ElementalBosses(None).to_dict()
    state['bosses'][enemy_id]['discovered'] = True
    state['pending'] = ticket(enemy_id)
    return state


def journey(enemy_id='embravyr'):
    pending = ticket(enemy_id)
    return {'elemental_bosses': pending_state(enemy_id),
            'battle_rewards': {'version': 1, 'receipts': []},
            'player': {'scene': SCENE_ID, 'position': list(pending['position']), 'facing': 'back'},
            'cave_lesson': {'battle_cleared': True},
            'sanctuary_boss': {'pending': None},
            'cave_random_encounters': {'pending': None},
            'inventory': {'items': {}},
            'character_abilities': {'gear_gems': {'caelan': ['water']},
                                    'learned_abilities': {'caelan': ['aqua_edge']}},
            'party': {'active': pending['party_active'], 'characters': {
                key: {'current_hp': values['hp'], 'current_mp': values['mp']}
                for key, values in pending['party_resources'].items()}}}


class ElementalBossStateTests(unittest.TestCase):
    def test_missing_extension_defaults_unbeaten_and_does_not_mutate_old_journey(self):
        previous = {'player': {'scene': SCENE_ID}, 'battle_rewards': {'receipts': ['boss:vespermaw']}}
        before = deepcopy(previous)
        self.assertTrue(ElementalBosses.valid_journey(previous))
        self.assertEqual(previous, before)
        owner = ElementalBosses(None)
        self.assertTrue(owner.restore())
        self.assertIsNone(owner.pending)
        self.assertFalse(any(any(state.values()) for state in owner.bosses.values()))
        self.assertEqual(owner.victory_order, [])
        previous['battle_rewards']['receipts'].append('boss:embravyr')
        self.assertFalse(ElementalBosses.valid_journey(previous))
        previous['battle_rewards']['receipts'].pop()
        for amount in (1, 999999, True):
            previous['inventory'] = {'items': {'red_focus_gem': amount}}
            self.assertFalse(ElementalBosses.valid_journey(previous))

    def test_registry_uses_exported_arena_geometry_and_unique_rewards(self):
        arenas = json.loads((ROOT/'assets/maps/sanctuary_cave/map.json').read_text())['cave']['elemental_arenas']
        self.assertEqual({entry['enemy_id'] for entry in arenas}, set(REGISTRY))
        self.assertEqual({entry['receipt'] for entry in REGISTRY.values()},
                         {'boss:embravyr', 'boss:nivareth'})
        for arena in arenas:
            actual = definition(arena['enemy_id'])
            for key in ('center', 'approach', 'retreat', 'trigger'):
                self.assertEqual(actual[key], tuple(arena[key]))
            for key in ('level', 'battlefield', 'room'):
                self.assertEqual(actual[key], arena[key])
            self.assertEqual(enemy_for_receipt(actual['receipt']), arena['enemy_id'])
        original = definition('embravyr')
        original['gem'] = 'ice'
        self.assertEqual(definition('embravyr')['gem'], 'fire')
        self.assertIsNone(definition('vespermaw'))

    def test_tickets_reject_crossed_receipts_positions_and_malformed_resources(self):
        for enemy_id in REGISTRY:
            self.assertTrue(valid_ticket(ticket(enemy_id)))
        mutations = {'version': True, 'enemy_id': 'vespermaw', 'level': 7,
                     'receipt': 'boss:nivareth', 'scene': 'eldenmere.playable',
                     'position': [10**1000, 1], 'combat_seed': True,
                     'battlefield': 'cave_stillfrost', 'party_active': ['mira']}
        for key, value in mutations.items():
            with self.subTest(field=key):
                changed = ticket();changed[key] = value
                self.assertFalse(valid_ticket(changed))
        for key, value in (('hp', -1), ('hp', True), ('hp', 10000), ('mp', 1000)):
            changed = ticket();changed['party_resources']['mira'][key] = value
            self.assertFalse(valid_ticket(changed))
        changed = ticket();changed['party_resources']['mira']['hp'] = 0
        self.assertFalse(valid_ticket(changed))

    def test_completion_keeps_presentation_queued_and_bosses_independent_in_either_order(self):
        for order in (('embravyr', 'nivareth'), ('nivareth', 'embravyr')):
            with self.subTest(order=order):
                owner = ElementalBosses(None)
                for key in order:
                    record = owner.to_dict()
                    record['bosses'][key]['discovered'] = True
                    record['pending'] = ticket(key)
                    self.assertTrue(owner.restore(record))
                    detached = owner.pending;detached['combat_seed'] = 999
                    self.assertEqual(owner.pending['combat_seed'], 17)
                    self.assertTrue(owner.entry_loaded())
                    self.assertFalse(owner.mark_defeated('boss:vespermaw'))
                    self.assertTrue(owner.mark_defeated(REGISTRY[key]['receipt']))
                    self.assertFalse(owner.mark_defeated(REGISTRY[key]['receipt']))
                    self.assertTrue(owner.finish(REGISTRY[key]['receipt']))
                    self.assertFalse(owner.finish(REGISTRY[key]['receipt']))
                    self.assertTrue(owner.bosses[key]['pending_acquisition'])
                    self.assertIsNone(owner.pending)
                    self.assertTrue(owner.valid_snapshot(owner.to_dict()))
                self.assertEqual(owner.victory_order, list(order))
                first = owner._acquisition_lines(order[0])
                second = owner._acquisition_lines(order[1])
                self.assertGreater(len(first), len(second))
                self.assertIn('I can feel the Aether moving through me now. Before, I was just pushing.',
                              [line['text'] for line in first])
                self.assertIn('Follow it through the gem. Let it take its shape.',
                              [line['text'] for line in first])

    def test_journey_pending_requires_aqua_clear_entry_resources_and_unique_owner(self):
        data = journey()
        self.assertTrue(ElementalBosses.valid_journey(data))
        for field in ('player', 'party', 'battle_rewards'):
            changed = deepcopy(data);changed[field] = None
            self.assertFalse(ElementalBosses.valid_journey(changed))
        for field in ('sanctuary_boss', 'cave_random_encounters'):
            changed = deepcopy(data);changed[field]['pending'] = {'other': 'encounter'}
            self.assertFalse(ElementalBosses.valid_journey(changed))
        changed = deepcopy(data);changed['cave_lesson']['battle_cleared'] = False
        self.assertFalse(ElementalBosses.valid_journey(changed))
        changed = deepcopy(data);changed['party']['characters']['mira']['current_hp'] -= 1
        self.assertFalse(ElementalBosses.valid_journey(changed))
        for amount in (1, 999999, True):
            changed = deepcopy(data);changed['inventory']['items']['red_focus_gem'] = amount
            self.assertFalse(ElementalBosses.valid_journey(changed))

    def test_awarded_and_finished_journeys_require_receipt_gem_item_and_skill(self):
        data = journey('nivareth');owner = ElementalBosses(None)
        self.assertTrue(owner.restore(data['elemental_bosses']))
        self.assertTrue(owner.mark_defeated('boss:nivareth'))
        data['elemental_bosses'] = owner.to_dict()
        data['battle_rewards']['receipts'].append('boss:nivareth')
        data['character_abilities']['gear_gems']['caelan'].append('ice')
        data['character_abilities']['learned_abilities']['caelan'].append('ice_edge')
        data['inventory']['items']['white_focus_gem'] = 1
        data['post_battle'] = {'kind': 'elemental_boss', 'stage': 'awarded',
                               'encounter': ticket('nivareth'),
                               'party_before': ticket('nivareth')['party_resources']}
        data['party']['characters']['mira']['current_hp'] = 21
        self.assertTrue(ElementalBosses.valid_journey(data))
        for field in ('gear_gems', 'learned_abilities'):
            changed = deepcopy(data);changed['character_abilities'][field]['caelan'] = []
            self.assertFalse(ElementalBosses.valid_journey(changed))
        changed = deepcopy(data);changed['inventory']['items'].clear()
        self.assertFalse(ElementalBosses.valid_journey(changed))
        for amount in (0, 2, 999999, True):
            changed = deepcopy(data);changed['inventory']['items']['white_focus_gem'] = amount
            self.assertFalse(ElementalBosses.valid_journey(changed))
        changed = deepcopy(data);changed['battle_rewards']['receipts'].clear()
        self.assertFalse(ElementalBosses.valid_journey(changed))
        self.assertTrue(owner.finish('boss:nivareth'))
        data['elemental_bosses'] = owner.to_dict();data.pop('post_battle')
        self.assertTrue(ElementalBosses.valid_journey(data))
        changed = deepcopy(data);changed['cave_lesson']['battle_cleared'] = False
        self.assertFalse(ElementalBosses.valid_journey(changed))

    def test_state_restore_is_atomic_and_rejects_inconsistent_history(self):
        owner = ElementalBosses(None)
        before = owner.to_dict()
        invalid = []
        changed = deepcopy(before);changed['version'] = True;invalid.append(changed)
        changed = deepcopy(before);changed['bosses']['embravyr']['pending_acquisition'] = True;invalid.append(changed)
        changed = deepcopy(before);changed['bosses']['embravyr']['intro_seen'] = True;invalid.append(changed)
        changed = deepcopy(before);changed['victory_order'] = ['embravyr'];invalid.append(changed)
        changed = deepcopy(before);changed['pending'] = ticket();invalid.append(changed)
        for changed in invalid:
            self.assertFalse(owner.restore(changed))
            self.assertEqual(owner.to_dict(), before)


if __name__ == '__main__':unittest.main()
