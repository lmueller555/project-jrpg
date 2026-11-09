#!/usr/bin/env python3
"""Inspect the Bestiary without opening the game or reading a saved journey."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bestiary import ELEMENT_IDS, ELEMENT_NAMES, build_enemy, load_bestiary
from character_attributes import ATTRIBUTE_IDS


def overview_rows(catalogue):
    for identifier, entry in catalogue['enemies'].items():
        levels = entry.get('level_range')
        yield {'id': identifier, 'name': entry['name'],
               'kind': 'species' if entry.get('mode') == 'species' else 'fixed',
               'levels': f"{levels['min']}–{levels['max']}" if levels else 'fixed',
               'tier': entry.get('tier', ''),
               'stat_profile': entry.get('stat_profile', ''),
               'fighting_style': entry.get('fighting_style', ''),
               'element': entry.get('elemental_profile', {}).get('element', 'unassigned'),
               'combat_pending': (bool(entry.get('combat_design'))
                                  and entry['combat_design']['status'] != 'ready'),
               'presentation_pending': (entry.get('mode') == 'species'
                                        and entry['presentation']['sprite_id'] is None)}


def stat_rows(records, *, include_elements=False):
    for record in records:
        combat = record['combat']
        row = {'id': record['id'], 'name': combat['name'],
               'level': record['level'], 'xp_reward': record['xp_reward'],
               **{key: combat['attributes'][key] for key in ATTRIBUTE_IDS},
               'combat_pending': record['metadata'].get('combat_pending', False),
               'presentation_pending': record['metadata']['presentation_pending']}
        if include_elements:
            profile = record['metadata'].get('elemental_profile')
            row['element'] = profile['element'] if profile else 'unassigned'
            row.update({f'damage_percent_{key}': profile['damage_percentages'][key]
                        if profile else None for key in ELEMENT_IDS})
            row['absorption_elements'] = (';'.join(profile['absorption']['elements']) or 'none'
                                          if profile else 'unassigned')
            row['absorption_healing_percent'] = (profile['absorption']['healing_percent']
                                                 if profile else None)
        yield row


def elemental_rows(profile):
    """Display the effective relationship, including absorption precedence."""
    absorption = profile['absorption']
    for element in ELEMENT_IDS:
        if element in absorption['elements']:
            response = f"{absorption['healing_percent']}% healing (absorb)"
        else:
            response = f"{profile['damage_percentages'][element]}% damage"
        yield {'Element': ELEMENT_NAMES[element], 'Response': response}


def table(rows):
    columns = list(rows[0])
    print('| ' + ' | '.join(columns) + ' |')
    print('| ' + ' | '.join('---' for _ in columns) + ' |')
    for row in rows:
        print('| ' + ' | '.join('—' if row[key] is None or row[key] == ''
                               else str(row[key]) for key in columns) + ' |')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--list', action='store_true', help='List all dictionary entries.')
    selection.add_argument('--enemy', help='Resolve one enemy by its stable dictionary ID.')
    parser.add_argument('--levels', type=int, nargs='+', help='Explicit levels within the species range.')
    parser.add_argument('--format', choices=('markdown', 'json', 'csv'), default='markdown')
    args = parser.parse_args(argv)
    if args.enemy is None and args.levels is not None:
        parser.error('--levels requires --enemy')
    try:
        catalogue = load_bestiary()
        if args.enemy is None:
            records = None
            rows = list(overview_rows(catalogue))
        else:
            if args.enemy not in catalogue['enemies']:
                parser.error('unknown Bestiary ID: '+args.enemy)
            entry = catalogue['enemies'][args.enemy]
            levels = args.levels
            if levels is None:
                authored = entry.get('level_range')
                levels = list(range(authored['min'], authored['max']+1)) if authored else [None]
            records = [build_enemy(args.enemy, level, data=catalogue) for level in levels]
            rows = list(stat_rows(records, include_elements=args.format == 'csv'))
    except (TypeError, ValueError) as error:
        parser.error(str(error))
    if args.format == 'json':
        json.dump(records if records is not None else rows, sys.stdout, indent=2)
        print()
    elif args.format == 'csv':
        writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    else:
        print('Bestiary authoring preview; no encounters, journeys or rewards are modified.')
        print()
        table(rows)
        if records is not None:
            record = records[0]
            if record['behavior'] is not None:
                print()
                print('Action sequence: ' + ' → '.join(record['behavior']['sequence']))
                print('Free fallback: ' + record['behavior']['fallback'])
                print('Targeting: ' + record['behavior']['targeting'])
            if record['presentation'] is not None:
                sprite_id = record['presentation']['sprite_id']
                print('Presentation: ' + (sprite_id if sprite_id is not None else
                                         'pending (models/animations deferred)'))
            design = record['metadata'].get('combat_design')
            if design is not None:
                pending = record['metadata'].get('combat_pending', True)
                print('Combat: pending (authored design; runtime mechanics deferred)' if pending
                      else 'Combat: ready (live action rules)')
                print()
                table([{'Action': identifier, 'Name': action['name'],
                        'Kind': action['kind'], 'Target': action['target'],
                        'Potency': action['potency'], 'MP': action['mp_cost']}
                       for identifier, action in design['actions'].items()])
                print()
                print('Windup: marked target gets at least '
                      + str(design['windup']['minimum_target_actions'])+' action opportunity; '
                      'repeat warning when retargeting.')
                recovery = design['recovery']
                print('Recovery: damage taken ×'+str(recovery['damage_taken_multiplier'])
                      +' after '+recovery['after_action']+' until '
                      +recovery['ends_before_action']+' begins.')
                print('Encounter: one-time solo story battle; not placed.' if pending
                      else 'Encounter: one-time solo story battle.')
            profile = record['metadata'].get('elemental_profile')
            print()
            if profile is None:
                print('Elemental profile: unassigned (fixed encounter).')
            else:
                print('Element: ' + ELEMENT_NAMES[profile['element']])
                print('Elemental relationships are authoring data; battle effects are not active.')
                print()
                table(list(elemental_rows(profile)))
                print()
                print('Design rationale: ' + profile['design_rationale'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
