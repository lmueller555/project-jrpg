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

from prologue_flight_audio import PrologueFlightAudio
from ui_style import BRASS, MUTED

ROOT = Path(__file__).resolve().parent
SCENE = ROOT/'assets/story/fire_veinhold_opening/scene.json'
RENDER_SIZE = (960, 640)
LOGICAL_SIZE = (480, 320)
LAYER_NAMES = ('sky', 'distant', 'mid', 'foreground_a', 'foreground_b', 'crest')


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
                       for key in ('id', 'gallery_id', 'name', 'description', 'environment', 'eagle'))
                or shot.get('type') != 'eagle_ascent'
                or type(shot.get('duration')) not in (int, float)
                or not math.isfinite(shot['duration']) or shot['duration'] <= 0
                or shot['id'] in identifiers or shot['gallery_id'] in gallery_ids):
            raise ValueError('Invalid or duplicate implemented prologue shot')
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
        self.duration = sum(float(shot['duration']) for shot in self.shots)
        self._assets = {}
        self.flight_audio = PrologueFlightAudio(game)
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
            raise ValueError('Incomplete prologue artwork metadata') from error
        # A failed later clip must not leave a partially playable cached reel.
        self._assets = assets

    def _load_assets(self):
        assets = {}
        for shot in self.shots:
            environment_path = self._path(shot['environment'])
            environment = json.loads(environment_path.read_text(encoding='utf-8'))
            if environment.get('version') != 1 or environment.get('density') != 2:
                raise ValueError('Prologue scenery requires native density two')
            layers = {}
            for name in LAYER_NAMES:
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
            assets[shot['id']] = {'layers':layers, 'eagle':sequences,
                                 'anchor':anchor, 'timing':timing}
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

        Camera units describe the authored flight path. Terrain parallax maps
        that path into this shot's 2.5D composition; they are not world tiles.
        """
        self._load()
        shot, local, _ = self._locate(float(seconds))
        t = local*10./shot['duration']
        u = t/10.
        sway = .3 if self.reduced_motion else 1.
        x = 10.*math.sin(math.pi*u)*sway
        position = [x, 180.*u+20.*u*u, 110.+55.*u+10.*u*u]
        velocity = [10.*math.pi*math.cos(math.pi*u)*sway/shot['duration'],
                    (180.+40.*u)/shot['duration'], (55.+20.*u)/shot['duration']]
        timing = self._assets[shot['id']]['timing']
        period = timing['period_ms']/1000.
        if t < 2.:
            sequence, clock = 'flap', t+timing['first_phase_ms']/1000.
            phase = clock/period
        elif 5. <= t < 8.:
            sequence, clock = 'flap', t-5.+timing['second_phase_ms']/1000.
            phase = 4.+clock/period
        elif t < 5.:
            sequence, clock = 'bank', t-2.
            phase = 3.+timing['second_phase_ms']/1000./period+(t-2.)/3.
        else:
            sequence, clock = 'glide', t-8.
            phase = 8.+timing['second_phase_ms']/1000./period+(t-8.)/period
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
        bird_x = 480.+28.*math.sin(math.pi*u)*sway
        bird_y = 378.-25.*u+1.5*math.sin(t*math.tau/period)*sway
        # The horizon falls through frame as we gain height. Near rock faces
        # peel away much faster than the hazy range on the other side.
        layers = {
            'sky':{'offset':[-x*.15, -20.+10.*u], 'scale':1.08},
            'distant':{'offset':[-x*.8, 5.+45.*u], 'scale':1.02+.025*u},
            'mid':{'offset':[-x*2., -35.+420.*u], 'scale':1.20+.18*u},
            'foreground_a':{'offset':[-100.-580.*u, 10.+470.*u], 'scale':1.25+.55*u},
            'foreground_b':{'offset':[140.+720.*u, 130.+640.*u], 'scale':1.40+.75*u},
            'crest':{'offset':[-x*1.5, -200.+900.*u*u], 'scale':1.05+.15*u},
        }
        return {'shot_id':shot['id'], 'local_time':local,
                'camera':{'position':position, 'velocity':velocity, 'progress':u},
                'eagle':{'position':[bird_x, bird_y], 'sequence':sequence,
                         'frame':index, 'wing_phase':phase,
                         'anchor':list(self._assets[shot['id']]['anchor'])},
                'layers':layers}

    @property
    def handoff_state(self):
        state = self.state_at(self.duration)
        state['audio'] = {'wind_playhead':self.duration, 'wind_continues':True}
        return state

    def reset(self):
        if getattr(self, 'flight_audio', None) is not None:
            self.flight_audio.reset()
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
        self.active = True
        self.focused = bool(getattr(self.game, '_music_focused', True))
        self._on_finish = on_finish
        self.flight_audio.start()
        if not self.focused:
            self.flight_audio.pause()

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
            return
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            return
        previous = self.elapsed
        self.elapsed = min(self.duration, previous+seconds)
        if self.duration-self.elapsed <= 1e-9:
            self.elapsed = self.duration
        before = self.state_at(previous)
        after = self.state_at(self.elapsed)
        if before['shot_id'] == after['shot_id']:
            self.flight_audio.update(before['local_time'], after['local_time'],
                wing_phase=(before['eagle']['wing_phase'], after['eagle']['wing_phase']),
                mode=after['eagle']['sequence'])
        else:
            # Current reel shares one continuous wind bed across clip joins.
            # Per-shot cues restart locally, while no world story is advanced.
            self.flight_audio.begin_shot(after['local_time'])
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
            if not self._mouse_held:
                self._mouse_held = True
                point = self.game.to_canvas(event.pos)
                if point is not None and self.skip_rect.collidepoint(point):
                    self.skip()
        if not self.active or self.paused or not self.focused or not getattr(self.game, '_music_focused', True):
            self.flight_audio.pause()
        else:
            self.flight_audio.resume()

    def _terrain(self, target, image, record, *, align='center'):
        scale = max(RENDER_SIZE[0]/image.get_width(), RENDER_SIZE[1]/image.get_height())*record['scale']
        size = (round(image.get_width()*scale), round(image.get_height()*scale))
        art = pygame.transform.scale(image, size)
        ox, oy = record['offset']
        x = (960-size[0])/2.+ox
        y = (640-size[1])/2.+oy
        # Ground cards continue below frame. Their opaque source bottom must
        # never slide into view as a horizontal cut across another mountain.
        y = max(640-size[1], y)
        if align == 'left': x = -size[0]*.52+ox
        elif align == 'right': x = 960-size[0]*.85+ox
        target.blit(art, (round(x), round(y)))

    def render_frame(self, time=None):
        """Render from source detail, never through the 480×320 world canvas."""
        state = self.state_at(self.elapsed if time is None else time)
        art = self._assets[state['shot_id']]
        target = pygame.Surface(RENDER_SIZE).convert()
        target.fill('#b6c8db')
        for name in ('sky', 'distant', 'mid', 'crest'):
            self._terrain(target, art['layers'][name], state['layers'][name])
        # Complete eagle frames stay at one chase distance. Wing extent never
        # drives body scale or registration, including during its bank.
        eagle = state['eagle']
        image = art['eagle'][eagle['sequence']]['frames'][eagle['frame']][0]
        target.blit(image, (round(eagle['position'][0]-eagle['anchor'][0]),
                            round(eagle['position'][1]-eagle['anchor'][1])))
        for name, align in (('foreground_a', 'left'), ('foreground_b', 'right')):
            if not self.reduced_motion:
                self._terrain(target, art['layers'][name], state['layers'][name], align=align)
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
