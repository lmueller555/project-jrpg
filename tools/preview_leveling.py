#!/usr/bin/env python3
"""Print approved growth curves without loading Pygame or a saved journey.

Examples:
    python tools/preview_leveling.py --levels 1 25 50 75 100
    python tools/preview_leveling.py --all-levels --format csv
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from character_attributes import ATTRIBUTE_IDS
from enemy_growth import baseline_enemy_stats
from leveling import (MAX_LEVEL, character_ids, character_stats, monster_xp,
                      total_xp_for_level, xp_to_next_level)


def growth_rows(levels):
    """Yield comparable fixed-reference player and baseline-enemy rows."""
    for level in levels:
        for identifier in (*character_ids(), 'enemy_baseline'):
            stats = (baseline_enemy_stats(level) if identifier == 'enemy_baseline'
                     else character_stats(identifier, level))
            yield {'profile': identifier, 'level': level,
                   'total_xp_to_level': total_xp_for_level(level),
                   'xp_to_next_level': xp_to_next_level(level),
                   'normal_monster_xp': monster_xp(level),
                   'boss_xp': monster_xp(level, boss=True), **stats}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--levels', type=int, nargs='+', default=[1, 25, 50, 75, 100])
    selection.add_argument('--all-levels', action='store_true')
    parser.add_argument('--format', choices=('markdown', 'csv', 'json'), default='markdown')
    args = parser.parse_args(argv)
    levels = list(range(1, MAX_LEVEL+1)) if args.all_levels else args.levels
    if any(not 1 <= level <= MAX_LEVEL for level in levels):
        parser.error('levels must be between 1 and 100')
    rows = list(growth_rows(levels))
    if args.format == 'json':
        json.dump(rows, sys.stdout, indent=2)
        print()
    elif args.format == 'csv':
        writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    else:
        print('Approved natural growth; enemy rows precede archetype/species/boss modifiers.')
        print('This preview does not award live XP or modify journeys, resources, or RP.')
        print()
        columns = ['profile', 'level', *ATTRIBUTE_IDS]
        print('| ' + ' | '.join(columns) + ' |')
        print('| ' + ' | '.join('---' for _ in columns) + ' |')
        for row in rows:
            print('| ' + ' | '.join(str(row[key]) for key in columns) + ' |')
        print()
        print('| level | total XP to level | XP to next | normal monster XP | boss XP |')
        print('| --- | --- | --- | --- | --- |')
        for level in levels:
            print(f'| {level} | {total_xp_for_level(level)} | {xp_to_next_level(level)} '
                  f'| {monster_xp(level)} | {monster_xp(level, boss=True)} |')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
