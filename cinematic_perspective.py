"""Bounded playback of camera-registered, pre-rendered cinematic perspectives.

The manifest contains inclusive endpoint samples: 301 images describe 300
intervals at 60 Hz, rather than a 301/60-second movie. Sampling is pure; PNG
access belongs to preload/draw and decoded surfaces have an explicit bound.
"""
from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
import json
import math
from pathlib import Path
import struct
import time
import zlib

import pygame


RENDER_SIZE = (960, 640)
ALARM_PERIOD = 2.
_PNG = b'\x89PNG\r\n\x1a\n'


def _number(value, *, positive=False):
    return (type(value) in (int, float) and math.isfinite(value)
            and (value > 0 if positive else value >= 0))


def _clock(seconds):
    if not _number(seconds):raise ValueError('Invalid perspective clock')
    return float(seconds)


def _finite_tree(value):
    """Metadata may contain labels and nested points, but never NaN/Infinity."""
    if isinstance(value, dict):return all(_finite_tree(v) for v in value.values())
    if isinstance(value, list):return all(_finite_tree(v) for v in value)
    return not isinstance(value, float) or math.isfinite(value)


def _json(path):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError(f'Invalid perspective metadata: {path.name}') from error


def _png_size(path):
    """Check all chunk CRCs without keeping compressed or decoded reels in RAM."""
    try:
        with path.open('rb') as source:
            if source.read(8) != _PNG:raise ValueError('Invalid PNG signature')
            size, has_data, ended = None, False, False
            while not ended:
                header = source.read(8)
                if len(header) != 8:raise ValueError('Truncated PNG')
                length, kind = struct.unpack('>I4s', header)
                if length > 64*1024*1024:raise ValueError('Invalid PNG chunk length')
                if size is None and (kind != b'IHDR' or length != 13):
                    raise ValueError('Missing PNG header')
                checksum = zlib.crc32(kind)
                remaining = length
                head = b''
                while remaining:
                    block = source.read(min(remaining, 65536))
                    if not block:raise ValueError('Truncated PNG chunk')
                    if kind == b'IHDR':head += block
                    checksum = zlib.crc32(block, checksum)
                    remaining -= len(block)
                crc = source.read(4)
                if len(crc) != 4 or struct.unpack('>I', crc)[0] != checksum & 0xffffffff:
                    raise ValueError('Corrupt PNG chunk')
                if kind == b'IHDR':
                    if size is not None:raise ValueError('Duplicate PNG header')
                    width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', head)
                    if (depth != 8 or color not in (2, 6) or compression or filtering
                            or interlace not in (0, 1)):
                        raise ValueError('Perspective PNG must be 8-bit RGB or RGBA')
                    size = (width, height)
                elif kind == b'IDAT':has_data = True
                elif kind == b'IEND':
                    if length or not has_data:raise ValueError('Invalid PNG ending')
                    ended = True
            if source.read(1):raise ValueError('Trailing PNG data')
            return size
    except (OSError, struct.error, ValueError) as error:
        raise ValueError(f'Invalid perspective image: {path.name}') from error


def _decode_png(path):
    """Software PNG decoding only; display conversion stays on the main thread."""
    try:
        image = pygame.image.load(str(path))
        if image.get_size() != RENDER_SIZE:raise ValueError('Perspective image dimensions changed')
        return image
    except (OSError, pygame.error, ValueError) as error:
        raise ValueError(f'Cannot decode perspective frame: {path.name}') from error


class CinematicPerspective:
    """Share one validated reel and one bounded surface cache across its shots.

    ``samples`` never reads images. ``preload`` queues a bounded lookahead on
    two software decoders; ``draw`` converts ready surfaces on the main thread.
    ``close`` clears decoded working data and remains reusable for Gallery
    restart and deterministic review renders after completion.
    """
    def __init__(self, manifest_path, *, allowed_root=None, cache_size=24):
        self.path = Path(manifest_path).resolve()
        self.root = Path(allowed_root).resolve() if allowed_root is not None else self.path.parent
        if not self.path.is_relative_to(self.root):
            raise ValueError('Perspective manifest leaves cinematic artwork')
        if type(cache_size) is not int or not 4 <= cache_size <= 64:
            raise ValueError('Invalid perspective cache bound')
        self.cache_size = cache_size
        self._cache = OrderedDict()
        self._executor = None
        self._windows = {}
        self._active_segment = None
        self._hits = self._misses = 0
        self._waits = 0
        self._wait_seconds = 0.
        data = _json(self.path)
        if (not isinstance(data, dict) or data.get('version') != 1
                or (data.get('width'), data.get('height')) != RENDER_SIZE
                or data.get('fps') != 60 or type(data.get('fps')) is not int
                or not isinstance(data.get('segments'), dict) or not data['segments']):
            raise ValueError('Invalid perspective manifest')
        self.fps = data['fps']
        self.segments = {}
        checked = set()
        for name, record in data['segments'].items():
            if not isinstance(name, str) or not name or not isinstance(record, dict):
                raise ValueError('Invalid perspective segment')
            duration = record.get('duration_ms')
            if not _number(duration, positive=True):raise ValueError('Invalid perspective duration')
            duration /= 1000.
            loop = record.get('loop_ms')
            if loop is not None and not _number(loop, positive=True):
                raise ValueError('Invalid perspective loop')
            loop = None if loop is None else loop/1000.
            frames = self._paths(record.get('frames'))
            alarms = self._paths(record.get('alarm_frames'))
            if len(frames) != len(alarms):raise ValueError('Perspective alarm count differs from beauty frames')
            intervals = duration*self.fps
            if loop is None and (abs(intervals-round(intervals)) > 1e-8
                                 or len(frames) != round(intervals)+1):
                raise ValueError('Perspective sequence needs inclusive 60 FPS endpoints')
            if loop is not None and len(frames) < 2:
                raise ValueError('Perspective loop needs multiple frames')
            for filename in (*frames, *alarms):
                if filename not in checked:
                    if _png_size(filename) != RENDER_SIZE:
                        raise ValueError('Perspective image dimensions differ from render size')
                    checked.add(filename)
            metadata = self._metadata(record, len(frames))
            self.segments[name] = {'frames':frames, 'alarm_frames':alarms,
                'duration':duration, 'loop':loop, 'metadata':metadata}

    def _confined(self, filename):
        if not isinstance(filename, str) or not filename:
            raise ValueError('Invalid perspective asset path')
        candidate = (self.path.parent/filename).resolve()
        if Path(filename).is_absolute() or not candidate.is_relative_to(self.root):
            raise ValueError('Perspective asset leaves cinematic artwork')
        if not candidate.is_file():raise ValueError(f'Missing perspective asset: {candidate.name}')
        return candidate

    def _paths(self, values):
        if not isinstance(values, list) or not values or len(values) > 3601:
            raise ValueError('Invalid perspective frame list')
        return tuple(self._confined(value) for value in values)

    def _metadata(self, record, count):
        if 'metadata_path' not in record:return tuple({} for _ in range(count))
        data = _json(self._confined(record['metadata_path']))
        if not isinstance(data, list) or len(data) != count or not _finite_tree(data):
            raise ValueError('Invalid perspective camera samples')
        for index, sample in enumerate(data):
            if (not isinstance(sample, dict) or sample.get('index') != index
                    or not _number(sample.get('time_seconds'))
                    or not isinstance(sample.get('camera'), dict)):
                raise ValueError('Invalid perspective camera sample')
            camera = sample['camera']
            for key in ('position', 'target', 'up'):
                values = camera.get(key)
                if (not isinstance(values, list) or len(values) != 3
                        or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
                    raise ValueError('Invalid perspective camera vector')
            if not _number(camera.get('fov_degrees'), positive=True) or camera['fov_degrees'] >= 180:
                raise ValueError('Invalid perspective camera field of view')
        return tuple(data)

    def _segment(self, name):
        try:return self.segments[name]
        except (KeyError, TypeError) as error:raise ValueError('Unknown perspective segment') from error

    def validate_segment(self, name, duration_seconds):
        record = self._segment(name)
        if (not _number(duration_seconds, positive=True)
                or abs(record['duration']-duration_seconds) > 1e-8):
            raise ValueError('Perspective segment and shot durations disagree')
        return True

    def samples(self, segment, seconds, reduced_motion=False):
        record = self._segment(segment)
        at = min(record['duration'], _clock(seconds))
        count = len(record['frames'])
        if record['loop'] is None:
            index = min(count-1, math.floor(at*self.fps+1e-8))
        else:
            position = (at % record['loop'])/record['loop']*count
            index = min(count-1, math.floor(position+1e-8))
        state = {'segment':segment, 'local_time':at, 'frame_index':index,
                 'reduced_motion':bool(reduced_motion)}
        if reduced_motion and record['loop'] is None:
            # Calmer representative views dissolve instead of moving through
            # every perspective. Rush endpoints also omit authored speed lines.
            indices = [0, count-1] if record['duration'] <= 1 else [0, (count-1)//2, count-1]
            position = at/record['duration']*(len(indices)-1)
            part = min(len(indices)-2, math.floor(position))
            state.update(frame_index=indices[part], blend_frame_index=indices[part+1],
                         blend=max(0., min(1., position-part)))
            if state['blend'] >= 1.:
                state['frame_index'] = state.pop('blend_frame_index')
                state.pop('blend')
        elif reduced_motion:
            state['frame_index'] = 0
        elif record['loop'] is not None:
            # The camera is fixed in these loops: interpolate plume animation
            # continuously, including the last-to-first seam, at display rate.
            state.update(blend_frame_index=(index+1) % count,
                         blend=max(0., min(1., position-index)))
        sample = record['metadata'][state['frame_index']]
        state['camera'] = deepcopy(sample.get('camera', {}))
        state['landmarks'] = deepcopy(sample.get('landmarks', {}))
        return state

    def _image(self, path, *, alarm=False):
        key = (path, alarm)
        if key in self._cache:
            self._hits += 1
            self._cache.move_to_end(key)
            cached = self._cache[key]
            if not isinstance(cached, Future):return cached
        else:
            self._misses += 1
            cached = None
        try:
            if cached is not None:
                waiting = not cached.done()
                before = time.perf_counter()
                image = cached.result()
                if waiting:
                    self._waits += 1
                    self._wait_seconds += time.perf_counter()-before
            else:image = _decode_png(path)
            image = image.convert_alpha().premul_alpha().convert() if alarm else image.convert()
        except (OSError, pygame.error, ValueError) as error:
            self._cache.pop(key, None)
            raise ValueError(f'Cannot decode perspective frame: {path.name}') from error
        self._cache[key] = image
        self._trim()
        return image

    def _trim(self):
        while len(self._cache) > self.cache_size:
            protected = {key for keys in self._windows.values() for key in keys}
            # Consume old pictures before evicting the next shot's ready start.
            # A running decoder keeps its reservation even during a large seek.
            candidates = [key for key in self._cache if key not in protected]
            candidates += [key for keys in reversed(tuple(self._windows.values()))
                           for key in reversed(keys) if key in self._cache]
            for key in candidates:
                image = self._cache[key]
                if isinstance(image, Future) and not image.done() and not image.cancel():continue
                del self._cache[key];break
            else:raise RuntimeError('Perspective cache has no evictable slot')

    def _queue(self, path, *, alarm=False):
        key = (path, alarm)
        if key in self._cache:
            self._cache.move_to_end(key)
            return
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='cinematic-png')
        self._cache[key] = self._executor.submit(_decode_png, path)
        self._misses += 1
        self._trim()

    def preload(self, segment, seconds=0., *, reduced_motion=False, alarm_active=False,
                blocking=False, max_slots=16, priority='active'):
        """Queue a window; explicitly warm it before standalone playback starts.

        Active windows reserve up to sixteen surfaces; a neighboring clip uses
        eight, so both fit the default twenty-four-slot cache. Reservations
        include queued and completed decoder futures, not only drawn surfaces.
        """
        if type(max_slots) is not int or max_slots < 4:
            raise ValueError('Invalid perspective prefetch window')
        if priority not in ('active', 'upcoming'):
            raise ValueError('Invalid perspective prefetch priority')
        state = self.samples(segment, seconds, reduced_motion)
        record = self._segment(segment)
        indices = [state['frame_index']]
        if 'blend_frame_index' in state:indices.append(state['blend_frame_index'])
        slots = min(self.cache_size, max_slots)
        if not reduced_motion:
            for step in range(1, slots+1):
                index = state['frame_index']+step
                if record['loop'] is not None:index %= len(record['frames'])
                if index < len(record['frames']) and index not in indices:indices.append(index)
        keys = []
        for index in indices:
            frame_keys = [(record['frames'][index], False)]
            if alarm_active:frame_keys.append((record['alarm_frames'][index], True))
            for key in frame_keys:
                if key not in keys:keys.append(key)
            if len(keys) >= slots:break
        keys = keys[:slots]
        if priority == 'active' and segment != self._active_segment:
            self._windows.clear()
            self._active_segment = segment
        self._windows[segment] = keys
        for path, alarm in keys:self._queue(path, alarm=alarm)
        if blocking:
            for path, alarm in keys:self._image(path, alarm=alarm)
        return state

    @staticmethod
    def alarm_strength(seconds, reduced_motion=False):
        if reduced_motion:return .68
        phase = _clock(seconds) % ALARM_PERIOD
        # A readable slow warning pulse, rather than full-screen strobing.
        return .1+.9*max(0., 1.-phase/.4)**.65

    def draw(self, target, state, *, alarm_active=False, alarm_elapsed=0.):
        if target.get_size() != RENDER_SIZE:raise ValueError('Perspective target has wrong dimensions')
        record = self._segment(state.get('segment'))
        index = state.get('frame_index')
        if type(index) is not int or not 0 <= index < len(record['frames']):
            raise ValueError('Invalid perspective frame index')
        self.preload(state['segment'], state['local_time'],
                     reduced_motion=state.get('reduced_motion', False), alarm_active=alarm_active)
        target.blit(self._image(record['frames'][index]), (0, 0))
        blend = state.get('blend', 0.)
        if blend:
            other = self._image(record['frames'][state['blend_frame_index']]).copy()
            other.set_alpha(round(255*blend));target.blit(other, (0, 0))
        if alarm_active:
            strength = self.alarm_strength(alarm_elapsed, state.get('reduced_motion', False))
            overlay = self._image(record['alarm_frames'][index], alarm=True).copy()
            factor = round(255*strength*(1-blend))
            overlay.fill((factor, factor, factor), special_flags=pygame.BLEND_RGB_MULT)
            target.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            if blend:
                overlay = self._image(record['alarm_frames'][state['blend_frame_index']], alarm=True).copy()
                factor = round(255*strength*blend)
                overlay.fill((factor, factor, factor), special_flags=pygame.BLEND_RGB_MULT)
                target.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    @property
    def cache_info(self):
        decoded, pending, size = 0, 0, 0
        for image in self._cache.values():
            if isinstance(image, Future):
                if not image.done():pending += 1;continue
                if image.cancelled() or image.exception() is not None:continue
                image = image.result()
            decoded += 1
            size += image.get_pitch()*image.get_height()
        pending_bytes = pending*RENDER_SIZE[0]*RENDER_SIZE[1]*4
        return {'surfaces':len(self._cache), 'capacity':self.cache_size,
                'decoded_surfaces':decoded, 'pending_surfaces':pending,
                'decoded_bytes':size, 'pending_bytes':pending_bytes,
                'bytes':size+pending_bytes, 'hits':self._hits, 'decodes':self._misses,
                'waits':self._waits, 'wait_seconds':self._wait_seconds}

    def close(self):
        for image in self._cache.values():
            if isinstance(image, Future):image.cancel()
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None
        self._cache.clear()
        self._windows.clear()
        self._active_segment = None
