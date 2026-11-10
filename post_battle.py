"""Durable victory facts used to resume Spoils without replaying a battle."""
from __future__ import annotations

import math
import re

from battle_rewards import BattleRewards
from bestiary import build_enemy, load_bestiary
from character_attributes import CharacterAttributes
from inventory import Inventory
from leveling import monster_xp
from party_state import MAX_PARTY, PartyState
from quests import MILL_QUEST, QuestLog


FIELDS = {'version', 'kind', 'receipt', 'stage', 'rewards', 'before', 'resources',
          'scene', 'position', 'facing', 'incapacitated'}
PARTY_FIELDS = {'party_before', 'party_resources', 'party_active'}
CAVE_FIELDS = FIELDS | PARTY_FIELDS | {'encounter'}
PROGRESSION_FIELDS = {'progression', 'offered_drops'}


def _previous_reward_xp(kind, encounter=None):
    """Recognize exact totals from the two previously shipped reward curves.

    These fixed/cave enemies were normal reward references at levels 1–100.
    New victories always use battle_reward_definition and the current curve.
    """
    boss = kind in ('cave_boss', 'elemental_boss')
    levels = ([member['level'] for member in encounter['members']] if kind == 'cave'
              else [encounter['level']] if boss else [3 if kind == 'mill' else 1])
    original = [2*int(30*level**0.5+0.5) for level in levels]
    reduced = sum((amount*70+50)//100 for amount in original)*(10 if boss else 1)
    # Authored bosses shipped after the 30% cut. They never used the older curve.
    previous = (reduced,) if boss else (sum(original), reduced)
    # MQ02 formerly awarded 37 EXP using the 24 × level^0.4 normal L3 reference.
    return (*previous, 37) if kind == 'mill' else previous


def battle_reward_definition(kind, encounter=None):
    """Resolve authored EXP and drops without retuning legacy combat stats.

    The town Bat retains its level-one normal reward reference. MQ02 uses its
    level-one Brute boss. Cave formations use each selected Bestiary level.
    """
    if kind == 'cave_boss':
        resolved = build_enemy('vespermaw', 7)
        return {'drops': dict(resolved['combat']['rewards']['drops']), 'xp': resolved['xp_reward']}
    if kind == 'mill':
        resolved = build_enemy('ridgeback_tusker', 1)
        return {'drops': dict(resolved['combat']['rewards']['drops']), 'xp': resolved['xp_reward']}
    if kind == 'elemental_boss':
        from elemental_bosses import valid_ticket
        if not valid_ticket(encounter):raise ValueError('Invalid elemental encounter reward')
        resolved = build_enemy(encounter['enemy_id'], encounter['level'])
        return {'drops': dict(resolved['combat']['rewards']['drops']), 'xp': resolved['xp_reward']}
    if kind == 'cave':
        drops, xp = {}, 0
        for member in encounter['members']:
            resolved = build_enemy(member['enemy_id'], member['level'])
            xp += resolved['xp_reward']
            for item, amount in resolved['combat']['rewards']['drops'].items():
                drops[item] = drops.get(item, 0)+amount
        return {'drops': drops, 'xp': xp}
    return {'drops': dict(load_bestiary()['enemies']['bat']['rewards']['drops']),
            'xp': monster_xp(1)}


def _resources(value):
    return (isinstance(value, dict) and set(value) == {'hp', 'mp'}
            and type(value['hp']) is int and 0 <= value['hp'] <= 9999
            and type(value['mp']) is int and 0 <= value['mp'] <= 999)


def valid_pending_snapshot(record, data=None):
    """Validate the pending grant together with its already-saved journey.

    A pending record describes an unawarded victory; an awarded record requires
    its receipt and final resources. Neither stores presentation clocks.
    """
    if record is None:return True
    cave = isinstance(record, dict) and record.get('kind') == 'cave'
    elemental = isinstance(record, dict) and record.get('kind') == 'elemental_boss'
    boss = isinstance(record, dict) and record.get('kind') in ('cave_boss', 'elemental_boss')
    cave_battle = cave or boss
    modern = isinstance(record, dict) and type(record.get('version')) is int and record['version'] == 2
    extra = PROGRESSION_FIELDS if modern else set()
    shapes = (FIELDS | extra, FIELDS | PARTY_FIELDS | extra, CAVE_FIELDS | extra)
    if (not isinstance(record, dict) or set(record) not in shapes
            or type(record['version']) is not int or record['version'] not in (1, 2)
            or record['kind'] not in ('bat', 'mill', 'cave', 'cave_boss', 'elemental_boss')
            or (set(record) == CAVE_FIELDS | extra) != cave_battle
            or (boss and not modern)
            or record['stage'] not in ('pending', 'awarded')
            or not isinstance(record['receipt'], str)
            or not _resources(record['before']) or not _resources(record['resources'])
            or (record['before']['hp'] < 1 and 'party_active' not in record)
            or (record['resources']['hp'] < 1 and not cave_battle)
            or type(record['incapacitated']) is not bool
            or record['facing'] not in ('front', 'back', 'left', 'right')
            or not isinstance(record['scene'], str)
            or not isinstance(record['position'], list) or len(record['position']) != 2
            or any(type(n) not in (int, float) or abs(n) >= 1e7 or not math.isfinite(n)
                   for n in record['position'])):
        return False
    has_party = 'party_active' in record
    if modern and not has_party:return False
    if has_party:
        active = record['party_active']
        known = PartyState(CharacterAttributes()).known_ids
        if (not isinstance(active, list) or not 1 <= len(active) <= MAX_PARTY
                or any(not isinstance(identifier, str) or identifier not in known for identifier in active)
                or len(active) != len(set(active)) or active[0] != 'caelan'):
            return False
        for field in ('party_before', 'party_resources'):
            values = record[field]
            if (not isinstance(values, dict) or set(values) != set(active)
                    or not all(_resources(value) for value in values.values())):return False
        if (record['party_before']['caelan'] != record['before']
                or record['party_resources']['caelan'] != record['resources']):return False
        for identifier in active:
            before, after = record['party_before'][identifier], record['party_resources'][identifier]
            if after['mp'] > before['mp']:return False
            if (cave_battle or identifier != 'caelan' or not record['incapacitated']) and after['hp'] > before['hp']:
                return False
        if cave_battle and not any(value['hp'] for value in record['party_resources'].values()):return False
    mill = record['kind'] == 'mill'
    if mill:
        if record['receipt'] != 'mq02:ridgeback_tusker' or record['scene'] != 'upstream':return False
        if has_party and 'mira' not in record['party_active']:return False
    elif cave:
        from cave_random_encounters import valid_ticket
        ticket = record['encounter']
        if (not valid_ticket(ticket) or record['scene'] != 'sanctuary_cave'
                or record['receipt'] != ticket['receipt']
                or record['position'] != ticket['position']
                or record['incapacitated'] != (record['resources']['hp'] == 0)):
            return False
    elif boss:
        if elemental:
            from elemental_bosses import SCENE_ID, valid_ticket
        else:
            from sanctuary_boss import SCENE_ID, valid_ticket
        ticket = record['encounter']
        if (not valid_ticket(ticket) or record['scene'] != SCENE_ID
                or record['receipt'] != ticket['receipt']
                or record['position'] != ticket['position']
                or record['facing'] != ticket['facing']
                or record['party_active'] != ticket['party_active']
                or record['party_before'] != ticket['party_resources']
                or record['incapacitated'] != (record['resources']['hp'] == 0)):
            return False
    elif (re.fullmatch(r'battle:[0-9a-f]{32}', record['receipt']) is None
          or record['scene'] != 'eldenmere.playable' or (record['incapacitated'] and not has_party)):
        return False
    rewards = record['rewards']
    canonical = battle_reward_definition(record['kind'], record.get('encounter'))
    if (not isinstance(rewards, dict) or set(rewards) != {'drops'}
            or not isinstance(rewards['drops'], dict)
            or any(key not in canonical['drops'] or type(amount) is not int
                   or not 1 <= amount <= canonical['drops'][key]
                   for key, amount in rewards['drops'].items())):
        return False
    # A story focus is guaranteed; it cannot disappear through ordinary loot
    # capacity handling or be substituted with a similarly colored material.
    if elemental and rewards['drops'] != canonical['drops']:return False
    if modern:
        from character_progression import CharacterProgression
        plan = record['progression']
        approved_xp = (canonical['xp'], *_previous_reward_xp(record['kind'], record.get('encounter')))
        if (not CharacterProgression.valid_plan(plan)
                or plan['amount'] not in approved_xp
                or plan['active_ids'] != record['party_active']
                or not isinstance(record['offered_drops'], dict)
                or any(type(value) is not int for value in record['offered_drops'].values())
                or record['offered_drops'] != canonical['drops']
                or record['incapacitated'] != (plan['end_hp']['caelan'] == 0)):
            return False
        for identifier in record['party_active']:
            hp = plan['end_hp'][identifier]
            expected = record['party_resources'][identifier]['hp']
            if identifier == 'caelan' and record['incapacitated'] and not cave_battle:
                if hp != 0:return False
            elif hp != expected:return False
    if record['resources']['mp'] > record['before']['mp']:return False
    if (cave_battle or not record['incapacitated']) and record['resources']['hp'] > record['before']['hp']:return False
    if data is None:return True
    try:
        if (data['player']['scene'] != record['scene']
                or data['player']['position'] != record['position']
                or data['player']['facing'] != record['facing']):return False
        receipts = BattleRewards(Inventory())
        if not receipts.restore(data['battle_rewards']):return False
        attributes = CharacterAttributes('caelan')
        if not attributes.restore(data['character_attributes']):return False
        if (record['resources']['hp'] > attributes.value('hp')
                or record['resources']['mp'] > attributes.value('mp')):return False
        before_hp = (record['progression']['characters']['caelan']['stats_before']['hp']
                     if modern else attributes.value('hp'))
        if not cave_battle and record['incapacitated'] and record['resources']['hp'] != max(1, before_hp//4):return False
        if cave:
            from cave_random_encounters import CaveRandomEncounters
            state = data['cave_random_encounters']
            if (not CaveRandomEncounters.valid_snapshot(state)
                    or state.get('pending') != record['encounter']):return False
        awarded = record['stage'] == 'awarded'
        if boss:
            if elemental:
                from elemental_bosses import ElementalBosses, definition
                state = data['elemental_bosses']
                if (not ElementalBosses.valid_snapshot(state)
                        or state['pending'] != record['encounter']
                        or state['bosses'][record['encounter']['enemy_id']]['defeated'] != awarded):return False
                if awarded:
                    reward = definition(record['encounter']['enemy_id'])
                    abilities = data.get('character_abilities') or {}
                    if (reward['gem'] not in abilities.get('gear_gems', {}).get('caelan', [])
                            or reward['skill'] not in abilities.get('learned_abilities', {}).get('caelan', [])
                            or data.get('inventory', {}).get('items', {}).get(reward['item'], 0) < 1):return False
            else:
                from sanctuary_boss import SanctuaryBoss
                state = data['sanctuary_boss']
                if (not SanctuaryBoss.valid_snapshot(state)
                        or state['pending'] != record['encounter']
                        or state['defeated'] != awarded):return False
        if receipts.has_receipt(record['receipt']) != awarded:return False
        resources = record['resources'] if awarded else record['before']
        if (attributes.current_hp, attributes.current_mp) != (resources['hp'], resources['mp']):return False
        if has_party:
            party_data = data['party']
            if party_data['characters']['caelan'] != data['character_attributes']:return False
            party = PartyState(attributes)
            if not party.restore(party_data) or list(party.active_ids) != record['party_active']:return False
            expected = record['party_resources'] if awarded else record['party_before']
            for identifier in record['party_active']:
                member = party.characters[identifier]
                for field in ('party_before', 'party_resources'):
                    values = record[field][identifier]
                    if values['hp'] > member.value('hp') or values['mp'] > member.value('mp'):return False
                if (member.current_hp, member.current_mp) != (expected[identifier]['hp'], expected[identifier]['mp']):
                    return False
            if modern:
                if 'character_levels' not in data:return False
                progression = CharacterProgression(party)
                if (not progression.restore(data['character_levels'])
                        or not progression.matches_plan(record['progression'], after=awarded)):
                    return False
        quests = QuestLog()
        if not quests.restore(data['quests']):return False
        if mill:
            facts = data['mill_quest']
            if (facts.get('legacy_bypass') or not facts.get('warned')
                    or facts.get('aftermath_done') or facts.get('restored')
                    or bool(facts.get('encounter_cleared')) != awarded
                    or quests.status(MILL_QUEST) != 'active'
                    or quests.objective_status(MILL_QUEST, 'secure_trail')
                       != ('completed' if awarded else 'active')):return False
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
    return True
