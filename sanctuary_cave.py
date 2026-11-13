"""Authored cave passages and one-time discoveries, independent of MQ03 progress.

The arrival cutscene and encounters have separate future owners. Walking into
this dungeon never accepts unread story, recruits a character or starts a boss.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path

import pygame

from social import clear_sight


ROOT = Path(__file__).resolve().parent
RESERVE_ID = 'elden_vale_sanctuary'
RESERVE_ENTRY_APPROACH = (1008, 406)
SCENE_ID = 'sanctuary_cave'
SCENE_FILES = {SCENE_ID: ROOT/'assets/maps/sanctuary_cave/map.json'}
CAVE_SCENES = frozenset(SCENE_FILES)
LEGACY_SCENES = frozenset(f'sanctuary_cave_{name}'
                          for name in ('entrance', 'hollow', 'depths'))
REWARDS = {
    'cave_vein_cache': {'aether_sapphire': 1},
    'cave_grotto_pack': {'aether_emerald': 1},
    'cave_grotto_chest': {'aether_opal': 1, 'aether_amethyst': 1},
    'cave_keeper_chest': {'aether_topaz': 1},
    'cave_overlook_cache': {'aether_amethyst': 2},
    'cave_quiet_cache': {'aether_opal': 1},
}


def migrate_legacy_cave(data, landings=None):
    """Move an old room checkpoint into the corresponding continuous area.

    Room-local coordinates cannot be reused on the new map. Only the player's
    scene and feet change; discovery receipts, inventory, party resources and
    the pending Sanctuary story handoff retain their original values. The
    returned journey still has to pass every ordinary save validator.
    """
    player = data.get('player') if isinstance(data, dict) else None
    scene = player.get('scene') if isinstance(player, dict) else None
    if not isinstance(scene, str) or scene not in LEGACY_SCENES:return data
    position = player.get('position')
    if not (isinstance(position, list) and len(position) == 2
            and all(type(value) in (int, float) and math.isfinite(value)
                    and abs(value) < 1e7 for value in position)):
        raise ValueError('Invalid legacy cave checkpoint')
    if landings is None:
        metadata = json.loads(SCENE_FILES[SCENE_ID].read_text(encoding='utf-8'))
        landings = metadata['cave']['legacy_landings']
    landing = landings.get(scene) if isinstance(landings, dict) else None
    if not (isinstance(landing, (list, tuple)) and len(landing) == 2
            and all(type(value) in (int, float) and math.isfinite(value)
                    and abs(value) < 1e7 for value in landing)):
        raise ValueError('Invalid continuous cave landing')
    result = deepcopy(data)
    result['player']['scene'] = SCENE_ID
    result['player']['position'] = list(landing)
    return result


class SanctuaryCave:
    def __init__(self, game):
        self.game = game
        self.opened = set()
        self.lucan_guest_initialized = False
        self.lucan_departed = False

    @property
    def active(self):
        return self.game.world.data.get('id') in CAVE_SCENES

    @staticmethod
    def valid_snapshot(record):
        if (not isinstance(record, dict) or not {'version', 'opened'} <= set(record)
                or not set(record) <= {'version', 'opened', 'lucan_guest_initialized', 'lucan_departed'}
                or any(type(record[key]) is not bool for key in
                       ('lucan_guest_initialized', 'lucan_departed') if key in record)
                or record.get('lucan_departed', False) and not record.get('lucan_guest_initialized', False)):
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
            record = data['sanctuary_cave']
            boss = data.get('sanctuary_boss', {})
            return (SanctuaryCave.valid_snapshot(record)
                    and (not record.get('lucan_departed', False)
                         or isinstance(boss, dict) and boss.get('defeated') is True))
        # Existing journeys predate the cave. A cave checkpoint itself must
        # carry its receipts, so malformed new saves cannot silently refill it.
        return data.get('player', {}).get('scene') not in CAVE_SCENES | LEGACY_SCENES

    def to_dict(self):
        record = {'version': 1, 'opened': sorted(self.opened)}
        if self.lucan_guest_initialized:record['lucan_guest_initialized'] = True
        if self.lucan_departed:record['lucan_departed'] = True
        return record

    def reset(self):
        self.opened.clear()
        self.lucan_guest_initialized = self.lucan_departed = False
        self._sync_cached_worlds()

    def restore(self, record=None):
        if record is not None and not self.valid_snapshot(record):return False
        self.opened = set(record['opened']) if record is not None else set()
        self.lucan_guest_initialized = record.get('lucan_guest_initialized', False) if record else False
        self.lucan_departed = record.get('lucan_departed', False) if record else False
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
        if self.active:
            self._sync_world(self.game.world)
            if self._available() and getattr(self.game,'_music_focused',True):
                self.game.world.chasm_elapsed_ms = getattr(self.game.world,'chasm_elapsed_ms',0.)+max(0.,seconds)*1000

    def _available(self):
        g = self.game
        return (not g.on_title and not g.social.locked and not g.pause.is_open
                and not g.inventory_ui.is_open and not g.party_ui.is_open
                and not getattr(getattr(g,'status_ui',None),'is_open',False)
                and not g.world_map_viewer.is_open and not g.map_open
                and not g.quest_ui.journal_open and not g.combat.active
                and not g.transfer_cooldown and not g.opening_fade
                and not g.household_action and not g.opening.locks_player
                and not g.opening_cinematic.active)

    def _entry(self):
        g = self.game
        if g.world.data.get('id') != RESERVE_ID:return None
        arrival=getattr(g,'sanctuary_arrival',None)
        if (arrival is not None and not arrival.completed
                and getattr(getattr(g,'regent_quest',None),'stage',None)=='sanctuary_arrival_pending'):
            return None
        point = g.world.data.get('public_approaches', {}).get('cave', RESERVE_ENTRY_APPROACH)
        return {'id': 'sanctuary_to_cave', 'position': point, 'radius': 28,
                'destination': SCENE_ID, 'label': ('Enter the cave' if getattr(arrival,'completed',False)
                                                    else 'Lift the rail and enter the cave')}

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
        rescue = getattr(g, 'sanctuary_rescue', None)
        if (rescue is not None and getattr(getattr(g, 'sanctuary_arrival', None), 'completed', False)
                and g.world.data.get('id') in CAVE_SCENES
                and destination.data.get('id') == RESERVE_ID
                and getattr(getattr(g, 'sanctuary_boss', None), 'defeated', False)
                and rescue.stage != 'evacuated'):
            return self._say('We need to bring the injured worker back. Lucan is waiting with him at Greenwell.',
                             'worker_waiting')
        if (g.world.data.get('id') in CAVE_SCENES and destination.data.get('id') == RESERVE_ID
                and getattr(getattr(g,'sanctuary_boss',None), 'defeated', False)
                and g.party.is_guest('lucan') and not self.lucan_departed):
            return self._depart_with_lucan(destination, landing, record)
        return g.overworld_travel._commit(destination, landing,
                                          record.get('facing', 'back'), record)

    def _depart_with_lucan(self, destination, landing, record):
        """Checkpoint the physical post-boss exit and guest departure together."""
        from sanctuary_arrival_party import sync_arrival_party
        g = self.game
        party_before, cave_before = g.party.to_dict(), self.to_dict()
        rescue = getattr(g, 'sanctuary_rescue', None)
        rescue_before = rescue.stage if rescue is not None else None
        levels_before = g.character_progression.to_dict()
        origin, position, facing = g.world, tuple(g.player.position), g.player.facing
        cooldown = g.transfer_cooldown
        self.lucan_departed = True
        if rescue is not None:rescue.stage = 'evacuated'
        if sync_arrival_party(g) is not False:
            g.overworld_travel._commit(destination, landing, record.get('facing', 'back'),
                                      record, checkpoint=False)
            if not g.save_store.enabled or g.save_progress():
                g.sanctuary_arrival.sync_residents()
                g.party_travel.reset()
                return True
        g.party.restore(party_before)
        g.character_progression.restore(levels_before)
        self.restore(cave_before)
        if rescue is not None:rescue.stage = rescue_before
        g.world = origin
        g.player.position.update(position);g.player.facing = facing
        g.transfer_cooldown = cooldown
        g.sanctuary_arrival.sync_residents()
        g.party_travel.reset();g.camera.reset();g._sync_world_music()
        return False

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
        if record.get('healing_pool'):
            self.game.player.facing = 'right'
            for identifier in self.game.party.active_ids:
                self.game.party.attributes(identifier).recover()
            self._say(record['text'], record['id'])
            self.game.save_progress()
            return True
        present=getattr(getattr(self.game,'party',None),'active_ids',())
        if 'dialogue' in record and all(key in present for key in record.get('requires_party',())):
            self.game.player.moving = False
            return self.game.social.start_script(record['dialogue'], identifier='sanctuary_cave_'+record['id'])
        return self._say(record['text'], record['id'])


def migrate_chasm_checkpoint(data, metadata=None):
    """Relocate only checkpoints covered by the newly authored Echo rupture.

    Matching encounter coordinates move together so pending boss/reward records
    remain valid. Resources, rewards, seeds and story facts are never rewritten.
    The returned copy still passes the ordinary save validators before use.
    """
    player=data.get('player') if isinstance(data,dict) else None
    if not isinstance(player,dict) or player.get('scene')!=SCENE_ID:return data
    position=player.get('position')
    if (not isinstance(position,list) or len(position)!=2
            or any(type(n) not in (int,float) or abs(n)>=1e7 or not math.isfinite(n) for n in position)):return data
    metadata=metadata or json.loads(SCENE_FILES[SCENE_ID].read_text())
    chasm=metadata.get('cave',{}).get('chasm')
    if not chasm:return data
    probe=pygame.Rect(round(position[0])-12,round(position[1])-6,24,12)
    if not pygame.Rect(chasm['bounds']).inflate(12,12).colliderect(probe):return data
    collision=pygame.image.load(str(ROOT/metadata['collision']))
    if not any(collision.get_at((x,y)).r for y in range(probe.top,probe.bottom)
               for x in range(probe.left,probe.right)):return data
    landing=list(chasm['safe_landing'])
    result=deepcopy(data);result['player']['position']=landing
    owners=[result[key].get('pending') for key in ('sanctuary_boss','cave_random_encounters')
            if isinstance(result.get(key),dict)]
    post=result.get('post_battle')
    if isinstance(post,dict) and post.get('kind') in ('cave','cave_boss'):
        owners += [post,post.get('encounter')]
    for record in owners:
        if isinstance(record,dict) and record.get('scene')==SCENE_ID and record.get('position')==position:
            record['position']=list(landing)
    return result
