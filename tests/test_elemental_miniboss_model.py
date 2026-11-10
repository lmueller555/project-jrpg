"""Level-four elemental bosses, shared Edge rules and honest MP-free lessons."""
from copy import deepcopy
from fractions import Fraction
import random
import unittest

from battle_model import BattleModel, ELEMENTAL_EDGE_ACTIONS, load_actions
from bestiary import ELEMENT_IDS, build_enemy, load_bestiary
from character_abilities import CharacterAbilities
from character_attributes import ATTRIBUTE_IDS, CharacterAttributes
from combat_damage import magical_damage, physical_damage
from inventory import Inventory
from leveling import character_stats, level_for_total_xp, total_xp_for_level
from test_aether_edge_battle_model import FixedVariance


BOSSES = ('embravyr', 'nivareth')
STATS = {
    'embravyr': (612, 37, 15, 15, 16, 28, 11, 11, 17, 15, 16),
    'nivareth': (658, 61, 12, 18, 19, 11, 28, 12, 17, 15, 16)}
GEMS = {'embravyr': ('fire', 'flame_edge', 'red_focus_gem'),
        'nivareth': ('ice', 'ice_edge', 'white_focus_gem')}


def model_catalog():
    """Exercise the complete production Bestiary with each boss's own art."""
    return load_bestiary()


def party_profiles(level, resources=None):
    profiles = []
    for identifier in ('caelan', 'mira'):
        stats = character_stats(identifier, level)
        hp, mp = ((stats['hp'], stats['mp']) if resources is None else resources[identifier])
        profiles.append({'identifier': 'player' if identifier == 'caelan' else identifier,
            'name': identifier.title(), 'attributes': stats, 'hp': hp, 'mp': mp,
            'attack': 'attack' if identifier == 'caelan' else 'bolt_shot'})
    return profiles


class ElementalMinibossModelTests(unittest.TestCase):
    def model(self, identifier='embravyr', level=3, **options):
        options.setdefault('party_members', party_profiles(level))
        options.setdefault('learned_abilities', ['aether_edge', *ELEMENTAL_EDGE_ACTIONS])
        options.setdefault('weapon_equipped', True)
        options.setdefault('owned_gems', ('water', 'fire', 'ice'))
        options.setdefault('rng', FixedVariance())
        options.setdefault('elemental_tutorial', True)
        return BattleModel.from_bestiary(CharacterAttributes(), identifier, 4,
            bestiary_data=model_catalog(), **options)

    def ready(self, model):
        for actor in (*model.party, *model.enemies, *model.bots):actor.atb = 0
        model.player.atb = 1
        model.update(0)
        self.assertTrue(model.waiting_for_player)

    def finish(self, model):
        action = model.current_action
        model.update(action.duration-action.elapsed)
        self.assertTrue(action.resolved)
        return action

    def enemy_turn(self, model):
        if model.current_action is not None:
            self.assertEqual(model.current_action.actor, 'enemy')
            return self.finish(model)
        for actor in (*model.party, *model.enemies, *model.bots):actor.atb = 0
        model.enemy.atb = 1
        model.update(0)
        self.assertEqual(model.current_action.actor, 'enemy')
        return self.finish(model)

    def prepare_and_guard(self, model):
        model._enemy_action_index = 2
        self.enemy_turn(model)
        marked = model.combatant(model.telegraphed_target)
        for actor in (*model.party, *model.enemies, *model.bots):actor.atb = 0
        model.enemy.atb = 1
        before = marked.hp
        model.update(.05)
        self.assertIsNone(model.current_action)
        self.assertEqual(marked.hp, before)
        marked.atb = 1
        model.update(0)
        self.assertTrue(model.choose_action('guard', actor_id=marked.identifier))
        self.finish(model)
        return self.enemy_turn(model)

    def test_exact_level_four_profiles_full_affinities_rewards_and_pure_aether_family(self):
        for identifier in BOSSES:
            with self.subTest(identifier=identifier):
                record = build_enemy(identifier, 4)
                self.assertEqual(record['combat']['attributes'], dict(zip(ATTRIBUTE_IDS, STATS[identifier])))
                self.assertEqual(record['xp_reward'], 420)
                self.assertEqual(record['combat']['rewards']['drops'], {GEMS[identifier][2]: 1})
                metadata = record['metadata']
                self.assertEqual((metadata['tier'], metadata['family']), ('boss', 'aether_elemental'))
                self.assertEqual(metadata['level_range'], {'min': 4, 'max': 4})
                self.assertEqual(metadata['stat_profile'], 'armored' if identifier == 'embravyr' else 'warded')
                self.assertEqual(metadata['combat_design']['status'], 'ready')
                self.assertFalse(metadata['presentation_pending'])
                self.assertFalse(metadata['combat_pending'])
                self.assertEqual(record['presentation']['sprite_id'], identifier)
                self.assertEqual(metadata['combat_design']['recovery']['damage_taken_multiplier'], 1.5)
                self.assertTrue(metadata['combat_design']['encounter']['flee_allowed'])
                profile = metadata['elemental_profile']
                exceptional = {'water': 200, 'ice': 150, 'nature': 50} if identifier == 'embravyr' else {'fire': 200, 'water': 50}
                self.assertEqual(profile['damage_percentages'], {key: exceptional.get(key, 100) for key in ELEMENT_IDS})
                self.assertEqual(profile['absorption'], {'elements': [GEMS[identifier][0]], 'healing_percent': 100})
                for level in (None, 3, 5, True, 4.0):
                    with self.assertRaises(ValueError):build_enemy(identifier, level)

    def test_focus_cores_are_protected_and_only_the_matching_story_boss_can_drop_them(self):
        inventory = Inventory()
        self.assertTrue(inventory.add_many({'red_focus_gem': 1, 'white_focus_gem': 1}))
        for item in ('red_focus_gem', 'white_focus_gem'):
            self.assertEqual(inventory.definitions[item]['category'], 'key_items')
            self.assertFalse(inventory.remove(item))
            self.assertFalse(inventory.consume_bundle({item: 1}))
        for identifier in BOSSES:
            for drops in ({GEMS[identifier][2]: 2}, {GEMS[identifier][2]: 0},
                          {GEMS[BOSSES[1-BOSSES.index(identifier)]][2]: 1}, {}, None):
                bad = load_bestiary();bad['enemies'][identifier]['rewards']['drops'] = drops
                with self.subTest(identifier=identifier, drops=drops), self.assertRaises(ValueError):load_bestiary(bad)
        bad = load_bestiary();bad['enemies']['cave_bat']['rewards']['drops'] = {'red_focus_gem': 1}
        with self.assertRaises(ValueError):load_bestiary(bad)
        bad = load_bestiary();bad['enemies']['vespermaw']['rewards']['drops'] = {'white_focus_gem': 1}
        with self.assertRaises(ValueError):load_bestiary(bad)

    def test_ability_registration_never_grants_gems_or_skills_from_material_items(self):
        inventory = Inventory();owner = CharacterAbilities(inventory)
        self.assertTrue(owner.acquire_weapon('caelan', 'caelan_gearblade', learn_starter=True))
        self.assertTrue(inventory.add_many({'aether_ruby': 1, 'aether_opal': 1}))
        self.assertEqual(owner.owned_gems(), ('water',))
        for skill in ('flame_edge', 'ice_edge'):self.assertNotIn(skill, owner.known_abilities())
        for gem, skill, core in GEMS.values():
            self.assertTrue(inventory.add(core))
            self.assertNotIn(skill, owner.known_abilities())
            self.assertTrue(owner.grant_gem(gem))
            self.assertNotIn(skill, owner.known_abilities())
            self.assertTrue(owner.learn_ability('caelan', skill))
            self.assertIn(skill, owner.known_abilities())
        saved = owner.to_dict();restored = CharacterAbilities(inventory)
        self.assertTrue(restored.restore(saved))
        self.assertEqual(restored.to_dict(), saved)

    def test_all_elemental_edges_are_free_only_in_authored_teaching_battles(self):
        for identifier in BOSSES:
            model = self.model(identifier)
            model.player.mp = model.combatant('mira').mp = 0
            for skill in ELEMENTAL_EDGE_ACTIONS:self.assertEqual(model.action_mp_cost(skill, 'player'), 0)
            self.assertEqual(model.action_mp_cost('aether_edge', 'player'), 4)
            self.assertEqual(model.action_mp_cost('overclock', 'mira'), 5)
            for skill, gem in (('aqua_edge', 'water'), ('flame_edge', 'fire'), ('ice_edge', 'ice')):
                self.ready(model);self.assertTrue(model.set_active_gem(gem))
                self.assertTrue(model.choose_action(skill))
                self.assertEqual(model.current_action.choreography, 'aether_edge')
                self.finish(model)
                self.assertEqual(model.player.mp, 0)
            normal = self.model(identifier, elemental_tutorial=False)
            for skill in ELEMENTAL_EDGE_ACTIONS:self.assertEqual(normal.action_mp_cost(skill, 'player'), 4)
        for value in (1, 'yes', [], None):
            with self.assertRaises(ValueError):self.model(elemental_tutorial=value)
        with self.assertRaises(ValueError):
            BattleModel.from_bestiary(CharacterAttributes(), 'cave_bat', 2, elemental_tutorial=True)

    def test_zero_mp_context_does_not_bypass_knowledge_ownership_or_selected_focus(self):
        for skill, gem in (('flame_edge', 'fire'), ('ice_edge', 'ice')):
            unknown = self.model(learned_abilities=['aether_edge'])
            self.ready(unknown);self.assertFalse(unknown.choose_action(skill))
            unowned = self.model(owned_gems=('water',))
            self.ready(unowned);self.assertFalse(unowned.set_active_gem(gem))
            self.assertFalse(unowned.choose_action(skill))
            known = self.model();self.ready(known)
            self.assertFalse(known.choose_action(skill))
            self.assertTrue(known.set_active_gem(gem))
            self.assertEqual(known.action_reason(skill), '')

    def test_new_edge_component_powers_and_element_tags_are_validated(self):
        actions = load_actions()
        for skill, gem in (('flame_edge', 'fire'), ('ice_edge', 'ice')):
            self.assertEqual((actions[skill]['kind'], actions[skill]['potency'],
                              actions[skill]['magical_potency'], actions[skill]['mp_cost'],
                              actions[skill]['element']), ('spellblade', 1, .5, 4, gem))
            bad = deepcopy(actions);bad[skill]['element'] = 'water'
            with self.assertRaises(ValueError):load_actions({'version': 1, 'actions': bad})
        for identifier, skill, gem, affinity in (
                ('embravyr', 'aqua_edge', 'water', 2),
                ('embravyr', 'ice_edge', 'ice', Fraction(3, 2)),
                ('nivareth', 'aqua_edge', 'water', Fraction(1, 2)),
                ('nivareth', 'flame_edge', 'fire', 2)):
            model = self.model(identifier);self.ready(model);model.set_active_gem(gem)
            self.assertTrue(model.choose_action(skill));action = self.finish(model)
            self.assertEqual(action.damage, physical_damage(model.player, model.enemy)+
                magical_damage(model.player, model.enemy, .5, affinity=affinity))

    def test_matching_element_absorbs_only_magic_and_cannot_overheal(self):
        for identifier in BOSSES:
            model = self.model(identifier)
            model.enemy.hp = 100
            self.ready(model)
            gem, skill, _ = GEMS[identifier]
            self.assertTrue(model.set_active_gem(gem));self.assertTrue(model.choose_action(skill))
            physical = physical_damage(model.player, model.enemy)
            healing = magical_damage(model.player, model.enemy, .5)
            self.finish(model)
            self.assertEqual(model.enemy.hp, 100-physical+healing)
            impact = next(e for e in model.events if e['type'] == 'impact')
            self.assertTrue(impact['absorbed']);self.assertEqual(impact['healing'], healing)

    def test_windup_waits_for_a_real_guard_then_hits_before_recovery_ends(self):
        for identifier in BOSSES:
            model = self.model(identifier)
            action = self.prepare_and_guard(model)
            self.assertTrue(action.action.endswith(('furnace_lunge', 'frostspire_thrust')))
            self.assertEqual(model.enemy_recovery_states, {'enemy': 1.5})
            impact = next(e for e in reversed(model.events) if e['type'] == 'impact')
            self.assertTrue(impact['guarded'])
            recovery = self.enemy_turn(model)
            self.assertEqual(recovery.kind, 'recover')
            self.assertEqual(model.enemy_recovery_states, {'enemy': 1.5})
            for actor in (*model.party, *model.enemies, *model.bots):actor.atb = 0
            model.enemy.atb = 1;model.update(0)
            self.assertEqual(model.enemy_recovery_states, {})

    def test_recovery_multiplies_each_complete_edge_hit_once_and_obeys_cap(self):
        for identifier in (*BOSSES, 'vespermaw'):
            for skill, gem in (('aether_edge', 'water'), ('aqua_edge', 'water'),
                                ('flame_edge', 'fire'), ('ice_edge', 'ice')):
                hits = []
                for vulnerable in (False, True):
                    options = dict(weapon_equipped=True, owned_gems=('water', 'fire', 'ice'),
                        active_gem=gem, learned_abilities=[skill], rng=FixedVariance())
                    model = (self.model(identifier, **options) if identifier in BOSSES else
                        BattleModel.from_bestiary(CharacterAttributes(), identifier, 7, **options))
                    model.enemy.hp = model.enemy.attributes['hp'] = 999999
                    model._enemy_states['enemy'].vulnerable = vulnerable
                    model._start_action('player', skill)
                    hits.append(self.finish(model).damage)
                self.assertEqual(hits[1], hits[0]*3//2)
        capped = self.model();capped.player.attributes.update(str=999, mag=999)
        capped._enemy_states['enemy'].vulnerable = True
        capped._start_action('player', 'aqua_edge')
        self.assertEqual(self.finish(capped).damage, 9999)

    def play(self, identifier, level, resources, gems, known, seed, *, require_both_alive=True):
        members = party_profiles(level, resources)
        before = deepcopy(members)
        model = self.model(identifier, level=level, party_members=members,
            learned_abilities=known, owned_gems=tuple(gems), rng=random.Random(seed),
            initial_atb=True, initial_atb_seed=seed)
        for _ in range(20000):
            if model.waiting_for_player:
                actor = model.ready_actor
                if actor in model.enemy_telegraphs.values():command = 'guard'
                elif actor == 'player':
                    if identifier == 'embravyr':command = 'aqua_edge'
                    elif 'flame_edge' in known:
                        model.set_active_gem('fire');command = 'flame_edge'
                    elif model.player.mp >= 4:command = 'aether_edge'
                    else:command = 'attack'
                elif (model.active_bot() and not model.active_bot().haste_turns
                      and model.active_player.mp >= 5):command = 'overclock'
                else:command = 'attack'
                self.assertTrue(model.choose_action(command))
            model.update(.05);model.drain_events()
            if model.ended:break
        self.assertEqual(model.phase, 'victory')
        if require_both_alive:self.assertTrue(all(member.hp > 0 for member in model.party))
        self.assertEqual(members, before)
        return model

    def test_level_one_through_four_party_can_win_either_first_boss_at_zero_mp(self):
        for level in (1, 2, 3, 4):
            resources = {key: (character_stats(key, level)['hp'], 0) for key in ('caelan', 'mira')}
            for identifier in BOSSES:
                for seed in range(5):
                    with self.subTest(level=level, identifier=identifier, seed=seed):
                        model = self.play(identifier, level, resources, ['water'],
                                          ['aether_edge', 'aqua_edge'], seed)
                        self.assertEqual((model.player.mp, model.combatant('mira').mp), (0, 0))

    def test_both_orders_at_level_two_through_four_carry_resources_without_refills(self):
        for initial_level in (2, 3, 4):
            for zero_mp in (False, True):
                for order in (BOSSES, tuple(reversed(BOSSES))):
                    for seed in range(5):
                        with self.subTest(level=initial_level, zero_mp=zero_mp, order=order, seed=seed):
                            level = initial_level
                            xp = total_xp_for_level(level)
                            resources = ({key: (character_stats(key, level)['hp'], 0)
                                          for key in ('caelan', 'mira')} if zero_mp else None)
                            gems, known = ['water'], ['aether_edge', 'aqua_edge']
                            for identifier in order:
                                # Reduced EXP grants fewer stats between fights.
                                # Victory may cost a KO on the final no-rest fight;
                                # a first-fight KO must not seed the second fight.
                                model = self.play(identifier, level, resources, gems, known, seed,
                                    require_both_alive=identifier == order[0])
                                resources = {'caelan': (model.player.hp, model.player.mp),
                                             'mira': (model.combatant('mira').hp, model.combatant('mira').mp)}
                                if zero_mp:self.assertEqual((resources['caelan'][1], resources['mira'][1]), (0, 0))
                                # Rewards grow maxima/ratings; the captured resources stay unchanged.
                                xp += 420;level = level_for_total_xp(xp)
                                gems.append(GEMS[identifier][0]);known.append(GEMS[identifier][1])

    def test_new_bosses_allow_flee_but_vespermaw_still_does_not(self):
        for identifier in BOSSES:
            model = self.model(identifier);self.ready(model)
            self.assertTrue(model.flee_allowed)
            self.assertTrue(model.choose_action('flee'));self.finish(model)
            self.assertEqual(model.phase, 'fled')
        final = BattleModel.from_bestiary(CharacterAttributes(), 'vespermaw', 7)
        self.assertFalse(final.flee_allowed)


if __name__ == '__main__':unittest.main()
