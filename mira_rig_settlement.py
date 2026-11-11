"""Validate rig outcomes without persisting action clocks or temporary barriers."""
from mira_rig_rules import SKILLS, healing_amount
from mira_rig_state import MiraRigState

RIG_FIELDS = {'rig_before', 'rig_after', 'rig_skill_uses', 'rig_healing', 'rig_stats'}
MAX_USES = 999999


def valid_rig_outcome(record, mp_allowance):
    """Bound restorative gains by canonical casts, entry stats and available MP.

    This is a checkpoint summary, not a replay log. It authorizes only gains
    possible with the recorded techniques and bounded effective entry stats.
    These preserve temporary modifiers that need not survive battle. Resources remain separately
    checked against the validated progression and party snapshots.
    """
    try:
        for field in ('rig_before', 'rig_after'):
            if not MiraRigState().restore(record[field]):return False
        uses, healing = record['rig_skill_uses'], record['rig_healing']
        if (not isinstance(uses, dict) or not isinstance(healing, dict)
                or any(not isinstance(key, str) or key not in SKILLS
                       or type(count) is not int or not 1 <= count <= MAX_USES
                       for key, count in uses.items())):return False
        active = record['party_active']
        if not isinstance(active, list):return False
        basis = record['rig_stats']
        canonical = record['progression']['characters']
        if not isinstance(basis, dict) or set(basis) != set(active):return False
        for key in active:
            values = basis[key]
            if (not isinstance(values, dict) or set(values) != {'hp', 'spr'}
                    or type(values['hp']) is not int or not 1 <= values['hp'] <= 9999
                    or type(values['spr']) is not int or not 0 <= values['spr'] <= 999
                    or values['hp'] < min(9999, canonical[key]['stats_before']['hp'])
                    or values['spr'] < min(999, canonical[key]['stats_before']['spr'])
                    or record['party_before'][key]['hp'] > values['hp']):return False
        if 'mira' not in active:
            return not uses and not healing and record['rig_before'] == record['rig_after']
        if any(not isinstance(key, str) or key not in active or type(value) is not int
               or value <= 0 for key, value in healing.items()):return False
        spent = sum(SKILLS[key]['mp_cost']*count for key, count in uses.items())
        before, after = record['party_before']['mira'], record['party_resources']['mira']
        if spent+after['mp'] > before['mp']+mp_allowance:return False
        casts = uses.get('repair_pulse', 0)
        spirit = basis['mira']['spr']
        minimum_casts = 0
        for key, amount in healing.items():
            maximum = healing_amount(spirit, basis[key]['hp'])
            minimum_casts += (amount+maximum-1)//maximum
        return minimum_casts <= casts
    except (KeyError, TypeError, ValueError, AttributeError, ZeroDivisionError):
        return False
