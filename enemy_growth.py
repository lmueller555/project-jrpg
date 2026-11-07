"""Approved enemy growth and stat profiles, independent of battle AI.

The fixed five-character reference excludes party selection, equipment and
temporary effects. Named profiles apply the approved numerical multipliers;
species and tier adjustments remain explicitly authored optional layers.
The catalog does not replace the authored Bat or Tusker encounters.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import json
import math
from pathlib import Path

from character_attributes import ATTRIBUTE_CAPS, ATTRIBUTE_IDS
from leveling import MAX_LEVEL, raw_character_stats


CATALOG_PATH = Path(__file__).parent/'assets/combat/enemy_archetypes.json'
REFERENCE_CHARACTER_IDS = ('caelan', 'mira', 'lucan', 'rhea', 'edran')
# Match the battle catalog's existing structural resource limit. This is not
# the player HP cap or a new enemy balance target.
MAX_ENEMY_HP = 999999999
ENEMY_STAT_CAPS = {**ATTRIBUTE_CAPS, 'hp': MAX_ENEMY_HP}
STAT_PROFILE_IDS = ('balanced', 'brute', 'armored', 'warded', 'swift',
                    'evasive', 'caster', 'hybrid', 'support', 'lightweight')
CONCEPT_IDS = ('soldier', 'brute', 'bulwark', 'warder', 'duelist', 'skirmisher',
               'arcanist', 'battlemage', 'windup_attacker', 'mender', 'captain',
               'berserker', 'opportunist', 'counterfighter', 'stancechanger',
               'swarmer', 'regenerator', 'siphoner', 'guardian', 'disruptor')


def _level(level):
    if type(level) is not int or not 1 <= level <= MAX_LEVEL:
        raise ValueError('Enemy level must be an integer from 1 to 100')


def _round(value):
    return int(Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def raw_baseline_enemy_stats(level):
    """Return unrounded values before profile, species, tier or combat caps."""
    _level(level)
    reference = [raw_character_stats(identifier, level)
                 for identifier in REFERENCE_CHARACTER_IDS]
    values = {key: 1.25*sum(profile[key] for profile in reference)/len(reference)
              for key in ATTRIBUTE_IDS}
    values['hp'] = 180+49820*((level-1)/(MAX_LEVEL-1))**1.8
    return values


def baseline_enemy_stats(level):
    """Return the rounded normal-enemy reference without archetype weights."""
    return build_enemy_stats(level, multipliers={})


def build_enemy_stats(level, *, multipliers):
    """Apply explicitly authored multipliers, then round and cap once.

    Omitted keys retain their baseline value. No archetype weights are inferred
    from a name. Multipliers must be finite, nonnegative ints/floats bounded by
    the existing HP storage limit; HP needs a positive multiplier and its
    resulting maximum is at least one.
    This returns attributes only, without creating an encounter or applying AI.
    """
    return _layered_enemy_stats(level, (multipliers,))


def _valid_multipliers(multipliers, *, complete=False):
    return (isinstance(multipliers, dict)
            and (set(multipliers) == set(ATTRIBUTE_IDS) if complete
                 else set(multipliers) <= set(ATTRIBUTE_IDS))
            and all(type(value) in (int, float) and 0 <= value <= MAX_ENEMY_HP
                    and math.isfinite(value) for value in multipliers.values())
            and multipliers.get('hp', 1) > 0)


def _layered_enemy_stats(level, layers):
    if any(not _valid_multipliers(layer) for layer in layers):
        raise ValueError('Enemy multipliers must be finite nonnegative stat values')
    values = raw_baseline_enemy_stats(level)
    result = {}
    for key, value in values.items():
        # Decimal multiplier composition keeps authored decimal factors exact.
        # Preserve the unrounded baseline through every layer; a large earlier
        # multiplier must not hit a cap before a later reduction is applied.
        adjusted = Decimal(str(value))
        for layer in layers:adjusted *= Decimal(str(layer.get(key, 1)))
        result[key] = max(1 if key == 'hp' else 0,
                          _round(min(Decimal(ENEMY_STAT_CAPS[key]), adjusted)))
    return result


def profile_multipliers(profile_id):
    """Return a fresh complete multiplier dictionary for a named profile."""
    if not isinstance(profile_id, str) or profile_id not in STAT_PROFILE_IDS:
        raise ValueError('Unknown enemy stat profile')
    return load_archetypes()['stat_profiles'][profile_id]['multipliers']


def profile_enemy_stats(profile_id, level, *, species_multipliers=None,
                        tier_multipliers=None):
    """Compose baseline, named profile, species and tier before one round/cap.

    Optional adjustment dictionaries are sparse: omitted attributes use ×1.
    No species or boss weights, abilities, behavior or levels are inferred.
    """
    layers = (profile_multipliers(profile_id),
              {} if species_multipliers is None else species_multipliers,
              {} if tier_multipliers is None else tier_multipliers)
    return _layered_enemy_stats(level, layers)


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 600


def _texts(value):
    return (isinstance(value, list) and all(_text(item) for item in value)
            and len(value) == len(set(value)))


def load_archetypes(data=None):
    """Validate and copy the approved profiles, concepts and behavior metadata.

    Numerical profile weights are approved; species weights remain unauthored.
    Existing-pattern annotations describe current bespoke battle behavior;
    they do not claim that this catalog is bound to the live battle engine.
    """
    if data is None:data = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
    if (not isinstance(data, dict)
            or set(data) != {'version', 'runtime_binding', 'reference_characters',
                             'stat_profiles', 'fighting_styles', 'concepts', 'enemy_references'}
            or type(data['version']) is not int or data['version'] != 1
            or data['runtime_binding'] != 'metadata_only'
            or data['reference_characters'] != list(REFERENCE_CHARACTER_IDS)
            or not isinstance(data['stat_profiles'], dict)
            or set(data['stat_profiles']) != set(STAT_PROFILE_IDS)
            or not isinstance(data['fighting_styles'], dict) or not data['fighting_styles']
            or not isinstance(data['concepts'], dict) or set(data['concepts']) != set(CONCEPT_IDS)
            or not isinstance(data['enemy_references'], dict)
            or set(data['enemy_references']) != {'bat', 'ridgeback_tusker'}):
        raise ValueError('Invalid enemy archetype catalog')
    for profile in data['stat_profiles'].values():
        if (not isinstance(profile, dict)
                or set(profile) != {'name', 'description', 'high_stats', 'low_stats', 'multipliers'}
                or not _text(profile['name']) or not _text(profile['description'])
                or not _texts(profile['high_stats']) or not _texts(profile['low_stats'])
                or not set(profile['high_stats']+profile['low_stats']) <= set(ATTRIBUTE_IDS)
                or set(profile['high_stats']) & set(profile['low_stats'])
                or not _valid_multipliers(profile['multipliers'], complete=True)):
            raise ValueError('Invalid enemy stat profile')
    for identifier, style in data['fighting_styles'].items():
        if (not _text(identifier) or not isinstance(style, dict)
                or set(style) != {'name', 'description', 'implementation', 'requirements'}
                or not _text(style['name']) or not _text(style['description'])
                or style['implementation'] not in ('existing_pattern', 'requires_implementation')
                or not _texts(style['requirements'])):
            raise ValueError('Invalid enemy fighting style metadata')
    for concept in data['concepts'].values():
        if (not isinstance(concept, dict)
                or set(concept) != {'name', 'stat_profile', 'fighting_style', 'description', 'requirements'}
                or not _text(concept['name']) or not _text(concept['description'])
                or not isinstance(concept['stat_profile'], str)
                or concept['stat_profile'] not in data['stat_profiles']
                or not isinstance(concept['fighting_style'], str)
                or concept['fighting_style'] not in data['fighting_styles']
                or not _texts(concept['requirements'])):
            raise ValueError('Invalid enemy concept reference')
    for enemy in data['enemy_references'].values():
        if (not isinstance(enemy, dict)
                or set(enemy) != {'stat_profile', 'fighting_style', 'species_adjustments', 'notes'}
                or not isinstance(enemy['stat_profile'], str)
                or enemy['stat_profile'] not in data['stat_profiles']
                or not isinstance(enemy['fighting_style'], str)
                or enemy['fighting_style'] not in data['fighting_styles']
                or enemy['species_adjustments'] is not None or not _text(enemy['notes'])):
            raise ValueError('Invalid current enemy design reference')
    return deepcopy(data)
