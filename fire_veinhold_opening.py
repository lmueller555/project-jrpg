"""Native-detail, appendable Fire Veinhold prologue presentation.

The authored shot list drives both the complete Gallery film and individual
shot reviews. This presentation grants no story progress and deliberately
does not replace New Game while its later shots/handoff are unimplemented.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame

from cinematic_smoke import CinematicSmoke
from cinematic_facility import CinematicFacility
from cinematic_perspective import CinematicPerspective
from cinematic_bridge_run import CinematicBridgeRun
from prologue_flight_audio import PrologueFlightAudio, wing_phase_at
from prologue_alert_audio import PrologueAlertAudio
from ui_style import BRASS, MUTED

ROOT = Path(__file__).resolve().parent
SCENE = ROOT/'assets/story/fire_veinhold_opening/scene.json'
RENDER_SIZE = (960, 640)
LOGICAL_SIZE = (480, 320)


def _read_scene(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if (not isinstance(data, dict)
            or data.get('version') != 1 or data.get('id') != 'fire_veinhold_opening'
            or tuple(data.get('render_size', ())) != RENDER_SIZE
            or tuple(data.get('logical_size', ())) != LOGICAL_SIZE
            or not isinstance(data.get('shots'), list) or not data['shots']):
        raise ValueError('Invalid Fire Veinhold prologue scene')
    identifiers, gallery_ids = set(), set()
    for shot in data['shots']:
        if (not isinstance(shot, dict)
                or any(not isinstance(shot.get(key), str) or not shot[key]
                       for key in ('id', 'gallery_id', 'name', 'description'))
                or shot.get('type') not in ('eagle_ascent', 'perspective_sequence', 'bridge_running')
                or type(shot.get('duration')) not in (int, float)
                or not math.isfinite(shot['duration']) or shot['duration'] <= 0
                or shot['id'] in identifiers or shot['gallery_id'] in gallery_ids):
            raise ValueError('Invalid or duplicate implemented prologue shot')
        thumbnail = shot.get('thumbnail_time', shot['duration']*.6)
        if (type(thumbnail) not in (int, float) or not math.isfinite(thumbnail)
                or not 0 <= thumbnail <= shot['duration']):
            raise ValueError('Invalid prologue thumbnail time')
        if shot['type'] == 'perspective_sequence':
            if any(not isinstance(shot.get(key), str) or not shot[key]
                   for key in ('sequence', 'segment')):
                raise ValueError('Incomplete perspective shot metadata')
            identifiers.add(shot['id']); gallery_ids.add(shot['gallery_id'])
            continue
        if shot['type'] == 'bridge_running':
            if not isinstance(shot.get('performance'), str) or not shot['performance']:
                raise ValueError('Incomplete bridge-running shot metadata')
            identifiers.add(shot['id']); gallery_ids.add(shot['gallery_id'])
            continue
        if any(not isinstance(shot.get(key), str) or not shot[key]
               for key in ('environment', 'eagle')):
            raise ValueError('Incomplete eagle shot metadata')
        ascent = shot.get('ascent_duration', shot['duration']*.6)
        if type(ascent) not in (int, float) or not math.isfinite(ascent):
            raise ValueError('Invalid ascent timing')
        vista = shot.get('vista_duration', shot['duration']-ascent)
        if (any(type(value) not in (int, float) or not math.isfinite(value)
                or value <= 0 for value in (ascent, vista))
                or abs(ascent+vista-shot['duration']) > 1e-9):
            raise ValueError('Invalid ascent and vista timing')
        identifiers.add(shot['id']); gallery_ids.add(shot['gallery_id'])
    return data


def available_shots(scene_path=SCENE):
    """Return only implemented clips, in their authored playback order."""
    return [dict(shot) for shot in _read_scene(scene_path)['shots']]


def sequence_duration(scene_path=SCENE):
    return sum(float(shot['duration']) for shot in available_shots(scene_path))


def _smooth(value):
    value = max(0., min(1., value))
    return value*value*(3.-2.*value)


class FireVeinholdOpening:
    """A disposable cinematic with a continuous clock and full-detail output."""
    render_size = RENDER_SIZE

    def __init__(self, game, shot_id=None, *, scene_path=SCENE):
        self.game = game
        self.scene_path = Path(scene_path).resolve()
        self.data = _read_scene(self.scene_path)
        self.shots = [shot for shot in self.data['shots']
                      if shot_id is None or shot['id'] == shot_id]
        if not self.shots:
            raise ValueError('Unknown implemented prologue shot: '+str(shot_id))
        # A standalone Gallery clip keeps its authored position in the reel.
        # Alarm/smoke clocks therefore agree with complete-film playback.
        self.global_offset = 0.
        if shot_id is not None:
            for shot in self.data['shots']:
                if shot['id'] == shot_id:
                    break
                self.global_offset += float(shot['duration'])
        self.duration = sum(float(shot['duration']) for shot in self.shots)
        self._boundaries = []
        boundary = 0.
        for shot in self.shots:
            boundary += float(shot['duration'])
            self._boundaries.append(boundary)
        self._assets = {}
        self._perspectives = {}
        self._running = {}
        self.flight_audio = PrologueFlightAudio(game)
        self.alert_audio = PrologueAlertAudio(game)
        self.skip_rect = pygame.Rect(426, 292, 44, 20)
        self.reset()

    def _path(self, filename, base=None):
        """References may be scene-local or explicit repo-relative exports."""
        if not isinstance(filename, str) or Path(filename).is_absolute():
            raise ValueError('Prologue assets must be relative paths')
        base = self.scene_path.parent if base is None else base
        prefix = 'assets/story/fire_veinhold_opening/'
        if filename.startswith(prefix):
            path = (self.scene_path.parent/filename[len(prefix):]).resolve()
        else:
            path = (base/filename).resolve()
        if not path.is_relative_to(self.scene_path.parent):
            raise ValueError('Prologue asset leaves its scene directory')
        return path

    def _load(self):
        if self._assets:
            return
        try:
            assets = self._load_assets()
        except (KeyError, TypeError, AttributeError, IndexError) as error:
            self._close_perspectives()
            self._perspectives.clear()
            self._close_running()
            self._running.clear()
            raise ValueError('Incomplete prologue artwork metadata') from error
        except (OSError, ValueError, pygame.error):
            self._close_perspectives()
            self._perspectives.clear()
            self._close_running()
            self._running.clear()
            raise
        # A failed later clip must not leave a partially playable cached reel.
        self._assets = assets

    def _load_assets(self):
        assets = {}
        for shot in self.shots:
            if shot['type'] == 'bridge_running':
                performance_path = self._path(shot['performance'])
                if performance_path not in self._running:
                    self._running[performance_path] = CinematicBridgeRun(
                        performance_path, allowed_root=self.scene_path.parent)
                performance = self._running[performance_path]
                performance.validate_duration(shot['duration'])
                assets[shot['id']] = {'running':performance}
                continue
            if shot['type'] == 'perspective_sequence':
                sequence_path = self._path(shot['sequence'])
                if sequence_path not in self._perspectives:
                    self._perspectives[sequence_path] = CinematicPerspective(
                        sequence_path, allowed_root=self.scene_path.parent)
                perspective = self._perspectives[sequence_path]
                perspective.validate_segment(shot['segment'], shot['duration'])
                assets[shot['id']] = {'perspective':perspective, 'segment':shot['segment']}
                continue
            environment_path = self._path(shot['environment'])
            environment = json.loads(environment_path.read_text(encoding='utf-8'))
            if environment.get('version') != 1 or environment.get('density') != 2:
                raise ValueError('Prologue scenery requires native density two')
            if set(environment['layers']) != {'panorama'}:
                raise ValueError('Flight requires one continuous mountain panorama')
            layers = {}
            for name in environment['layers']:
                record = environment['layers'][name]
                image = pygame.image.load(str(self._path(record['image'], environment_path.parent)))
                image = image.convert_alpha()
                # Registration padding is metadata, not visible scenery extent.
                bounds = image.get_bounding_rect(min_alpha=1)
                if bounds.width == 0 or bounds.height == 0:
                    raise ValueError('Empty prologue scenery: '+name)
                layers[name] = image
            eagle_path = self._path(shot['eagle'])
            eagle = json.loads(eagle_path.read_text(encoding='utf-8'))
            if (eagle.get('version') != 1 or eagle.get('density') != 2
                    or tuple(eagle.get('canvas', ())) != (256, 256)):
                raise ValueError('Invalid complete eagle flight canvas')
            anchor = eagle.get('anchor')
            if (not isinstance(anchor, list) or len(anchor) != 2
                    or any(type(value) is not int or not 0 <= value < 256 for value in anchor)):
                raise ValueError('Invalid eagle chest registration')
            sequences = {}
            for name in ('flap', 'bank', 'glide'):
                sequence = eagle['sequences'][name]
                if type(sequence['loop']) is not bool:
                    raise ValueError('Invalid eagle loop flag')
                frames = []
                for record in sequence['frames']:
                    duration = record['duration_ms']
                    if (type(duration) not in (int, float)
                            or not math.isfinite(duration) or duration <= 0):
                        raise ValueError('Invalid eagle frame duration')
                    image = pygame.image.load(str(self._path(record['file'], eagle_path.parent))).convert_alpha()
                    if image.get_size() != (256, 256):
                        raise ValueError('Eagle poses must retain their registered canvas')
                    frames.append((image, duration/1000.))
                if not frames:
                    raise ValueError('Empty eagle flight sequence')
                sequences[name] = {'loop':bool(sequence['loop']), 'frames':frames,
                                   'duration':sum(frame[1] for frame in frames)}
            timing = eagle['timing']
            if (not isinstance(timing, dict)
                    or any(type(timing[key]) not in (int, float)
                           or not math.isfinite(timing[key]) for key in
                           ('period_ms', 'first_phase_ms', 'second_phase_ms', 'downstroke_phase'))
                    or timing['period_ms'] <= 0
                    or not 0 <= timing['first_phase_ms'] < timing['period_ms']
                    or not 0 <= timing['second_phase_ms'] < timing['period_ms']
                    or not 0 <= timing['downstroke_phase'] < 1
                    or abs(timing['period_ms']/1000.-sequences['flap']['duration']) > 1e-9):
                raise ValueError('Invalid eagle phase timing')
            framing = environment.get('framing', {})
            if not isinstance(framing, dict):
                raise ValueError('Invalid panorama framing')
            for key in ('ascent_start_y', 'vista_y'):
                value = framing.get(key, 0.)
                if (type(value) not in (int, float) or not math.isfinite(value)
                        or not 0 <= value <= layers['panorama'].get_height()):
                    raise ValueError('Invalid panorama source window')
            smoke_record = environment['smoke']
            plume_frames = []
            for frame_record in smoke_record['frames']:
                image = pygame.image.load(str(self._path(frame_record['file'], environment_path.parent))).convert_alpha()
                plume_frames.append((image, frame_record['duration_ms']/1000.))
            smoke = CinematicSmoke(plume_frames, smoke_record['anchor'], smoke_record['emitters'], layers['panorama'].get_size())
            facility = CinematicFacility(environment['facility'], layers['panorama'].get_size())
            layers['panorama'] = facility.inactive_background(layers['panorama'])
            assets[shot['id']] = {'layers':layers, 'eagle':sequences, 'smoke':smoke, 'facility':facility,
                                 'anchor':anchor, 'timing':timing,
                                 'framing':framing}
        return assets

    @property
    def reduced_motion(self):
        return bool(getattr(getattr(self.game, 'audio', None), 'reduced_motion', False))

    def _locate(self, seconds):
        at = max(0., min(self.duration, seconds))
        start = 0.
        for index, shot in enumerate(self.shots):
            end = start+shot['duration']
            if at < end or index == len(self.shots)-1:
                return shot, at-start, start
            start = end

    def state_at(self, seconds):
        """Deterministic shot-local staging, independent of update frame rate.

        Camera units describe the authored flight path, not world tiles.
        One continuous panorama supplies both the summit and offshore view.
        """
        self._load()
        shot, local, selected_start = self._locate(float(seconds))
        global_time = self.global_offset+max(0., min(self.duration, float(seconds)))
        # Both a standalone clip and the complete reel derive local staging
        # from their shared global clock. Decimal seeks such as 39.4 therefore
        # cannot choose different camera offsets through float cancellation.
        local = max(0., min(float(shot['duration']),
                           global_time-(self.global_offset+selected_start)))
        if shot['type'] == 'bridge_running':
            running = self._assets[shot['id']]['running'].samples(local, self.reduced_motion)
            return {**running, 'shot_id':shot['id'], 'global_time':global_time,
                    'alarm':{'active':global_time >= 30., 'elapsed':max(0., global_time-30.)}}
        if shot['type'] == 'perspective_sequence':
            art = self._assets[shot['id']]
            perspective = art['perspective'].samples(art['segment'], local, self.reduced_motion)
            return {'shot_id':shot['id'], 'local_time':local,
                    'global_time':global_time, 'phase':art['segment'],
                    'camera':perspective.get('camera', {}),
                    'perspective':perspective,
                    'alarm':{'active':global_time >= 30.,
                             'elapsed':max(0., global_time-30.)}}
        # Staging follows authored phase lengths; wing cadence uses real time.
        ascent = shot.get('ascent_duration', shot['duration']*.6)
        climb = min(1., local/ascent)
        vista = max(0., (local-ascent)/(shot['duration']-ascent))
        u = local/shot['duration']
        sway = .3 if self.reduced_motion else 1.
        x = 7.*math.sin(math.pi*u)*sway
        position = [x, 28.*local+.8*local*local,
                    145.+150.*_smooth(climb)]
        velocity = [7.*math.pi*math.cos(math.pi*u)*sway/shot['duration'],
                    28.+1.6*local,
                    150.*6.*climb*(1.-climb)/ascent if local < ascent else 0.]
        timing = self._assets[shot['id']]['timing']
        period = timing['period_ms']/1000.
        if local < 2.:
            sequence, clock = 'flap', local+timing['first_phase_ms']/1000.
        elif 5. <= local < 13.25:
            sequence, clock = 'flap', local-5.+timing['second_phase_ms']/1000.
        elif local < 5.:
            sequence, clock = 'bank', local-2.
        else:
            sequence, clock = 'glide', local-13.25
        phase = wing_phase_at(local)
        animation = self._assets[shot['id']]['eagle'][sequence]
        if animation['loop']:
            frame_clock = clock % animation['duration']
        else:
            # A complete gentle bank-and-recovery arc spans the curved pass.
            frame_clock = min(animation['duration']-1e-9, clock/3.*animation['duration'])
        index = 0
        for index, (_, duration) in enumerate(animation['frames']):
            if frame_clock < duration:
                break
            frame_clock -= duration
        bird_x = 480.+20.*math.sin(math.pi*climb)*sway
        # Release the chase at the crest. The eagle glides down beneath the
        # continuing camera, clearing the frame without fading or shrinking.
        exit_seconds = max(0., local-ascent)
        bird_y = 410.+40.*_smooth(climb)+85.*exit_seconds*exit_seconds
        bird_y += 1.5*math.sin(local*math.tau/period)*sway
        # A single tall painting supplies approach AND offshore vista. Panning
        # its source window over the ridge preserves every terrain relationship.
        panorama = self._assets[shot['id']]['layers']['panorama']
        zoom = 1.05-.05*_smooth(climb)+.035*vista
        factor = max(960/panorama.get_width(), 640/panorama.get_height())*zoom
        framing = self._assets[shot['id']]['framing']
        source_y = (framing.get('ascent_start_y', 650.)*(1.-_smooth(climb))
                    +framing.get('vista_y', 0.)*_smooth(climb))
        layers = {'panorama':{'offset':[-x, (panorama.get_height()*factor-640)/2-source_y*factor],
                              'scale':zoom}}
        return {'shot_id':shot['id'], 'local_time':local, 'global_time':global_time,
                'camera':{'position':position, 'velocity':velocity, 'progress':u},
                'eagle':{'position':[bird_x, bird_y], 'sequence':sequence,
                         'frame':index, 'wing_phase':phase,
                         'anchor':list(self._assets[shot['id']]['anchor']),
                         'scale':1.,
                         'visible':bird_y-self._assets[shot['id']]['anchor'][1] < RENDER_SIZE[1]},
                'phase':'ascent' if local < ascent else 'cinder_vista',
                'crest_time':ascent, 'vista_elapsed':max(0., local-ascent),
                'smoke':self._assets[shot['id']]['smoke'].samples(local, self.reduced_motion),
                'facility':self._assets[shot['id']]['facility'].samples(local, self.reduced_motion, alarm_active=False),
                'layers':layers}

    @property
    def handoff_state(self):
        state = self.state_at(self.duration)
        state['audio'] = {'wind_playhead':self.global_offset+self.duration, 'wind_continues':True}
        return state

    def _close_perspectives(self):
        for perspective in self._perspectives.values():
            perspective.close()

    def _close_running(self):
        for running in self._running.values():
            running.close()

    def reset(self):
        if getattr(self, 'flight_audio', None) is not None:
            self.flight_audio.reset()
        if getattr(self, 'alert_audio', None) is not None:
            self.alert_audio.reset()
        self._close_perspectives()
        self._close_running()
        self.active = False
        self.paused = False
        self.focused = True
        self.elapsed = 0.
        self.finished_reason = None
        self._on_finish = None
        self._mouse_held = False

    def start(self, on_finish=None):
        self._load()
        self.reset()
        try:
            self._preload_at(0., blocking=True)
        except (ValueError, OSError, pygame.error):
            self._close_perspectives()
            self._close_running()
            raise
        self.active = True
        self.focused = bool(getattr(self.game, '_music_focused', True))
        self._on_finish = on_finish
        self.flight_audio.start(self.global_offset)
        self.alert_audio.start(self.global_offset)
        if not self.focused:
            self.flight_audio.pause()
            self.alert_audio.pause()

    def _finish(self, reason):
        if not self.active:
            return
        callback = self._on_finish
        self.active = False
        self.paused = False
        self._mouse_held = False
        self.finished_reason = reason
        self._on_finish = None
        self.flight_audio.stop()
        self.alert_audio.stop()
        self._close_perspectives()
        self._close_running()
        if callback is not None:
            callback()

    def skip(self):
        self._finish('skipped')

    def update(self, seconds):
        if not self.active:
            return
        playing = (not self.paused and self.focused
                   and getattr(self.game, '_music_focused', True))
        if not playing:
            self.flight_audio.pause()
            self.alert_audio.pause()
            return
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            return
        previous = self.elapsed
        self.elapsed = min(self.duration, previous+seconds)
        for boundary in self._boundaries:
            if abs(boundary-self.elapsed) <= 1e-9:
                self.elapsed = boundary
                break
        before = self.state_at(previous)
        after = self.state_at(self.elapsed)
        if before['phase'] != 'bridge_running' and after['phase'] == 'bridge_running':
            # The side-on performance has its own small source-frame cache.
            # Release the completed orbit's reservations at this editorial cut.
            self._close_perspectives()
        if before['shot_id'] == after['shot_id'] and 'eagle' in after:
            self.flight_audio.update(before['global_time'], after['global_time'],
                wing_phase=(before['eagle']['wing_phase'], after['eagle']['wing_phase']),
                mode=after['eagle']['sequence'])
        else:
            # Continue the wind without rearming flight cues or restarting the
            # warning siren at orbit/hold/rush/reveal joins.
            self.flight_audio.update(before['global_time'], after['global_time'], mode='glide')
        if self.elapsed >= self.duration:
            self._finish('completed')
            return
        self.alert_audio.update(before['global_time'], after['global_time'])
        self._preload_at(self.elapsed)

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
            if not self._mouse_held:
                self._mouse_held = True
                point = self.game.to_canvas(event.pos)
                if point is not None and self.skip_rect.collidepoint(point):
                    self.skip()
        if not self.active or self.paused or not self.focused or not getattr(self.game, '_music_focused', True):
            self.flight_audio.pause()
            self.alert_audio.pause()
        else:
            self.flight_audio.resume()
            self.alert_audio.resume()

    def _preload_at(self, seconds, *, blocking=False):
        """Warm the active clip and the next clip before its first picture."""
        shot, local, start = self._locate(seconds)
        art = self._assets[shot['id']]
        if 'running' in art:
            art['running'].preload(local, reduced_motion=self.reduced_motion,
                                   blocking=blocking)
        if 'perspective' in art:
            art['perspective'].preload(art['segment'], local,
                                      reduced_motion=self.reduced_motion,
                                      blocking=blocking,
                                      alarm_active=self.global_offset+seconds >= 30.)
        # Start looking ahead during the end of the current shot. The shared
        # cache remains bounded even when two segments share the window.
        if shot['duration']-local <= .5:
            index = self.shots.index(shot)+1
            if index < len(self.shots):
                upcoming = self.shots[index]
                next_art = self._assets[upcoming['id']]
                if 'running' in next_art:
                    next_art['running'].preload(0., reduced_motion=self.reduced_motion)
                if 'perspective' in next_art:
                    next_art['perspective'].preload(next_art['segment'], 0.,
                        reduced_motion=self.reduced_motion,
                        max_slots=8 if 'perspective' in art else 16,
                        priority='upcoming',
                        alarm_active=self.global_offset+start+shot['duration'] >= 30.)

    def _panorama_projection(self, image, record):
        scale = max(RENDER_SIZE[0]/image.get_width(), RENDER_SIZE[1]/image.get_height())*record['scale']
        size = (round(image.get_width()*scale), round(image.get_height()*scale))
        ox, oy = record['offset']
        x = (960-size[0])/2.+ox
        y = (640-size[1])/2.+oy
        # Ground cards continue below frame. Their opaque source bottom must
        # never slide into view as a horizontal cut across another mountain.
        y = min(0, max(640-size[1], y))
        x = min(0, max(960-size[0], x))
        return scale, (round(x), round(y)), size

    def _terrain(self, target, image, record):
        _, origin, size = self._panorama_projection(image, record)
        target.blit(pygame.transform.scale(image, size), origin)

    @staticmethod
    def _bridge_motion(target, seconds):
        """Short camera-flight blur; leave both authored join poses sharp."""
        if not 0. < seconds < .88:
            return
        strength = math.sin(math.pi*seconds/.88)**1.6
        focus = (480, 285)
        # Accumulate the soft radial samples at half resolution, then blend
        # once over the untouched native frame. Native detail and sharp join
        # poses survive without three full-size alpha composites per tick.
        original = pygame.transform.scale(target, (480, 320))
        blur = original.copy()
        for step in (1, 2):
            factor = 1.+strength*.021*step
            size = (round(480*factor), round(320*factor))
            sample = pygame.transform.scale(original, size)
            sample.set_alpha(128)
            blur.blit(sample, (round(focus[0]*.5*(1-factor)),
                               round(focus[1]*.5*(1-factor))))
        overlay = pygame.transform.scale(blur, RENDER_SIZE)
        overlay.set_alpha(round(60*strength))
        target.blit(overlay, (0, 0))
        # Black contributes nothing to this additive, opaque line layer.
        lines = pygame.Surface(RENDER_SIZE).convert()
        for index in range(34):
            angle = index*2.399963
            radius = 295+((index*73)%190)
            advance = (seconds*1250+index*91)%170
            inner = radius+advance
            outer = inner+(45+index%5*14)*strength
            a = (round(focus[0]+math.cos(angle)*inner), round(focus[1]+math.sin(angle)*inner*.72))
            b = (round(focus[0]+math.cos(angle)*outer), round(focus[1]+math.sin(angle)*outer*.72))
            gain = (45+index%4*8)*strength/255.
            pygame.draw.line(lines, tuple(round(channel*gain) for channel in (161, 191, 225)), a, b)
        target.blit(lines, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def render_frame(self, time=None):
        """Render from source detail, never through the 480×320 world canvas."""
        state = self.state_at(self.elapsed if time is None else time)
        art = self._assets[state['shot_id']]
        target = pygame.Surface(RENDER_SIZE).convert()
        if 'running' in art:
            art['running'].draw(target, state)
            return target
        if 'perspective' in art:
            alarm = state['alarm']
            art['perspective'].draw(target, state['perspective'],
                                    alarm_active=alarm['active'], alarm_elapsed=alarm['elapsed'])
            if state['phase'] == 'rush' and not self.reduced_motion:
                self._bridge_motion(target, state['local_time'])
            return target
        self._terrain(target, art['layers']['panorama'], state['layers']['panorama'])
        scale, origin, _ = self._panorama_projection(art['layers']['panorama'], state['layers']['panorama'])
        art['smoke'].draw(target, state['smoke'], scale, origin)
        art['facility'].draw(target, state['facility'], scale, origin)
        # Complete eagle frames stay at one chase distance. Wing extent never
        # drives body scale or registration, including during its bank.
        eagle = state['eagle']
        image = art['eagle'][eagle['sequence']]['frames'][eagle['frame']][0]
        image = image.copy()
        image.fill((145, 175, 220, 255), special_flags=pygame.BLEND_RGBA_MULT)
        scale = eagle['scale']
        if scale != 1.:
            image = pygame.transform.scale(image, (round(256*scale), round(256*scale)))
        if eagle['visible']:
            target.blit(image, (round(eagle['position'][0]-eagle['anchor'][0]*scale),
                                round(eagle['position'][1]-eagle['anchor'][1]*scale)))
        return target

    def draw(self, canvas, ui_surface):
        frame = self.render_frame()
        # Logical canvas exists for legacy debug/capture consumers only. The
        # displayed image is sampled directly from the detailed source frame.
        pygame.transform.scale(frame, LOGICAL_SIZE, canvas)
        pygame.transform.scale(frame, ui_surface.get_size(), ui_surface)
        painter = self.game.ui.painter(ui_surface)
        height = max(20, painter.font().get_linesize()+8)
        width = max(44, painter.font().size('Skip')[0]+18)
        self.skip_rect = pygame.Rect(470-width, 310-height, width, height)
        painter.button(self.skip_rect, 'Skip')
        key = 'P' if getattr(self.game, '_is_gallery_preview', False) else 'Esc'
        painter.text(f'{key} · Resume' if self.paused else f'{key} · Pause',
                     (12, self.skip_rect.centery), role='small', color=MUTED, anchor='midleft')
        if self.paused or not self.focused or not getattr(self.game, '_music_focused', True):
            rect = pygame.Rect(189, 15, 102, 27)
            painter.rect('#172831', rect)
            painter.rect(BRASS, rect, 1)
            painter.text('Paused', rect.center, role='label', bold=True, anchor='center')
