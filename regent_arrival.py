"""One-shot, present-day arrival of Aldric's relief caravan after the mill.

Only the pending/seen receipt is durable. Shots, reading positions, art clocks
and audio belong to this view; the exploration world never advances behind it.
"""
from __future__ import annotations

from array import array
import json
import math
from pathlib import Path
import random

import pygame

import speech_bubble
from regent_aerial import RegentAerial
from regent_aerial_audio import RegentAerialAudio
from opening_audio import MorningAudio
from quests import MILL_QUEST, REGENT_QUEST, QuestLog
from ui_style import BRASS, IVORY, MUTED

ROOT = Path(__file__).resolve().parent
SCENE = ROOT/'assets/story/regent_arrival/scene.json'
VIEW_SIZE = (480, 320)
STATES = ('waiting', 'pending', 'seen')


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value*value*(3-2*value)


class ArrivalAudio:
    """Quiet diegetic cues, with ownership checks on every borrowed channel."""
    def __init__(self, game):
        self.game = game
        self.sounds = {}
        self.channels = []
        self.travel = 0.
        self.next_hoof = 0.
        self.next_wood = 0.
        self.stream = None
        self.mode = None
        self.gain = 1.

    def stop(self):
        for channel, sound in self.channels:
            try:
                if channel.get_sound() is sound:channel.stop()
            except pygame.error:pass
        self.channels.clear();self.stream = None;self.mode = None

    def _sound(self, name):
        spec = pygame.mixer.get_init()
        if not spec or spec[1] != -16:return None
        rate, _, channels = spec
        key = (name, rate, channels)
        if key not in self.sounds:
            if name == 'stream':samples = MorningAudio._samples('stream', rate, channels)
            else:
                duration = .16 if name == 'hoof' else .32
                rng = random.Random(7351)
                samples = array('h')
                for index in range(round(rate*duration)):
                    t = index/rate
                    envelope = (1-t/duration)**3
                    value = (math.sin(t*math.tau*(82 if name == 'hoof' else 190))*.55+
                             rng.uniform(-1, 1)*(.36 if name == 'hoof' else .13))
                    sample = round(18000*value*envelope)
                    samples.extend([sample]*channels)
            self.sounds[key] = pygame.mixer.Sound(buffer=samples.tobytes())
        return self.sounds[key]

    def _play(self, name, volume, loop=False):
        sound = self._sound(name)
        if sound is None:return None
        sound.set_volume(volume*float(self.game.audio.effects_volume))
        channel = sound.play(loops=-1 if loop else 0)
        if channel is not None:
            channel.set_volume(self.gain)
            self.channels.append((channel, sound))
        return (channel, sound) if channel is not None else None

    def update(self, seconds, mode, paused=False, gain=1., travel_rate=1.):
        self.gain = max(0., min(1., gain))
        volume = float(self.game.audio.effects_volume)
        if volume <= 0:
            self.stop();return
        if mode != self.mode:
            self.stop();self.mode = mode
            self.travel = self.next_hoof = self.next_wood = 0.
        for channel, sound in self.channels:
            try:
                if channel.get_sound() is sound:
                    channel.set_volume(self.gain)
                    if paused:channel.pause()
                    else:channel.unpause()
            except pygame.error:pass
        if paused:return
        try:
            self.channels = [(c, s) for c, s in self.channels if c.get_sound() is s]
            if mode == 'riverbank' and self.stream is None:
                self.stream = self._play('stream', .055, loop=True)
            if mode == 'travel':
                self.travel += seconds*travel_rate
                if self.travel >= self.next_hoof:
                    self._play('hoof', .075)
                    self.next_hoof = self.travel+(.28 if int(self.travel*2)%2 else .46)
                if self.travel >= self.next_wood:
                    self._play('wood', .04);self.next_wood = self.travel+2.8
        except (pygame.error, OSError):self.stop()


class RegentArrival:
    """A saved arrival receipt with transient, player-paced cinematic shots."""
    def __init__(self, game, *, scene_path=SCENE):
        self.game = game
        self.scene_path = Path(scene_path).resolve()
        self.data = json.loads(self.scene_path.read_text())
        self._validate()
        self.audio = ArrivalAudio(game)
        self.bird_audio = RegentAerialAudio(game)
        self.aerial = RegentAerial(self)
        self._reference_clock = None
        self._reference_camera = None
        self._reference_world = None
        self.scenery = None
        self.actor_art = {}
        self.profiles = {}
        self.portraits = {}
        self.skip_rect = pygame.Rect(426, 292, 44, 20)
        self.caption_rect = pygame.Rect(88, 8, speech_bubble.PANEL_WIDTH, 0)
        self.caption_layout = None
        self.caption_pages = []
        self.caption_lines = []
        self.reset()

    def _validate(self):
        if (self.data.get('version') != 1 or self.data.get('canvas') != [960, 480]
                or self.data.get('viewport') != list(VIEW_SIZE)
                or not self.data.get('phases')):
            raise ValueError('Invalid regent arrival scene')
        seen = set()
        for phase in self.data['phases']:
            duration = phase.get('min_seconds')
            if (not isinstance(phase.get('id'), str) or phase['id'] in seen
                    or type(duration) not in (int, float) or not math.isfinite(duration)
                    or not 0 < duration <= 60):
                raise ValueError('Invalid arrival shot')
            seen.add(phase['id'])
            for p in (phase['camera']['from'], phase['camera']['to']):
                if (len(p) != 2 or any(type(n) not in (int, float) or not math.isfinite(n) for n in p)
                        or not 0 <= p[0] <= 480 or not 0 <= p[1] <= 160):
                    raise ValueError('Arrival camera leaves its plate')
            for line in phase['dialogue']:
                if line.get('speaker') not in self.data['speakers'] or not line.get('text'):
                    raise ValueError('Invalid arrival dialogue')
            for actor in phase['actors']:
                if actor['id'] not in self.data['actors']:
                    raise ValueError('Unknown arrival actor')

    def _path(self, filename):
        path = (self.scene_path.parent/filename).resolve()
        if not path.is_relative_to(self.scene_path.parent):
            raise ValueError('Arrival asset leaves its folder')
        return path

    @staticmethod
    def valid_snapshot(data):
        return (isinstance(data, dict) and set(data) == {'version', 'state'}
                and type(data['version']) is int and data['version'] == 1
                and isinstance(data['state'], str) and data['state'] in STATES)

    @staticmethod
    def valid_journey(data):
        record = data.get('regent_arrival')
        if not RegentArrival.valid_snapshot(record):return False
        quests = QuestLog()
        if not quests.restore(data.get('quests')):return False
        mill = quests.status(MILL_QUEST);regent = quests.status(REGENT_QUEST)
        state = record['state']
        if state == 'waiting':return mill != 'completed' and regent == 'locked'
        if mill != 'completed':return False
        if state == 'pending':
            return (regent == 'available' and
                    data.get('regent_quest', {}).get('stage', 'idle') == 'idle')
        return regent in ('available', 'active', 'ready', 'completed')

    def to_dict(self):return {'version': 1, 'state': self.state}

    @property
    def arrival_complete(self):return self.state == 'seen'

    def reset(self):
        self.audio.stop()
        self.bird_audio.reset()
        self.state = 'waiting'
        self.active = False;self.paused = False;self.focused = True
        self.phase_index = 0;self.phase_time = 0.;self.elapsed = 0.
        self.dialogue_index = 0;self.page_index = 0
        self.finished_reason = None;self._mouse_held = False
        self._batch_advanced = False;self._batch_pause = False
        self._music_transition_started = False
        self.caption_layout = None;self.caption_pages = [];self.caption_lines = []

    def restore(self, data=None):
        if data is not None and not self.valid_snapshot(data):return False
        self.reset()
        # Old journeys have already lived through the original caravan staging.
        self.state = (data['state'] if data is not None else
                      'seen' if self.game.quests.status(MILL_QUEST) == 'completed' else 'waiting')
        return True

    def request(self):
        if (self.state != 'waiting' or self.game.quests.status(MILL_QUEST) != 'completed'
                or self.game.quests.status(REGENT_QUEST) != 'available'):return False
        self.state = 'pending'
        return True

    def maybe_start(self):
        if (self.state != 'pending' or self.active or self.game.on_title
                or self.game.social.active or self.game.pause.is_open
                or self.game.combat.active):return False
        self.active = True;self.paused = False;self.focused = bool(self.game._music_focused)
        self.phase_index = 0;self.phase_time = 0.;self.elapsed = 0.
        self.dialogue_index = 0;self.page_index = 0
        self.game.player.moving = False;self.game._mouse_held = False
        self.game.social.clear_pointer()
        self.game.map_open = False;self.game.quest_ui.reset()
        self.game.inventory_ui.reset();self.game.world_map_viewer.close()
        self.game.opening_audio.set_paused(True)
        return True

    @property
    def phase(self):return self.data['phases'][self.phase_index]
    @property
    def shot(self):return self.phase['id']
    @property
    def dialogue(self):
        lines = self.phase['dialogue']
        if self.phase_time < self.phase.get('dialogue_delay', .4):return None
        return lines[self.dialogue_index] if self.dialogue_index < len(lines) else None
    @property
    def reduced_motion(self):return bool(self.game.audio.reduced_motion)
    @property
    def camera_position(self):
        if self._reference_camera is not None:return pygame.Vector2(self._reference_camera)
        camera = self.phase['camera']
        progress = (1. if self.reduced_motion else
                    smooth((self.phase_time-camera.get('move_start', 0.))/
                           camera.get('move_seconds', self.phase['min_seconds'])))
        return pygame.Vector2(camera['from']).lerp(camera['to'], progress)

    def aerial_snapshot(self):
        if self.phase['scene'] != 'aerial':return None
        seconds = sum(p['min_seconds'] for p in self.data['phases'][:self.phase_index]
                      if p['scene'] == 'aerial')+self.phase_time
        return self.aerial.sample(seconds, reduced_motion=self.reduced_motion)

    def begin_input_batch(self):
        self._batch_advanced = False;self._batch_pause = False

    def advance(self):
        if (not self.active or self.paused or not self.focused or self._batch_advanced
                or not self.game._music_focused or self.dialogue is None):return False
        self._batch_advanced = True
        self._layout(self.game.ui.painter(self.game.ui_surface))
        if self.page_index+1 < len(self.caption_pages):self.page_index += 1
        else:self.dialogue_index += 1;self.page_index = 0
        self._next_if_ready()
        return True

    def handle_event(self, event):
        if event.type == pygame.WINDOWFOCUSLOST:
            self.focused = False;self.audio.update(0, self._audio_mode(), paused=True)
            self.bird_audio.update(0, self.aerial_snapshot(), paused=True)
        elif event.type == pygame.WINDOWFOCUSGAINED:self.focused = True
        elif not self.focused:return
        elif event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key == pygame.K_ESCAPE and not self._batch_pause:
                self.paused = not self.paused;self._batch_pause = True
                self.audio.update(0, self._audio_mode(), paused=self.paused, gain=self._audio_gain())
                self.bird_audio.update(0, self.aerial_snapshot(), paused=self.paused)
            elif event.key in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN):self.advance()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:self._mouse_held = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            point = self.game.to_canvas(event.pos)
            if point is None:return
            if not self._mouse_held:
                if self.skip_rect.collidepoint(point):self.finish('skipped')
                else:self.advance()
            self._mouse_held = True

    def _next_if_ready(self):
        if (self.phase_time < self.phase['min_seconds']
                or self.dialogue_index < len(self.phase['dialogue'])):return
        if self.phase_index+1 == len(self.data['phases']):self.finish('finished');return
        self.phase_index += 1;self.phase_time = 0.
        self.dialogue_index = 0;self.page_index = 0
        self.caption_layout = None;self.caption_pages = [];self.caption_lines = []

    def _audio_mode(self, snapshot=None):
        if self.phase['scene'] == 'aerial':
            if snapshot is None:snapshot = self.aerial_snapshot()
            return 'travel' if snapshot.get('party_visible') and snapshot.get('party_moving') else None
        if self.phase.get('sound') == 'travel':
            for actor in self.phase['actors']:
                if actor['id'] not in ('aldric', 'caravan'):continue
                start = actor.get('move_start', 0.)
                duration = actor.get('move_seconds', self.phase['min_seconds'])
                if (any(key in actor for key in ('to', 'path', 'route'))
                        and start <= self.phase_time < start+duration):return 'travel'
        return 'riverbank' if self.phase['scene'] == 'riverbank' or self.phase.get('sound') == 'riverbank' else None

    def _audio_gain(self, snapshot=None):
        if self.phase['scene'] == 'aerial':
            if snapshot is None:snapshot = self.aerial_snapshot()
            return 1. if snapshot.get('ground_handoff') else .25
        if self.shot == 'gate_admission':return 1-self.fade_alpha/255
        if self.shot == 'gate_departure_black':return .35*smooth(self.phase_time/self.phase['min_seconds'])
        if self.shot == 'bridge_establishing':return .35+.65*smooth(self.phase_time/self.phase.get('fade_in', 1.))
        return 1.

    def _travel_rate(self, snapshot=None):
        if self.phase['scene'] == 'aerial':
            if snapshot is None:snapshot = self.aerial_snapshot()
            return snapshot.get('approach_speed_pixels', 40.)/40.
        return min((actor.get('animation_rate', 1.) for actor in self.phase['actors']
                    if actor['id'] in ('aldric', 'caravan')), default=1.)

    def update(self, seconds):
        if not self.active:return
        paused = self.paused or not self.focused or not self.game._music_focused
        snapshot = self.aerial_snapshot()
        self.audio.update(0 if paused else seconds, self._audio_mode(snapshot), paused=paused,
                          gain=self._audio_gain(snapshot), travel_rate=self._travel_rate(snapshot))
        self.bird_audio.update(0 if paused else seconds, snapshot, paused=paused)
        if paused:return
        self.phase_time += max(0., seconds);self.elapsed += max(0., seconds)
        if (self.shot == 'mill_close' and self.fade_alpha
                and not self._music_transition_started):
            self._music_transition_started = True
            self.game.music.play('royalty', fade_ms=1000)
        self._next_if_ready()

    def finish(self, reason='finished'):
        if not self.active:return False
        self.audio.stop();self.bird_audio.stop()
        self.active = False;self.paused = False;self.state = 'seen';self.finished_reason = reason
        self.game._mouse_held = False;self.game.social.clear_pointer()
        self.game.player.moving = False
        self.game.regent_quest.restore(self.game.regent_quest.to_dict())
        self.game.music.set_paused(not self.game._music_focused)
        self.game.music.set_ducked(False)
        self.game.music.play('eldenmere')
        self.game.save_progress()
        return True

    def _load(self):
        if self.scenery is not None:return
        manifest_path = self._path(self.data['scenery_manifest'])
        scenery = json.loads(manifest_path.read_text())
        plates = {}
        for key, record in scenery['scenes'].items():
            loaded = dict(record)
            for part in ('background', 'foreground'):
                if record.get(part):
                    image = pygame.image.load(str(manifest_path.parent/record[part])).convert_alpha()
                    if image.get_size() != tuple(self.data['canvas']):
                        raise ValueError('Arrival scenery has incorrect dimensions')
                    loaded[part] = image
            if record.get('gate_leaf'):
                leaf = dict(record['gate_leaf'])
                leaf['image'] = pygame.image.load(str(manifest_path.parent/leaf['file'])).convert_alpha()
                loaded['gate_leaf'] = leaf
            loaded['occluders'] = []
            for record_layer in record.get('occluders', []):
                image = pygame.image.load(str(manifest_path.parent/record_layer['file'])).convert_alpha()
                if image.get_size() != tuple(self.data['canvas']):
                    raise ValueError('Arrival occlusion layer has incorrect dimensions')
                # RGB zero lets subtraction construct an inverse alpha mask
                # without changing the actor's painted colors.
                image.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
                loaded['occluders'].append({**record_layer, 'image':image})
            plates[key] = loaded
        actors = {}
        for identifier, filename in self.data['actors'].items():
            path = self._path(filename);record = json.loads(path.read_text())
            frames = {key: pygame.image.load(str(path.parent/name)).convert_alpha()
                      for key, name in record['poses'].items()}
            loops = {key: [(pygame.image.load(str(path.parent/f['file'])).convert_alpha(), f['duration_ms']/1000)
                           for f in sequence] for key, sequence in record.get('loops', {}).items()}
            if (not frames or any(image.get_size() != tuple(record['canvas']) for image in frames.values())
                    or any(not sequence or any(image.get_size() != tuple(record['canvas'])
                        or not math.isfinite(duration) or duration <= 0 for image, duration in sequence)
                        for sequence in loops.values())):
                raise ValueError('Invalid arrival actor frames or loop duration')
            for pose,gait in record.get('gaits', {}).items():
                stride = gait.get('stride_pixels')
                if (pose not in loops or type(stride) not in (int,float)
                        or not math.isfinite(stride) or stride <= 0):
                    raise ValueError('Invalid arrival actor stride')
            actors[identifier] = {**record, 'poses': frames, 'loops': loops}
        for key, record in self.data['speakers'].items():
            profile = dict(self.game.social.data['speakers'].get(record.get('profile'), record))
            if record.get('portrait_file'):
                portrait = pygame.image.load(str(self._path(record['portrait_file']))).convert_alpha()
                profile['portrait'] = 'arrival_'+key
            else:portrait = self.game.social.portraits[profile['portrait']]
            self.profiles[key] = profile;self.portraits[profile['portrait']] = portrait
        self.scenery = plates;self.actor_art = actors

    def _movement_fraction(self, actor):
        start = actor.get('move_start', 0.)
        duration = actor.get('move_seconds', self.phase['min_seconds'])
        return max(0., min(1., (self.phase_time-start)/duration))

    def actor_route_distance(self, actor):
        return actor['route_start']+(actor['route_end']-actor['route_start'])*self._movement_fraction(actor)

    def _route_sample(self, actor):
        """Project a shared ground route; depth controls both size and feet.

        The stations are ground-space lateral position and distance away from
        the foreground. Equal travel distances keep the party spaced along
        the bend while perspective naturally reduces apparent speed.
        """
        route = self.data['routes'][actor['route']]
        points = [pygame.Vector2(x, depth*route['depth_unit']) for x,depth in route['stations']]
        remaining = self.actor_route_distance(actor)
        point = points[-1]
        for a,b in zip(points, points[1:]):
            length = a.distance_to(b)
            if remaining <= length:
                point = a.lerp(b, max(0., remaining/length))
                break
            remaining -= length
        scale = 1/(1+point.y/route['depth_unit'])
        vanish = pygame.Vector2(route['vanishing_point'])
        position = pygame.Vector2(vanish.x+(point.x-vanish.x)*scale,
                                  vanish.y+(route['ground_y']-vanish.y)*scale)
        return position,scale

    def actor_position(self, actor):
        if actor.get('route'):return self._route_sample(actor)[0]
        progress = self._movement_fraction(actor)
        points = actor.get('path', [actor['position'], actor.get('to', actor['position'])])
        lengths = [pygame.Vector2(a).distance_to(b) for a,b in zip(points, points[1:])]
        distance = sum(lengths)*progress
        for a, b, length in zip(points, points[1:], lengths):
            if distance <= length and length:
                return pygame.Vector2(a).lerp(b, distance/length)
            distance -= length
        return pygame.Vector2(points[-1])

    def actor_pose(self, actor):
        pose = actor['pose']
        start = actor.get('move_start', 0.)
        duration = actor.get('move_seconds', self.phase['min_seconds'])
        if 'to' in actor or 'path' in actor or 'route' in actor:
            if self.phase_time < start:pose = actor.get('before_pose', 'parked_left' if actor['id'] == 'caravan' else 'stand_left')
            elif self.phase_time >= start+duration:pose = actor.get('after_pose', 'parked_left' if actor['id'] == 'caravan' else 'stand_left')
            elif actor.get('route'):
                for distance,mark_pose in actor.get('route_poses', []):
                    if self.actor_route_distance(actor) >= distance:pose = mark_pose
        if (actor.get('turn_start') is not None and
                actor['turn_start'] <= self.phase_time < start):pose = actor['turn_pose']
        if actor['id'] == 'serene' and self.dialogue_index >= 2:pose = 'turn_right'
        return pose

    def _frame(self, actor):
        art = self.actor_art[actor['id']]
        pose = self.actor_pose(actor)
        start = actor.get('move_start', 0.)
        if pose in art['loops']:
            frames = art['loops'][pose];total = sum(d for _,d in frames)
            clock = (max(0., self.phase_time-start) if self._reference_clock is None
                     else self._reference_clock-start)
            gait = art.get('gaits', {}).get(pose)
            if gait and any(key in actor for key in ('to','path','route')):
                # The authored support boot advances opposite the root by one
                # stride per cycle. Scene-specific time multipliers must not
                # make the feet race or drag as travel speed changes. Negative
                # reference clocks retain the aerial-to-ground gait phase.
                duration = actor.get('move_seconds',self.phase['min_seconds'])
                if actor.get('route'):
                    distance = actor['route_end']-actor['route_start']
                else:
                    points = actor.get('path',[actor['position'],actor.get('to',actor['position'])])
                    distance = sum(pygame.Vector2(a).distance_to(b) for a,b in zip(points,points[1:]))
                time = (clock*distance/duration/gait['stride_pixels']*total)%total
            else:
                time = (clock*actor.get('animation_rate',1.))%total
            for image, duration in frames:
                if time < duration:return image
                time -= duration
            return frames[-1][0]
        return art['poses'][pose]

    def _actor_scale(self, actor):
        scale = actor.get('scale', 1.)
        if actor.get('route'):return scale*self._route_sample(actor)[1]
        if 'scale_to' in actor:
            fraction = max(0., min(1., (self.phase_time-actor.get('move_start', 0.))/actor.get('move_seconds', self.phase['min_seconds'])))
            scale += (actor['scale_to']-scale)*fraction
        return scale

    def _draw_actor(self, canvas, actor, camera):
        image = self._frame(actor);art = self.actor_art[actor['id']]
        anchor = pygame.Vector2(art['anchor']);position = self.actor_position(actor)
        scale = self._actor_scale(actor)
        if scale != 1.:
            image = pygame.transform.scale(image, (max(1, round(image.get_width()*scale)), max(1, round(image.get_height()*scale))))
            anchor *= scale
        point = position-camera-anchor
        occluders = self.scenery.get(self.phase['scene'], {}).get('occluders', [])
        for layer in occluders:
            if position.y > layer['behind_y']:continue
            visibility = pygame.Surface(image.get_size(), pygame.SRCALPHA)
            visibility.fill((255, 255, 255, 255))
            origin = position-anchor
            visibility.blit(layer['image'], (-round(origin.x), -round(origin.y)),
                            special_flags=pygame.BLEND_RGBA_SUB)
            image = image.copy()
            image.blit(visibility, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        old_clip = canvas.get_clip()
        clips = actor.get('clip_rects')
        if clips:
            for bounds in clips:
                clip = pygame.Rect(bounds).move(-round(camera.x), -round(camera.y)).clip(old_clip)
                canvas.set_clip(clip)
                canvas.blit(image, (round(point.x), round(point.y)))
            canvas.set_clip(old_clip)
        else:canvas.blit(image, (round(point.x), round(point.y)))
        return image.get_bounding_rect().move(round(point.x), round(point.y))

    def _draw_world(self, canvas):
        game = self.game;camera = game.camera.position()
        game.world.draw(canvas, camera, game.player, game.elapsed_ms+self.elapsed*1000, include_ui=False)
        game.combat.draw_world(canvas, camera);game.opening.draw_world(canvas, camera)
        for visit in game.household_visits:visit.draw_world(canvas, camera)

    @property
    def fade_alpha(self):
        phase = self.phase
        if phase.get('black'):return 255
        fade_in = max(0., 1-self.phase_time/phase['fade_in']) if phase.get('fade_in') else 0.
        fade_out = (max(0., (self.phase_time-(phase['min_seconds']-phase['fade_out']))/phase['fade_out'])
                    if phase.get('fade_out') else 0.)
        return round(255*max(0., min(1., max(fade_in, fade_out))))

    def _layout(self, painter):
        height = max(20, painter.font().get_linesize()+8)
        width = max(44, painter.font().size('Skip')[0]+18)
        self.skip_rect = pygame.Rect(470-width, 310-height, width, height)
        self.caption_layout = None;self.caption_pages = [];self.caption_lines = []
        line = self.dialogue
        if line is None:return
        profile = self.profiles.get(line['speaker'])
        if profile is None:
            source = self.data['speakers'][line['speaker']]
            profile = self.game.social.data['speakers'].get(source.get('profile'), source)
        wrapped = painter.wrap(line['text'], speech_bubble.TEXT_WIDTH)
        self.caption_pages = [wrapped[i:i+speech_bubble.MAX_LINES] for i in range(0, len(wrapped), speech_bubble.MAX_LINES)]
        self.page_index = min(self.page_index, len(self.caption_pages)-1)
        self.caption_lines = self.caption_pages[self.page_index]
        name = profile['name']+(' · thoughts' if line.get('thought') else '')
        names, text_top, line_height, height = speech_bubble.measure_dialogue(painter, name, self.caption_lines)
        panel = pygame.Rect((480-speech_bubble.PANEL_WIDTH)//2, 8, speech_bubble.PANEL_WIDTH, math.ceil(height))
        self.caption_rect = panel
        portrait = pygame.Rect(panel.x+speech_bubble.PADDING, panel.y+12, speech_bubble.PORTRAIT_SIZE, speech_bubble.PORTRAIT_SIZE)
        self.caption_layout = speech_bubble.BubbleLayout(panel, portrait,
            (panel.x+speech_bubble.TEXT_OFFSET, panel.y+text_top), (), panel.midbottom,
            None, False, False, profile['portrait'], name_lines=names, line_height=line_height)

    def gate_leaf_frame(self, leaf):
        # A wooden gate turns about its fixed hinge. Foreshortening gives the
        # side-on end pose without dragging a full-width leaf through masonry.
        fraction = smooth(self.phase_time/.85) if self.phase.get('gate_open') else 0.
        target = leaf.get('open_scale', (.08, 1.))
        sx, sy = (1+(value-1)*fraction for value in target)
        original = leaf['image']
        image = (original if fraction == 0 else pygame.transform.scale(original,
                 (max(1,round(original.get_width()*sx)),max(1,round(original.get_height()*sy)))))
        hinge = pygame.Vector2(leaf.get('hinge',(0,original.get_height())))
        position = (pygame.Vector2(leaf['position'])-pygame.Vector2(leaf.get('anchor',(0,0)))
                    +hinge-pygame.Vector2(hinge.x*sx,hinge.y*sy)-self.camera_position)
        return image, position

    def _draw_plate(self, canvas, include_actors=True, include_gate=True):
        if self.phase['scene'] == 'aerial':
            snapshot = self.aerial_snapshot()
            self.aerial.draw(canvas, snapshot['seconds'], self.ground_reference_frame,
                             reduced_motion=self.reduced_motion)
            return
        camera = self.camera_position
        if self.phase['scene'] == 'world':self._draw_world(canvas)
        else:
            scenery = self.scenery[self.phase['scene']]
            canvas.blit(scenery['background'], (-round(camera.x), -round(camera.y)))
            if include_gate and scenery.get('gate_leaf'):
                image, position = self.gate_leaf_frame(scenery['gate_leaf'])
                canvas.blit(image, (round(position.x), round(position.y)))
            for actor in sorted(self.phase['actors'] if include_actors else [], key=lambda a:self.actor_position(a).y):
                self._draw_actor(canvas, actor, camera)
                if actor['id'] == 'caravan':
                    art = self.actor_art['caravan']
                    if (art.get('driver_offset') and not actor.get('driver_baked')
                            and self.actor_pose(actor) not in art.get('driver_baked_poses', [])
                            and not any(a['id'] == 'driver' for a in self.phase['actors'])):
                        driver = {'id':'driver','pose':art.get('driver_seated_pose','seated_left'),
                                  'position':list(self.actor_position(actor)+pygame.Vector2(art['driver_offset'])*self._actor_scale(actor)),
                                  'scale':self._actor_scale(actor), 'clip_rects':actor.get('clip_rects')}
                        self._draw_actor(canvas, driver, camera)
            if scenery.get('foreground'):
                canvas.blit(scenery['foreground'], (-round(camera.x), -round(camera.y)))

    def ground_reference_frame(self, canvas, seconds=0., include_actors=True, include_gate=True,
                               viewport=None, standing=False):
        """Render the registered ground scene without advancing the story.

        The aerial camera's foreground pass reveals a wider view of this very
        plate. The remaining descent is a camera push, not an image dissolve.
        """
        index = next(i for i,p in enumerate(self.data['phases']) if p['id']=='gate_approach')
        phase = self.data['phases'][index]
        saved = (self.phase_index,self.phase_time,self._reference_clock,self._reference_camera)
        reference = dict(phase)
        reference['actors'] = [dict(actor) for actor in phase['actors']]
        for actor in reference['actors']:
            if actor['id'] in ('aldric','caravan'):
                # Translate the whole path, not only its start. The reference
                # root moves at24px/s; its gait must retain that same speed.
                for key in ('position','to'):
                    if key in actor:
                        actor[key] = list(actor[key])
                        actor[key][0] += max(0.,-seconds)*24
                if standing:
                    actor['pose'] = 'stand_left' if actor['id']=='aldric' else 'parked_left'
                    for key in ('to','path','move_start','move_seconds','before_pose','after_pose'):
                        actor.pop(key,None)
        try:
            self.data['phases'][index] = reference
            self.phase_index = index;self.phase_time = 0.;self._reference_clock = seconds
            if viewport is None:self._draw_plate(canvas, include_actors=include_actors, include_gate=include_gate)
            else:
                self._reference_camera = (0,0)
                if self._reference_world is None:self._reference_world=pygame.Surface((960,480))
                self._draw_plate(self._reference_world,include_actors=include_actors,include_gate=include_gate)
                bounds=pygame.Rect(*(round(v) for v in viewport))
                if not self._reference_world.get_rect().contains(bounds):raise ValueError('Aerial landing leaves its ground plate')
                pygame.transform.scale(self._reference_world.subsurface(bounds),canvas.get_size(),canvas)
        finally:
            self.data['phases'][index] = phase
            self.phase_index,self.phase_time,self._reference_clock,self._reference_camera = saved

    def draw(self, canvas, ui_surface):
        self._load();canvas.fill('#1d302a')
        self._draw_plate(canvas)
        pygame.transform.scale(canvas, ui_surface.get_size(), ui_surface)
        painter = self.game.ui.painter(ui_surface)
        self._layout(painter)
        if self.caption_layout is not None:
            speech_bubble.draw_dialogue_frame(painter, self.caption_layout, self.portraits[self.caption_layout.portrait_key])
            speech_bubble.draw_dialogue_prose(painter, self.caption_layout, self.caption_lines,
                hint='Click to continue', show_indicator=self.reduced_motion or int(self.elapsed/.65)%2 == 0)
        if self.phase.get('caption'):painter.text(self.phase['caption'], (240, 24), color=IVORY, anchor='midtop')
        if self.fade_alpha:
            veil = pygame.Surface(ui_surface.get_size(), pygame.SRCALPHA)
            veil.fill((0, 0, 0, self.fade_alpha))
            ui_surface.blit(veil, (0, 0))
        painter.button(self.skip_rect,'Skip')
        pause_key = 'P' if getattr(self.game, '_is_gallery_preview', False) else 'Esc'
        painter.text(f'{pause_key} · Resume' if self.paused else f'{pause_key} · Pause', (12,self.skip_rect.centery), role='small',color=MUTED,anchor='midleft')
        if self.paused or not self.focused or not self.game._music_focused:
            rect = pygame.Rect(193,264,94,26)
            painter.panel(rect);painter.text('Paused',rect.center,role='label',color=IVORY,bold=True,anchor='center')
