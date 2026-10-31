"""Scale-changing outdoor travel without moving town actors into streamed chunks.

Quest checkpoints own party membership and progress. The overworld moves only
the leader; detailed-scene actors keep their owners until the party returns.
"""
import json
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent
REGION_FILE = ROOT/'assets/maps/overworld/elden_vale/region.json'
WORLD_ID = 'auratia.overworld'
REGION_ID = 'elden_vale_start'
TOWN_EXIT = (516, 1332)
TOWN_RETURN = (516, 1284)
TOWN_EXIT_RECT = pygame.Rect(492, 1320, 48, 24)


class OverworldTravel:
    """Own contact rearming, guard exchanges, and atomic regional transfers."""

    def __init__(self, game):
        self.game = game
        self._town_armed = True
        self._region_armed = False
        self.discovered = {'eldenmere'}
        self.farm_state = None
        self._speaking_guard = None
        self._guard_script = None
        self.bridge_state = None

    @property
    def active(self):
        return bool(getattr(self.game.world, 'is_overworld', False))

    def to_dict(self):
        world = self.game._overworld_world
        bridge = world.bridge_crew.to_dict() if world is not None else self.bridge_state
        farm = world.grain_farm.to_dict() if world is not None else self.farm_state
        return {'version': 1, 'region': REGION_ID, 'discovered': sorted(self.discovered),
                **({'bridge_crew': bridge} if bridge is not None else {}),
                **({'grain_farm': farm} if farm is not None else {})}

    @staticmethod
    def discovery_ids():
        # Metadata is small; validating a journey never constructs the world,
        # loads art, or introduces a regional edge to an NPC's town graph.
        manifest = json.loads(REGION_FILE.read_text(encoding='utf-8'))
        return {'eldenmere', *(item['id'] for item in manifest.get('landmarks', []))}

    @staticmethod
    def valid_journey(data):
        if not isinstance(data, dict) or not isinstance(data.get('player'), dict):
            return False
        record = data.get('overworld')
        active = data.get('player', {}).get('scene') == WORLD_ID
        if record is None:
            return not active
        from grain_farm import valid_state
        from bridge_crew import valid_state as valid_bridge_state
        if not (isinstance(record, dict) and {'version', 'region'} <= set(record)
                and set(record) <= {'version', 'region', 'discovered', 'grain_farm', 'bridge_crew'}
                and ('bridge_crew' not in record or valid_bridge_state(record['bridge_crew']))
                and ('grain_farm' not in record or valid_state(record['grain_farm']))
                and type(record['version']) is int and record['version'] == 1
                and record['region'] == REGION_ID
                and not (active and data.get('post_battle') is not None)):
            return False
        discovered = record.get('discovered', ['eldenmere'])
        return (isinstance(discovered, list) and all(isinstance(item, str) for item in discovered)
                and len(discovered) == len(set(discovered)) and 'eldenmere' in discovered
                and set(discovered) <= OverworldTravel.discovery_ids())

    def restore(self, data=None):
        """Rearm only after leaving a destination's contact footprint."""
        self._clear_guard()
        self._town_armed = False
        self._region_armed = False
        self.farm_state = (data or {}).get('grain_farm')
        self.bridge_state = (data or {}).get('bridge_crew')
        self.discovered.clear()
        self.discovered.update((data or {}).get('discovered', ['eldenmere']))
        if self.game._overworld_world is not None:
            self.game._overworld_world.set_progress(self.game.social.flags)
            self.game._overworld_world.grain_farm.restore(self.farm_state)
            self.game._overworld_world.bridge_crew.restore(self.bridge_state)

    def stage_story_restore(self):
        """Restore committed town actors at town scale, retaining region feet."""
        if not self.active:
            return None
        checkpoint = (self.game.world, tuple(self.game.player.position), self.game.player.facing)
        self.game.world = self.game.town
        self.game.player.position.update(TOWN_RETURN)
        return checkpoint

    def finish_story_restore(self, checkpoint):
        if checkpoint is not None:
            self.game.world, position, self.game.player.facing = checkpoint
            self.game.player.position.update(position)
            self._stop_party()
        self._town_armed = self._region_armed = False

    def can_travel(self):
        g = self.game
        return not (g.on_title or g.pause.is_open or g.inventory_ui.is_open
                    or g.map_open or g.quest_ui.journal_open or g.world_map_viewer.is_open
                    or g.combat.active or g.opening_cinematic.active or g.social.locked
                    or g.household_action or g.opening.locks_player or g.opening.controls_player
                    or g.opening.in_action or g.opening_fade or g.transfer_cooldown
                    or g.mill_quest.encounter_cutscene_active)

    @staticmethod
    def _landing(world, desired, accept=lambda point: True):
        """Resolve a clear footprint before changing worlds or actor ownership."""
        candidates = [desired]
        for radius in range(4, 97, 4):
            candidates.extend((desired[0]+dx, desired[1]+dy)
                              for dx, dy in ((0, -radius), (-radius, 0), (radius, 0), (0, radius)))
        return next((point for point in candidates if accept(point) and world.can_stand(point)), None)

    def _party(self):
        """Return same actor instances and their authoritative placement owner."""
        g = self.game
        members = []
        if g.halden_visit.owns_tomas:
            members.append((g.halden_visit.tomas, g.halden_visit._place_tomas))
        if g.mill_quest.active and g.mill_quest._done('meet_mira'):
            members.append((g.mill_quest.mira, g.mill_quest._place_mira))
        if g.regent_quest.stage in ('met', 'escorting'):
            members.extend((actor, lambda world, point, actor=actor:
                            g.regent_quest._place(actor, world, point)) for actor in g.regent_quest.party)
        lantern = g.lantern_quest
        if lantern.active and lantern._owned:
            members.append((lantern.tomas, lambda world, point: lantern._place(lantern.tomas, world, point)))
            if lantern._liam_claimed:
                members.append((lantern.liam, lambda world, point: lantern._place(lantern.liam, world, point)))
            if lantern._mira_owned:
                members.append((lantern.mira, lambda world, point: lantern._place(lantern.mira, world, point)))
        # Later quest owners have priority for shared Tomas and Mira instances.
        unique = {}
        for actor, place in members:
            unique[actor] = place
        return list(unique.items())

    def _stop_party(self):
        for actor, _ in self._party():
            actor.moving = False

    def _restore_party(self):
        g = self.game
        for index, (actor, place) in enumerate(self._party()):
            desired = (g.player.position.x+(-28 if index % 2 == 0 else 28),
                       g.player.position.y-20-(index//2)*18)
            avoid = g.town.probe_rect(g.player.position)
            landing = None
            for radius in range(0, 97, 8):
                for dx, dy in ((0, -radius), (-radius, 0), (radius, 0), (0, radius)):
                    point = (desired[0]+dx, desired[1]+dy)
                    if g.town.can_stand(point, actor.probe_size, actor, avoid):
                        landing = point
                        break
                if landing is not None:
                    break
            if landing is not None:
                place(g.town, landing)
                actor.facing = 'back'

    def _commit(self, destination, position, facing, transition):
        g = self.game
        origin = g.world
        self._clear_guard()
        if origin is g.town:
            g.exterior_position.update(g.player.position)
        g.world = destination
        g.player.position.update(position)
        g.player.facing = facing
        g.player.moving = g.player.running = False
        g.player.walk_ms = 0
        g.transfer_cooldown = .35
        g.social.clear_pointer()
        g._mouse_held = False
        self._town_armed = self._region_armed = False
        for owner in (g.mill_quest, g.regent_quest, g.lantern_quest):
            owner.on_enter_scene(origin, transition)
        if destination is g.town:
            self._restore_party()
        else:
            self._stop_party()
        g.map_ui.reset()
        g.camera.reset()
        g.location_label = None
        g.location_seconds = 3.5
        g.save_progress()
        return True

    def enter_region(self):
        g = self.game
        if g.world is not g.town or not self.can_travel():
            return False
        destination = g.overworld_world
        destination.set_progress(g.social.flags)
        landing = self._landing(destination, destination.town_exit,
                                lambda point: not destination.town_entry_rect.collidepoint(point))
        if landing is None:
            return False
        return self._commit(destination, landing, 'front', {'id': 'town_to_overworld'})

    def enter_town(self):
        g = self.game
        if not self.active or not self.can_travel():
            return False
        landing = self._landing(g.town, TOWN_RETURN,
                                lambda point: not TOWN_EXIT_RECT.collidepoint(point))
        if landing is None:
            return False
        return self._commit(g.town, landing, 'back', {'id': 'overworld_to_town'})

    def update(self, seconds=0):
        g = self.game
        if self._speaking_guard is not None and (
                not self.active or not g.social.locked
                or g.social.script_identifier != self._guard_script):
            self._clear_guard()
        if g._overworld_world is not None:
            g._overworld_world.set_progress(g.social.flags)
        if self.active:
            g.world.grain_farm.update(seconds, g)
            g.world.bridge_crew.update(seconds, g)
        # Observe leaving a contact even during the short transfer cooldown.
        # A running player can reach the town exit again before it expires.
        if g.world is g.town:
            touching = TOWN_EXIT_RECT.colliderect(g.town.probe_rect(g.player.position))
            if not touching:
                self._town_armed = True
        elif self.active:
            touching = g.world.town_entry_rect.colliderect(g.world.probe_rect(g.player.position).inflate(2, 2))
            if not touching:
                self._region_armed = True
        else:
            return False
        if not self.can_travel():
            return False
        if g.world is g.town:
            if touching and self._town_armed:
                return self.enter_region()
        elif self.active:
            for landmark in g.world.data.get('landmarks', []):
                if g.player.position.distance_to(landmark['position']) <= 144:
                    self.discovered.add(landmark['id'])
            if touching and self._region_armed:
                return self.enter_town()
        return False

    def nearby_guard(self):
        if not self.active:
            return None
        return next((gate for gate in self.game.world.gates
                     if any(self.game.player.position.distance_to(point) <= 52
                            for point in gate.get('guard_positions', [gate['guard_position']]))), None)

    def _clear_guard(self):
        """Release the selected speaker on completion, cancellation or travel."""
        if self._speaking_guard is not None:
            self._speaking_guard.end_conversation()
        self._speaking_guard = None
        self._guard_script = None

    def interaction_hint(self):
        if self.active:
            hint = self.game.world.bridge_crew.interaction_hint(self.game)
            if hint:return hint
            hint = self.game.world.grain_farm.interaction_hint(self.game)
            if hint:return hint
        return 'E: Speak with the road guard' if self.nearby_guard() is not None else ''

    def interact(self):
        if not self.can_travel():
            return False
        if self.active and self.game.world.bridge_crew.interact(self.game):return True
        if self.active and self.game.world.grain_farm.interact(self.game):return True
        gate = self.nearby_guard()
        if gate is None:
            return False
        cleared = gate['clearance_flag'] in self.game.social.flags
        if not cleared:
            text = ('The road beyond this checkpoint remains closed. Stay inside the valley walls '
                    'for now; the village is still preparing for the Festival of Light.')
        elif not gate.get('destination_ready', False):
            text = 'The onward road is still closed to travelers. You can explore inside the valley walls.'
        else:
            text = 'The road is open. Travel safely.'
        guards = [actor for actor in self.game.world.npcs
                  if actor.data['id'].startswith('road_guard:'+gate['id']+':')]
        if not guards:return False
        actor = min(guards, key=lambda actor: actor.position.distance_squared_to(self.game.player.position))
        self.game.social.data['speakers']['road_guard']['actor_id'] = actor.data['id']
        identifier = 'overworld_guard_'+gate['id']
        started = self.game.social.start_script([{'speaker': 'road_guard', 'text': text}],
                                               on_complete=self._clear_guard, identifier=identifier)
        if started:
            from social import facing_toward
            # Keep this approach facing for the entire exchange rather than
            # rapidly flipping as the player moves around a planted guard.
            actor.begin_conversation(facing_toward(self.game.player.position-actor.position),
                                     self.game.elapsed_ms)
            self._speaking_guard = actor
            self._guard_script = identifier
        return started
