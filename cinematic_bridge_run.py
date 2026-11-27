"""Side-tracking bridge performance using complete authored character frames.

The camera follows the lead pair and eases back toward the trailing soldier.
Only uniform whole-image sampling and camera projection happen here. Anatomy,
near/far limb overlap, running recoil and cloth motion belong to the drawings.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
import json
import math
from pathlib import Path
import struct
import time

import pygame


RENDER_SIZE = (960, 640)
RUN_SCENE = Path(__file__).resolve().parent/'assets/story/fire_veinhold_opening/shot06/scene.json'
_ACTORS = {'lucan', 'iselin', 'crown_soldier'}


def _number(value, *, minimum=0., positive=False):
    return (type(value) in (int, float) and math.isfinite(value)
            and (value > minimum if positive else value >= minimum))


def _read(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError(f'Invalid bridge-running metadata: {path.name}') from error
    if not isinstance(data, dict):
        raise ValueError('Bridge-running metadata must be an object')
    return data


def _path(filename, base, root):
    if not isinstance(filename, str) or not filename or Path(filename).is_absolute():
        raise ValueError('Bridge-running artwork must use relative paths')
    candidate = (base/filename).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise ValueError('Bridge-running artwork leaves or is missing from its scene')
    return candidate


def _pair(value, *, integer=False):
    return (isinstance(value, list) and len(value) == 2
            and all(type(v) is int if integer else type(v) in (int, float)
                    and math.isfinite(v) for v in value))


def _png_size(path):
    try:
        with path.open('rb') as source:
            header = source.read(24)
        if (len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n'
                or header[12:16] != b'IHDR'):
            raise ValueError('Invalid PNG header')
        return struct.unpack('>II', header[16:24])
    except (OSError, struct.error) as error:
        raise ValueError(f'Invalid bridge-running PNG: {path.name}') from error


def _decode_png(path, canvas):
    """Decode software pixels only; display conversion belongs to the caller."""
    try:
        image = pygame.image.load(str(path))
    except (OSError, pygame.error) as error:
        raise ValueError(f'Cannot decode running artwork: {path.name}') from error
    if canvas is not None and image.get_size() != tuple(canvas):
        raise ValueError('Running artwork dimensions changed after validation')
    return image


def _animation(path, root, *, check_images):
    data = _read(path)
    canvas, anchor = data.get('canvas'), data.get('anchor')
    if (data.get('version') != 1 or not _pair(canvas, integer=True)
            or any(not 0 < value <= 1024 for value in canvas)
            or not _pair(anchor) or any(not 0 <= anchor[i] <= canvas[i] for i in range(2))
            or not isinstance(data.get('frames'), list) or not 4 <= len(data['frames']) <= 64):
        raise ValueError('Invalid complete running-frame registration')
    frames, boundaries, duration = [], [], 0.
    for record in data['frames']:
        if not isinstance(record, dict) or not _number(record.get('duration_ms'), positive=True):
            raise ValueError('Invalid running-frame duration')
        image = _path(record.get('file'), path.parent, root)
        if check_images and _png_size(image) != tuple(canvas):
            raise ValueError('Running frames must share the authored canvas')
        seconds = record['duration_ms']/1000.
        duration += seconds
        boundaries.append(duration)
        frames.append({'path':image, 'duration_seconds':seconds})
    if 'duration_ms' in data:
        if (not _number(data['duration_ms'], positive=True)
                or abs(data['duration_ms']/1000.-duration) > 1e-8):
            raise ValueError('Running cycle duration differs from its frames')
        duration = data['duration_ms']/1000.
        boundaries[-1] = duration
    contacts = data.get('contacts')
    if not isinstance(contacts, list) or len(contacts) != 2:
        raise ValueError('Running cycle needs one near and one far contact')
    normalized, feet = [], set()
    for contact in contacts:
        if (not isinstance(contact, dict) or contact.get('foot') not in ('near', 'far')
                or contact['foot'] in feet or type(contact.get('frame')) is not int
                or not 0 <= contact['frame'] < len(frames)):
            raise ValueError('Invalid running foot-contact metadata')
        feet.add(contact['foot'])
        index = contact['frame']
        normalized.append({'frame':index, 'foot':contact['foot'],
                           'time_seconds':0. if index == 0 else boundaries[index-1]})
    return {'canvas':tuple(canvas), 'anchor':tuple(anchor), 'frames':tuple(frames),
            'boundaries':tuple(boundaries), 'cycle_seconds':duration,
            'contacts':tuple(normalized)}


def _metadata(path, root, *, check_images):
    data = _read(path)
    if (data.get('version') != 1 or tuple(data.get('render_size', ())) != RENDER_SIZE
            or not _number(data.get('duration_seconds'), positive=True)
            or not isinstance(data.get('actors'), list)
            or len(data['actors']) != 3):
        raise ValueError('Invalid bridge-running scene')
    actors, identifiers = [], set()
    for record in data['actors']:
        if (not isinstance(record, dict) or record.get('id') not in _ACTORS
                or record['id'] in identifiers
                or not _number(record.get('phase_offset_seconds'))
                or not _number(record.get('depth_scale'), positive=True)
                or not _number(record.get('offset_metres'), minimum=-100.)
                or not _number(record.get('ground_y'))
                or not _number(record.get('lane_metres', 0.), minimum=-100.)):
            raise ValueError('Invalid running actor formation')
        identifiers.add(record['id'])
        animation_path = _path(record.get('animation'), path.parent, root)
        animation = _animation(animation_path, root, check_images=check_images)
        actors.append({**record, 'animation':animation})
    lead = next(a for a in actors if a['id'] == 'lucan')
    trailing = next(a for a in actors if a['id'] == 'crown_soldier')
    if abs((lead['offset_metres']-trailing['offset_metres'])-3.048) > 1e-8:
        raise ValueError('Crown soldier must retain the ten-foot trailing gap')
    if lead['offset_metres'] != 0 or any(a['offset_metres'] > 0 for a in actors):
        raise ValueError('Lucan must lead the running formation')
    camera = data.get('camera')
    if (not isinstance(camera, dict)
            or any(not _number(camera.get(name), positive=True)
                   for name in ('pixels_per_metre', 'actor_scale', 'speed_metres_per_second'))
            or not _number(camera.get('anchor_x'))
            or not _number(camera.get('starting_party_metres', 0.))
            or not _number(camera.get('drift_metres'))
            or not _number(camera.get('drift_start'))
            or not _number(camera.get('drift_end'), positive=True)
            or not camera['drift_start'] < camera['drift_end'] <= data['duration_seconds']):
        raise ValueError('Invalid bridge-running camera')
    layers = data.get('layers')
    if not isinstance(layers, list) or not layers:
        raise ValueError('Bridge-running scene needs an authored bridge layer')
    result_layers = []
    for record in layers:
        if (not isinstance(record, dict) or not isinstance(record.get('id'), str)
                or not record['id'] or record.get('plane') not in ('background', 'foreground')
                or not _number(record.get('speed_factor'))
                or not _number(record.get('reduced_motion_factor'))
                or record['reduced_motion_factor'] > 1.
                or not _number(record.get('offset_y'), minimum=-2048.)):
            raise ValueError('Invalid authored bridge layer')
        for flag in ('mirror_repeat', 'omit_reduced_motion', 'ground'):
            if flag in record and type(record[flag]) is not bool:
                raise ValueError('Invalid bridge-layer presentation flag')
        if record.get('ground', False) and (record['plane'] != 'background'
                or record['speed_factor'] != 1. or record['reduced_motion_factor'] != 1.
                or record.get('omit_reduced_motion', False)):
            raise ValueError('The running ground must retain its stride-relative speed')
        image = _path(record.get('file'), path.parent, root)
        size = _png_size(image) if check_images else None
        if size is not None and not (0 < size[0] <= 8192 and 0 < size[1] <= 2048):
            raise ValueError('Invalid bridge-layer dimensions')
        result_layers.append({**record, 'path':image, 'size':size})
    return {**data, 'actors':tuple(actors), 'layers':tuple(result_layers)}


def read_run_timing(manifest_path=RUN_SCENE):
    """Read shared footfall timing without loading or transforming any image.

    Positive phase offsets advance each actor's cycle. A contact therefore
    occurs at ``(contact_time - phase_offset) % cycle`` after the shot begins.
    Audio owners may cache this immutable-by-convention result for their lease.
    """
    path = Path(manifest_path).resolve()
    data = _metadata(path, path.parent, check_images=False)
    return tuple({'id':actor['id'],
                  'cycle_seconds':actor['animation']['cycle_seconds'],
                  'phase_offset_seconds':actor['phase_offset_seconds'],
                  'contacts':[dict(contact) for contact in actor['animation']['contacts']]}
                 for actor in data['actors'])


def _smooth(value):
    value = max(0., min(1., value))
    return value*value*(3.-2.*value)


class CinematicBridgeRun:
    """A bounded source-frame cache and deterministic whole-drawing staging."""
    def __init__(self, manifest_path=RUN_SCENE, *, allowed_root=None, cache_size=12):
        self.path = Path(manifest_path).resolve()
        root = self.path.parent if allowed_root is None else Path(allowed_root).resolve()
        if not self.path.is_relative_to(root):
            raise ValueError('Running manifest leaves its cinematic')
        if type(cache_size) is not int or not 3 <= cache_size <= 24:
            raise ValueError('Invalid running-frame cache size')
        self.data = _metadata(self.path, root, check_images=True)
        self.duration = self.data['duration_seconds']
        self.cache_size = cache_size
        self._cache = OrderedDict()
        self._backgrounds = {}
        self._sizes = {layer['path']:layer['size'] for layer in self.data['layers']}
        for actor in self.data['actors']:
            self._sizes.update({frame['path']:actor['animation']['canvas']
                                for frame in actor['animation']['frames']})
        self._window = ()
        self._executor = None
        self._decodes = 0
        self._waits = 0
        self._wait_seconds = 0.

    def validate_duration(self, seconds):
        if not _number(seconds, positive=True) or abs(seconds-self.duration) > 1e-8:
            raise ValueError('Running scene and shot durations differ')

    def samples(self, seconds, reduced_motion=False):
        if not _number(seconds):
            raise ValueError('Invalid running-shot clock')
        local = min(self.duration, float(seconds))
        camera = self.data['camera']
        drift = camera['drift_metres']*_smooth(
            (local-camera['drift_start'])/(camera['drift_end']-camera['drift_start']))
        if reduced_motion:
            drift = 0.
        along = camera['speed_metres_per_second']*local-drift
        actors = []
        for actor in self.data['actors']:
            animation = actor['animation']
            phase = (local+actor['phase_offset_seconds']) % animation['cycle_seconds']
            if animation['cycle_seconds']-phase <= 1e-9:
                phase = 0.
            index = min(len(animation['frames'])-1,
                        bisect_right(animation['boundaries'], phase+1e-10))
            depth = actor['depth_scale']
            scale = camera['actor_scale']*depth
            foot_x = camera['anchor_x']+(actor['offset_metres']+drift)*camera['pixels_per_metre']*depth
            position = [foot_x-animation['anchor'][0]*scale,
                        actor['ground_y']-animation['anchor'][1]*scale]
            bounds = pygame.Rect(round(position[0]), round(position[1]),
                                 round(animation['canvas'][0]*scale), round(animation['canvas'][1]*scale))
            actors.append({'id':actor['id'], 'frame_index':index, 'cycle_phase':phase,
                'phase_offset_seconds':actor['phase_offset_seconds'], 'scale':scale,
                'space':'local_bridge_tracking',
                'world_position_metres':[camera['speed_metres_per_second']*local+actor['offset_metres'],
                                          actor.get('lane_metres', 0.)],
                'draw_position':position, 'ground_anchor':[foot_x, actor['ground_y']],
                'visible':bounds.colliderect(pygame.Rect((0, 0), RENDER_SIZE)),
                'depth_scale':depth, 'draw_order':actor.get('lane_metres', 0.)})
        return {'local_time':local, 'phase':'bridge_running', 'reduced_motion':bool(reduced_motion),
                'camera':{'space':'local_bridge_tracking',
                          'position_metres':[along, 0., .55], 'drift_metres':drift,
                          'party_travel_metres':camera.get('starting_party_metres', 0.)
                                                +camera['speed_metres_per_second']*local,
                          'direction':'toward_veinhold', 'screen_direction':'right'},
                'runners':actors}

    def _image(self, path, *, canvas=None, background=False):
        cache = self._backgrounds if background else self._cache
        if path in cache:
            if not background:
                cache.move_to_end(path)
            image = cache[path]
            if not isinstance(image, Future):
                return image
            waiting = not image.done()
            before = time.perf_counter()
            try:
                image = image.result()
            except ValueError:
                cache.pop(path, None)
                raise
            if waiting:
                self._waits += 1
                self._wait_seconds += time.perf_counter()-before
        else:
            image = _decode_png(path, canvas)
            self._decodes += 1
        # Premultiplication precedes the actors' uniform resampling, so RGB
        # hidden under transparent pixels cannot bleed into a boot silhouette.
        if background:
            image = image.convert_alpha() if image.get_flags() & pygame.SRCALPHA else image.convert()
        else:
            image = image.convert_alpha().premul_alpha()
        cache[path] = image
        if not background:
            self._trim_frames()
        return image

    def _trim_frames(self):
        while len(self._cache) > self.cache_size:
            candidates = [path for path in self._cache if path not in self._window]
            candidates += [path for path in reversed(self._window) if path in self._cache]
            for path in candidates:
                image = self._cache[path]
                if isinstance(image, Future) and not image.done() and not image.cancel():
                    continue
                del self._cache[path]
                break
            else:
                raise RuntimeError('Running cache has no evictable reservation')

    def _queue(self, path, *, background=False):
        cache = self._backgrounds if background else self._cache
        if path in cache:
            if not background:cache.move_to_end(path)
            return
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='running-png')
        cache[path] = self._executor.submit(_decode_png, path, self._sizes[path])
        self._decodes += 1
        if not background:self._trim_frames()

    def preload(self, seconds=0., *, reduced_motion=False, blocking=False):
        """Reserve current/next poses on two bounded software decoders.

        Standalone playback waits before starting its clock. The complete film
        starts this work during the preceding hold, without blocking its draw.
        """
        state = self.samples(seconds, reduced_motion)
        for layer in self.data['layers']:
            self._queue(layer['path'], background=True)
        keys = []
        for step in range(4):
            for stage, actor in zip(state['runners'], self.data['actors']):
                animation = actor['animation']
                record = animation['frames'][(stage['frame_index']+step) % len(animation['frames'])]
                if record['path'] not in keys:keys.append(record['path'])
        self._window = tuple(keys[:self.cache_size])
        for path in self._window:self._queue(path)
        if blocking:
            for layer in self.data['layers']:
                self._image(layer['path'], canvas=layer['size'], background=True)
            for path in self._window:self._image(path, canvas=self._sizes[path])
        return state

    def _layers(self, target, state, plane):
        camera = self.data['camera']
        for layer in self.data['layers']:
            if layer['plane'] != plane:
                continue
            if state['reduced_motion'] and layer.get('omit_reduced_motion', False):
                continue
            image = self._image(layer['path'], canvas=layer['size'], background=True)
            factor = layer['speed_factor']
            if state['reduced_motion']:
                factor *= layer['reduced_motion_factor']
            offset = -state['camera']['position_metres'][0]*camera['pixels_per_metre']*factor
            tile = math.floor(-round(offset)/image.get_width())
            x = round(offset)+tile*image.get_width()
            if x > 0:
                tile -= 1
                x -= image.get_width()
            while x < RENDER_SIZE[0]:
                shown = image
                if layer.get('mirror_repeat', False) and tile % 2:
                    key = (layer['path'], 'mirror')
                    if key not in self._backgrounds:
                        self._backgrounds[key] = pygame.transform.flip(image, True, False)
                    shown = self._backgrounds[key]
                target.blit(shown, (x, round(layer['offset_y'])))
                x += image.get_width()
                tile += 1

    @staticmethod
    def _whole_drawing(target, image, position, scale):
        # Crop only outside the output viewport before uniform sampling. This
        # preserves authored pixels and avoids allocating a mostly invisible
        # 1,200-pixel-tall body for a knees-down camera.
        left = max(0, math.floor(-position[0]/scale))
        top = max(0, math.floor(-position[1]/scale))
        right = min(image.get_width(), math.ceil((RENDER_SIZE[0]-position[0])/scale))
        bottom = min(image.get_height(), math.ceil((RENDER_SIZE[1]-position[1])/scale))
        if right <= left or bottom <= top:
            return
        source = image.subsurface((left, top, right-left, bottom-top))
        size = (max(1, round(source.get_width()*scale)), max(1, round(source.get_height()*scale)))
        sampled = pygame.transform.smoothscale(source, size)
        target.blit(sampled, (round(position[0]+left*scale), round(position[1]+top*scale)),
                    special_flags=pygame.BLEND_PREMULTIPLIED)

    def draw(self, target, state):
        if target.get_size() != RENDER_SIZE:
            raise ValueError('Running shot requires native output dimensions')
        target.fill('#0b1521')
        self._layers(target, state, 'background')
        by_id = {actor['id']:actor for actor in self.data['actors']}
        for stage in sorted(state['runners'], key=lambda actor:actor['draw_order']):
            if not stage['visible']:
                continue
            animation = by_id[stage['id']]['animation']
            record = animation['frames'][stage['frame_index']]
            image = self._image(record['path'], canvas=animation['canvas'])
            self._whole_drawing(target, image, stage['draw_position'], stage['scale'])
        self._layers(target, state, 'foreground')

    @property
    def cache_info(self):
        entries = [*self._cache.items(), *self._backgrounds.items()]
        size, pending = 0, 0
        for path, image in entries:
            if isinstance(image, Future):
                if not image.done():
                    width, height = self._sizes[path]
                    pending += width*height*4
                    continue
                if image.cancelled() or image.exception() is not None:continue
                image = image.result()
            size += image.get_pitch()*image.get_height()
        return {'surfaces':len(entries), 'frame_surfaces':len(self._cache),
                'background_surfaces':len(self._backgrounds),
                'capacity':self.cache_size+sum(2 if layer.get('mirror_repeat', False) else 1
                                               for layer in self.data['layers']),
                'frame_capacity':self.cache_size,
                'bytes':size+pending, 'decoded_bytes':size, 'pending_bytes':pending,
                'decodes':self._decodes, 'waits':self._waits, 'wait_seconds':self._wait_seconds}

    def close(self):
        for image in (*self._cache.values(), *self._backgrounds.values()):
            if isinstance(image, Future):image.cancel()
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None
        self._cache.clear()
        self._backgrounds.clear()
        self._window = ()
