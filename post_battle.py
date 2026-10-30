"""Durable victory facts used to resume Spoils without replaying a battle."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re

from aether_lattice import AetherLattice
from character_attributes import CharacterAttributes
from quests import MILL_QUEST, QuestLog


ROOT = Path(__file__).resolve().parent
FIELDS = {'version', 'kind', 'receipt', 'stage', 'rewards', 'before', 'resources',
          'scene', 'position', 'facing', 'incapacitated'}


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
    if (not isinstance(record, dict) or set(record) != FIELDS
            or type(record['version']) is not int or record['version'] != 1
            or record['kind'] not in ('bat', 'mill')
            or record['stage'] not in ('pending', 'awarded')
            or not isinstance(record['receipt'], str)
            or not _resources(record['before']) or not _resources(record['resources'])
            or record['before']['hp'] < 1 or record['resources']['hp'] < 1
            or type(record['incapacitated']) is not bool
            or record['facing'] not in ('front', 'back', 'left', 'right')
            or not isinstance(record['scene'], str)
            or not isinstance(record['position'], list) or len(record['position']) != 2
            or any(type(n) not in (int, float) or not math.isfinite(n) or abs(n) >= 1e7
                   for n in record['position'])):
        return False
    mill = record['kind'] == 'mill'
    if mill:
        if record['receipt'] != 'mq02:ridgeback_tusker' or record['scene'] != 'upstream':return False
    elif (re.fullmatch(r'battle:[0-9a-f]{32}', record['receipt']) is None
          or record['scene'] != 'eldenmere.playable' or record['incapacitated']):
        return False
    rewards = record['rewards']
    catalog = json.loads((ROOT/'assets/combat/enemies.json').read_text())['enemies']
    canonical = catalog['ridgeback_tusker' if mill else 'bat']['rewards']
    if (not isinstance(rewards, dict) or set(rewards) != {'rp', 'drops'}
            or type(rewards['rp']) is not int or not 0 <= rewards['rp'] <= canonical['rp']
            or not isinstance(rewards['drops'], dict)
            or any(key not in canonical['drops'] or type(amount) is not int
                   or not 1 <= amount <= canonical['drops'][key]
                   for key, amount in rewards['drops'].items())):
        return False
    if record['resources']['mp'] > record['before']['mp']:return False
    if not record['incapacitated'] and record['resources']['hp'] > record['before']['hp']:return False
    if data is None:return True
    try:
        if (data['player']['scene'] != record['scene']
                or data['player']['position'] != record['position']
                or data['player']['facing'] != record['facing']):return False
        lattice = AetherLattice()
        if not lattice.restore(data['aether_lattice']):return False
        attributes = CharacterAttributes('caelan')
        if not attributes.restore(data['character_attributes'], lattice_bonuses=lattice.bonuses()):return False
        if (record['resources']['hp'] > attributes.value('hp')
                or record['resources']['mp'] > attributes.value('mp')):return False
        if record['incapacitated'] and record['resources']['hp'] != max(1, attributes.value('hp')//4):return False
        awarded = record['stage'] == 'awarded'
        if lattice.has_receipt(record['receipt']) != awarded:return False
        resources = record['resources'] if awarded else record['before']
        if (attributes.current_hp, attributes.current_mp) != (resources['hp'], resources['mp']):return False
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
        elif not (data.get('mill_quest', {}).get('encounter_cleared')
                  or data.get('mill_quest', {}).get('legacy_bypass')):
            return False
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
    return True
