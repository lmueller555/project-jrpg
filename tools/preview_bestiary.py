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

from bestiary import build_enemy, load_bestiary
from character_attributes import ATTRIBUTE_IDS


def overview_rows(catalogue):
    for identifier, entry in catalogue['enemies'].items():
        levels = entry.get('level_range')
        yield {'id': identifier, 'name': entry['name'],
               'kind': 'species' if entry.get('mode') == 'species' else 'fixed',
               'levels': f"{levels['min']}–{levels['max']}" if levels else 'fixed',
               'tier': entry.get('tier', ''),
               'stat_profile': entry.get('stat_profile', ''),
               'fighting_style': entry.get('fighting_style', '')}


def stat_rows(records):
    for record in records:
        combat = record['combat']
        yield {'id': record['id'], 'name': combat['name'],
               'level': record['level'], 'xp_reward': record['xp_reward'],
               **{key: combat['attributes'][key] for key in ATTRIBUTE_IDS}}


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
            rows = list(stat_rows(records))
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
                print('Presentation: ' + record['presentation']['sprite_id'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
