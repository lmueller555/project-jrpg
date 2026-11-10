"""Independent Bestiary item rolls, isolated from combat randomness."""
from hashlib import sha256
import random

from bestiary import build_enemy


def roll_table(rows, rng):
    drops = {}
    for row in rows:
        if rng.randrange(100) < row['chance']:
            drops[row['item']] = drops.get(row['item'], 0)+row['quantity']
    return drops


def encounter_drops(kind, encounter, receipt, guaranteed):
    """The saved encounter identity fixes one roll per enemy and table row.

    New Spoils save the resulting offer. Version-two and older Spoils never
    call this function, retaining their original guaranteed-only grants.
    """
    result = dict(guaranteed)
    if kind not in ('cave', 'cave_boss', 'elemental_boss'):return result
    members = (encounter['members'] if kind == 'cave' else
               [{'enemy_id': encounter['enemy_id'], 'level': encounter['level']}])
    seed = sha256(('cave-loot-v1:'+receipt+':'+str(encounter['combat_seed'])).encode()).digest()
    rng = random.Random(int.from_bytes(seed, 'big'))
    for member in members:
        record = build_enemy(member['enemy_id'], member['level'])
        for item, count in roll_table(record['metadata']['rewards'].get('drop_table', []), rng).items():
            result[item] = result.get(item, 0)+count
    return result
