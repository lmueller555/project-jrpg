"""A layered, real-time opening scene before the ordinary sanctuary morning.

The cinematic has its own visual clock and never advances the exploration world.
Game owns music, persistence and the final handoff; this view owns its shots,
acting, readable timed captions and explicit pause/skip controls.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame

import speech_bubble
from ui_style import BRASS, GOLD, IVORY, MUTED


ROOT = Path(__file__).resolve().parent
SCENE = ROOT/'assets/story/opening_cinematic/scene.json'
VIEW_SIZE = (480, 320)


def _smooth(value):
    value = max(0.0, min(1.0, value))
    return value*value*(3-2*value)


class OpeningCinematic:
    """Bounded authored shots with a single completion callback per playback."""

    def __init__(self, game, *, scene_path=SCENE):
        self.game = game
        self.scene_path = Path(scene_path).resolve()
        self.data = json.loads(self.scene_path.read_text(encoding='utf-8'))
        self._validate()
        self.duration = float(self.data['duration'])
        self.layers = None
        self.actors = None
        self._actor_loops = {}
        self._prop_art = {}
        self._upper_sky = None
        self._upper_edge_layers = {}
        self._mist_texture = None
        self.skip_rect = pygame.Rect(426, 292, 44, 20)
        self.caption_rect = pygame.Rect(22, 250, 436, 32)
        self.caption_lines = []
        self.caption_pages = []
        self.caption_page_index = 0
        self.caption_layout = None
        self._caption_cache = {}
        self._dialogue_speakers = {}
        self._dialogue_portraits = {}
        self.reset()

    def _validate(self):
        data = self.data
        if (data.get('version') != 1 or tuple(data.get('viewport', ())) != VIEW_SIZE
                or tuple(data.get('canvas', ())) != (960, 480)
                or type(data.get('duration')) not in (int, float)
                or not math.isfinite(data['duration']) or data['duration'] <= 0):
            raise ValueError('Invalid opening cinematic scene')
        bounds = data.get('camera_bounds', (0, 0, 480, 160))
        if (len(bounds) != 4 or any(type(value) not in (int, float)
                or not math.isfinite(value) for value in bounds)
                or bounds[0] > bounds[2] or bounds[1] > bounds[3]):
            raise ValueError('Invalid cinematic camera bounds')
        end = 0.0
        for record in data['shots']:
            if record['start'] != end or record['end'] <= record['start']:
                raise ValueError('Opening cinematic shots must be continuous')
            end = record['end']
            for point in (record['from'], record['to']):
                if (len(point) != 2 or any(type(value) not in (int, float)
                        or not math.isfinite(value) for value in point)
                        or not (bounds[0] <= point[0] <= bounds[2]
                                and bounds[1] <= point[1] <= bounds[3])):
                    raise ValueError('Opening cinematic camera leaves the authored scene')
            if any(type(value) not in (int, float) or not math.isfinite(value)
                   or not 1 <= value <= 3 for value in record.get('zoom', (1, 1))):
                raise ValueError('Invalid cinematic zoom')
        if end != data['duration']:
            raise ValueError('Opening cinematic shots must cover its duration')
        end = 0.0
        for record in data['dialogue']:
            if (record['start'] < end or record['end'] <= record['start']
                    or record['end'] > data['duration'] or not record['text']):
                raise ValueError('Invalid opening cinematic dialogue timing')
            end = record['end']
        for actor, tracks in data.get('position_tracks', {}).items():
            if actor not in data['acting']:
                raise ValueError('Unknown moving cinematic actor')
            end = 0.0
            for record in tracks:
                if record['start'] < end or record['end'] <= record['start']:
                    raise ValueError('Cinematic actor paths must not overlap')
                for point in (record['from'], record['to']):
                    if len(point) != 2 or any(type(value) not in (int, float)
                            or not math.isfinite(value) for value in point):
                        raise ValueError('Invalid cinematic actor path')
                end = record['end']
        flare = data.get('flare')
        if flare is not None:
            times = [flare.get('charge_start', flare['launch']), flare['launch'],
                     flare['flight_end'], flare['burst_end'],
                     flare.get('glimmer_until', data['duration'])]
            if (any(type(value) not in (int, float) or not math.isfinite(value)
                    for value in times) or times != sorted(times)
                    or flare['flight_end'] <= flare['launch']
                    or flare['burst_end'] <= flare['flight_end']):
                raise ValueError('Invalid cinematic flare sequence')
            release = flare.get('charge_release_start', flare['launch'])
            if not times[0] <= release <= flare['launch']:
                raise ValueError('Invalid flare hand-raise timing')
        lamp = data.get('dynamic_props', {}).get('lamp')
        if lamp is not None:
            if len(lamp['states']) < 2:
                raise ValueError('Cinematic lamp needs visible repair stages')
            gate = lamp.get('restored_after_shot')
            if gate is not None and gate not in {shot['id'] for shot in data['shots']}:
                raise ValueError('Unknown lamp restoration camera gate')

    def _path(self, filename):
        path = (self.scene_path.parent/filename).resolve()
        if not path.is_relative_to(self.scene_path.parent.resolve()):
            raise ValueError('Cinematic asset leaves its folder')
        return path

    def _load(self):
        if self.layers is not None:
            return
        layers = []
        for record in self.data['layers']:
            image = pygame.image.load(str(self._path(record['file']))).convert_alpha()
            if image.get_size() != tuple(self.data['canvas']):
                raise ValueError('Cinematic layers must share their authored canvas')
            layers.append((record, image))
        upper_sky = None
        if self.data.get('upper_sky') is not None:
            record = self.data['upper_sky']
            upper_sky = pygame.image.load(str(self._path(record['file']))).convert_alpha()
            if record.get('size') and upper_sky.get_size() != tuple(record['size']):
                raise ValueError('Incorrect upper-sky artwork size')
        actors, actor_loops = [], {}
        for record in self.data['actors']:
            manifest_path = self._path(record['manifest'])
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            frames = {}
            def load_frame(filename):
                path = self._path((manifest_path.parent/filename).relative_to(self.scene_path.parent).as_posix())
                image = pygame.image.load(str(path)).convert_alpha()
                if image.get_size() != tuple(manifest['canvas']):
                    raise ValueError('Cinematic poses must share their actor canvas')
                return image
            for pose, filename in manifest['poses'].items():
                frames[pose] = load_frame(filename)
            loops = {}
            for state, records in manifest.get('loops', {}).items():
                sequence = []
                for frame in records:
                    duration = frame['duration_ms']
                    if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
                        raise ValueError('Invalid cinematic loop duration')
                    sequence.append((load_frame(frame['file']), duration/1000))
                if not sequence:
                    raise ValueError('Empty cinematic actor loop')
                loops[state] = sequence
                # An alias preserves the static pose and old four-tuple API.
                frames.setdefault(state, sequence[0][0])
            actor_loops[record['id']] = loops
            transitions = {}
            for identifier, records in manifest.get('transitions', {}).items():
                sequence = []
                for frame in records:
                    duration = frame['duration_ms']
                    if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
                        raise ValueError('Invalid cinematic transition duration')
                    sequence.append((load_frame(frame['file']), duration/1000))
                if not sequence:
                    raise ValueError('Empty cinematic actor transition')
                transitions[identifier] = sequence
            if any(cue['pose'] not in frames for cue in self.data['acting'][record['id']]):
                raise ValueError('Cinematic actor is missing an authored pose')
            actors.append((record, tuple(manifest['anchor']), frames, transitions))
        prop_art = {}
        for identifier, record in self.data.get('dynamic_props', {}).items():
            if identifier == 'lamp':
                prop_art[identifier] = [pygame.image.load(str(self._path(filename))).convert_alpha()
                                        for filename in record['states']]
            elif record.get('file'):
                prop_art[identifier] = pygame.image.load(str(self._path(record['file']))).convert_alpha()
        upper_edge_layers = {}
        if upper_sky is not None:
            for record, image in layers:
                mask = pygame.Surface(image.get_size(), pygame.SRCALPHA)
                mask.fill((255, 255, 255, 255))
                # These ground plates were authored to the original frame.
                # A soft edge lets the vertical camera reveal the new sky
                # without displaying the old artwork's rectangular crop.
                for y in range(48):
                    alpha = round(255*_smooth(y/47))
                    pygame.draw.line(mask, (255, 255, 255, alpha), (0, y),
                                     (image.get_width()-1, y))
                softened = image.copy()
                softened.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                upper_edge_layers[record['file']] = softened
        self.layers, self.actors = layers, actors
        self._actor_loops, self._prop_art, self._upper_sky = actor_loops, prop_art, upper_sky
        self._upper_edge_layers = upper_edge_layers
        social = getattr(self.game, 'social', None)
        speakers = (social.data['speakers'] if social is not None else
                    json.loads((ROOT/'assets/dialogue/eldenmere.json').read_text())['speakers'])
        portraits = getattr(social, 'portraits', {})
        manifest = None
        for name in {record['speaker'] for record in self.data['dialogue']}:
            key = name.lower()
            profile = speakers[key]
            portrait_key = profile['portrait']
            portrait = portraits.get(portrait_key)
            if portrait is None:
                if manifest is None:
                    manifest = json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())
                filename = manifest['portraits'][portrait_key]['file']
                portrait = pygame.image.load(str(ROOT/'assets/portraits/eldenmere'/filename)).convert_alpha()
            self._dialogue_speakers[name] = profile
            self._dialogue_portraits[portrait_key] = portrait
        mist = pygame.Surface((240, 32), pygame.SRCALPHA)
        for inset in range(14):
            pygame.draw.ellipse(mist, (151, 172, 188, 1+inset),
                                (inset*5, inset, 240-inset*10, 32-inset*2))
        self._mist_texture = mist

    def reset(self):
        """Release transient staging without invoking a discarded callback."""
        self.active = False
        self.paused = False
        self.focused = True
        self.elapsed = 0.0
        self.finished_reason = None
        self._on_finish = None
        self._mouse_held = False

    @property
    def reduced_motion(self):
        return bool(getattr(self.game.audio, 'reduced_motion', False))

    @property
    def shot_record(self):
        return next((record for record in self.data['shots']
                     if record['start'] <= self.elapsed < record['end']),
                    self.data['shots'][-1])

    @property
    def shot(self):
        return self.shot_record['id']

    @property
    def camera_position(self):
        record = self.shot_record
        progress = ((self.elapsed-record['start']) /
                    (record['end']-record['start']))
        # Reduced Motion displays a clean static composition for each shot.
        fraction = 1.0 if self.reduced_motion else _smooth(progress)
        point = pygame.Vector2(record['from']).lerp(record['to'], fraction)
        if record.get('track_flare') and not self.reduced_motion and self.flare_position is not None:
            anchor = pygame.Vector2(record.get('flare_anchor', (.5, .5)))
            target = self.flare_position-pygame.Vector2(VIEW_SIZE).elementwise()*anchor
            blend = _smooth((self.elapsed-record['start'])/record.get('track_blend', 1.0))
            point = pygame.Vector2(record['from']).lerp(target, blend)
        bounds = self.data.get('camera_bounds', (0, 0, 480, 160))
        return pygame.Vector2(max(bounds[0], min(bounds[2], point.x)),
                              max(bounds[1], min(bounds[3], point.y)))

    @property
    def camera_zoom(self):
        if self.reduced_motion:
            return 1.0
        record = self.shot_record
        start, end = record.get('zoom', (1.0, 1.0))
        fraction = _smooth((self.elapsed-record['start'])/(record['end']-record['start']))
        return start+(end-start)*fraction

    @property
    def camera_settled(self):
        record = self.shot_record
        return (self.reduced_motion or (record['from'] == record['to']
                and not (record.get('track_flare') and self.flare_phase == 'flight')))

    def shot_complete(self, identifier):
        return any(record['id'] == identifier and self.elapsed >= record['end']
                   for record in self.data['shots'])

    def actor_position(self, actor):
        point = pygame.Vector2(next(record['position'] for record in self.data['actors']
                                    if record['id'] == actor))
        for record in self.data.get('position_tracks', {}).get(actor, ()):
            if self.elapsed < record['start']:
                break
            if self.elapsed >= record['end']:
                point = pygame.Vector2(record['to'])
                continue
            fraction = (self.elapsed-record['start'])/(record['end']-record['start'])
            if record.get('ease', 'linear') == 'smooth':
                fraction = _smooth(fraction)
            return pygame.Vector2(record['from']).lerp(record['to'], fraction)
        return point

    @property
    def lamp_stage(self):
        record = self.data.get('dynamic_props', {}).get('lamp')
        if record is None:
            return 0
        stage = 0
        for cue in record.get('stage_cues', ()):
            if self.elapsed >= cue['start']:
                stage = cue['stage']
        final = len(record['states'])-1
        stage = max(0, min(final, stage))
        gate = record.get('restored_after_shot')
        if stage == final and gate and not self.shot_complete(gate):
            stage = final-1
        return stage

    @property
    def cup_visible(self):
        return self._prop_visible('cup')

    @property
    def memorial_visible(self):
        return self._prop_visible('memorial')

    def _prop_visible(self, identifier):
        record = self.data.get('dynamic_props', {}).get(identifier)
        return bool(record and record.get('visible_from', 0) <= self.elapsed
                    < record.get('visible_until', self.duration+1))

    @property
    def flare_phase(self):
        record = self.data.get('flare')
        if record is None or self.elapsed < record.get('charge_start', record['launch']):
            return 'dormant'
        if self.elapsed < record['launch']:
            return 'charging'
        if self.elapsed < record['flight_end']:
            return 'flight'
        if self.elapsed < record['burst_end']:
            return 'burst'
        if self.elapsed < record.get('glimmer_until', self.duration+1):
            return 'glimmer'
        return 'dormant'

    @property
    def glimmer_visible(self):
        return self.flare_phase == 'glimmer'

    def _flight_point(self, time):
        record = self.data['flare']
        fraction = max(0.0, min(1.0, (time-record['launch'])/
                                  (record['flight_end']-record['launch'])))
        fraction = 1-(1-fraction)**2
        point = pygame.Vector2(record['origin']).lerp(record['apex'], fraction)
        point.x += math.sin(fraction*math.pi)*8
        return point

    @property
    def flare_position(self):
        phase = self.flare_phase
        if phase == 'dormant':
            return None
        record = self.data['flare']
        if phase == 'charging':
            prepared = pygame.Vector2(record.get('charge_origin', record['origin']))
            release = record.get('charge_release_start', record['launch'])
            duration = record['launch']-release
            fraction = (_smooth((self.elapsed-release)/duration) if duration > 0
                        else float(self.elapsed >= release))
            return prepared.lerp(record['origin'], fraction)
        if phase == 'flight' and not self.reduced_motion:
            return self._flight_point(self.elapsed)
        return pygame.Vector2(record['apex'])

    @property
    def dialogue(self):
        record = next((record for record in self.data['dialogue']
                       if record['start'] <= self.elapsed < record['end']), None)
        lamp = self.data.get('dynamic_props', {}).get('lamp', {})
        completion = lamp.get('restoration_dialogue_id', lamp.get('completion_dialogue_id'))
        if (record is not None and record.get('id') == completion
                and lamp.get('restored_after_shot')
                and not self.shot_complete(lamp['restored_after_shot'])):
            return None
        return record

    @property
    def framing_caption(self):
        record = self.data.get('framing_caption')
        return record if record and record['start'] <= self.elapsed < record['end'] else None

    def pose(self, actor):
        return next(cue['pose'] for cue in reversed(self.data['acting'][actor])
                    if cue['start'] <= self.elapsed)

    def _actor_frame(self, actor, frames, transitions):
        cues = self.data['acting'][actor]
        index = next(index for index in range(len(cues)-1, -1, -1)
                     if cues[index]['start'] <= self.elapsed)
        cue = cues[index]
        if index and not self.reduced_motion:
            previous = cues[index-1]['pose']
            local = self.elapsed-cue['start']
            for image, duration in transitions.get(previous+':'+cue['pose'], ()):
                if local < duration:
                    return image
                local -= duration
        loop = self._actor_loops.get(actor, {}).get(cue['pose'])
        # Locomotion remains legible when camera/ambient motion is reduced;
        # a held walking frame would slide the body across the floor.
        if loop and (not self.reduced_motion or cue['pose'].startswith('walk_')):
            local = (self.elapsed-cue['start']) % sum(duration for _, duration in loop)
            for image, duration in loop:
                if local < duration:
                    return image
                local -= duration
        return frames[cue['pose']]

    def start(self, on_finish=None):
        self._load()
        self.reset()
        self.active = True
        self.focused = bool(getattr(self.game, '_music_focused', True))
        self._on_finish = on_finish

    def _finish(self, reason):
        if not self.active:
            return
        callback = self._on_finish
        self.active = False
        self.paused = False
        self._mouse_held = False
        self.finished_reason = reason
        self._on_finish = None
        if callback is not None:
            callback()

    def skip(self):
        self._finish('skipped')

    def update(self, seconds):
        if (not self.active or self.paused or not self.focused
                or not getattr(self.game, '_music_focused', True)):
            return
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            return
        self.elapsed = min(self.duration, self.elapsed+seconds)
        if self.elapsed >= self.duration:
            self._finish('completed')

    def handle_event(self, event):
        if not self.active:
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self.focused = False
            self._mouse_held = False
        elif event.type == pygame.WINDOWFOCUSGAINED:
            self.focused = True
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if not getattr(event, 'repeat', False):
                self.paused = not self.paused
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse_held = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._mouse_held:
                return
            self._mouse_held = True
            point = self.game.to_canvas(event.pos)
            if point is not None and self.skip_rect.collidepoint(point):
                self.skip()

    def _draw_layer(self, canvas, record, image, camera):
        factor = record.get('parallax', 1.0)
        drift = 0 if self.reduced_motion or record['file'] != 'sky.png' else math.sin(self.elapsed*.035)*5
        x = max(0, min(image.get_width()-VIEW_SIZE[0], camera.x*factor+drift))
        # The original ground scene keeps its authored depth. Above it the
        # camera must genuinely move the architecture out of view, revealing
        # the additional sky plate rather than pinning scenery to the border.
        y = camera.y if camera.y < 0 else max(0, min(image.get_height()-VIEW_SIZE[1], camera.y*factor))
        if camera.y < 0:
            image = self._upper_edge_layers.get(record['file'], image)
        if record['file'] == 'sky.png' and camera.y < 0 and self._upper_sky is not None:
            image.set_alpha(round(255*max(0.0, 1+camera.y/180)))
            canvas.blit(image, (-round(x), -round(y)))
            image.set_alpha(255)
            return
        canvas.blit(image, (-round(x), -round(y)))

    def _draw_upper_sky(self, canvas, camera):
        if self._upper_sky is None:
            return
        record = self.data['upper_sky']
        point = pygame.Vector2(record.get('origin', (0, -800)))-camera
        canvas.blit(self._upper_sky, (round(point.x), round(point.y)))

    def _draw_prop(self, canvas, identifier, camera):
        if not self._prop_visible(identifier) or identifier not in self._prop_art:
            return
        record = self.data['dynamic_props'][identifier]
        image = self._prop_art[identifier]
        if identifier == 'lamp':
            image = image[self.lamp_stage]
        point = pygame.Vector2(record['position'])-camera-pygame.Vector2(record.get('anchor', (0, 0)))
        canvas.blit(image, (round(point.x), round(point.y)))

    def _lantern(self, canvas, camera):
        x, y = pygame.Vector2(self.data['lantern_position'])-camera
        pulse = 0 if self.reduced_motion else math.sin(self.elapsed*4.3)*2+math.sin(self.elapsed*7.1)
        lamp = self.data.get('dynamic_props', {}).get('lamp')
        stage = self.lamp_stage
        gain = (0.42, 0.55, 0.76, 1.4)[min(stage, 3)] if lamp else 1.0
        glow = pygame.Surface(VIEW_SIZE, pygame.SRCALPHA)
        for radius, opacity in ((48, 5), (35, 7), (24, 10), (12, 16)):
            pygame.draw.circle(glow, (248, 172, 68, max(0, min(255, round((opacity+pulse)*gain)))),
                               (round(x), round(y)), round(radius*min(1.2, gain)))
        canvas.blit(glow, (0, 0))
        lean = 0 if self.reduced_motion else round(math.sin(self.elapsed*5.6))
        pygame.draw.ellipse(canvas, '#e9a04d', (round(x)-2+lean, round(y)-4, 4, 6))
        pygame.draw.ellipse(canvas, '#f8dca0', (round(x)-1, round(y)-2, 2, 4))

    def _air(self, canvas, camera):
        if self.reduced_motion:
            return
        # Sparse motes in the lamp's pool of light; their visual clock pauses
        # with every other layer rather than drifting behind a paused actor.
        origin = pygame.Vector2(self.data['lantern_position'])-camera
        layer = pygame.Surface(VIEW_SIZE, pygame.SRCALPHA)
        for index in range(7):
            cycle = (self.elapsed*.045+index/7)%1
            x = origin.x-21+index*6+math.sin(self.elapsed*.35+index)*3
            y = origin.y+8-cycle*37
            opacity = round(50*math.sin(cycle*math.pi))
            pygame.draw.circle(layer, (244, 210, 157, opacity), (round(x), round(y)), 1)
        canvas.blit(layer, (0, 0))

    def _mist(self, canvas, camera):
        # Mist belongs to the distant valley plane, behind the sanctuary.
        # The authored architecture masks it naturally at the doorway/window.
        time = 0 if self.reduced_motion else self.elapsed
        for index in range(4):
            x = ((index*231+time*(.8+index*.12))%1120)-160-camera.x*.3
            y = 204+index*19-(camera.y if camera.y < 0 else camera.y*.3)
            canvas.blit(self._mist_texture, (round(x), round(y)))

    def _flare(self, canvas, camera):
        phase = self.flare_phase
        if phase == 'dormant':
            return
        record = self.data['flare']
        point = self.flare_position-camera
        layer = pygame.Surface(VIEW_SIZE, pygame.SRCALPHA)

        def glow(center, radius, opacity=150):
            center = (round(center.x), round(center.y))
            for scale, alpha, color in ((2.0, .12, (53, 127, 239)),
                                         (1.4, .25, (70, 164, 255)),
                                         (1.0, .75, (105, 206, 255)),
                                         (.48, 1.0, (224, 250, 255))):
                pygame.draw.circle(layer, (*color, round(opacity*alpha)), center,
                                   max(1, round(radius*scale)))

        if self.reduced_motion:
            # A static blue star conveys the signal without continuous camera
            # travel, radial flashes or moving particle trails.
            if phase != 'charging':
                glow(point, 4, 180)
                pygame.draw.line(layer, (197, 237, 255, 180),
                                 (round(point.x)-6, round(point.y)),
                                 (round(point.x)+6, round(point.y)))
                pygame.draw.line(layer, (197, 237, 255, 180),
                                 (round(point.x), round(point.y)-6),
                                 (round(point.x), round(point.y)+6))
        elif phase == 'charging':
            duration = record['launch']-record.get('charge_start', record['launch'])
            fraction = (self.elapsed-record.get('charge_start', record['launch']))/max(.001, duration)
            glow(point, 3+fraction*5, 140)
            for index in range(5):
                angle = self.elapsed*2.4+index*math.tau/5
                orbit = 15*(1-fraction)+5
                dot = point+pygame.Vector2(math.cos(angle)*orbit, math.sin(angle)*orbit)
                glow(dot, 1, 110)
        elif phase == 'flight':
            for index in range(15, 0, -1):
                time = self.elapsed-index*.035
                if time < record['launch']:
                    continue
                tail = self._flight_point(time)-camera
                glow(tail, max(1, 7-index*.35), round(150*(1-index/17)))
            glow(point, 8, 230)
        elif phase == 'burst':
            fraction = (self.elapsed-record['flight_end'])/(record['burst_end']-record['flight_end'])
            radius = 8+78*math.sin(min(1, fraction)*math.pi/2)
            alpha = round(220*(1-fraction)**.65)
            for index in range(24):
                angle = index*math.tau/24+(index%3)*.035
                reach = radius*(.76+(index*7%11)/45)
                direction = pygame.Vector2(math.cos(angle), math.sin(angle))
                end = point+direction*reach+pygame.Vector2(0, fraction*fraction*14)
                start = point+direction*max(0, reach-12*(1-fraction))
                pygame.draw.line(layer, (93, 188, 255, max(0, alpha)),
                                 (round(start.x), round(start.y)), (round(end.x), round(end.y)), 2)
                glow(end, 2, max(0, alpha))
                if index%3 == 0:
                    spark = end+pygame.Vector2(-direction.y, direction.x)*(3+fraction*5)
                    glow(spark, 1, max(0, alpha//2))
            glow(point, max(2, 9*(1-fraction)), max(100, alpha))
        else:
            pulse = .5+.5*math.sin(self.elapsed*2.2)
            glow(point, 2.6+pulse*.5, 150)
            span = 4+round(pulse*2)
            pygame.draw.line(layer, (194, 235, 255, 150),
                             (round(point.x)-span, round(point.y)),
                             (round(point.x)+span, round(point.y)))
            pygame.draw.line(layer, (194, 235, 255, 150),
                             (round(point.x), round(point.y)-span),
                             (round(point.x), round(point.y)+span))
        canvas.blit(layer, (0, 0))

    def _draw_actors(self, canvas, camera):
        for record, anchor, frames, transitions in sorted(self.actors,
                key=lambda actor: self.actor_position(actor[0]['id']).y):
            image = self._actor_frame(record['id'], frames, transitions)
            point = self.actor_position(record['id'])-camera
            # Whole authored bodies keep fixed physical proportions and contact.
            canvas.blit(image, (round(point.x-anchor[0]), round(point.y-anchor[1])))

    def _zoom(self, canvas, camera):
        zoom = self.camera_zoom
        if zoom <= 1:
            return
        focus = pygame.Vector2(self.shot_record.get('zoom_focus',
                                                   (camera.x+240, camera.y+160)))-camera
        size = (math.ceil(VIEW_SIZE[0]*zoom), math.ceil(VIEW_SIZE[1]*zoom))
        enlarged = pygame.transform.scale(canvas, size)
        canvas.blit(enlarged, (round(focus.x*(1-zoom)), round(focus.y*(1-zoom))))

    @property
    def fade_alpha(self):
        fade_in = 0 if self.reduced_motion else max(0.0, 1-self.elapsed/1.1)
        record = self.data.get('fade_out')
        if record is not None:
            fade_out = max(0.0, min(1.0, (self.elapsed-record['start'])/
                                   (record['end']-record['start'])))
        else:
            fade_out = 0 if self.reduced_motion else max(0.0, (self.elapsed-(self.duration-1.1))/1.1)
        return round(255*max(fade_in, fade_out))

    def _layout(self, painter):
        height = max(20, painter.font().get_linesize()+8)
        width = max(44, painter.font().size('Skip')[0]+18)
        self.skip_rect = pygame.Rect(470-width, 310-height, width, height)
        self.caption_lines = []
        self.caption_pages = []
        self.caption_page_index = 0
        self.caption_layout = None
        record = self.dialogue
        if record is None:
            self.caption_rect = pygame.Rect(22, self.skip_rect.top-8, 436, 0)
            return
        profile = self._dialogue_speakers[record['speaker']]
        font = painter.font()
        signature = (record['id'], record['text'], font.size(record['text']),
                     font.get_linesize(), painter.font('name', bold=True).get_linesize())
        cached = self._caption_cache.get(signature)
        if cached is None:
            wrapped = painter.wrap(record['text'], speech_bubble.TEXT_WIDTH)
            count = math.ceil(len(wrapped)/speech_bubble.MAX_LINES)
            lines_per_page, extra = divmod(len(wrapped), count)
            pages, offset = [], 0
            for index in range(count):
                end = offset+lines_per_page+(index < extra)
                pages.append(wrapped[offset:end])
                offset = end
            # Balance the pages so a short trailing line cannot become a
            # fleeting final page when the readability font is enlarged.
            # Allocate the existing line hold by text length. Every page gets
            # its reading time without shifting dialogue or acting cues.
            weights = [sum(len(line) for line in page) for page in pages]
            cached = pages, weights
            self._caption_cache[signature] = cached
        self.caption_pages, weights = cached
        progress = (self.elapsed-record['start'])/(record['end']-record['start'])
        remaining = max(0.0, progress)*sum(weights)
        for index, weight in enumerate(weights):
            self.caption_page_index = index
            if remaining < weight:
                break
            remaining -= weight
        self.caption_lines = self.caption_pages[self.caption_page_index]
        names, text_top, line_height, height = speech_bubble.measure_dialogue(
            painter, profile['name'], self.caption_pages[0], reserve_hint=False)
        # Keep one steady panel size throughout an automatically paged passage.
        x = (VIEW_SIZE[0]-speech_bubble.PANEL_WIDTH)//2
        candidates = [pygame.Rect(x, self.skip_rect.top-9-math.ceil(height),
                                  speech_bubble.PANEL_WIDTH, math.ceil(height)),
                      pygame.Rect(x, 6, speech_bubble.PANEL_WIDTH, math.ceil(height))]
        protected = []
        for actor, anchor, frames, transitions in self.actors:
            image = self._actor_frame(actor['id'], frames, transitions)
            point = self.actor_position(actor['id'])-self.camera_position
            rect = image.get_bounding_rect().move(round(point.x-anchor[0]),
                                                   round(point.y-anchor[1]))
            if pygame.Rect((0, 0), VIEW_SIZE).colliderect(rect):
                protected.append(rect.inflate(8, 8))
        self.caption_rect = min(candidates, key=lambda panel: sum(
            panel.clip(rect).width*panel.clip(rect).height for rect in protected))
        panel = self.caption_rect
        portrait = pygame.Rect(panel.x+speech_bubble.PADDING, panel.y+12,
                               speech_bubble.PORTRAIT_SIZE, speech_bubble.PORTRAIT_SIZE)
        self.caption_layout = speech_bubble.BubbleLayout(
            panel, portrait, (panel.x+speech_bubble.TEXT_OFFSET, panel.y+text_top),
            (), panel.midbottom, None, False, False, profile['portrait'],
            name_lines=names, line_height=line_height)

    def _draw_captions(self, painter):
        layout = self.caption_layout
        if layout is None:
            return
        speech_bubble.draw_dialogue_frame(
            painter, layout, self._dialogue_portraits[layout.portrait_key])
        speech_bubble.draw_dialogue_prose(painter, layout, self.caption_lines)

    def draw(self, canvas, ui_surface):
        self._load()
        canvas.fill('#111e2a')
        camera = self.camera_position
        self._draw_upper_sky(canvas, camera)
        for record, image in self.layers:
            if not record.get('foreground', False):
                self._draw_layer(canvas, record, image, camera)
                if record['file'] == 'valley.png':
                    self._mist(canvas, camera)
        self._draw_prop(canvas, 'lamp', camera)
        self._draw_prop(canvas, 'cup', camera)
        self._lantern(canvas, camera)
        self._air(canvas, camera)
        self._draw_actors(canvas, camera)
        self._flare(canvas, camera)
        for record, image in self.layers:
            if record.get('foreground', False):
                self._draw_layer(canvas, record, image, camera)
        # The memorial occupies a nearer depth plane than both characters.
        self._draw_prop(canvas, 'memorial', camera)
        self._zoom(canvas, camera)
        pygame.transform.scale(canvas, ui_surface.get_size(), ui_surface)
        painter = self.game.ui.painter(ui_surface)
        self._layout(painter)
        self._draw_captions(painter)
        framing = self.framing_caption
        if framing is not None:
            painter.text(framing['text'], (240, 29), color=IVORY, anchor='midtop')
        if self.fade_alpha:
            painter.veil(self.fade_alpha)
        painter.button(self.skip_rect, 'Skip')
        painter.text('Esc · Resume' if self.paused else 'Esc · Pause',
                     (12, self.skip_rect.centery), role='small', color=MUTED,
                     anchor='midleft')
        if self.paused or not self.focused or not getattr(self.game, '_music_focused', True):
            label = 'Paused'
            width = max(102, painter.font('label', bold=True).size(label)[0]+28)
            y = 15 if self.caption_rect.height == 0 or self.caption_rect.top > 100 else 273-self.skip_rect.height
            rect = pygame.Rect(round(240-width/2), y, width, 27)
            painter.rect('#172831', rect)
            painter.rect(BRASS, rect, 1)
            painter.text(label, rect.center, role='label', bold=True, anchor='center')
