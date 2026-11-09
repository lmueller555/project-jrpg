"""Canonical enemy definitions, leveled species and authored encounter records.

The dictionary stores enemy design; generation supplies fresh combat snapshots.
It does not place encounters, award XP, unlock a dungeon, or enable planned
elemental/Stagger mechanics. Fixed encounter records preserve existing journeys.
"""
from copy import deepcopy
import json
import math
from pathlib import Path
import re

from character_attributes import ATTRIBUTE_CAPS, ATTRIBUTE_IDS
from enemy_growth import MAX_ENEMY_HP, load_archetypes, profile_enemy_stats
from inventory import Inventory, MAX_QUANTITY
from leveling import MAX_LEVEL, monster_xp


ROOT = Path(__file__).resolve().parent
BESTIARY_PATH = ROOT/'assets/combat/bestiary.json'
CATALOG_PATH = BESTIARY_PATH
ELEMENT_IDS = ('non_elemental', 'fire', 'electric', 'water', 'ice', 'nature',
               'wind', 'holy', 'ground')
ELEMENT_NAMES = dict(zip(ELEMENT_IDS, (
    'Non-Elemental', 'Fire', 'Electric', 'Water', 'Ice', 'Nature', 'Wind',
    'Holy', 'Ground')))
FIXED_FIELDS = frozenset(('name', 'attributes', 'abilities', 'rewards'))
SPECIES_FIELDS = frozenset((
    'mode', 'name', 'description', 'family', 'tier', 'habitats', 'level_range',
    'archetype', 'stat_profile', 'fighting_style', 'species_multipliers',
    'tier_multipliers', 'behavior', 'presentation', 'rewards',
    'elemental_profile', 'planned_mechanics', 'encounter_guidance'))
_IDENTIFIER = re.compile(r'^[a-zA-Z0-9_.:/-]{1,128}$')
_DAMAGE_KINDS = ('physical', 'magical')


def _identifier(value):
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


def _text(value, maximum=2000):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum


def _integer(value, minimum=0, maximum=MAX_ENEMY_HP):
    return type(value) is int and minimum <= value <= maximum


def _multipliers(values):
    return (isinstance(values, dict) and set(values) <= set(ATTRIBUTE_IDS)
            and all(type(value) in (int, float) and 0 <= value <= MAX_ENEMY_HP
                    and math.isfinite(value) for value in values.values())
            and values.get('hp', 1) > 0)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:raise ValueError('Duplicate Bestiary key: '+key)
        result[key] = value
    return result


def _actions(actions):
    # The local import permits BattleModel's legacy loader to delegate here
    # after its action validator has been defined, without an import cycle.
    from battle_model import load_actions
    return load_actions(None if actions is None else {'version': 1, 'actions': actions})


def _drops(values, definitions=None):
    if not isinstance(values, dict):return False
    for identifier, amount in values.items():
        if not _identifier(identifier) or not _integer(amount, 1, MAX_QUANTITY):return False
        if definitions is not None and (identifier not in definitions
                or definitions[identifier]['category'] == 'key_items'):
            return False
    return True


def _validate_fixed(enemy, actions):
    if (not _text(enemy['name'], 120) or not isinstance(enemy['attributes'], dict)
            or set(enemy['attributes']) != set(ATTRIBUTE_IDS)
            or any(not _integer(value, 1 if key == 'hp' else 0,
                                MAX_ENEMY_HP if key in ('hp', 'mp') else ATTRIBUTE_CAPS[key])
                   for key, value in enemy['attributes'].items())
            or not isinstance(enemy['abilities'], list) or not enemy['abilities']
            or any(not isinstance(identifier, str) or identifier not in actions
                   or actions[identifier]['kind'] not in (*_DAMAGE_KINDS, 'prepare', 'recover')
                   for identifier in enemy['abilities'])
            or len(enemy['abilities']) != len(set(enemy['abilities']))
            or not any(actions[identifier]['mp_cost'] == 0
                       and actions[identifier]['kind'] in _DAMAGE_KINDS
                       for identifier in enemy['abilities'])
            or not isinstance(enemy['rewards'], dict) or set(enemy['rewards']) != {'drops'}
            or not _drops(enemy['rewards']['drops'])):
        raise ValueError('Invalid authored Bestiary encounter')


def _validate_elemental_profile(profile):
    """Validate hidden authoring data, without applying elemental combat rules.

    Same-element absorption supersedes the damage percentage. Non-Elemental
    means unaligned, so it never implies absorption of ordinary attacks.
    """
    if (not isinstance(profile, dict)
            or set(profile) != {'element', 'damage_percentages', 'absorption', 'design_rationale'}
            or not isinstance(profile['element'], str)
            or profile['element'] not in ELEMENT_IDS
            or not isinstance(profile['damage_percentages'], dict)
            or set(profile['damage_percentages']) != set(ELEMENT_IDS)
            or any(type(value) not in (int, float) or not 0 <= value <= 200
                   or not math.isfinite(value)
                   for value in profile['damage_percentages'].values())
            or not _text(profile['design_rationale'])):
        raise ValueError('Invalid Bestiary elemental profile')
    absorption = profile['absorption']
    expected = [] if profile['element'] == 'non_elemental' else [profile['element']]
    if (not isinstance(absorption, dict) or set(absorption) != {'elements', 'healing_percent'}
            or not isinstance(absorption['elements'], list)
            or absorption['elements'] != expected
            or type(absorption['healing_percent']) is not int
            or absorption['healing_percent'] != 100):
        raise ValueError('Invalid Bestiary elemental absorption')


def _validate_species(enemy, actions, archetypes, items):
    if (set(enemy) not in (SPECIES_FIELDS, SPECIES_FIELDS | {'combat_design'})
            or enemy['mode'] != 'species'
            or not _text(enemy['name'], 120) or not _text(enemy['description'])
            or not _identifier(enemy['family']) or enemy['tier'] not in ('normal', 'boss')
            or not isinstance(enemy['habitats'], list) or not enemy['habitats']
            or any(not _identifier(value) for value in enemy['habitats'])
            or len(enemy['habitats']) != len(set(enemy['habitats']))
            or not isinstance(enemy['level_range'], dict)
            or set(enemy['level_range']) != {'min', 'max'}
            or not _integer(enemy['level_range']['min'], 1, MAX_LEVEL)
            or not _integer(enemy['level_range']['max'], enemy['level_range']['min'], MAX_LEVEL)
            or not isinstance(enemy['archetype'], str)
            or enemy['archetype'] not in archetypes['concepts']
            or not isinstance(enemy['stat_profile'], str)
            or enemy['stat_profile'] not in archetypes['stat_profiles']
            or not isinstance(enemy['fighting_style'], str)
            or enemy['fighting_style'] not in archetypes['fighting_styles']
            or not _multipliers(enemy['species_multipliers'])
            or not _multipliers(enemy['tier_multipliers'])):
        raise ValueError('Invalid Bestiary species profile')
    behavior = enemy['behavior']
    has_design = 'combat_design' in enemy
    if has_design:
        from enemy_combat_design import validate_combat_design
        designed_actions = validate_combat_design(enemy['combat_design'], behavior)
        if enemy['combat_design']['status'] == 'ready':
            for identifier, definition in designed_actions.items():
                if (identifier not in actions
                        or any(actions[identifier].get(key) != value for key, value in definition.items())):
                    raise ValueError('Ready combat design must match its live actions')
        else:
            if any(any(actions[identifier].get(key) != value for key, value in definition.items())
                   for identifier, definition in designed_actions.items() if identifier in actions):
                raise ValueError('Pending combat actions cannot override live actions')
            actions = {**actions, **designed_actions}
    allowed_kinds = (*_DAMAGE_KINDS, 'prepare')
    if has_design:allowed_kinds += ('recover',)
    if (not isinstance(behavior, dict) or set(behavior) != {'sequence', 'fallback', 'targeting'}
            or not isinstance(behavior['sequence'], list) or not behavior['sequence']
            or any(not isinstance(identifier, str) or identifier not in actions
                   or actions[identifier]['kind'] not in allowed_kinds
                   for identifier in behavior['sequence'])
            or not isinstance(behavior['fallback'], str)
            or behavior['fallback'] not in behavior['sequence']
            or actions[behavior['fallback']]['mp_cost'] != 0
            or actions[behavior['fallback']]['kind'] not in _DAMAGE_KINDS
            or behavior['targeting'] != 'cycle_living_party'):
        raise ValueError('Invalid Bestiary behavior')
    if enemy['fighting_style'] == 'physical_magical_alternation':
        sequence = behavior['sequence']
        if (len(sequence) != 2
                or [actions[key]['kind'] for key in sequence] != ['physical', 'magical']
                or behavior['fallback'] != sequence[0]):
            raise ValueError('Mixed attackers require physical/magical alternation')
    presentation = enemy['presentation']
    if (not isinstance(presentation, dict) or set(presentation) != {'sprite_id', 'action_aliases'}
            or not isinstance(presentation['action_aliases'], dict)
            or any(key not in behavior['sequence'] or not isinstance(value, str)
                   or (value not in actions and not (has_design and _identifier(value)))
                   for key, value in presentation['action_aliases'].items())):
        raise ValueError('Invalid Bestiary presentation')
    sprite_id = presentation['sprite_id']
    if sprite_id is None:
        # A species can be authored and previewed before its art exists. An
        # empty alias map prevents accidental reuse of another enemy's poses.
        if presentation['action_aliases']:
            raise ValueError('Pending Bestiary presentation requires empty action aliases')
    elif (not _identifier(sprite_id) or Path(sprite_id).name != sprite_id
          or not (ROOT/'assets/combat'/sprite_id/'animation.json').is_file()):
        raise ValueError('Invalid Bestiary presentation')
    else:
        manifest = json.loads((ROOT/'assets/combat'/sprite_id/'animation.json').read_text())
        states = manifest.get('animations') if isinstance(manifest, dict) else None
        def authored_state(identifier):
            alias = presentation['action_aliases'].get(identifier)
            if alias in states:return alias
            return actions.get(alias or identifier, {}).get('animation', alias or identifier)
        if not isinstance(states, dict) or any(
                authored_state(identifier) not in states for identifier in behavior['sequence']):
            raise ValueError('Bestiary actions require authored animation states')
    if (not isinstance(enemy['rewards'], dict) or set(enemy['rewards']) != {'drops'}
            or (enemy['rewards']['drops'] is not None
                and not _drops(enemy['rewards']['drops'], items))):
        raise ValueError('Invalid Bestiary drops')
    _validate_elemental_profile(enemy['elemental_profile'])
    planned = enemy['planned_mechanics']
    if (not isinstance(planned, dict) or set(planned) != {'stagger'}):
        raise ValueError('Invalid planned Bestiary mechanics')
    stagger = planned['stagger']
    if (not isinstance(stagger, dict) or set(stagger) != {'status', 'resistance'}
            or stagger['status'] != 'planned' or stagger['resistance'] not in ('low', 'normal', 'high')):
        raise ValueError('Invalid planned Bestiary mechanics')
    guidance = enemy['encounter_guidance']
    if (not isinstance(guidance, dict) or set(guidance) != {'solo_count', 'party_count'}
            or any(not _integer(value, 1, 99) for value in guidance.values())):
        raise ValueError('Invalid Bestiary encounter guidance')


def load_bestiary(data=None, actions=None):
    """Validate the entire canonical dictionary and return a detached copy.

    An optional action dictionary uses ``load_actions()``'s output shape.
    Authored four-field records and leveled species share one source of truth.
    """
    if data is None:
        data = json.loads(CATALOG_PATH.read_text(encoding='utf-8'), object_pairs_hook=_unique_object)
    if (not isinstance(data, dict) or set(data) != {'version', 'enemies'}
            or type(data['version']) is not int or data['version'] != 1
            or not isinstance(data['enemies'], dict) or not data['enemies']):
        raise ValueError('Invalid Bestiary dictionary')
    actions = _actions(actions)
    archetypes, items = load_archetypes(), Inventory().definitions
    for identifier, enemy in data['enemies'].items():
        if not _identifier(identifier) or not isinstance(enemy, dict):
            raise ValueError('Invalid Bestiary enemy identifier')
        if set(enemy) == FIXED_FIELDS:_validate_fixed(enemy, actions)
        else:_validate_species(enemy, actions, archetypes, items)
    return deepcopy(data)


def fixed_enemy_definitions(data=None, actions=None):
    """Return the currently authored fixed encounters after complete validation."""
    catalog = load_bestiary(data, actions)
    return {key: value for key, value in catalog['enemies'].items() if set(value) == FIXED_FIELDS}


def build_enemy(enemy_id, level=None, *, data=None, actions=None):
    """Resolve an authored enemy or a species at an explicitly selected level.

    ``combat`` retains the four-field enemy-definition shape. Pending combat
    designs preserve their local action IDs for inspection; the battle adapter
    rejects these records until their runtime rules are implemented. XP and
    planning metadata remain separate so compilation cannot award rewards or
    silently activate future elemental/Stagger rules. A pending loot design
    yields an empty combat item bundle and ``metadata['drops_pending']``. A
    null sprite ID preserves deferred art as ``metadata['presentation_pending']``.
    """
    catalog = load_bestiary(data, actions)
    if not isinstance(enemy_id, str) or enemy_id not in catalog['enemies']:
        raise ValueError('Unknown Bestiary enemy')
    entry = catalog['enemies'][enemy_id]
    if set(entry) == FIXED_FIELDS:
        if level is not None:raise ValueError('Authored encounters have no assigned level')
        return {'id': enemy_id, 'level': None, 'xp_reward': None,
                'combat': entry, 'fighting_style': None, 'behavior': None,
                'presentation': {'sprite_id': enemy_id, 'action_aliases': {}},
                'metadata': {'mode': 'authored', 'drops_pending': False,
                             'presentation_pending': False}}
    limits = entry['level_range']
    if not _integer(level, limits['min'], limits['max']):
        raise ValueError('Select an integer level within the species range')
    stats = profile_enemy_stats(entry['stat_profile'], level,
                               species_multipliers=entry['species_multipliers'],
                               tier_multipliers=entry['tier_multipliers'])
    pending = entry['rewards']['drops'] is None
    combat = {'name': entry['name'], 'attributes': stats,
              'abilities': list(dict.fromkeys(entry['behavior']['sequence'])),
              'rewards': {'drops': {} if pending else deepcopy(entry['rewards']['drops'])}}
    metadata = deepcopy(entry)
    metadata['drops_pending'] = pending
    metadata['presentation_pending'] = entry['presentation']['sprite_id'] is None
    metadata['combat_pending'] = ('combat_design' in entry
                                  and entry['combat_design']['status'] != 'ready')
    return {'id': enemy_id, 'level': level,
            'xp_reward': monster_xp(level, boss=entry['tier'] == 'boss'),
            'combat': combat, 'fighting_style': entry['fighting_style'],
            'behavior': deepcopy(entry['behavior']),
            'presentation': deepcopy(entry['presentation']), 'metadata': metadata}
