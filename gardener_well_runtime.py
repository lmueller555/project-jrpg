"""Native presentation for the live gardener, using her current roster identity.

The new well's sixteen crank samples select the nearest of the eight registered
whole-body roster drawings. Only rigid canonical pails rotate; no anatomy is
generated, warped or stretched. This adapter reads actor/model state only.
"""
from collections import OrderedDict, deque
from copy import deepcopy
import json
import math
from pathlib import Path
import random

import pygame

from rendering import draw, layer, load_art

ROOT = Path(__file__).resolve().parent


class GardenerWellArt:
    CACHE_LIMIT = 192

    def __init__(self, actor, world):
        self.actor = actor
        self.metadata = {}
        self.pails = {}
        folder = Path('assets/characters/npcs/female_02/gardener_well_hd')
        # Read checked-in bindings directly. The offline PR3 review adapter
        # imports Pillow, which is deliberately not a gameplay dependency.
        bank = json.loads((ROOT/folder/'animations.json').read_text())
        for variant in bank['pails']['variants']:
            angle, units = variant['angle'], variant['units']
            key = f'bucket_{angle}_{units}'
            record = dict(variant, artwork_pixels_per_world_pixel=2)
            self.pails[key] = load_art(world, (folder/variant['file']).as_posix(), record)
            self.metadata[key] = dict(variant, grip=variant['grip_logical'],
                                      spout=variant['stream_origin_logical'])
        self.cache = OrderedDict()

    def selection(self):
        actor = self.actor
        name, frame = actor.pose()
        pose = actor.animation['poses'][name]
        grip = [a+b for a, b in zip(actor.animation['body_offset'], pose['grip'])]
        units = actor.water_units
        angle = frame.get('angle', 0)
        owner = actor.pail_location
        state = actor.well_snapshot
        return {'pose_id': name, 'body_file': pose['body'],
                'pail_visible': owner == 'actor', 'pail_owner': owner,
                'water_units': units, 'angle': angle,
                'hand_grip_logical': grip,
                'pail_order': pose['order'],
                'pail': deepcopy(self.metadata[f'bucket_{angle}_{units}']),
                'crank_sample': state.crank_sample,
                'phase_id': state.phase_id, 'effect': frame.get('effect'),
                'unladen': actor._in_well_operation and state.pail_owner == 'well'
                            and state.required_station is not None}

    def sprite(self):
        actor = self.actor
        selected = self.selection()
        if selected['unladen'] and actor.roster_art is not None:
            body = actor.roster_art.sprite(actor.facing, actor.moving, actor.walk_ms)
            key = ('unladen', body)
            offset = actor.animation['body_offset']
        else:
            body = actor.bodies[selected['pose_id']]
            offset = (0, 0)
            key = (selected['pose_id'], selected['angle'], selected['water_units'],
                   selected['pail_visible'])
        found = self.cache.pop(key, None)
        if found is None:
            found = layer(actor.animation['action_canvas'], pygame.SRCALPHA)
            pail = self.pails[f'bucket_{selected["angle"]}_{selected["water_units"]}']
            grip = selected['hand_grip_logical']
            anchor = selected['pail']['grip_logical']
            xy = tuple(grip[i]-anchor[i] for i in (0, 1))
            if selected['pail_visible'] and selected['pail_order'] == 'before':
                found.blit(pail, xy)
            found.blit(body, offset)
            if selected['pail_visible'] and selected['pail_order'] == 'after':
                found.blit(pail, xy)
        self.cache[key] = found
        while len(self.cache) > self.CACHE_LIMIT:
            self.cache.popitem(last=False)
        if selected['effect'] != 'pour' or not selected['water_units']:
            return found
        # Water starts at the transformed target-facing lower lip. The actual
        # bed root is a world target; drawing never consumes a water unit.
        out = found.copy()
        grip = pygame.Vector2(selected['hand_grip_logical'])
        origin = grip-pygame.Vector2(selected['pail']['grip_logical'])
        origin += selected['pail']['stream_origin_logical']
        bed = actor.steps[actor.step_index]['bed']
        target = pygame.Vector2(bed['root'])-actor.position+actor.draw_anchor
        middle = origin.lerp(target, .5); middle.y -= 1
        points = [tuple(point) for point in (origin, middle, target)]
        draw.lines(out, '#598e9f', False, points, 1)
        draw.lines(out, '#b9d9d2', False, [(x+.5, y) for x, y in points], 1)
        return out


class Gardener:
    """One persistent ambient pail, with model-gated well work and dry routes."""
    POUR_MS = 2400
    POUR_CUE = 5/8

    def __init__(self, record, world, rng=None):
        # Imported when actors are constructed, after npc_routines has finished
        # defining its shared pathfinder and appearance-selection constants.
        from npc_routines import find_path, GARDENER_HD_ACTION, GARDENER_ROSTER
        from npc_roster_art import RosterArt
        self._pathfinder = find_path
        self.data = record
        self.world = world
        self.behavior = json.loads((ROOT/record['behavior']).read_text())
        self.animation_path = GARDENER_HD_ACTION
        self.animation = json.loads((ROOT/self.animation_path).read_text())
        self.roster_art = RosterArt(world, GARDENER_ROSTER)
        self.portrait_path = self.roster_art.portrait_path
        self.draw_anchor = self.animation['draw_anchor']
        self.position = pygame.Vector2(record['position'])
        self.probe_size = tuple(record['probe_size'])
        self.well = world.well
        self.water_capacity = self.well.model.contract['pail']['capacity_units']
        self._rng = rng if rng is not None else random.Random()
        self.rest_duration_ms = self._new_rest_duration()
        folder = Path(self.animation_path).parent
        metadata = {'artwork_pixels_per_world_pixel': 2,
                    'logical_size': self.animation['action_canvas']}
        self.bodies = {name: load_art(world, (folder/pose['body']).as_posix(), metadata)
                       for name, pose in self.animation['poses'].items()}
        self.art = GardenerWellArt(self, world)
        self.buckets = self.art.pails
        # Runtime metadata selects canonical pails; the retained source bank is
        # unchanged, and no legacy bucket pixels are loaded by this actor.
        self.animation['buckets'] = self.art.metadata
        self.steps = self._steps()
        self.step_index = 0
        self.state_ms = 0.0; self.walk_ms = 0.0
        self.facing = 'right'; self.moving = False; self.waiting = False
        self._water_units = 0; self._pail_location = 'rest'
        self.completed_cycles = 0
        self.events = deque(maxlen=64); self.well_events = deque(maxlen=64)
        self.watered_beds = []
        self.operation_token = None
        self._gate_phase = None; self._gate_route = None
        self.path = None; self.waypoint_index = 0
        self.blocked_seconds = 0.0; self.retry_seconds = 0.0
        self._accumulator = 0.0; self._pour_committed = False
        # A deposited pail has world support/depth independent of the body.
        ground_grip = pygame.Vector2(self.behavior['rest_position'])
        ground_grip -= self.draw_anchor
        ground_grip += (34, 27.5)
        pail = self.art.metadata['bucket_0_0']
        self.surface_props = [{'id': record['id']+'.pail', 'scene': world.data['id'],
                               'surface': self.buckets['bucket_0_0'],
                               'position': tuple(ground_grip-pygame.Vector2(pail['grip_logical'])),
                               'sort_y': self.behavior['rest_position'][1]+4,
                               'sort_priority': 1.5}]
        world.attach_routine_props(self)

    @property
    def blocker(self):
        w, h = self.probe_size
        return pygame.Rect(round(self.position.x)-w//2, round(self.position.y)-h//2, w, h)

    @property
    def _in_well_operation(self):
        return self.steps[self.step_index]['id'] == 'well_operation'

    @property
    def well_snapshot(self):
        return self.well.model.snapshot()

    @property
    def state(self):
        if not self._in_well_operation:
            return self.steps[self.step_index]['id']
        phase = self.well_snapshot.phase_id if self.operation_token is not None else 'await_loading'
        return {'await_operator': 'well_to_crank',
                'await_retrieval': 'well_to_loading'}.get(phase, 'well_'+phase)

    @property
    def pail_location(self):
        if self._in_well_operation and self.operation_token is not None:
            return self.well_snapshot.pail_owner
        return self._pail_location

    @property
    def water_units(self):
        if self._in_well_operation and self.operation_token is not None:
            return self.well_snapshot.water_units
        return self._water_units

    @water_units.setter
    def water_units(self, value):
        self._water_units = max(0, min(self.water_capacity, int(value)))

    @property
    def rest_remaining_ms(self):
        return max(0, self.rest_duration_ms-self.state_ms) if self.state == 'rest' else 0

    def surface_prop_visible(self, prop):
        return self.pail_location == 'rest' and self in getattr(self.world, 'npcs', ())

    def _new_rest_duration(self):
        return self._rng.randint(*self.behavior['rest_range_ms'])

    def _steps(self):
        b = self.behavior
        result = [{'id': 'rest', 'animation': 'rest', 'facing': 'right'},
                  {'id': 'pickup', 'animation': 'pickup', 'facing': 'right'},
                  {'id': 'to_well', 'waypoints': b['outbound_waypoints']},
                  {'id': 'well_operation', 'facing': 'back'},
                  {'id': 'return_to_sanctuary', 'waypoints': b['return_waypoints']}]
        for index, bed in enumerate(b['beds']):
            via = [bed['position']]
            if index == 0: via = [[340, 334], bed['position']]
            if index == 2: via = [*b['garden_crossing'], bed['position']]
            if 'via' in bed: via = [*bed['via'], bed['position']]
            result.extend([
                {'id': 'approach_'+bed['id'], 'waypoints': via},
                {'id': 'inspect_'+bed['id'], 'animation': 'inspect.'+bed['facing'],
                 'facing': bed['facing'], 'bed': bed},
                {'id': 'water_'+bed['id'], 'animation': bed.get('pour_animation', 'pour.'+bed['facing']),
                 'facing': bed['facing'], 'bed': bed}])
        return result+[{'id': 'return_to_rest', 'waypoints': b['rest_waypoints']},
                       {'id': 'setdown', 'animation': 'setdown', 'facing': 'right'}]

    def _clear_motion(self):
        self.path = None; self.waypoint_index = 0
        self.blocked_seconds = 0.0; self.retry_seconds = 0.0
        self.moving = False; self.waiting = False

    def reset_cycle(self):
        """Restore the ambient checkpoint as one actor/mechanism transaction.

        Normal room visits never call this. New journey/Continue reconstruction
        starts from rest, without serializing transient ambient pail transfers.
        """
        if self.well.owner is self or self.well.owner is None:
            self.well.reset()
        self.operation_token = None
        self._water_units = 0; self._pail_location = 'rest'
        self.position.update(self.behavior['rest_position'])
        self.step_index = 0; self.state_ms = 0.0; self.walk_ms = 0.0
        self.facing = 'right'; self._accumulator = 0.0
        self._gate_phase = None; self._gate_route = None
        self._pour_committed = False
        self.completed_cycles = 0; self.watered_beds = []
        self.events.clear(); self.well_events.clear()
        self._clear_motion()

    def _advance(self):
        self.step_index = (self.step_index+1) % len(self.steps)
        if self.step_index == 0:
            self.completed_cycles += 1
            self.rest_duration_ms = self._new_rest_duration()
            self.events.append({'type': 'cycle', 'cycle': self.completed_cycles,
                                'rest_duration_ms': self.rest_duration_ms})
        if self.state == 'pickup': self.watered_beds = []
        self.state_ms = 0.0; self.walk_ms = 0.0
        self._pour_committed = False
        self._clear_motion()
        self.facing = self.steps[self.step_index].get('facing', self.facing)

    def _well_tick(self, dt, world, player):
        if self.operation_token is None:
            self.operation_token = self.well.reserve(self, water_units=self._water_units)
            if self.operation_token is None:
                self.waiting = True; return
        snapshot = self.well_snapshot
        if snapshot.required_station is not None:
            if self._gate_phase != snapshot.phase_id:
                station = self.well.model.contract['stations'][snapshot.required_station]
                target = station['feet_world_logical']
                points = [] if snapshot.phase_id == 'await_loading' else [[564, 894]]
                self._gate_route = {'waypoints': points+[target]}
                self._gate_phase = snapshot.phase_id
                self._clear_motion()
            if self._move(dt, world, player, self._gate_route):
                station = self.well.model.contract['stations'][snapshot.required_station]
                self.facing = station['facing']; self.moving = False
                # A blocked actual station cannot open a readiness gate.
                if world.can_stand(self.position, self.probe_size, self, player):
                    self.well.model.signal_ready(self.operation_token, snapshot.required_station)
                else: self.waiting = True
            return
        self.moving = False; self.waiting = False
        self.facing = 'back' if snapshot.phase_id in ('attach', 'detach', 'complete') else 'left'
        self.well.model.update(dt)
        for event in self.well.model.drain_events():
            self.well_events.append(event)
            self.events.append({'type': 'well', 'cue_id': event.cue_id,
                                'event_id': event.event_id, 'units': event.water_units})
            if event.cue_id == 'fill_complete':
                self.events.append({'type': 'filled', 'position': tuple(self.position),
                                    'units': event.water_units})
        snapshot = self.well_snapshot
        self.state_ms = snapshot.phase_elapsed_ms
        if snapshot.completed:
            self._water_units = snapshot.water_units; self._pail_location = 'actor'
            self.well.release(self); self.operation_token = None
            self._gate_phase = None; self._gate_route = None
            self._advance()

    def update(self, seconds, world, player_blocker=None):
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Gardener update seconds must be finite and nonnegative')
        self._accumulator += seconds
        count = int((self._accumulator+1e-9)*60)
        self._accumulator -= count/60
        for _ in range(count):
            dt = 1/60
            step = self.steps[self.step_index]
            if self._in_well_operation:
                self._well_tick(dt, world, player_blocker)
            elif 'waypoints' in step:
                if self._move(dt, world, player_blocker, step): self._advance()
            else:
                self.moving = False; self.waiting = False
                self.state_ms += dt*1000
                duration = self._duration()
                if self.state == 'pickup' and self.state_ms >= duration*.5:
                    self._pail_location = 'actor'
                if self.state == 'setdown' and self.state_ms >= duration*.5:
                    self._pail_location = 'rest'
                if self.state.startswith('water_') and not self._pour_committed and self.state_ms >= duration*self.POUR_CUE:
                    self._water_units = max(0, self._water_units-1)
                    self._pour_committed = True
                    self.watered_beds.append(step['bed']['id'])
                    self.events.append({'type': 'watered', 'bed': step['bed']['id'], 'units': self.water_units})
                if self.state_ms+1e-7 >= duration: self._advance()

    def _duration(self):
        if self.state == 'rest': return self.rest_duration_ms
        if self.state.startswith('water_'): return self.POUR_MS
        return sum(frame['duration_ms'] for frame in self.animation['animations'][self.steps[self.step_index]['animation']])

    def _move(self, seconds, world, player, step):
        self.moving = False; self.waiting = False
        if self.waypoint_index >= len(step['waypoints']): return True
        goal = step['waypoints'][self.waypoint_index]
        if self.position.distance_squared_to(goal) < 1e-8:
            self.waypoint_index += 1; self.path = None
            return self.waypoint_index >= len(step['waypoints'])
        if self.path is None:
            self.retry_seconds = max(0, self.retry_seconds-seconds)
            if self.retry_seconds: self.waiting = True; return False
            self.path = self._pathfinder(world, self.position, goal, self.probe_size, self)
            if self.path is None: self.retry_seconds = 1; self.waiting = True; return False
        loaded = self.water_units > 0 and self.pail_location == 'actor'
        speed = self.behavior['loaded_speed'] if loaded else self.behavior['empty_speed']
        budget = speed*seconds
        while budget > 1e-7 and self.path:
            delta = pygame.Vector2(self.path[0])-self.position
            distance = delta.length()
            if distance < 1e-7: self.path.popleft(); continue
            direction = delta/distance; travel = min(1.0, budget, distance)
            candidate = self.position+direction*travel
            if not world.can_stand(candidate, self.probe_size, self, player):
                self.waiting = True; self.blocked_seconds += seconds
                if self.blocked_seconds >= .8:
                    alternate = self._pathfinder(world, self.position, goal, self.probe_size, self, player)
                    if alternate is not None: self.path = alternate
                    self.blocked_seconds = 0
                return False
            self.position.update(candidate); budget -= travel
            self.walk_ms += travel/60*1000
            self.facing = ('right' if direction.x > 0 else 'left') if abs(direction.x) > abs(direction.y) else ('front' if direction.y > 0 else 'back')
            self.moving = True; self.blocked_seconds = 0
        if not self.path: self.path = None
        return False

    def pose(self):
        """Current whole-body key and presentation tags; never advances state."""
        if self._in_well_operation and self.operation_token is None:
            return 'idle_full.'+self.facing, {}
        if self._in_well_operation and self.operation_token is not None:
            snapshot = self.well_snapshot; p = snapshot.phase_progress
            if snapshot.required_station is not None:
                # Unladen travel uses the roster gait in the compositor.
                return 'idle_full.'+self.facing, {}
            if snapshot.phase_id == 'attach':
                if p < .7: name = 'well_attach_back_'+str(min(6, int(p/.7*7)))
                else: name = 'well_release_back_'+str(min(4, int((p-.7)/.3*5)))
                return name, {}
            if snapshot.phase_id == 'detach':
                if p < .65: name = 'well_catch_back_'+str(min(6, int(p/.65*7)))
                else: name = 'well_take_back_'+str(min(6, int((p-.65)/.35*7)))
                return name, {}
            sample = int(math.floor(snapshot.crank_sample/2+.5)) % 8
            prefix = 'well_heavy_left_' if snapshot.phase_id == 'raise' else 'well_crank_left_'
            return prefix+str(sample), {}
        step = self.steps[self.step_index]
        if 'waypoints' in step:
            # The higher full-carry grip also keeps an empty canonical pail
            # above the ground, without changing the existing body drawing.
            if not self.moving: return 'idle_full.'+self.facing, {}
            frames = self.animation['animations']['carry_full.'+self.facing]
            return frames[int(self.walk_ms//140) % 4]['pose'], {}
        if self.state.startswith('water_'):
            key = min(7, int(self.state_ms/self.POUR_MS*8))
            trough = 'pour_trough' in step['animation']
            if trough:
                names = ['lift', 'lift', 'half', 'raise', 'raise', 'half', 'lift', 'idle']
                part = names[key]
                name = ('idle_full.'+self.facing if part == 'idle' else part+'_trough_'+self.facing)
            else: name = 'idle_full.'+self.facing if key in (0, 7) else 'raise_'+self.facing
            angle = (0, 0, 25, 50, 50, 25, 0, 0)[key]*(1 if self.facing == 'left' else -1)
            return name, {'angle': angle, 'effect': 'pour' if key in (3, 4) else None}
        frames = self.animation['animations'][step['animation']]
        time = self.state_ms
        for frame in frames:
            if time < frame['duration_ms']: return frame['pose'], frame
            time -= frame['duration_ms']
        return frames[-1]['pose'], frames[-1]

    def bucket_placement(self):
        name, frame = self.pose(); pose = self.animation['poses'][name]
        key = f'bucket_{frame.get("angle", 0)}_{self.water_units}'
        xy = pygame.Vector2(self.animation['body_offset'])+pose['grip']-pygame.Vector2(self.art.metadata[key]['grip_logical'])
        return name, frame, pose, key, xy

    def presentation_selection(self):
        return self.art.selection()

    def sprite(self, elapsed_ms):
        return self.art.sprite()
