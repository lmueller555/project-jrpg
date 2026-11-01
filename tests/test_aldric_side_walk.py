"""Aldric's cinematic side walk has authored support, swing and stable identity."""
import copy
import hashlib
import json
import math
from pathlib import Path
import unittest

import pygame
from PIL import Image

from regent_arrival import RegentArrival
from tools import build_aldric_side_walk as author


ROOT = Path(__file__).resolve().parents[1]
ACTOR = ROOT/'assets/story/regent_arrival/actors/aldric'
SOURCES = ROOT/'assets/source/cinematics/regent_arrival/actors'
SOURCE = SOURCES/'aldric_side_walk'
PHASES = ('near_contact', 'near_down', 'near_passing', 'near_up',
          'far_contact', 'far_down', 'far_passing', 'far_up')
BOB = (0, 1, 0, -1, 0, 1, 0, -1)
DISTANCE_PHASES = ((1, 0), (5, 1), (9, 2), (13, 3), (17, 4),
                   (21, 5), (25, 6), (29, 7), (33, 0))


def rgba(path):
    with Image.open(path) as image:
        return image.convert('RGBA')


class AldricSideWalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ACTOR/'animation.json').read_text())
        cls.side = json.loads((SOURCE/'side_walk.json').read_text())
        cls.scene_data = json.loads((ROOT/'assets/story/regent_arrival/scene.json').read_text())
        cls.sheet = rgba(SOURCE/cls.side['sheet'])
        cls.native = tuple(cls.sheet.crop((i*80, 0, (i+1)*80, 96)) for i in range(8))
        cls.images = tuple(rgba(ACTOR/frame['file'])
                           for frame in cls.manifest['loops']['walk_left'])
        cls.reference = rgba(ACTOR/cls.manifest['poses']['stand_left'])
        # PNG decoding needs neither a video mode nor Game/audio initialization.
        cls.art = {
            **cls.manifest,
            'poses': {pose: pygame.image.load(str(ACTOR/name))
                      for pose, name in cls.manifest['poses'].items()},
            'loops': {pose: [(pygame.image.load(str(ACTOR/frame['file'])),
                              frame['duration_ms']/1000) for frame in frames]
                      for pose, frames in cls.manifest['loops'].items()},
        }

    def setUp(self):
        self.scene = RegentArrival.__new__(RegentArrival)
        self.scene.data = copy.deepcopy(self.scene_data)
        self.scene.phase_index = 0
        self.scene.phase_time = 0.
        self.scene._reference_clock = None
        self.scene.actor_art = {'aldric': self.art}

    def actor(self, shot):
        self.scene.phase_index = next(i for i, phase in enumerate(self.scene.data['phases'])
                                      if phase['id'] == shot)
        return next(actor for actor in self.scene.phase['actors'] if actor['id'] == 'aldric')

    def assert_frame(self, actor, index, pose='walk_left'):
        self.assertIs(self.scene._frame(actor), self.art['loops'][pose][index][0])

    def test_side_walk_contains_a_complete_eight_phase_cycle(self):
        frames = self.manifest['loops']['walk_left']
        self.assertEqual(len(frames), 8)
        self.assertEqual(tuple(frame['phase'] for frame in frames), PHASES)
        self.assertTrue(all(frame['duration_ms'] == 125 for frame in frames))
        self.assertEqual(tuple(frame['file'] for frame in frames),
                         tuple(f'walk_{i}.png' for i in range(8)))
        self.assertEqual(frames, [{key: frame[key] for key in ('file', 'duration_ms', 'phase')}
                                  for frame in self.side['frames']])
        for manifest in (self.manifest, self.side):
            self.assertEqual(manifest['canvas'], [80, 96])
            self.assertEqual(manifest['anchor'], [40, 92])
        self.assertEqual(self.side['stride_pixels'], 32)
        self.assertEqual(self.manifest['gaits']['walk_left']['stride_pixels'], 32)

    def test_native_and_exported_frames_are_eight_distinct_binary_alpha_cells(self):
        self.assertEqual(self.sheet.size, (640, 96))
        for name, frames in (('native', self.native), ('runtime', self.images)):
            with self.subTest(asset=name):
                self.assertEqual(len(frames), 8)
                self.assertEqual(len({frame.tobytes() for frame in frames}), 8)
            for index, frame in enumerate(frames):
                with self.subTest(asset=name, phase=PHASES[index]):
                    self.assertEqual(frame.size, (80, 96))
                    self.assertEqual(set(frame.getchannel('A').tobytes()), {0, 255})

    def test_retained_head_pixels_follow_exact_declared_one_pixel_bob(self):
        self.assertEqual(hashlib.sha256(self.reference.tobytes()).hexdigest(),
                         self.side['reference_pixels_sha256'])
        self.assertEqual([frame['body_offset'] for frame in self.side['frames']],
                         [[0, bob] for bob in BOB])
        head = self.reference.crop((0, 0, 80, 30))
        self.assertIsNotNone(head.getbbox())
        for index, (frame, bob) in enumerate(zip(self.images, BOB)):
            with self.subTest(phase=PHASES[index]):
                # Compare the entire registered head region, including its
                # silhouette, not a rescaled crop or a few sampled face colors.
                self.assertEqual(frame.crop((0, bob, 80, 30+bob)).tobytes(), head.tobytes())
                self.assertEqual(frame.getbbox()[1], self.reference.getbbox()[1]+bob)

    def test_stored_leg_joints_preserve_both_seventeen_pixel_segments(self):
        self.assertEqual(self.side['leg_lengths'], [17., 17.])
        for frame in self.side['frames']:
            for side in ('near', 'far'):
                leg = frame[side+'_leg']
                with self.subTest(phase=frame['phase'], leg=side):
                    self.assertAlmostEqual(math.dist(leg['hip'], leg['knee']), 17., places=10)
                    self.assertAlmostEqual(math.dist(leg['knee'], leg['ankle']), 17., places=10)
                    self.assertEqual(leg['hip'], [41. if side == 'near' else 39.,
                                                  55.+frame['body_offset'][1]])

    def test_stored_arm_joints_preserve_upper_arm_and_forearm_lengths(self):
        self.assertEqual(self.side['arm_lengths'], [math.hypot(3, 11), 10.])
        for frame in self.side['frames']:
            for side in ('near', 'far'):
                arm = frame[side+'_arm']
                with self.subTest(phase=frame['phase'], arm=side):
                    self.assertAlmostEqual(math.dist(arm['shoulder'], arm['elbow']),
                                           math.hypot(3, 11), places=10)
                    self.assertAlmostEqual(math.dist(arm['elbow'], arm['wrist']), 10., places=10)
                    self.assertEqual(arm['shoulder'], [46. if side == 'near' else 34.,
                                                       33.+frame['body_offset'][1]])

    def test_contacts_alternate_feet_and_passing_silhouettes_are_narrow(self):
        widths = {}
        for index in (0, 2, 4, 6):
            record = self.side['frames'][index]
            alpha = self.images[index].getchannel('A')
            # Measure the painted boots below the coat, not declared bounds.
            columns = {x for x in range(80) for y in range(88, 92) if alpha.getpixel((x, y))}
            self.assertTrue(columns, PHASES[index])
            widths[index] = max(columns)-min(columns)+1
            with self.subTest(phase=PHASES[index]):
                if index in (0, 4):
                    self.assertGreaterEqual(widths[index], 28)
                    expected = (32, 48) if index == 0 else (48, 32)
                    self.assertEqual((record['near_leg']['ankle'][0],
                                      record['far_leg']['ankle'][0]), expected)
                    for side in ('near', 'far'):
                        leg = record[side+'_leg']
                        self.assertTrue(leg['planted'])
                        left, _, right, bottom = leg['foot_bounds']
                        self.assertEqual(bottom, 92)
                        self.assertTrue(any(alpha.getpixel((x, 91)) for x in range(left, right)))
                else:
                    self.assertLessEqual(widths[index], 14)
                    support, swing = ('near', 'far') if index == 2 else ('far', 'near')
                    self.assertTrue(record[support+'_leg']['planted'])
                    self.assertFalse(record[swing+'_leg']['planted'])
                    self.assertEqual(record['near_leg']['ankle'][0], 40)
                    self.assertEqual(record['far_leg']['ankle'][0], 40)
        self.assertLess(max(widths[2], widths[6]), min(widths[0], widths[4])*.5)

    def test_swing_boot_clearance_is_only_two_or_three_native_pixels(self):
        for index in (1, 2, 3, 5, 6, 7):
            record = self.side['frames'][index]
            support, swing = ('near', 'far') if index < 4 else ('far', 'near')
            planted = record[support+'_leg']
            lifted = record[swing+'_leg']
            alpha = self.images[index].getchannel('A')
            with self.subTest(phase=PHASES[index]):
                self.assertTrue(planted['planted'])
                self.assertFalse(lifted['planted'])
                self.assertEqual(planted['foot_bounds'][3], 92)
                self.assertIn(92-lifted['foot_bounds'][3], (2, 3))
                self.assertTrue(any(alpha.getpixel((x, 91)) for x in range(80)))
                self.assertIsNone(alpha.crop((0, 92, 80, 96)).getbbox())
                # Passing boots overlap. Down/up poses expose the swing toe
                # outside the support boot, so also measure its real raster floor.
                if index in (1, 5):
                    left = max(lifted['foot_bounds'][0], planted['foot_bounds'][2])
                    right = lifted['foot_bounds'][2]
                elif index in (3, 7):
                    left = lifted['foot_bounds'][0]
                    right = min(lifted['foot_bounds'][2], planted['foot_bounds'][0])
                else:
                    continue
                rows = [y for y in range(78, 96)
                        if any(alpha.getpixel((x, y)) for x in range(left, right))]
                self.assertTrue(rows)
                self.assertEqual(max(rows)+1, lifted['foot_bounds'][3])

    def test_support_ankle_world_x_is_locked_at_authored_keyframes(self):
        """Keyframe ankle lock does not promise zero sub-frame raster sliding."""
        actor = self.actor('gate_approach')
        start_x, start_y = actor['position']
        actor['to'] = [start_x-64, start_y]
        actor['move_seconds'] = 16.  # Four root pixels per authored phase.
        self.assertEqual(self.art['gaits']['walk_left']['stride_pixels'], 32)
        for first, side, offset in ((0, 'near', -8), (4, 'far', -24)):
            for key in range(first, first+5):
                self.scene.phase_time = float(key)
                record = self.side['frames'][key % 8]
                leg = record[side+'_leg']
                with self.subTest(support=side, keyframe=key):
                    self.assert_frame(actor, key % 8)
                    self.assertTrue(leg['planted'])
                    world_x = (self.scene.actor_position(actor).x-self.art['anchor'][0]
                               +leg['ankle'][0])
                    self.assertAlmostEqual(world_x, start_x+offset, places=10)

    def test_native_source_cells_match_pygame_decoded_runtime_pixels_exactly(self):
        for index, (native, (surface, _)) in enumerate(zip(self.native, self.art['loops']['walk_left'])):
            with self.subTest(phase=PHASES[index]):
                self.assertEqual(surface.get_size(), (80, 96))
                self.assertEqual(pygame.image.tobytes(surface, 'RGBA'), native.tobytes())

    def test_all_protected_generated_and_non_side_assets_keep_stored_sha256(self):
        protected = self.side['protected_sha256']
        expected = set(SOURCES.glob('*_generated.png'))
        for path in ACTOR.parent.rglob('*'):
            if not path.is_file() or path.name == 'provenance.json':
                continue
            if path.parent == ACTOR and (path.name == 'animation.json' or
                    (path.stem.startswith('walk_') and path.stem[5:].isdigit())):
                continue
            expected.add(path)
        # A removed hash entry must not silently stop protecting an asset.
        self.assertEqual(set(protected), {path.relative_to(ROOT).as_posix() for path in expected})
        for filename, sha in protected.items():
            with self.subTest(asset=filename):
                self.assertEqual(hashlib.sha256((ROOT/filename).read_bytes()).hexdigest(), sha)
        for filename, sha in ((self.side['appearance_source'], self.side['appearance_source_sha256']),
                              (self.side['authoring_tool'], self.side['authoring_tool_sha256'])):
            with self.subTest(provenance=filename):
                self.assertEqual(hashlib.sha256((ROOT/filename).read_bytes()).hexdigest(), sha)

    def test_read_only_authoring_rebuild_matches_saved_pixels_and_joint_records(self):
        # Check-style comparison in memory: never call the writing CLI, and do
        # not mistake Pillow/zlib recompression for a change in decoded pixels.
        reference, _ = author.references()
        self.assertEqual(reference.tobytes(), self.reference.tobytes())
        layers = author.parts(reference)
        palette = sorted({pixel[:3] for pixel in reference.get_flattened_data() if pixel[3]})
        for index, stored in enumerate(self.side['frames']):
            frame, record = author.authored_frame(reference, layers, palette, index)
            with self.subTest(phase=PHASES[index]):
                self.assertEqual(frame.tobytes(), self.native[index].tobytes())
                # JSON converts the builder's joint tuples to stored lists.
                self.assertEqual(json.loads(json.dumps(record)), stored)

    def test_side_walk_uses_distance_despite_duration_and_animation_rate_changes(self):
        actor = self.actor('gate_approach')
        actor['move_start'] = .5
        distance = math.dist(actor['position'], actor['to'])
        for explicit_duration in (True, False):
            for duration in (1.5, 3., 6.):
                self.scene.phase['min_seconds'] = duration+.75 if explicit_duration else duration
                if explicit_duration:
                    actor['move_seconds'] = duration
                else:
                    actor.pop('move_seconds', None)
                for rate in (0., .6, 7.):
                    actor['animation_rate'] = rate
                    for traveled, index in DISTANCE_PHASES:
                        self.scene.phase_time = .5+duration*traveled/distance
                        with self.subTest(explicit_duration=explicit_duration, duration=duration,
                                          animation_rate=rate, traveled=traveled):
                            self.assertAlmostEqual(self.scene.actor_position(actor).distance_to(
                                actor['position']), traveled, places=10)
                            self.assert_frame(actor, index)

    def test_diagonal_side_travel_counts_both_coordinates(self):
        actor = self.actor('town_parking')
        length = math.dist(actor['position'], actor['to'])
        for traveled, index in ((5, 1), (17, 4), (28.5, 7), (33, 0), (61, 7), (65, 0)):
            self.scene.phase_time = actor['move_seconds']*traveled/length
            with self.subTest(traveled=traveled):
                self.assertAlmostEqual(self.scene.actor_position(actor).distance_to(
                    actor['position']), traveled, places=10)
                self.assert_frame(actor, index)

    def test_polyline_side_travel_counts_completed_segments_not_the_endpoint_chord(self):
        actor = self.actor('gate_approach')
        x, y = actor['position']
        actor.pop('to')
        actor['path'] = [[x, y], [x, y-24], [x-32, y-24], [x-32, y]]
        actor['move_start'] = .5
        actor['move_seconds'] = 10.
        actor['animation_rate'] = 7.
        samples = ((5, 1, (0, -5)), (25, 6, (-1, -24)), (33, 0, (-9, -24)),
                   (61, 7, (-32, -19)), (73, 2, (-32, -7)))
        for traveled, index, (dx, dy) in samples:
            self.scene.phase_time = .5+traveled/8  # Eight pixels/second over an 80px path.
            with self.subTest(traveled=traveled):
                self.assertLess(self.scene.actor_position(actor).distance_to((x+dx, y+dy)), 1e-8)
                self.assert_frame(actor, index)

    def test_routed_side_walk_uses_ground_distance_delta_not_projected_position(self):
        actor = self.actor('gate_admission')
        actor.pop('route_poses')  # Keep the side gait while exercising the real depth route.
        speed = (actor['route_end']-actor['route_start'])/actor['move_seconds']
        for traveled, index in ((1, 0), (5, 1), (29, 7), (33, 0),
                                (165, 1), (299, 2), (501, 5), (923, 6)):
            self.scene.phase_time = actor['move_start']+traveled/speed
            with self.subTest(traveled=traveled):
                self.assertAlmostEqual(self.scene.actor_route_distance(actor)-actor['route_start'],
                                       traveled, places=10)
                self.assert_frame(actor, index)

    def test_zero_distance_does_not_cycle_the_side_walk(self):
        actor = self.actor('gate_approach')
        actor['to'] = list(actor['position'])
        actor['animation_rate'] = 100.
        for seconds in (.1, .4, .9, 1.4):
            self.scene.phase_time = seconds
            with self.subTest(seconds=seconds):
                self.assertEqual(self.scene.actor_position(actor), pygame.Vector2(actor['position']))
                self.assert_frame(actor, 0)

    def test_negative_aerial_reference_clock_wraps_distance_phase_without_clamping(self):
        actor = self.actor('gate_approach')
        actor['animation_rate'] = 0.
        # This real approach travels 36px in 1.5s, or 24 native pixels/second.
        samples = ((-33, 7), (-29, 0), (-25, 1), (-21, 2), (-17, 3),
                   (-13, 4), (-9, 5), (-5, 6), (-1, 7), (0, 0), (5, 1))
        for phase_time in (0., .7):
            self.scene.phase_time = phase_time
            for traveled, index in samples:
                self.scene._reference_clock = traveled/24
                with self.subTest(phase_time=phase_time, reference_distance=traveled):
                    self.assert_frame(actor, index)

    def test_actual_aerial_ground_reference_keeps_original_speed_and_restores_scene(self):
        self.actor('town_approach')
        self.scene.phase_time = .73
        self.scene._reference_camera = None
        self.scene._reference_world = None
        original = copy.deepcopy(self.scene.data)
        state = (self.scene.phase_index, self.scene.phase_time, self.scene._reference_clock)
        observed = []

        def draw_plate(canvas, **kwargs):
            actor = next(a for a in self.scene.phase['actors'] if a['id']=='aldric')
            image = self.scene._frame(actor)
            index = next(i for i, (frame, _) in enumerate(self.art['loops']['walk_left'])
                         if image is frame)
            observed.append((index, self.scene.actor_position(actor).x))

        self.scene._draw_plate = draw_plate
        canvas = pygame.Surface((480, 320))
        # Aldric walks continuously at 24px/s before reaching [611,375].
        # At these exact phase boundaries his far support ankle stays at619.
        for seconds, expected_index in ((-1., 2), (-.5, 5), (-1/3, 6), (-1/6, 7), (0., 0)):
            self.scene.ground_reference_frame(canvas, seconds=seconds)
            index, root_x = observed[-1]
            with self.subTest(seconds=seconds):
                self.assertEqual(index, expected_index)
                self.assertAlmostEqual(root_x, 611-seconds*24)
                self.assertEqual(self.scene.data, original)
                self.assertEqual((self.scene.phase_index, self.scene.phase_time,
                                  self.scene._reference_clock), state)
                if seconds >= -.5:
                    ankle = self.side['frames'][index]['far_leg']['ankle'][0]
                    self.assertAlmostEqual(root_x-self.art['anchor'][0]+ankle, 619.)

    def test_rear_loops_retain_legacy_clock_rate_and_movement_start(self):
        actor = self.actor('gate_admission')
        for elapsed, pose, expected in ((.4, 'walk_left_back', (0, 1, 2, 3)),
                                        (2.1, 'walk_back', (0, 2, 1, 3))):
            self.scene.phase_time = actor['move_start']+elapsed
            self.assertEqual(self.scene.actor_pose(actor), pose)
            for rate, index in zip((0., .5, 1., 3.), expected):
                actor['animation_rate'] = rate
                with self.subTest(pose=pose, animation_rate=rate):
                    self.assert_frame(actor, index, pose)

    def test_rear_loops_still_honor_reference_clock_and_negative_elapsed_time(self):
        actor = self.actor('gate_admission')
        for elapsed, pose in ((.4, 'walk_left_back'), (2.1, 'walk_back')):
            self.scene.phase_time = actor['move_start']+elapsed
            for reference_elapsed, index in ((.23, 1), (-.09, 3)):
                self.scene._reference_clock = actor['move_start']+reference_elapsed
                with self.subTest(pose=pose, reference_elapsed=reference_elapsed):
                    self.assert_frame(actor, index, pose)

    def test_before_and_after_movement_return_real_static_poses_even_with_reference_clock(self):
        for shot in ('gate_approach', 'gate_admission'):
            actor = self.actor(shot)
            end = actor.get('move_start', 0.)+actor['move_seconds']
            samples = [(-.1, 'stand_left'), (end, actor.get('after_pose', 'stand_left')),
                       (end+100, actor.get('after_pose', 'stand_left'))]
            if shot == 'gate_admission':
                samples.append((.8, 'turn_left_back'))
            for phase_time, pose in samples:
                self.scene.phase_time = phase_time
                for clock in (None, -10., 10.):
                    self.scene._reference_clock = clock
                    with self.subTest(shot=shot, phase_time=phase_time, reference_clock=clock):
                        self.assertIs(self.scene._frame(actor), self.art['poses'][pose])


if __name__ == '__main__':
    unittest.main()