"""Pending boss designs retain full semantics without becoming live actions."""
from copy import deepcopy
import unittest

from enemy_combat_design import validate_combat_design


def fixture():
    def damage(name, kind, target, potency, cost=0):
        return {'name': name, 'kind': kind, 'target': target, 'potency': potency,
                'mp_cost': cost, 'element': 'non_elemental'}
    def utility(name, kind):
        return {'name': name, 'kind': kind, 'target': 'self', 'potency': 0, 'mp_cost': 0}
    behavior = {'sequence': ['claw', 'roar', 'gather', 'pounce', 'exhausted'],
                'fallback': 'claw', 'targeting': 'cycle_living_party'}
    design = {
        'status': 'pending_runtime',
        'requirements': ['party_wide_damage', 'recovery_vulnerability',
                         'guaranteed_target_response'],
        'actions': {
            'claw': damage('Raking Claw', 'physical', 'opponent', .65),
            'roar': damage('Confluence Roar', 'magical', 'all_opponents', .5, 6),
            'gather': utility('Gather Resonance', 'prepare'),
            'pounce': damage('Ruinous Pounce', 'physical', 'opponent', 1.4),
            'exhausted': utility('Exhausted', 'recover')},
        'windup': {'prepare_action': 'gather', 'attack_action': 'pounce',
                   'minimum_target_actions': 1, 'retargeting': 'repeat_warning'},
        'recovery': {'after_action': 'pounce', 'recovery_action': 'exhausted',
                     'damage_taken_multiplier': 1.25, 'ends_before_action': 'claw'},
        'encounter': {'trigger': 'story', 'repeatable': False, 'formation_size': 1}}
    return design, behavior


class EnemyCombatDesignTests(unittest.TestCase):
    def setUp(self):self.design, self.behavior = fixture()

    def test_complete_design_is_preserved_and_returned_actions_are_detached(self):
        before = deepcopy((self.design, self.behavior))
        actions = validate_combat_design(self.design, self.behavior)
        self.assertEqual(actions, self.design['actions'])
        self.assertEqual(actions['roar']['target'], 'all_opponents')
        self.assertEqual(actions['exhausted']['kind'], 'recover')
        self.assertEqual((self.design, self.behavior), before)
        actions['roar']['potency'] = 99
        actions.clear()
        self.assertEqual((self.design, self.behavior), before)

    def assert_invalid(self, design, behavior):
        before = deepcopy((design, behavior))
        with self.assertRaises(ValueError):validate_combat_design(design, behavior)
        self.assertEqual((design, behavior), before)

    def test_invalid_envelopes_requirements_and_references_fail_without_mutation(self):
        for field, value in (
                ('status', 'ready'), ('requirements', []),
                ('requirements', ['party_wide_damage']*3),
                ('requirements', ['party_wide_damage', [], 'guaranteed_target_response']),
                ('actions', {}), ('actions', []), ('extra', True)):
            with self.subTest(field=field, value=value):
                design = deepcopy(self.design);design[field] = value
                self.assert_invalid(design, self.behavior)
        for field in self.design:
            with self.subTest(missing=field):
                design = deepcopy(self.design);del design[field]
                self.assert_invalid(design, self.behavior)
        for field, value in (('sequence', []), ('sequence', ['missing']),
                             ('sequence', [['claw']]), ('fallback', 'missing'),
                             ('fallback', 'roar'), ('targeting', 'weakest')):
            with self.subTest(field=field, value=value):
                behavior = deepcopy(self.behavior);behavior[field] = value
                self.assert_invalid(self.design, behavior)

    def test_damage_and_utility_action_shapes_are_strict(self):
        cases = [
            ('claw', 'name', ''), ('claw', 'name', ' '*4),
            ('claw', 'kind', 'unsupported'), ('claw', 'target', 'self'),
            ('claw', 'potency', 0), ('claw', 'potency', True),
            ('claw', 'potency', float('inf')), ('claw', 'potency', 10**1000),
            ('claw', 'mp_cost', True), ('claw', 'mp_cost', -1),
            ('claw', 'element', 'aether'), ('claw', 'element', []),
            ('claw', 'animation', 'attack'), ('claw', 'duration', .8),
            ('gather', 'target', 'opponent'), ('gather', 'potency', 1),
            ('gather', 'potency', False), ('gather', 'mp_cost', 1),
            ('gather', 'element', 'non_elemental')]
        for action, field, value in cases:
            with self.subTest(action=action, field=field, value=repr(value)):
                design = deepcopy(self.design);design['actions'][action][field] = value
                self.assert_invalid(design, self.behavior)
        for action in self.design['actions']:
            for field in self.design['actions'][action]:
                with self.subTest(action=action, missing=field):
                    design = deepcopy(self.design);del design['actions'][action][field]
                    self.assert_invalid(design, self.behavior)

    def test_windup_must_warn_before_its_single_target_physical_attack(self):
        for field, value in (('prepare_action', 'claw'), ('attack_action', 'roar'),
                             ('attack_action', 'missing'), ('minimum_target_actions', True),
                             ('minimum_target_actions', 0), ('retargeting', 'silent'),
                             ('extra', True)):
            with self.subTest(field=field, value=value):
                design = deepcopy(self.design);design['windup'][field] = value
                self.assert_invalid(design, self.behavior)
        design = deepcopy(self.design);design['actions']['pounce']['target'] = 'all_opponents'
        self.assert_invalid(design, self.behavior)
        behavior = deepcopy(self.behavior)
        behavior['sequence'] = ['claw', 'gather', 'roar', 'pounce', 'exhausted']
        self.assert_invalid(self.design, behavior)
        # Reusing valid local IDs cannot introduce an unannounced Pounce.
        behavior = deepcopy(self.behavior)
        behavior['sequence'].extend(['claw', 'pounce', 'exhausted'])
        self.assert_invalid(self.design, behavior)
        behavior = deepcopy(self.behavior)
        behavior['sequence'] = ['pounce', 'exhausted', *behavior['sequence']]
        self.assert_invalid(self.design, behavior)

    def test_recovery_must_follow_pounce_and_expire_at_the_next_damage_action(self):
        for field, value in (('after_action', 'claw'), ('recovery_action', 'gather'),
                             ('ends_before_action', 'roar'),
                             ('damage_taken_multiplier', True),
                             ('damage_taken_multiplier', 1),
                             ('damage_taken_multiplier', float('inf')),
                             ('damage_taken_multiplier', 10.01), ('extra', True)):
            with self.subTest(field=field, value=value):
                design = deepcopy(self.design);design['recovery'][field] = value
                self.assert_invalid(design, self.behavior)
        behavior = deepcopy(self.behavior)
        behavior['sequence'] = ['claw', 'gather', 'pounce', 'roar', 'exhausted']
        self.assert_invalid(self.design, behavior)

    def test_story_encounter_cannot_be_random_repeatable_or_a_group(self):
        for field, value in (('trigger', 'random'), ('repeatable', True),
                             ('repeatable', 0), ('formation_size', True),
                             ('formation_size', 2), ('extra', True)):
            with self.subTest(field=field, value=value):
                design = deepcopy(self.design);design['encounter'][field] = value
                self.assert_invalid(design, self.behavior)


if __name__ == '__main__':unittest.main()
