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
        self._mist_texture = None
        self.skip_rect = pygame.Rect(426, 292, 44, 20)
        self.caption_rect = pygame.Rect(22, 250, 436, 32)
        self.caption_lines = []
        self.reset()

    def _validate(self):
        data = self.data
        if (data.get('version') != 1 or tuple(data.get('viewport', ())) != VIEW_SIZE
                or tuple(data.get('canvas', ())) != (960, 480)
                or type(data.get('duration')) not in (int, float)
                or not math.isfinite(data['duration']) or data['duration'] <= 0):
            raise ValueError('Invalid opening cinematic scene')
        end = 0.0
        for record in data['shots']:
            if record['start'] != end or record['end'] <= record['start']:
                raise ValueError('Opening cinematic shots must be continuous')
            end = record['end']
            for point in (record['from'], record['to']):
                if len(point) != 2 or not (0 <= point[0] <= 480 and 0 <= point[1] <= 160):
                    raise ValueError('Opening cinematic camera leaves the authored scene')
        if end != data['duration']:
            raise ValueError('Opening cinematic shots must cover its duration')
        end = 0.0
        for record in data['dialogue']:
            if (record['start'] < end or record['end'] <= record['start']
                    or record['end'] > data['duration'] or not record['text']):
                raise ValueError('Invalid opening cinematic dialogue timing')
            end = record['end']

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
        actors = []
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
        self.layers, self.actors = layers, actors
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
        return pygame.Vector2(record['from']).lerp(record['to'], fraction)

    @property
    def dialogue(self):
        return next((record for record in self.data['dialogue']
                     if record['start'] <= self.elapsed < record['end']), None)

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
        y = max(0, min(image.get_height()-VIEW_SIZE[1], camera.y*factor))
        canvas.blit(image, (-round(x), -round(y)))

    def _lantern(self, canvas, camera):
        x, y = pygame.Vector2(self.data['lantern_position'])-camera
        pulse = 0 if self.reduced_motion else math.sin(self.elapsed*4.3)*2+math.sin(self.elapsed*7.1)
        glow = pygame.Surface(VIEW_SIZE, pygame.SRCALPHA)
        for radius, opacity in ((35, 7), (24, 10), (12, 16)):
            pygame.draw.circle(glow, (248, 172, 68, round(opacity+pulse)),
                               (round(x), round(y)), radius)
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
            y = 204+index*19-camera.y*.3
            canvas.blit(self._mist_texture, (round(x), round(y)))

    def _draw_actors(self, canvas, camera):
        for record, anchor, frames, transitions in self.actors:
            image = self._actor_frame(record['id'], frames, transitions)
            point = pygame.Vector2(record['position'])-camera
            # Whole authored bodies keep fixed physical proportions and contact.
            canvas.blit(image, (round(point.x-anchor[0]), round(point.y-anchor[1])))

    def _layout(self, painter):
        height = max(20, painter.font().get_linesize()+8)
        width = max(44, painter.font().size('Skip')[0]+18)
        self.skip_rect = pygame.Rect(470-width, 310-height, width, height)
        self.caption_lines = []
        record = self.dialogue
        if record is None:
            self.caption_rect = pygame.Rect(22, self.skip_rect.top-8, 436, 0)
            return
        self.caption_lines = painter.wrap(record['text'], 412)
        line = painter.font().get_linesize()+2
        name = painter.font('small', bold=True).get_linesize()+4
        height = 16+name+line*len(self.caption_lines)
        self.caption_rect = pygame.Rect(22, self.skip_rect.top-9-height, 436, height)
        if self.caption_rect.top < 210:
            # Enlarged text gets the sky area, preserving the handoff, cup and
            # faces instead of pushing a taller subtitle strip over the actors.
            self.caption_rect.top = 15

    def _draw_captions(self, painter):
        record = self.dialogue
        if record is None:
            return
        shade = pygame.Surface(painter.canvas.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(shade, (10, 19, 27, 220), painter.area(self.caption_rect),
                         border_radius=max(1, round(3*painter.scale)))
        painter.canvas.blit(shade, (0, 0))
        x, y = self.caption_rect.x+12, self.caption_rect.y+8
        painter.text(record['speaker'], (x, y), role='small', color=GOLD, bold=True)
        y += painter.font('small', bold=True).get_linesize()+4
        for line in self.caption_lines:
            painter.text(line, (x, y), color=IVORY)
            y += painter.font().get_linesize()+2

    def draw(self, canvas, ui_surface):
        self._load()
        canvas.fill('#111e2a')
        camera = self.camera_position
        for record, image in self.layers:
            if not record.get('foreground', False):
                self._draw_layer(canvas, record, image, camera)
                if record['file'] == 'valley.png':
                    self._mist(canvas, camera)
        self._lantern(canvas, camera)
        self._air(canvas, camera)
        self._draw_actors(canvas, camera)
        for record, image in self.layers:
            if record.get('foreground', False):
                self._draw_layer(canvas, record, image, camera)
        pygame.transform.scale(canvas, ui_surface.get_size(), ui_surface)
        painter = self.game.ui.painter(ui_surface)
        self._layout(painter)
        self._draw_captions(painter)
        framing = self.framing_caption
        if framing is not None:
            painter.text(framing['text'], (240, 29), color=IVORY, anchor='midtop')
        # The brief dark dissolve joins the existing bedroom's morning fade.
        if not self.reduced_motion:
            fade_in = max(0.0, 1-self.elapsed/1.1)
            fade_out = max(0.0, (self.elapsed-(self.duration-1.1))/1.1)
            if fade_in or fade_out:
                painter.veil(round(255*max(fade_in, fade_out)))
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
