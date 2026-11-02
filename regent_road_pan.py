"""Stateless, native-resolution crossroads-to-bridge camera and scenery effects.

Parent integration: sample the parent's phase clock, render FRESH scenery at
``camera_position``, use the frame returned by ``apply``, then draw sharp UI.
Never include captions/skip/pause UI in the input or reuse an effected frame as
the next source. This helper loads no panorama, owns no clock and calls no
scene, actor, display or audio code. Sampling allocates no image buffers.
"""
from __future__ import annotations

from bisect import bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from numbers import Real

import numpy as np
import pygame


SIZE = (480, 320)
MAX_DECODED_BYTES = 50_000_000
MAX_BLUR_PX = 48.0
BLUR_TAPS = 7
MAX_STREAKS = 6
_WEIGHTS = (1, 6, 15, 20, 15, 6, 1)
Point = tuple[float, float]


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f'{name} must be a finite number')
    try:
        result = float(value)
    except (OverflowError, ValueError):
        raise ValueError(f'{name} must be a finite number') from None
    if not math.isfinite(result):
        raise ValueError(f'{name} must be a finite number')
    return result


def _sequence(value: object, name: str) -> Sequence:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f'{name} must be a sequence')
    return value


def _pair(value: object, name: str) -> Point:
    values = _sequence(value, name)
    if len(values) != 2:
        raise ValueError(f'{name} must contain two finite coordinates')
    return _number(values[0], name), _number(values[1], name)


def _field(spec: Mapping, name: str) -> object:
    if name not in spec:
        raise ValueError(f'manifest is missing {name}')
    return spec[name]


def _streak_alpha(strength: float, index: int) -> int:
    return round((48 + 8 * (index % 3)) * strength * strength)


@dataclass(frozen=True, slots=True)
class RoadPanSample:
    """Immutable state; ``progress`` is eased canonical arc fraction, not time.

    Camera coordinates are panorama top-left pixels, tile coordinates are the
    road reference point (NOT viewport center). Velocity is pixels/second;
    screen direction is its opposite unit vector, or zero at rest. Strength
    normalizes canonical arc velocity to its peak for the supplied duration.
    ``active`` means strictly inside the motion interval. Effects diagnostics
    are the actual blur span and number of visible, alpha-enveloped streaks.
    """

    camera_position: Point
    tile_position: Point
    progress: float
    arc_distance_tiles: float
    camera_velocity: Point
    screen_motion_direction: Point
    strength: float
    blur_px: float
    streak_count: int
    active: bool


class RoadWhipPan:
    """Read an already-decoded crossroads manifest; never retain/load its art.

    The manifest's distance labels are authoritative: resumming chords of its
    resampled points would shorten the canonical road, notably near the bridge.
    Camera and geography interpolate the SAME distance bracket, with quintic
    ease-in/out and analytical velocity, never a previous-frame difference.
    Only small immutable tuples are retained. The renderer's temporary arrays
    and surfaces are all native 480x320 or smaller; nothing is cached per draw.
    """

    __slots__ = ('_camera', '_tiles', '_arcs', '_length', '_peak_speed')

    def __init__(self, manifest: Mapping[str, object]):
        if not isinstance(manifest, Mapping):
            raise ValueError('manifest must be a mapping')
        width, height = _pair(_field(manifest, 'canvas'), 'canvas')
        if (width < SIZE[0] or height < SIZE[1]
                or not width.is_integer() or not height.is_integer()
                or width * height * 4 > MAX_DECODED_BYTES):
            raise ValueError('canvas must fit the native viewport and decoded 50MB limit')
        if _pair(_field(manifest, 'viewport'), 'viewport') != SIZE:
            raise ValueError('viewport must be native 480x320')
        if ('decoded_rgba_bytes' in manifest and
                _number(manifest['decoded_rgba_bytes'], 'decoded_rgba_bytes') != width * height * 4):
            raise ValueError('decoded_rgba_bytes disagrees with canvas')

        self._camera = tuple(_pair(p, 'camera_path') for p in
                             _sequence(_field(manifest, 'camera_path'), 'camera_path'))
        self._tiles = tuple(_pair(p, 'route_tile_points') for p in
                            _sequence(_field(manifest, 'route_tile_points'), 'route_tile_points'))
        self._arcs = tuple(_number(d, 'route_arc_distances_tiles') for d in
                           _sequence(_field(manifest, 'route_arc_distances_tiles'),
                                     'route_arc_distances_tiles'))
        if len(self._arcs) < 2 or not len(self._camera) == len(self._tiles) == len(self._arcs):
            raise ValueError('camera, tile and arc tracks must have matching lengths >= 2')
        if self._arcs[0] != 0 or any(b <= a for a, b in zip(self._arcs, self._arcs[1:])):
            raise ValueError('canonical arc distances must start at zero and strictly increase')
        self._length = self._arcs[-1]
        if ('route_length_tiles' in manifest and
                _number(manifest['route_length_tiles'], 'route_length_tiles') != self._length):
            raise ValueError('route_length_tiles disagrees with canonical distance track')
        for key, point in (('camera_junction', self._camera[0]),
                           ('camera_bridge', self._camera[-1])):
            if _pair(_field(manifest, key), key) != point:
                raise ValueError(f'{key} disagrees with camera_path endpoint')
        for key, point in (('junction_tile', self._tiles[0]), ('bridge_tile', self._tiles[-1])):
            if key in manifest and _pair(manifest[key], key) != point:
                raise ValueError(f'{key} disagrees with route_tile_points endpoint')
        if any(not (0 <= x <= width - SIZE[0] and 0 <= y <= height - SIZE[1])
               for x, y in self._camera):
            raise ValueError('camera viewport leaves panorama bounds')

        projection = _field(manifest, 'projection')
        if not isinstance(projection, Mapping):
            raise ValueError('projection must be a mapping')
        origin = _pair(_field(projection, 'origin_tiles'), 'origin_tiles')
        scale = _pair(_field(projection, 'pixels_per_tile'), 'pixels_per_tile')
        offset = _pair(projection.get('offset_pixels', (0, 0)), 'offset_pixels')
        if min(scale) <= 0:
            raise ValueError('pixels_per_tile must be positive')
        projected = tuple(((x - origin[0]) * scale[0] + offset[0],
                           (y - origin[1]) * scale[1] + offset[1]) for x, y in self._tiles)
        if any(not (0 <= x < width and 0 <= y < height) for x, y in projected):
            raise ValueError('geographic route leaves panorama bounds')

        reference = manifest.get('road_reference_in_viewport')
        if reference is not None:
            if not isinstance(reference, Mapping):
                raise ValueError('road_reference_in_viewport must be a mapping')
            start = _pair(_field(reference, 'from'), 'road reference from')
            end = _pair(_field(reference, 'to'), 'road reference to')
            if any(not (0 <= p[0] < SIZE[0] and 0 <= p[1] < SIZE[1]) for p in (start, end)):
                raise ValueError('road reference leaves viewport')
            for camera, tile_pixel, distance in zip(self._camera, projected, self._arcs):
                f = distance / self._length
                if any(abs(tile_pixel[i] - camera[i] - (start[i] + (end[i] - start[i]) * f))
                       > 0.00001 for i in (0, 1)):
                    raise ValueError('camera and geographic route disagree with road reference')

        slopes = []
        for i, (a, b) in enumerate(zip(self._camera, self._camera[1:])):
            span = self._arcs[i + 1] - self._arcs[i]
            chord = math.dist(self._tiles[i], self._tiles[i + 1])
            speed = math.dist(a, b) / span
            if chord == 0 or chord > span + 0.000001 or speed == 0 or not math.isfinite(speed):
                raise ValueError('route segments must move with consistent finite arc distances')
            slopes.append(speed)
        self._peak_speed = max(slopes) * self._length * 1.875
        if not math.isfinite(self._peak_speed):
            raise ValueError('route must yield finite camera velocities')

    def _endpoint(self, end: bool) -> RoadPanSample:
        index = -1 if end else 0
        return RoadPanSample(self._camera[index], self._tiles[index], float(end),
                             self._arcs[index], (0., 0.), (0., 0.), 0., 0., 0, False)

    def sample(self, seconds: float, duration: float = .8,
               reduced_motion: bool = False) -> RoadPanSample:
        """Sample elapsed phase seconds; finite negative/late times clamp exactly.

        Duration must be positive, finite and support finite pixel velocities.
        Reduced Motion is an immediate bridge cut at ANY finite time, with
        progress 1, zero velocity/effects and inactive state. No input is stored.
        """
        seconds = _number(seconds, 'seconds')
        duration = _number(duration, 'duration')
        if duration <= 0 or not math.isfinite(self._peak_speed / duration):
            raise ValueError('duration must be positive and yield finite camera velocities')
        if not isinstance(reduced_motion, bool):
            raise ValueError('reduced_motion must be a bool')
        if reduced_motion or seconds >= duration:
            return self._endpoint(True)
        if seconds <= 0:
            return self._endpoint(False)

        t = seconds / duration
        # Symmetry avoids quintic cancellation/overshoot near the bridge.
        u = min(t, 1. - t)
        ease = u * u * u * (10. + u * (-15. + 6. * u))
        progress = ease if t <= .5 else 1. - ease
        distance = progress * self._length
        index = min(len(self._arcs) - 2, bisect_right(self._arcs, distance) - 1)
        span = self._arcs[index + 1] - self._arcs[index]
        f = (distance - self._arcs[index]) / span

        def interpolate(track: tuple[Point, ...]) -> Point:
            a, b = track[index], track[index + 1]
            if f == 0:
                return a
            if f == 1:
                return b
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f

        strength = 16. * t * t * (1. - t) * (1. - t)
        arc_rate = self._length * (1.875 * strength / duration)
        a, b = self._camera[index], self._camera[index + 1]
        velocity = ((b[0] - a[0]) / span * arc_rate,
                    (b[1] - a[1]) / span * arc_rate)
        speed = math.hypot(*velocity)
        direction = (-velocity[0] / speed, -velocity[1] / speed) if speed else (0., 0.)
        return RoadPanSample(interpolate(self._camera), interpolate(self._tiles), progress,
                             distance, velocity, direction, strength, MAX_BLUR_PX * strength,
                             sum(_streak_alpha(strength, i) > 0 for i in range(MAX_STREAKS)), True)

    @staticmethod
    def _blur(source: pygame.Surface, target: pygame.Surface, state: RoadPanSample) -> None:
        alpha = round(144 * state.strength)
        if not alpha:
            return
        rgb = pygame.surfarray.pixels3d(source)
        output = pygame.surfarray.pixels3d(target)
        try:
            total = np.zeros(rgb.shape, dtype=np.uint16)
            x, y = np.arange(SIZE[0]), np.arange(SIZE[1])
            for i, weight in enumerate(_WEIGHTS):
                offset = state.blur_px * (i / (BLUR_TAPS - 1) - .5)
                dx, dy = (round(offset * component) for component in state.screen_motion_direction)
                # Sample the nearest source edge, including corners. No empty
                # shifted rectangles, panorama copies, wrapping or black fringe.
                xs, ys = np.clip(x - dx, 0, SIZE[0] - 1), np.clip(y - dy, 0, SIZE[1] - 1)
                total += np.multiply(rgb[xs[:, None], ys[None, :]], weight, dtype=np.uint16)
            total += 32
            total //= 64
            total *= alpha
            total += np.multiply(rgb, 255 - alpha, dtype=np.uint16)
            total += 127
            total //= 255
            output[:] = total
        finally:
            del output, rgb  # Release pygame locks before any blit/UI handoff.

    @staticmethod
    def _streaks(layer: pygame.Surface, state: RoadPanSample) -> None:
        sign = -1 if state.screen_motion_direction[0] < 0 else 1
        slope = max(-.12, min(.12, state.screen_motion_direction[1] /
                             max(.001, abs(state.screen_motion_direction[0]))))
        for i in range(MAX_STREAKS):
            alpha = _streak_alpha(state.strength, i)
            if not alpha:
                continue
            # Fixed integer/index layout plus continuous sine drift: no RNG,
            # frame-counter reseeding, wraparound or time-quantized flicker.
            x = 96 + (i * 73 + 19) % 288 + 14 * math.sin(math.pi * state.progress + i * 1.7)
            y = 24 + (i * 47 + 7) % 268
            length = (48 + (i * 31) % 57) * (.5 + .5 * state.strength)
            dx, dy = sign * length / 2, slope * length / 2
            tail, tip = (round(x - dx), round(y - dy)), (round(x + dx), round(y + dy))
            shoulder = (round(tip[0] - sign * 8), round(tip[1] - slope * 8))
            pygame.draw.polygon(layer, (232, 241, 220, alpha),
                                (tail, (shoulder[0], shoulder[1] - 1), tip,
                                 (shoulder[0], shoulder[1] + 1)))

    def apply(self, canvas: pygame.Surface, sample_or_seconds: RoadPanSample | float,
              duration: float = .8, reduced_motion: bool = False) -> pygame.Surface:
        """Return a NEW native scenery frame; never mutate source or draw UI.

        Accept a state from ``sample`` or elapsed seconds with the same options.
        Draw UI onto the returned frame AFTER this pass. Endpoint/reduced-motion
        copies preserve source pixels exactly, including alpha. No display or
        mixer initialization is required. Input should be 24/32-bit scenery.
        """
        if canvas.get_size() != SIZE or canvas.get_bitsize() not in (24, 32):
            raise ValueError('canvas must be a native 480x320 24/32-bit surface')
        if not isinstance(reduced_motion, bool):
            raise ValueError('reduced_motion must be a bool')
        state = (sample_or_seconds if isinstance(sample_or_seconds, RoadPanSample)
                 else self.sample(sample_or_seconds, duration, reduced_motion))
        result = canvas.copy()
        if reduced_motion or not state.active or state.strength == 0:
            return result
        result.set_clip(None)
        self._blur(canvas, result, state)
        if state.streak_count:
            layer = pygame.Surface(SIZE, pygame.SRCALPHA, 32)
            self._streaks(layer, state)
            result.blit(layer, (0, 0))
        result.set_clip(canvas.get_clip())
        return result