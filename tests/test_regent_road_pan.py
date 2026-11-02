"""Isolated road sampler/effects tests: real manifest, no Game or scene edits."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import math
import os
from pathlib import Path
import random
import sys
import tracemalloc
import unittest
from unittest.mock import patch

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pygame

from regent_road_pan import (BLUR_TAPS, MAX_BLUR_PX, MAX_DECODED_BYTES,
                             MAX_STREAKS, SIZE, RoadPanSample, RoadWhipPan)


ASSETS = ROOT / 'assets/story/regent_arrival/crossroads'


def interpolate(distance, distances, points):
    """Independent reference using the manifest's canonical distance labels."""
    return tuple(float(np.interp(distance, distances, [p[i] for p in points])) for i in (0, 1))


def time_for_progress(progress, duration=.8):
    """Invert the easing independently to exercise every real track knot."""
    low, high = 0., 1.
    for _ in range(60):
        t = (low + high) / 2
        ease = 6 * t ** 5 - 15 * t ** 4 + 10 * t ** 3
        if ease < progress:
            low = t
        else:
            high = t
    return duration * (low + high) / 2


def distance_to_segment(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    f = max(0., min(1., ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) /
                       (dx * dx + dy * dy)))
    return math.hypot(point[0] - a[0] - f * dx, point[1] - a[1] - f * dy)


def pixels(surface):
    return pygame.image.tobytes(surface, 'RGBA')


def patterned_surface(*, alpha=False, depth=32):
    surface = pygame.Surface(SIZE, pygame.SRCALPHA if alpha else 0, depth)
    x, y = np.indices(SIZE)
    array = np.stack(((x * 19 + y * 3) % 251, (x * 7 + y * 23) % 253,
                      (x * 11 + y * 13) % 255), axis=2).astype(np.uint8)
    pygame.surfarray.blit_array(surface, array)
    if alpha:
        view = pygame.surfarray.pixels_alpha(surface)
        view[:] = (x + y * 3) % 256
        del view
    return surface


class RoadWhipPanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ASSETS / 'manifest.json').read_text(encoding='utf-8'))
        cls.pan = RoadWhipPan(cls.manifest)

    def assertPointAlmostEqual(self, actual, expected, places=7):
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=places)

    def test_actual_manifest_contract_and_exact_clamped_endpoints(self):
        self.assertEqual(self.manifest['canvas'], [4928, 1728])
        self.assertEqual(len(self.manifest['camera_path']), 124)
        for seconds in (-100., -0., 0.):
            state = self.pan.sample(seconds)
            self.assertEqual(state.camera_position, (3734., 623.))
            self.assertEqual(state.tile_position, (7., 4.))
            self.assertEqual((state.progress, state.arc_distance_tiles), (0., 0.))
            self.assertEqual((state.strength, state.blur_px, state.streak_count), (0., 0., 0))
            self.assertEqual(state.camera_velocity, (0., 0.))
            self.assertEqual(state.screen_motion_direction, (0., 0.))
            self.assertFalse(state.active)
        for seconds in (.8, 1., 1e100):
            state = self.pan.sample(seconds)
            self.assertEqual(state.camera_position, (432., 1203.))
            self.assertEqual(state.tile_position, (-111., 29.))
            self.assertEqual((state.progress, state.arc_distance_tiles), (1., 122.06790536))
            self.assertEqual((state.strength, state.blur_px, state.streak_count), (0., 0., 0))
            self.assertEqual(state.camera_velocity, (0., 0.))
            self.assertFalse(state.active)
        self.assertNotEqual(self.pan.sample(1).tile_position,
                            tuple(self.manifest['bridge_world_anchor_tile']))

    def test_quintic_acceleration_and_normalized_arc_velocity_envelope(self):
        states = [self.pan.sample(.8 * f) for f in (0., .1, .25, .5, .75, .9, 1.)]
        self.assertEqual(states[3].progress, .5)
        self.assertEqual(states[3].strength, 1.)
        self.assertEqual(states[3].blur_px, 48.)
        self.assertEqual(states[3].streak_count, MAX_STREAKS)
        self.assertTrue(states[1].strength < states[2].strength < states[3].strength)
        self.assertTrue(states[3].strength > states[4].strength > states[5].strength)
        self.assertLess(states[1].progress, .1)
        self.assertGreater(states[5].progress, .9)
        for i in range(1, 200):
            t = i / 200
            state = self.pan.sample(t * .8)
            self.assertAlmostEqual(state.progress, 6 * t ** 5 - 15 * t ** 4 + 10 * t ** 3)
            self.assertAlmostEqual(state.strength, 30 * t * t * (1 - t) ** 2 / 1.875)
            self.assertTrue(state.active)
            self.assertTrue(0 < state.strength <= 1)

    def test_duration_changes_velocity_not_geography_or_normalized_effects(self):
        for fraction in (.01, .1, .34, .5, .88, .99):
            short = self.pan.sample(.8 * fraction)
            long = self.pan.sample(3.2 * fraction, 3.2)
            self.assertEqual(short.camera_position, long.camera_position)
            self.assertEqual(short.tile_position, long.tile_position)
            self.assertEqual(short.strength, long.strength)
            self.assertEqual(short.blur_px, long.blur_px)
            self.assertEqual(short.screen_motion_direction, long.screen_motion_direction)
            self.assertPointAlmostEqual(short.camera_velocity, tuple(v * 4 for v in long.camera_velocity))
        self.assertEqual(self.pan.sample(3.2, 3.2).camera_position, (432., 1203.))

    def test_every_actual_camera_and_tile_knot_uses_the_canonical_distance_track(self):
        arcs = self.manifest['route_arc_distances_tiles']
        for distance, camera, tile in zip(arcs, self.manifest['camera_path'],
                                          self.manifest['route_tile_points']):
            with self.subTest(distance=distance):
                state = self.pan.sample(time_for_progress(distance / arcs[-1]))
                self.assertAlmostEqual(state.arc_distance_tiles, distance, places=7)
                self.assertPointAlmostEqual(state.camera_position, camera, places=6)
                self.assertPointAlmostEqual(state.tile_position, tile)

    def test_supplied_arc_distances_are_not_recomputed_resampled_chords(self):
        route = self.manifest['route_tile_points']
        arcs = self.manifest['route_arc_distances_tiles']
        chord_arcs = [0.]
        for a, b in zip(route, route[1:]):
            chord_arcs.append(chord_arcs[-1] + math.dist(a, b))
        self.assertGreater(arcs[-1] - chord_arcs[-1], .5)
        state = self.pan.sample(time_for_progress(.88))
        expected = interpolate(state.progress * arcs[-1], arcs, route)
        wrong = interpolate(state.progress * chord_arcs[-1], chord_arcs, route)
        self.assertPointAlmostEqual(state.tile_position, expected, places=12)
        self.assertGreater(math.dist(state.tile_position, wrong), .4)
        straight = tuple(a + (b - a) * state.progress for a, b in zip(route[0], route[-1]))
        self.assertGreater(math.dist(state.tile_position, straight), 1.)

    def test_full_pan_stays_on_road_and_inside_native_panorama_bounds(self):
        m = self.manifest
        projection = m['projection']
        source = m['road_source_tile_points']
        last_x, last_distance = math.inf, -1.
        for i in range(801):
            state = self.pan.sample(.8 * i / 800)
            x, y = state.camera_position
            self.assertTrue(0 <= x <= m['canvas'][0] - SIZE[0])
            self.assertTrue(0 <= y <= m['canvas'][1] - SIZE[1])
            self.assertLessEqual(x, last_x)
            self.assertGreaterEqual(state.arc_distance_tiles, last_distance)
            self.assertPointAlmostEqual(state.camera_position,
                                       interpolate(state.arc_distance_tiles,
                                                   m['route_arc_distances_tiles'], m['camera_path']))
            self.assertPointAlmostEqual(state.tile_position,
                                       interpolate(state.arc_distance_tiles,
                                                   m['route_arc_distances_tiles'], m['route_tile_points']))
            # Literal arc-sample interpolation stays within a quarter tile of
            # the source centerline (road half-width is 1.25 tiles), including
            # the retained short bridge-approach bend; not an endpoint chord.
            self.assertLess(min(distance_to_segment(state.tile_position, a, b)
                                for a, b in zip(source, source[1:])), .26)
            for axis, (camera, tile) in enumerate(zip(state.camera_position, state.tile_position)):
                pixel = ((tile - projection['origin_tiles'][axis]) *
                         projection['pixels_per_tile'][axis] + projection['offset_pixels'][axis])
                reference = m['road_reference_in_viewport']
                anchor = reference['from'][axis] + (reference['to'][axis] - reference['from'][axis]) * state.progress
                self.assertAlmostEqual(pixel - camera, anchor, places=5)
            last_x, last_distance = x, state.arc_distance_tiles

    def test_velocity_matches_local_derivative_including_bridge_y_sign_change(self):
        arcs = self.manifest['route_arc_distances_tiles']
        positive_y = negative_y = False
        for a, b in zip(arcs, arcs[1:]):
            seconds = time_for_progress((a + b) / (2 * arcs[-1]))
            state = self.pan.sample(seconds)
            before, after = self.pan.sample(seconds - 1e-8), self.pan.sample(seconds + 1e-8)
            numerical = tuple((y - x) / 2e-8 for x, y in
                              zip(before.camera_position, after.camera_position))
            np.testing.assert_allclose(state.camera_velocity, numerical, rtol=2e-5, atol=.0002)
            self.assertLess(state.camera_velocity[0], 0)
            self.assertGreater(state.screen_motion_direction[0], 0)
            self.assertAlmostEqual(math.hypot(*state.screen_motion_direction), 1.)
            speed = math.hypot(*state.camera_velocity)
            self.assertPointAlmostEqual(state.screen_motion_direction,
                                       tuple(-v / speed for v in state.camera_velocity))
            positive_y |= state.camera_velocity[1] > 0
            negative_y |= state.camera_velocity[1] < 0
        self.assertTrue(positive_y and negative_y)

    def test_reduced_motion_is_an_immediate_bridge_cut_for_every_time(self):
        expected = self.pan.sample(.8)
        for duration in (.01, .8, 50.):
            for seconds in (-100., 0., duration / 2, duration, 1e100):
                self.assertEqual(self.pan.sample(seconds, duration, True), expected)

    def test_samples_are_immutable_and_detached_from_later_manifest_edits(self):
        manifest = deepcopy(self.manifest)
        pan = RoadWhipPan(manifest)
        expected = pan.sample(.4)
        with self.assertRaises(FrozenInstanceError):
            setattr(expected, 'strength', .2)
        manifest['camera_path'][50][0] = -999
        manifest['route_tile_points'][50][1] = -999
        manifest['route_arc_distances_tiles'][50] = -999
        self.assertEqual(pan.sample(.4), expected)

    def test_pause_and_out_of_order_sampling_have_no_history_or_clock(self):
        expected = self.pan.sample(.319)
        source = patterned_surface()
        expected_pixels = pixels(self.pan.apply(source, expected))
        with patch('pygame.time.get_ticks', side_effect=AssertionError('wall clock used')), \
             patch('time.monotonic', side_effect=AssertionError('wall clock used')), \
             patch('time.perf_counter', side_effect=AssertionError('wall clock used')):
            for seconds in (.7, .1, .319, 10., -.5, .001, .5):
                self.pan.sample(seconds)
                self.pan.apply(source, seconds)
                self.assertEqual(self.pan.sample(.319), expected)
                self.assertEqual(pixels(self.pan.apply(source, .319)), expected_pixels)
        # The parent pauses by retaining its phase time, not by calling an
        # update/pause hook here. Repeated draws of that time cannot advance it.
        self.assertEqual(self.pan.sample(.319), expected)

    def test_sampling_and_drawing_do_not_touch_python_or_numpy_rng(self):
        python_before, numpy_before = random.getstate(), np.random.get_state()
        source = patterned_surface()
        for seconds in (0., .1, .3, .4, .7, .8):
            self.pan.sample(seconds)
            self.pan.apply(source, seconds)
        self.assertEqual(random.getstate(), python_before)
        numpy_after = np.random.get_state()
        self.assertEqual(numpy_before[0], numpy_after[0])
        np.testing.assert_array_equal(numpy_before[1], numpy_after[1])
        self.assertEqual(numpy_before[2:], numpy_after[2:])

    def test_constructor_and_sampler_allocate_no_images_or_load_any_assets(self):
        with patch('pygame.image.load', side_effect=AssertionError('asset load')), \
             patch('pygame.Surface', side_effect=AssertionError('image allocation')), \
             patch('pygame.display.set_mode', side_effect=AssertionError('display init')), \
             patch('pygame.mixer.init', side_effect=AssertionError('audio init')):
            pan = RoadWhipPan(self.manifest)
            for seconds in (-1., 0., .2, .4, .8, 1.):
                self.assertIsInstance(pan.sample(seconds), RoadPanSample)
        for name in RoadWhipPan.__slots__:
            value = getattr(pan, name)
            self.assertNotIsInstance(value, (pygame.Surface, np.ndarray, Mapping))

    def test_renderer_requires_no_display_audio_or_initialization_calls(self):
        source = patterned_surface()
        before = (pygame.get_init(), pygame.display.get_init(), pygame.mixer.get_init())
        with patch('pygame.init', side_effect=AssertionError('pygame init')), \
             patch('pygame.display.init', side_effect=AssertionError('display init')), \
             patch('pygame.display.set_mode', side_effect=AssertionError('window created')), \
             patch('pygame.mixer.init', side_effect=AssertionError('mixer init')), \
             patch('pygame.mixer.Sound', side_effect=AssertionError('sound loaded')), \
             patch('pygame.mixer.music.load', side_effect=AssertionError('music loaded')):
            result = self.pan.apply(source, .4)
            self.assertNotEqual(pixels(result), pixels(source))
        self.assertEqual((pygame.get_init(), pygame.display.get_init(), pygame.mixer.get_init()), before)

    def test_nonfinite_or_nonnumeric_times_and_invalid_durations_are_rejected(self):
        invalid = (math.nan, math.inf, -math.inf, None, '0.4', True, 10 ** 1000)
        source = patterned_surface()
        for value in invalid:
            with self.subTest(time=repr(value)[:50]):
                for reduced in (False, True):
                    with self.assertRaises(ValueError):
                        self.pan.sample(value, reduced_motion=reduced)
                    with self.assertRaises(ValueError):
                        self.pan.apply(source, value, reduced_motion=reduced)
        for value in (*invalid, 0., -.8, math.ulp(0.)):
            with self.subTest(duration=repr(value)[:50]):
                for reduced in (False, True):
                    with self.assertRaises(ValueError):
                        self.pan.sample(.4, value, reduced)
        with self.assertRaises(ValueError):
            self.pan.sample(.4, reduced_motion='yes')

    def test_finite_extreme_valid_times_and_durations_never_produce_nan(self):
        for duration in (1e-250, .8, 1e250):
            for fraction in (0., 1e-12, .5, 1 - 1e-12, 1.):
                state = self.pan.sample(duration * fraction, duration)
                for value in (*state.camera_position, *state.tile_position, *state.camera_velocity,
                              *state.screen_motion_direction, state.progress, state.strength, state.blur_px):
                    self.assertTrue(math.isfinite(value))
                self.assertTrue(0 <= state.progress <= 1)

    def test_invalid_manifest_shape_and_track_data_are_rejected(self):
        cases = [
            ('camera_path', []), ('camera_path', [[0, 0]]), ('camera_path', 'invalid'),
            ('route_tile_points', []), ('route_arc_distances_tiles', []),
            ('camera_junction', [0, 0]), ('camera_bridge', [0, 0]),
            ('junction_tile', [8, 4]), ('bridge_tile', [-111, 30]),
            ('canvas', [479, 320]), ('canvas', [4928.5, 1728]), ('canvas', [10000, 10000]),
            ('viewport', [960, 640]), ('decoded_rgba_bytes', 1),
            ('route_length_tiles', 121), ('projection', None),
            ('road_reference_in_viewport', []),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                manifest = deepcopy(self.manifest)
                manifest[key] = value
                with self.assertRaises(ValueError):
                    RoadWhipPan(manifest)
        for key in ('canvas', 'viewport', 'camera_path', 'route_tile_points',
                    'route_arc_distances_tiles', 'camera_junction', 'camera_bridge', 'projection'):
            manifest = deepcopy(self.manifest)
            del manifest[key]
            with self.assertRaisesRegex(ValueError, 'missing'):
                RoadWhipPan(manifest)
        for manifest in (None, [], 'manifest.json'):
            with self.assertRaises(ValueError):
                RoadWhipPan(manifest)

    def test_nonfinite_out_of_bounds_duplicate_and_misregistered_route_data_rejected(self):
        def mutate(path, value):
            manifest = deepcopy(self.manifest)
            target = manifest
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            return manifest

        for path, values in (
                (('camera_path', 25, 0), (math.nan, math.inf, -1, 4449, '20', True)),
                (('camera_path', 25, 1), (-1, 1409)),
                (('route_tile_points', 25, 0), (math.nan, -10000, 10000)),
                (('route_arc_distances_tiles', 25), (math.nan, math.inf, 0, -1)),
                (('route_arc_distances_tiles', 0), (.1,)),
                (('projection', 'pixels_per_tile', 0), (0, -28, math.nan)),
                (('road_reference_in_viewport', 'from', 0), (480, math.inf)),
                (('camera_path', 25), ([0, 0], [1, 2, 3])),
                (('route_tile_points', 25), (self.manifest['route_tile_points'][24],)),
                (('route_arc_distances_tiles', 25), (self.manifest['route_arc_distances_tiles'][24],))):
            for value in values:
                with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                    RoadWhipPan(mutate(path, value))

    def test_effects_are_new_surfaces_and_do_not_mutate_source_pixels_or_metadata(self):
        source = patterned_surface(alpha=True)
        source.set_alpha(177)
        source.set_colorkey((1, 2, 3))
        source.set_clip((30, 40, 100, 120))
        before = (pixels(source), source.get_alpha(), source.get_colorkey(), source.get_clip(),
                  source.get_flags(), source.get_locked())
        for seconds in (0., .2, .4, .7, .8):
            result = self.pan.apply(source, seconds)
            self.assertIsNot(result, source)
            self.assertEqual(result.get_size(), SIZE)
            self.assertFalse(result.get_locked())
            self.assertEqual(before, (pixels(source), source.get_alpha(), source.get_colorkey(),
                                      source.get_clip(), source.get_flags(), source.get_locked()))

    def test_endpoint_and_reduced_motion_source_pixels_are_identical(self):
        for source in (patterned_surface(), patterned_surface(alpha=True), patterned_surface(depth=24)):
            before = pixels(source)
            for seconds in (-1., 0., .8, 100.):
                self.assertEqual(pixels(self.pan.apply(source, seconds)), before)
            for seconds in (-1., 0., .4, .8, 100.):
                state = self.pan.sample(seconds, reduced_motion=True)
                self.assertEqual(pixels(self.pan.apply(source, state)), before)
                self.assertEqual(pixels(self.pan.apply(source, seconds, reduced_motion=True)), before)
            self.assertEqual(pixels(self.pan.apply(source, self.pan.sample(.4), reduced_motion=True)), before)

    def test_actual_bridge_panorama_crop_is_exact_under_reduced_motion(self):
        panorama = pygame.image.load(str(ASSETS / self.manifest['background']))
        self.assertEqual(panorama.get_size(), (4928, 1728))
        state = self.pan.sample(0., reduced_motion=True)
        source = pygame.Surface(SIZE)
        source.blit(panorama, (0, 0), (*state.camera_position, *SIZE))
        del panorama
        self.assertEqual(pixels(self.pan.apply(source, state)), pixels(source))

    def test_active_blur_is_seven_edge_clamped_taps_with_a_velocity_alpha_envelope(self):
        source = patterned_surface()
        state = self.pan.sample(.4)
        result = self.pan.apply(source, state)
        # The six sparse foreground streaks occupy neither this row nor its
        # immediate neighbors. Independently compute the actual scenery pass.
        rgb = pygame.surfarray.array3d(source)
        actual = pygame.surfarray.array3d(result)
        weights = (1, 6, 15, 20, 15, 6, 1)
        self.assertEqual(BLUR_TAPS, len(weights))
        self.assertLessEqual(state.blur_px, MAX_BLUR_PX)
        alpha = round(144 * state.strength)
        for x in (0, 1, 24, 110, 240, 455, 478, 479):
            y = 180
            total = np.zeros(3, dtype=np.uint16)
            for i, weight in enumerate(weights):
                offset = state.blur_px * (i / 6 - .5)
                dx, dy = [round(offset * component) for component in state.screen_motion_direction]
                total += rgb[max(0, min(479, x - dx)), max(0, min(319, y - dy))].astype(np.uint16) * weight
            expected = (((total + 32) // 64 * alpha + rgb[x, y].astype(np.uint16) *
                         (255 - alpha) + 127) // 255).astype(np.uint8)
            np.testing.assert_array_equal(actual[x, y], expected)
        self.assertNotEqual(pixels(result), pixels(source))

    def test_blur_matches_float64_weighted_convolution_on_alternating_stripes(self):
        x = np.arange(SIZE[0])
        # Different stripe periods avoid aliasing with the peak's eight-pixel
        # tap spacing. Solid ends also exercise maximum sums and edge clamping.
        stripes = np.column_stack(((x // 7 % 2) * 255,
                                   ((x + 3) // 11 % 2) * 255,
                                   ((x + 5) // 13 % 2) * 255)).astype(np.float64)
        stripes[:48] = 255
        stripes[-48:] = 0
        source = pygame.Surface(SIZE)
        pygame.surfarray.blit_array(source,
            np.repeat(stripes[:, None, :], SIZE[1], axis=1).astype(np.uint8))
        for seconds in (0., .04, .2, .4, .6, .76, .8):
            with self.subTest(seconds=seconds):
                state = self.pan.sample(seconds)
                # Vertical stripes reduce the real directional blur to a 1D
                # convolution. Derive a binomial kernel independently; do not
                # import the helper's weights or mirror its uint16 arithmetic.
                offsets = np.rint(np.linspace(-state.blur_px / 2, state.blur_px / 2, 7) *
                                  state.screen_motion_direction[0]).astype(int)
                radius = int(np.max(np.abs(offsets)))
                kernel = np.zeros(2 * radius + 1, dtype=np.float64)
                for i, offset in enumerate(offsets):
                    kernel[radius + offset] += math.comb(6, i) / 64
                convolved = np.column_stack([
                    np.convolve(np.pad(stripes[:, channel], radius, mode='edge'),
                                kernel, mode='valid') for channel in range(3)])
                # Match the specified half-up rounding at BOTH stages, using
                # float64 throughout so an integer overflow cannot self-confirm.
                averaged = np.floor(convolved + .5)
                alpha = round(144 * state.strength)
                expected = np.floor((averaged * alpha + stripes * (255 - alpha)) /
                                    255 + .5).astype(np.uint8)
                target = source.copy()
                self.pan._blur(source, target, state)
                np.testing.assert_array_equal(pygame.surfarray.array3d(target),
                    np.repeat(expected[:, None, :], SIZE[1], axis=1))
                if seconds == .4:
                    self.assertFalse(np.array_equal(expected, stripes))

    def test_directional_blur_changes_expected_pixels_not_distant_rows(self):
        source = pygame.Surface(SIZE)
        source.fill((80, 110, 140))
        source.set_at((240, 180), (255, 255, 255))
        rgb = pygame.surfarray.array3d(self.pan.apply(source, .4))
        changed = np.any(rgb != (80, 110, 140), axis=2)
        # Away from the sparse streaks, one impulse spreads along the camera
        # tangent only; it cannot smear an unrelated distant patch or UI.
        self.assertGreater(np.count_nonzero(changed[210:271, 170:191]), 1)
        self.assertFalse(np.any(changed[210:271, 160:167]))
        self.assertFalse(np.any(changed[0:40, 175:185]))

    def test_edge_clamping_has_no_black_fringes_including_all_four_corners(self):
        source = pygame.Surface(SIZE)
        source.fill((91, 122, 147))
        for seconds in (.2, .4, time_for_progress(.95)):
            result = self.pan.apply(source, seconds)
            actual = pygame.surfarray.array3d(result)
            for x in (0, 1, 478, 479):
                np.testing.assert_array_equal(actual[x], np.tile((91, 122, 147), (320, 1)))
            for y in (0, 1, 318, 319):
                np.testing.assert_array_equal(actual[:, y], np.tile((91, 122, 147), (480, 1)))
            self.assertGreaterEqual(int(actual.min()), 91)

    def test_streak_diagnostics_are_real_sparse_horizontal_tapered_polygons(self):
        source = pygame.Surface(SIZE)
        source.fill((90, 110, 120))
        for seconds in (0., .01, .2, .4, .7, .8):
            state = self.pan.sample(seconds)
            with patch('pygame.draw.polygon', wraps=pygame.draw.polygon) as polygon:
                self.pan.apply(source, state)
                self.assertEqual(polygon.call_count, state.streak_count)
                self.assertLessEqual(polygon.call_count, 6)
                for call in polygon.call_args_list:
                    _, color, points = call.args
                    self.assertGreater(color[3], 0)
                    self.assertLessEqual(color[3], 64)
                    self.assertEqual(len(points), 4)
                    width = max(x for x, y in points) - min(x for x, y in points)
                    height = max(y for x, y in points) - min(y for x, y in points)
                    self.assertGreater(width, height * 3)
                    self.assertLessEqual(height, 15)
                    self.assertGreater(points[2][0], points[0][0])

    def test_repeated_draws_and_sample_vs_seconds_calls_are_pixel_identical(self):
        source = patterned_surface()
        before = pixels(source)
        for seconds in (.1, .319, .4, .6, .79):
            state = self.pan.sample(seconds)
            expected = pixels(self.pan.apply(source, state))
            for _ in range(3):
                self.assertEqual(pixels(self.pan.apply(source, seconds)), expected)
                self.assertEqual(pixels(RoadWhipPan(self.manifest).apply(source, state)), expected)
            self.assertEqual(pixels(source), before)

    def test_apply_seconds_respects_custom_duration_and_shared_sample_contract(self):
        source = patterned_surface()
        for duration in (.2, .8, 3.2):
            for fraction in (0., .1, .5, .9, 1.):
                seconds = duration * fraction
                state = self.pan.sample(seconds, duration)
                self.assertEqual(pixels(self.pan.apply(source, seconds, duration)),
                                 pixels(self.pan.apply(source, state)))

    def test_close_clock_inputs_move_streaks_continuously_instead_of_flickering(self):
        source = pygame.Surface(SIZE)
        source.fill((90, 110, 120))
        a = pygame.surfarray.array3d(self.pan.apply(source, .4)).astype(np.int16)
        b = pygame.surfarray.array3d(self.pan.apply(source, .400001)).astype(np.int16)
        self.assertLess(np.count_nonzero(np.any(a != b, axis=2)), 100)
        self.assertLess(int(np.abs(a - b).max()), 10)

    def test_sharp_ui_is_drawn_by_parent_after_effects_without_helper_ui_code(self):
        source = patterned_surface()
        result = self.pan.apply(source, .4)
        self.assertNotEqual(pixels(result), pixels(source))
        # This small sharp "UI" represents the parent's later caption/skip pass.
        panel = pygame.Surface((130, 32))
        panel.fill((8, 18, 30))
        pygame.draw.line(panel, (255, 247, 215), (5, 9), (121, 9))
        pygame.draw.rect(panel, (255, 247, 215), (112, 16, 11, 10), 1)
        result.blit(panel, (12, 10))
        self.assertEqual(pixels(result.subsurface((12, 10, 130, 32))), pixels(panel))
        self.assertIn('then draw sharp UI', __import__('regent_road_pan').__doc__)

    def test_non_native_or_unsupported_effect_surfaces_are_rejected(self):
        for size in ((960, 640), (4928, 1), (479, 320)):
            with self.assertRaises(ValueError):
                self.pan.apply(pygame.Surface(size), .4)
        with self.assertRaises(ValueError):
            self.pan.apply(pygame.Surface(SIZE, depth=8), .4)

    def test_draw_allocations_are_native_bounded_and_do_not_retain_frames(self):
        source = patterned_surface()
        surface_constructor = pygame.Surface
        allocations = []

        def native_surface(size, *args, **kwargs):
            allocations.append(tuple(size))
            self.assertLessEqual(size[0], 480)
            self.assertLessEqual(size[1], 320)
            return surface_constructor(size, *args, **kwargs)

        tracemalloc.start()
        try:
            with patch('pygame.Surface', side_effect=native_surface), \
                 patch('pygame.image.load', side_effect=AssertionError('panorama loaded by helper')):
                for _ in range(12):
                    frame = self.pan.apply(source, .4)
                    self.assertEqual(frame.get_size(), SIZE)
                    self.assertFalse(frame.get_locked())
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(allocations, [SIZE] * 12)  # One streak layer, not a panorama or tap stack.
        self.assertLess(peak, 10_000_000)
        # Include the single parent-owned panorama and a conservative allowance
        # for five native SDL surfaces, whose C allocations tracemalloc may omit.
        self.assertLess(self.manifest['decoded_rgba_bytes'] + peak + 5 * 480 * 320 * 4,
                        MAX_DECODED_BYTES)
        for name in RoadWhipPan.__slots__:
            self.assertNotIsInstance(getattr(self.pan, name), (surface_constructor, np.ndarray))


if __name__ == '__main__':
    unittest.main()