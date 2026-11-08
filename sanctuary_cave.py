"""Authored cave passages and one-time discoveries, independent of MQ03 progress.

The arrival cutscene and encounters have separate future owners. Walking into
this dungeon never accepts unread story, recruits a character or starts a boss.
"""
from __future__ import annotations

from pathlib import Path

import pygame

from social import clear_sight


ROOT = Path(__file__).resolve().parent
RESERVE_ID = 'elden_vale_sanctuary'
RESERVE_ENTRY_APPROACH = (1008, 406)
SCENE_FILES = {f'sanctuary_cave_{name}': ROOT/f'assets/maps/sanctuary_cave/{name}/map.json'
               for name in ('entrance', 'hollow', 'depths')}
CAVE_SCENES = frozenset(SCENE_FILES)
REWARDS = {
    'cave_vein_cache': {'aether_sapphire': 1},
    'cave_grotto_pack': {'aether_emerald': 1},
    'cave_grotto_chest': {'aether_opal': 1, 'aether_amethyst': 1},
    'cave_keeper_chest': {'aether_topaz': 1},
    'cave_overlook_cache': {'aether_amethyst': 2},
    'cave_quiet_cache': {'aether_opal': 1},
}


class SanctuaryCave:
    def __init__(self, game):
        self.game = game
        self.opened = set()

    @property
    def active(self):
        return self.game.world.data.get('id') in CAVE_SCENES

    @staticmethod
    def valid_snapshot(record):
        if not isinstance(record, dict) or set(record) != {'version', 'opened'}:
            return False
        opened = record['opened']
        return (type(record['version']) is int and record['version'] == 1
                and isinstance(opened, list) and len(opened) <= len(REWARDS)
                and all(isinstance(identifier, str) and identifier in REWARDS
                        for identifier in opened)
                and len(opened) == len(set(opened)))

    @staticmethod
    def valid_journey(data):
        if not isinstance(data, dict) or not isinstance(data.get('player'), dict):return False
        if 'sanctuary_cave' in data:
            return SanctuaryCave.valid_snapshot(data['sanctuary_cave'])
        # Existing journeys predate the cave. A cave checkpoint itself must
        # carry its receipts, so malformed new saves cannot silently refill it.
        return data.get('player', {}).get('scene') not in CAVE_SCENES

    def to_dict(self):
        return {'version': 1, 'opened': sorted(self.opened)}

    def reset(self):
        self.opened.clear()
        self._sync_cached_worlds()

    def restore(self, record=None):
        if record is not None and not self.valid_snapshot(record):return False
        self.opened = set(record['opened']) if record is not None else set()
        self._sync_cached_worlds()
        return True

    def _sync_world(self, world):
        if world.data.get('id') not in CAVE_SCENES:return
        for treasure in world.data.get('cave', {}).get('treasures', []):
            identifier = treasure['id']
            state = 'open' if identifier in self.opened else 'closed'
            entity = next((entity for entity in world.entities
                           if entity['id'] == treasure.get('entity_id', identifier)), None)
            if entity is not None and entity.get('state') != state:
                world.set_entity_state(entity['id'], state)

    def _sync_cached_worlds(self):
        for world in getattr(self.game, 'scenes', {}).values():self._sync_world(world)

    def update(self, seconds=0):
        if self.active:self._sync_world(self.game.world)

    def _available(self):
        g = self.game
        return (not g.on_title and not g.social.locked and not g.pause.is_open
                and not g.inventory_ui.is_open and not g.party_ui.is_open
                and not g.world_map_viewer.is_open and not g.map_open
                and not g.quest_ui.journal_open and not g.combat.active
                and not g.transfer_cooldown and not g.opening_fade
                and not g.household_action and not g.opening.locks_player
                and not g.opening_cinematic.active)

    def _entry(self):
        g = self.game
        if g.world.data.get('id') != RESERVE_ID:return None
        point = g.world.data.get('public_approaches', {}).get('cave', RESERVE_ENTRY_APPROACH)
        return {'id': 'sanctuary_to_cave', 'position': point, 'radius': 28,
                'destination': 'sanctuary_cave_entrance', 'label': 'Lift the rail and enter the cave'}

    def _nearby(self):
        if not self._available():return None
        g = self.game
        if not self.active:
            entry = self._entry()
            records = [('link', entry)] if entry is not None else []
        else:
            cave = g.world.data.get('cave', {})
            records = [('treasure', item) for item in cave.get('treasures', [])]
            records.extend(('link', item) for item in cave.get('links', []))
            records.extend(('inspection', item) for item in cave.get('inspections', []))
        candidates = []
        for kind, record in records:
            approach = pygame.Vector2(record.get('approach', record['position']))
            distance = g.player.position.distance_squared_to(approach)
            if distance > record.get('radius', 28)**2:continue
            # Query the reachable approach, since an actual chest root can be
            # solid. This prevents interaction through another passage's wall.
            if not clear_sight(g.world, g.player.position, approach):continue
            candidates.append((distance, record['id'], kind, record))
        return min(candidates, key=lambda item: item[:2])[2:] if candidates else None

    def interaction_hint(self):
        nearby = self._nearby()
        if nearby is None:return ''
        kind, record = nearby
        if kind == 'treasure':
            verb = 'Examine' if record['id'] in self.opened else 'Open'
            return 'E: '+verb+' '+record.get('label', 'the cache')
        return 'E: '+record.get('label', 'Continue through the passage')

    def _say(self, text, identifier):
        self.game.player.moving = False
        return self.game.social.start_script([{'speaker': 'caelan', 'text': text}],
                                              identifier='sanctuary_cave_'+identifier)

    def _travel(self, record):
        g = self.game
        destination = g._scene_by_id(record['destination'])
        desired = record.get('landing', destination.data['spawn'])
        landing = g.overworld_travel._landing(destination, desired)
        if landing is None:return False
        self._sync_world(destination)
        return g.overworld_travel._commit(destination, landing,
                                          record.get('facing', 'back'), record)

    def _open(self, record):
        identifier = record['id']
        if identifier in self.opened:
            return self._say('The container is empty.', identifier)
        bundle = REWARDS.get(record.get('reward_id', identifier))
        if not bundle:
            # An unfinished reward stays unopened for later authoring.
            return self._say("I'll leave this sealed for now.", identifier)
        if not self.game.inventory.add_many(bundle):
            return self._say("I can't take these supplies right now.", identifier)
        # Opening is the collection action; receipt dialogue can be dismissed
        # without removing the acquired item or making the reward repeatable.
        self.opened.add(identifier)
        self._sync_world(self.game.world)
        names = [self.game.inventory.definitions[item]['name']+' ×'+str(amount)
                 for item, amount in bundle.items()]
        self._say('Found: '+', '.join(names)+'.', identifier)
        self.game.save_progress()
        return True

    def interact(self):
        nearby = self._nearby()
        if nearby is None:return False
        kind, record = nearby
        if kind == 'link':return self._travel(record)
        if kind == 'treasure':return self._open(record)
        return self._say(record['text'], record['id'])
