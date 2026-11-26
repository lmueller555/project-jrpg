"""Shared timed cinematic playback with an explicit scene and disposable state.

Scenes own their art, actions and completion handoff. This player owns bounded
shot clocks, actor frames, readable portrait captions and pause/skip controls.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame

import speech_bubble
from ui_style import BRASS, MUTED

ROOT = Path(__file__).resolve().parent
VIEW_SIZE = (480, 320)


def _smooth(value):
    value = max(0.0, min(1.0, value))
    return value*value*(3-2*value)


class CinematicPlayer:
    """Bounded authored shots with a single completion callback per playback."""

    def __init__(self, game, *, scene_path):
        self.game = game
        self.scene_path = Path(scene_path).resolve()
        self.data = json.loads(self.scene_path.read_text(encoding='utf-8'))
        self._validate()
        self.duration = float(self.data['duration'])
        self.layers = None
        self.actors = None
        self._actor_loops = {}
        self._prop_art = {}
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
            raise ValueError('Invalid cinematic scene')
        bounds = data.get('camera_bounds', (0, 0, 480, 160))
        if (len(bounds) != 4 or any(type(value) not in (int, float)
                or not math.isfinite(value) for value in bounds)
                or bounds[0] > bounds[2] or bounds[1] > bounds[3]):
            raise ValueError('Invalid cinematic camera bounds')
        end = 0.0
        for record in data['shots']:
            if record['start'] != end or record['end'] <= record['start']:
                raise ValueError('Cinematic shots must be continuous')
            end = record['end']
            for point in (record['from'], record['to']):
                if (len(point) != 2 or any(type(value) not in (int, float)
                        or not math.isfinite(value) for value in point)
                        or not (bounds[0] <= point[0] <= bounds[2]
                                and bounds[1] <= point[1] <= bounds[3])):
                    raise ValueError('Cinematic camera leaves the authored scene')
            if any(type(value) not in (int, float) or not math.isfinite(value)
                   or not 1 <= value <= 3 for value in record.get('zoom', (1, 1))):
                raise ValueError('Invalid cinematic zoom')
        if end != data['duration']:
            raise ValueError('Cinematic shots must cover its duration')
        end = 0.0
        for record in data['dialogue']:
            if (record['start'] < end or record['end'] <= record['start']
                    or record['end'] > data['duration'] or not record['text']):
                raise ValueError('Invalid cinematic dialogue timing')
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
            if record.get('file'):
                prop_art[identifier] = pygame.image.load(str(self._path(record['file']))).convert_alpha()
        self.layers, self.actors = layers, actors
        self._actor_loops, self._prop_art = actor_loops, prop_art
        social = getattr(self.game, 'social', None)
        speakers = (social.data['speakers'] if social is not None else
                    json.loads((ROOT/'assets/dialogue/eldenmere.json').read_text())['speakers'])
        # Scene-local speakers need not become overworld NPC registrations.
        speakers = dict(speakers, **self.data.get('speakers', {}))
        portraits = getattr(social, 'portraits', {})
        manifest = None
        for name in {record['speaker'] for record in self.data['dialogue']}:
            key = name.lower()
            profile = speakers[key]
            portrait_key = profile['portrait']
            portrait = portraits.get(portrait_key)
            if profile.get('portrait_file'):
                portrait = pygame.image.load(str(self._path(profile['portrait_file']))).convert_alpha()
            if portrait is None:
                if manifest is None:
                    manifest = json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())
                filename = manifest['portraits'][portrait_key]['file']
                portrait = pygame.image.load(str(ROOT/'assets/portraits/eldenmere'/filename)).convert_alpha()
            self._dialogue_speakers[name] = profile
            self._dialogue_portraits[portrait_key] = portrait

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
        return self.reduced_motion or record['from'] == record['to']

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

    def _prop_visible(self, identifier):
        record = self.data.get('dynamic_props', {}).get(identifier)
        return bool(record and record.get('visible_from', 0) <= self.elapsed
                    < record.get('visible_until', self.duration+1))

    @property
    def dialogue(self):
        record = next((record for record in self.data['dialogue']
                       if record['start'] <= self.elapsed < record['end']), None)
        return record

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
        # Frame steps can land a few floating-point bits below an exact endpoint.
        if self.duration-self.elapsed <= 1e-9:
            self.elapsed = self.duration
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
        x = max(0, min(image.get_width()-VIEW_SIZE[0], camera.x*factor))
        y = max(0, min(image.get_height()-VIEW_SIZE[1], camera.y*factor))
        canvas.blit(image, (-round(x), -round(y)))

    def _draw_prop(self, canvas, identifier, camera):
        if not self._prop_visible(identifier) or identifier not in self._prop_art:
            return
        record = self.data['dynamic_props'][identifier]
        image = self._prop_art[identifier]
        point = pygame.Vector2(record['position'])-camera-pygame.Vector2(record.get('anchor', (0, 0)))
        canvas.blit(image, (round(point.x), round(point.y)))

    def _draw_actors(self, canvas, camera):
        for record, anchor, frames, transitions in sorted(self.actors,
                key=lambda actor: self.actor_position(actor[0]['id']).y):
            image = self._actor_frame(record['id'], frames, transitions)
            point = self.actor_position(record['id'])-camera
            # Whole authored bodies keep fixed physical proportions and contact.
            canvas.blit(image, (round(point.x-anchor[0]), round(point.y-anchor[1])))

    def _zoom_focus(self, camera):
        return pygame.Vector2(self.shot_record.get(
            'zoom_focus', (camera.x+240, camera.y+160)))-camera

    def _project_rect(self, rect, camera):
        zoom = self.camera_zoom
        if zoom <= 1:
            return rect.copy()
        focus = self._zoom_focus(camera)
        offset_x, offset_y = round(focus.x*(1-zoom)), round(focus.y*(1-zoom))
        scale_x = math.ceil(VIEW_SIZE[0]*zoom)/VIEW_SIZE[0]
        scale_y = math.ceil(VIEW_SIZE[1]*zoom)/VIEW_SIZE[1]
        left = math.floor(rect.left*scale_x)+offset_x
        top = math.floor(rect.top*scale_y)+offset_y
        right = math.ceil(rect.right*scale_x)+offset_x
        bottom = math.ceil(rect.bottom*scale_y)+offset_y
        return pygame.Rect(left, top, right-left, bottom-top)

    def _zoom(self, canvas, camera):
        zoom = self.camera_zoom
        if zoom <= 1:
            return
        focus = self._zoom_focus(camera)
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
            rect = self._project_rect(rect, self.camera_position)
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

    def _draw_scene(self, canvas, camera):
        canvas.fill('#111e2a')
        for record, image in self.layers:
            if not record.get('foreground', False):
                self._draw_layer(canvas, record, image, camera)
        for identifier in self._prop_art:
            self._draw_prop(canvas, identifier, camera)
        self._draw_actors(canvas, camera)
        for record, image in self.layers:
            if record.get('foreground', False):
                self._draw_layer(canvas, record, image, camera)

    def draw(self, canvas, ui_surface):
        self._load()
        camera = self.camera_position
        self._draw_scene(canvas, camera)
        self._zoom(canvas, camera)
        pygame.transform.scale(canvas, ui_surface.get_size(), ui_surface)
        painter = self.game.ui.painter(ui_surface)
        self._layout(painter)
        self._draw_captions(painter)
        if self.fade_alpha:
            painter.veil(self.fade_alpha)
        painter.button(self.skip_rect, 'Skip')
        pause_key = 'P' if getattr(self.game, '_is_gallery_preview', False) else 'Esc'
        painter.text(f'{pause_key} · Resume' if self.paused else f'{pause_key} · Pause',
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
