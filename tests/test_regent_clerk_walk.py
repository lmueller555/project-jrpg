"""Read-only native clerk art checks; no scene, renderer or game fixture writes."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops

from tools import build_regent_clerk_walk as author
from tools import build_regent_arrival_actors as ground_exporter
from tools import build_regent_aerial_actors as aerial_exporter


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/cinematics/regent_arrival/actors/clerk_walk'
GROUND = ROOT/'assets/story/regent_arrival/actors'
AERIAL = ROOT/'assets/story/regent_aerial/actors'
PHASES = ('near_contact', 'near_down', 'near_passing', 'near_up',
          'far_contact', 'far_down', 'far_passing', 'far_up')
BOB = (0, 1, 0, -1, 0, 1, 0, -1)
FOOT_X = (-7.5, -3.75, 0., 3.75, 7.5, 6., 0., -6.)
FLOORS = (92, 92, 92, 92, 92, 89, 89, 90)
MAIN_HASHES = {
    'assets/story/regent_arrival/actors/clerk/stand_left.png':
        '85e3a131695e0d2f92384481aa7718de358da258e9b0fb57b7ec16340fa4a03d',
    'assets/story/regent_arrival/actors/clerk/read_left.png':
        '4d598671adb748e13cc87afc4187b6b9245b52e569dfcd1aab5673bd2316504a',
    'assets/story/regent_arrival/actors/portraits/clerk.png':
        '36931d42c448f6b85f0470242df2a8588d762f118b8086d14d4342b36cdbcb96',
    'assets/story/regent_arrival/actors/aldric/stand_left.png':
        '4781136b0a06688dad9c07f0907e9e354350029c14bcaf440faa878efd2939a8',
    'assets/story/regent_aerial/actors/aldric/overhead.png':
        'b8ee65a5f62fab2dd398268b748217a2948abc92c4245e83e4645332f11fcf3a',
    'assets/story/regent_aerial/actors/aldric/oblique.png':
        'ce2057355b9cb2e46334960d2bd1b6b4bdfd091bb624fbf13ee1a4fa5c05a65f',
    'assets/source/cinematics/regent_arrival/actors/travelers_generated.png':
        '4345f3d017057fea42a42639e6931bc05429bd8c2a5e857c82a7c288ff809c86',
    'assets/source/cinematics/regent_arrival/actors/aldric_side_walk/side_walk.png':
        '29943dcdad0118ef6e3ef8de6064d76a67309131146082c1be83576212bb3064',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rgba(path):
    with Image.open(path) as image:
        return image.convert('RGBA')


def strip_cells(path):
    image = rgba(path)
    if image.size != (640, 96):
        raise AssertionError(f'Native layer is not eight registered cells: {path}')
    return tuple(image.crop((i*80, 0, (i+1)*80, 96)) for i in range(8))


def opaque_points(image):
    alpha = image.getchannel('A')
    return {(x, y) for y in range(image.height) for x in range(image.width)
            if alpha.getpixel((x, y))}


def overlap(first, second):
    mask = ImageChops.multiply(first.getchannel('A'), second.getchannel('A'))
    return sum(value > 0 for value in mask.get_flattened_data())


class RegentClerkWalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = json.loads((SOURCE/'clerk_walk.json').read_text())
        cls.manifest = json.loads((GROUND/'clerk/animation.json').read_text())
        cls.aerial_manifest = json.loads((AERIAL/'clerk/animation.json').read_text())
        cls.protected = json.loads((SOURCE/'protected_originals.json').read_text())
        cls.reference = rgba(GROUND/'clerk/stand_left.png')
        cls.frames = {name: strip_cells(SOURCE/record['sheet'])
                      for name, record in cls.native['loops'].items()}
        cls.layers = {name: {key: strip_cells(SOURCE/filename)
                            for key, filename in record['layers'].items()}
                      for name, record in cls.native['loops'].items()}

    def assert_bone_raster(self, image, a, b, half_width=3.9, overrun=2.1, endpoint_error=.8):
        """Measure the actual alpha, not just plausible metadata lengths."""
        points = opaque_points(image)
        self.assertTrue(points)
        length = math.dist(a, b)
        dx, dy = b[0]-a[0], b[1]-a[1]
        along = [((x-a[0])*dx+(y-a[1])*dy)/length for x, y in points]
        across = [abs((x-a[0])*dy-(y-a[1])*dx)/length for x, y in points]
        self.assertLessEqual(max(across), half_width)
        self.assertGreaterEqual(min(along), -overrun)
        self.assertLessEqual(max(along), length+overrun)
        self.assertGreaterEqual(max(along)-min(along), length-1.6)
        for endpoint in (a, b):
            self.assertLessEqual(min(math.dist(endpoint, pixel) for pixel in points), endpoint_error)

    def test_exact_native_registration_and_complete_distance_gaits(self):
        self.assertEqual(self.native['canvas'], [80, 96])
        self.assertEqual(self.native['anchor'], [40, 92])
        self.assertEqual(self.native['reference_height'], 77)
        self.assertEqual(self.manifest['canvas'], [80, 96])
        self.assertEqual(self.manifest['anchor'], [40, 92])
        self.assertEqual(set(self.native['loops']), {'walk_left', 'walk_left_back', 'walk_back'})
        self.assertEqual(set(self.manifest['gaits']), set(self.native['loops']))
        for loop, record in self.native['loops'].items():
            with self.subTest(loop=loop):
                self.assertEqual(record['stride_pixels'], 30)
                self.assertEqual(self.manifest['gaits'][loop], {'stride_pixels': 30})
                self.assertEqual(tuple(f['phase'] for f in record['frames']), PHASES)
                self.assertEqual([f['duration_ms'] for f in record['frames']], [125]*8)
                self.assertEqual(self.manifest['loops'][loop],
                    [{key: frame[key] for key in ('file', 'duration_ms', 'phase')}
                     for frame in record['frames']])

    def test_each_walk_has_eight_distinct_native_binary_alpha_cells(self):
        for loop, images in self.frames.items():
            self.assertEqual(len({image.tobytes() for image in images}), 8, loop)
            for i, image in enumerate(images):
                with self.subTest(loop=loop, phase=PHASES[i]):
                    self.assertEqual(image.size, (80, 96))
                    self.assertEqual(set(image.getchannel('A').tobytes()), {0, 255})
                    left, top, right, bottom = image.getbbox()
                    self.assertGreater(left, 0)
                    self.assertLess(right, 80)
                    self.assertEqual(top, 15+BOB[i])
                    self.assertLessEqual(bottom, 92)
                    self.assertIsNone(image.crop((0, 92, 80, 96)).getbbox())

    def test_registered_original_idle_and_read_are_pixel_and_byte_identical(self):
        standing, reading = author.references()
        self.assertEqual(standing.tobytes(), self.reference.tobytes())
        self.assertEqual(reading.tobytes(), rgba(GROUND/'clerk/read_left.png').tobytes())
        self.assertEqual(sha(standing.tobytes()), self.native['reference_pixels_sha256'])
        self.assertEqual(sha(reading.tobytes()), self.native['reading_pixels_sha256'])
        self.assertEqual(rgba(SOURCE/'reference.png').tobytes(), standing.tobytes())
        for filename in ('stand_left.png', 'read_left.png'):
            name = 'assets/story/regent_arrival/actors/clerk/'+filename
            self.assertEqual(sha((ROOT/name).read_bytes()), MAIN_HASHES[name])

    def test_side_face_silhouette_and_torso_pixels_follow_only_one_pixel_bob(self):
        head = self.reference.crop((0, 0, 80, 30))
        torso = self.reference.crop((38, 31, 44, 47))
        self.assertGreater(len(opaque_points(torso)), 80)
        for i, image in enumerate(self.frames['walk_left']):
            bob = BOB[i]
            with self.subTest(phase=PHASES[i]):
                self.assertEqual(image.crop((0, bob, 80, 30+bob)).tobytes(), head.tobytes())
                self.assertEqual(image.crop((38, 31+bob, 44, 47+bob)).tobytes(), torso.tobytes())
                self.assertEqual(self.native['loops']['walk_left']['frames'][i]['body_offset'], [0, bob])

    def test_each_view_keeps_exact_stable_head_torso_ledger_and_held_arm_layers(self):
        for loop, layers in self.layers.items():
            for key in ('head', 'torso', 'ledger_arm', 'ledger', 'ledger_hand'):
                base = layers[key][0]
                for i, image in enumerate(layers[key]):
                    with self.subTest(loop=loop, layer=key, phase=PHASES[i]):
                        self.assertEqual(image.crop((0, BOB[i], 80, 96+BOB[i])).tobytes(), base.tobytes())

    def test_fixed_leg_lengths_and_actual_painted_joint_to_joint_geometry(self):
        self.assertEqual(self.native['limb_lengths']['leg'], [16.5, 16.])
        for loop, record in self.native['loops'].items():
            for i, frame in enumerate(record['frames']):
                for side in ('near', 'far'):
                    leg = frame[side+'_leg']
                    a, p = leg['anatomical'], leg['screen']
                    with self.subTest(loop=loop, phase=PHASES[i], leg=side):
                        self.assertAlmostEqual(math.dist(a['hip'], a['knee']), 16.5, places=10)
                        self.assertAlmostEqual(math.dist(a['knee'], a['ankle']), 16., places=10)
                        self.assertEqual(a['hip'], [41. if side == 'near' else 39., 55.+BOB[i]])
                        self.assert_bone_raster(self.layers[loop][side+'_thigh'][i], p['hip'], p['knee'])
                        self.assert_bone_raster(self.layers[loop][side+'_shin'][i], p['knee'], p['ankle'])
                        self.assertGreater(overlap(self.layers[loop][side+'_thigh'][i],
                                                   self.layers[loop][side+'_shin'][i]), 0)
                        self.assertGreater(overlap(self.layers[loop][side+'_shin'][i],
                                                   self.layers[loop][side+'_boot'][i]), 0)

    def test_free_arm_fixed_lengths_are_present_in_actual_sleeve_pixels(self):
        lengths = [math.hypot(1, 12), math.hypot(2, 10)]
        self.assertEqual(self.native['limb_lengths']['free_arm'], lengths)
        for loop, record in self.native['loops'].items():
            for i, frame in enumerate(record['frames']):
                arm = frame['free_arm']
                a, p = arm['anatomical'], arm['screen']
                with self.subTest(loop=loop, phase=PHASES[i]):
                    self.assertEqual(arm['hand'], 'right')
                    self.assertAlmostEqual(math.dist(a['shoulder'], a['elbow']), lengths[0], places=10)
                    self.assertAlmostEqual(math.dist(a['elbow'], a['wrist']), lengths[1], places=10)
                    self.assert_bone_raster(self.layers[loop]['free_upper'][i], p['shoulder'], p['elbow'],
                                            half_width=4.5, overrun=3., endpoint_error=1.3)
                    self.assert_bone_raster(self.layers[loop]['free_forearm'][i], p['elbow'], p['wrist'],
                                            half_width=4.5, overrun=3., endpoint_error=1.3)
                    self.assertGreater(overlap(self.layers[loop]['free_forearm'][i],
                                               self.layers[loop]['free_hand'][i]), 0)

    def test_projected_joints_truthfully_follow_yaw_and_anatomical_hand_ownership(self):
        for loop, record in self.native['loops'].items():
            for frame in record['frames']:
                yaw = frame['yaw_radians']
                for name, lane in (('near_leg', -4.), ('far_leg', 4.),
                                   ('free_arm', 9.), ('ledger_arm', -9.)):
                    for joint, point in frame[name]['anatomical'].items():
                        forward = point[0]-40
                        expected = (40+math.cos(yaw)*forward+math.sin(yaw)*lane,
                                    point[1]+math.sin(yaw)*(forward*.22-1.65))
                        with self.subTest(loop=loop, phase=frame['phase'], limb=name, joint=joint):
                            for actual, value in zip(frame[name]['screen'][joint], expected):
                                self.assertAlmostEqual(actual, value, places=10)
        back = self.native['loops']['walk_back']['frames'][0]
        self.assertLess(back['ledger_arm']['screen']['grip'][0], 40)
        self.assertGreater(back['free_arm']['screen']['wrist'][0], 40)
        self.assertLess(self.layers['walk_back']['ledger'][0].getbbox()[0], 30)

    def test_ledger_grip_overlaps_actual_cover_hand_and_visible_runtime_pixels(self):
        self.assertEqual(self.native['limb_lengths']['ledger_arm'], [math.hypot(3, 12), 11.])
        for loop, record in self.native['loops'].items():
            for i, frame in enumerate(record['frames']):
                arm = frame['ledger_arm']
                a, p = arm['anatomical'], arm['screen']
                book, hand = self.layers[loop]['ledger'][i], self.layers[loop]['ledger_hand'][i]
                grip = tuple(round(n) for n in p['grip'])
                with self.subTest(loop=loop, phase=PHASES[i]):
                    self.assertEqual(arm['hand'], 'left')
                    self.assertAlmostEqual(math.dist(a['shoulder'], a['elbow']), math.hypot(3, 12), places=10)
                    self.assertAlmostEqual(math.dist(a['elbow'], a['wrist']), 11., places=10)
                    self.assertGreaterEqual(overlap(book, hand), 12)
                    self.assertEqual(book.getpixel(grip)[3], 255)
                    self.assertEqual(hand.getpixel(grip)[3], 255)
                    self.assertEqual(self.frames[loop][i].getpixel(grip), hand.getpixel(grip))
                    # The hidden cover is brown book material, not another
                    # copy of the flesh-colored hand inside the prop layer.
                    self.assertLess(book.getpixel(grip)[0], 160)
                    self.assertGreater(overlap(self.layers[loop]['ledger_arm'][i], hand), 0)
                    sleeve_pixels = opaque_points(self.layers[loop]['ledger_arm'][i])
                    for first, last in (('shoulder', 'elbow'), ('elbow', 'wrist')):
                        for sample in range(9):
                            t = sample/8
                            point = tuple(a+(b-a)*t for a, b in zip(p[first], p[last]))
                            self.assertLessEqual(min(math.dist(point, pixel) for pixel in sleeve_pixels), 1.5)
                    wx, wy = (round(n) for n in p['wrist'])
                    self.assertLessEqual(min(math.dist((wx, wy), pixel) for pixel in opaque_points(hand)), 2.)

    def test_free_hand_swings_opposite_its_leg_while_ledger_stays_steady(self):
        records = self.native['loops']['walk_left']['frames']
        for i in (0, 1, 3, 4, 5, 7):
            arm = records[i]['free_arm']['anatomical']
            leg = records[i]['far_leg']['anatomical']
            self.assertLess((arm['wrist'][0]-arm['shoulder'][0])*(leg['ankle'][0]-40), 0)
        layers = self.layers['walk_left']
        hand_centers = [sum(x for x, _ in opaque_points(image))/len(opaque_points(image))
                        for image in layers['free_hand']]
        self.assertGreater(max(hand_centers)-min(hand_centers), 9.)
        book_centers = [sum(x for x, _ in opaque_points(image))/len(opaque_points(image))
                        for image in layers['ledger']]
        self.assertEqual(max(book_centers)-min(book_centers), 0.)

    def test_contacts_and_passing_have_measured_wide_and_narrow_boot_silhouettes(self):
        widths = {}
        for i in (0, 2, 4, 6):
            layers = self.layers['walk_left']
            boots = opaque_points(layers['near_boot'][i]) | opaque_points(layers['far_boot'][i])
            widths[i] = max(x for x, _ in boots)-min(x for x, _ in boots)+1
            if i in (0, 4):
                self.assertGreaterEqual(widths[i], 28)
            else:
                self.assertLessEqual(widths[i], 15)
        self.assertLess(max(widths[2], widths[6]), min(widths[0], widths[4])*.51)
        records = self.native['loops']['walk_left']['frames']
        self.assertEqual(records[0]['near_leg']['anatomical']['ankle'][0], 32.5)
        self.assertEqual(records[4]['far_leg']['anatomical']['ankle'][0], 32.5)

    def test_support_swing_alternation_clearance_and_actual_boot_bounds(self):
        for loop, record in self.native['loops'].items():
            for i, frame in enumerate(record['frames']):
                for near in (True, False):
                    side = 'near' if near else 'far'
                    phase = i if near else (i+4)%8
                    leg = frame[side+'_leg']
                    boot = self.layers[loop][side+'_boot'][i]
                    depth = round(leg['screen']['ankle'][1]-leg['anatomical']['ankle'][1])
                    with self.subTest(loop=loop, phase=PHASES[i], side=side):
                        self.assertEqual(leg['planted'], phase <= 4)
                        self.assertEqual(list(boot.getbbox()), leg['foot_bounds'])
                        self.assertEqual(boot.getbbox()[3], FLOORS[phase]+depth)
                        self.assertEqual(92+depth-boot.getbbox()[3], 0 if phase <= 4 else 3 if phase <= 6 else 2)
                        left, _, right, floor = boot.getbbox()
                        self.assertTrue(any(boot.getpixel((x, floor-1))[3] for x in range(left, right)))
                        ankle = tuple(round(n) for n in leg['screen']['ankle'])
                        self.assertLessEqual(min(math.dist(ankle, pixel) for pixel in opaque_points(boot)), 1.5)
                self.assertTrue(frame['near_leg']['planted'] or frame['far_leg']['planted'])

    def test_side_support_is_locked_at_authored_thirty_pixel_stride_keyframes(self):
        records = self.native['loops']['walk_left']['frames']
        for first, side in ((0, 'near'), (4, 'far')):
            world_x = []
            for key in range(first, first+5):
                leg = records[key % 8][side+'_leg']
                self.assertTrue(leg['planted'])
                world_x.append(-key*30/8+leg['anatomical']['ankle'][0])
            self.assertLess(max(world_x)-min(world_x), 1e-10)

    def test_layers_recompose_every_actual_native_frame_without_hidden_extra_art(self):
        for loop, record in self.native['loops'].items():
            for i, frame in enumerate(record['frames']):
                image = Image.new('RGBA', (80, 96))
                self.assertEqual(set(frame['layer_order']), set(record['layers']))
                for name in frame['layer_order']:
                    layer = self.layers[loop][name][i]
                    self.assertEqual(set(layer.getchannel('A').tobytes()), {0, 255})
                    image.alpha_composite(layer)
                self.assertEqual(image.tobytes(), self.frames[loop][i].tobytes())

    def test_all_new_material_pixels_come_from_this_clerk_not_a_recolored_aldric(self):
        palette = {pixel for pixel in self.reference.get_flattened_data() if pixel[3]}
        for loop, images in self.frames.items():
            for i, image in enumerate(images):
                colors = {p for p in image.get_flattened_data() if p[3]}
                self.assertTrue(colors <= palette, (loop, PHASES[i], colors-palette))
        parts = json.loads((SOURCE/'parts.json').read_text())
        self.assertEqual(parts['masks']['ledger'], [list(p) for p in author.MASKS['ledger']])
        self.assertIn('ledger_hand', parts['parts'])
        self.assertIn('moss', parts['material_bounds'])
        self.assertIn('offline native part-authored', self.native['authoring'])
        self.assertIn('no imagegen tool used', self.native['authoring'])

    def test_rear_head_has_no_profile_face_and_differs_from_three_quarter(self):
        back = self.layers['walk_back']['head'][0]
        quarter = self.layers['walk_left_back']['head'][0]
        self.assertNotEqual(back.tobytes(), quarter.tobytes())
        crown = back.crop((0, 14, 80, 28))
        self.assertTrue(opaque_points(crown))
        self.assertTrue(all(p[0] < 130 and p[1] < 90
                            for p in crown.get_flattened_data() if p[3]))
        # Rear/quarter are independently authored silhouettes, not a mirrored
        # front face or a flat crop of the side standing body.
        self.assertNotEqual(back.tobytes(), self.layers['walk_left']['head'][0].tobytes())
        self.assertNotEqual(self.frames['walk_back'][0].tobytes(),
                            self.frames['walk_left_back'][0].tobytes())

    def test_matching_static_turn_and_back_keep_77px_height_and_registered_soles(self):
        for pose in ('turn_left_back', 'stand_back', 'stand_left_back'):
            record = self.native['poses'][pose]
            image = rgba(SOURCE/record['file'])
            runtime = rgba(GROUND/'clerk'/self.manifest['poses'][pose])
            with self.subTest(pose=pose):
                self.assertEqual(image.size, (80, 96))
                self.assertEqual(image.getbbox()[1], 15)
                self.assertEqual(image.getbbox()[3], 92)
                self.assertEqual(image.getbbox()[3]-image.getbbox()[1], 77)
                self.assertEqual(image.tobytes(), runtime.tobytes())
                self.assertEqual(record['joints']['phase'], 'idle')
                for side in ('near', 'far'):
                    self.assertTrue(record['joints'][side+'_leg']['planted'])
                    self.assertEqual(record['joints'][side+'_leg']['foot_bounds'][3], 92)
                loop = 'walk_back' if pose == 'stand_back' else 'walk_left_back'
                self.assertEqual(image.crop((0, 0, 80, 30)).tobytes(),
                                 self.frames[loop][0].crop((0, 0, 80, 30)).tobytes())

    def test_runtime_walk_pixels_are_exact_copies_of_registered_native_cells(self):
        for loop, record in self.native['loops'].items():
            for i, entry in enumerate(record['frames']):
                image = rgba(GROUND/'clerk'/entry['file'])
                with self.subTest(loop=loop, phase=PHASES[i]):
                    self.assertEqual(image.tobytes(), self.frames[loop][i].tobytes())
                    self.assertEqual(image.size, (80, 96))

    def test_aerial_mapping_and_native_copy_keep_correct_canvas_anchor_and_ledger_side(self):
        catalogue = json.loads((AERIAL/'manifest.json').read_text())
        self.assertEqual(catalogue['actors']['clerk'], 'clerk/animation.json')
        self.assertEqual(self.aerial_manifest['canvas'], [48, 64])
        self.assertEqual(self.aerial_manifest['anchor'], [24, 56])
        self.assertEqual(self.aerial_manifest['overhead_facing'], 'north')
        self.assertEqual(self.aerial_manifest['oblique_facing'], 'northwest')
        for pose, entry in self.native['aerial'].items():
            source = rgba(SOURCE/entry['file'])
            image = rgba(AERIAL/'clerk'/self.aerial_manifest['poses'][pose])
            self.assertEqual(source.size, (48, 64))
            self.assertEqual(source.tobytes(), image.tobytes())
            self.assertEqual(set(image.getchannel('A').tobytes()), {0, 255})
            palette = {pixel for pixel in self.reference.get_flattened_data() if pixel[3]}
            self.assertTrue({pixel for pixel in image.get_flattened_data() if pixel[3]} <= palette)
            self.assertEqual(image.getbbox()[3], 56)
            self.assertIsNone(image.crop((0, 56, 48, 64)).getbbox())
            # Actual brown ledger pixels protrude at the anatomical left hip.
            book = [p for p in image.crop((12, 34 if pose == 'oblique' else 42,
                                          18, 44 if pose == 'oblique' else 51)).get_flattened_data()
                    if p[3] and p[0] > p[1]*1.3]
            self.assertGreater(len(book), 15)

    def test_overhead_is_genuinely_foreshortened_and_matches_existing_aerial_adult_scale(self):
        overhead = rgba(AERIAL/'clerk/overhead.png')
        oblique = rgba(AERIAL/'clerk/oblique.png')
        heights = []
        for pose, image in (('overhead', overhead), ('oblique', oblique)):
            box = image.getbbox()
            height = box[3]-box[1]
            heights.append(height)
            aldric = rgba(AERIAL/'aldric'/(pose+'.png')).getbbox()
            self.assertLessEqual(abs(height-(aldric[3]-aldric[1])), 3)
            # Cropping and uniformly shrinking the upright body cannot
            # reproduce the explicitly authored crown/shoulder/hip geometry.
            scaled = self.reference.crop(self.reference.getbbox()).resize(
                (box[2]-box[0], height), Image.Resampling.NEAREST)
            self.assertNotEqual(image.crop(box).tobytes(), scaled.tobytes())
        self.assertLess(heights[0], heights[1]*.72)
        self.assertLess(heights[0], 77*.42)

    def test_main_original_hashes_and_all_protected_pngs_are_unchanged(self):
        self.assertEqual(len(self.protected), 91)
        for name, expected in MAIN_HASHES.items():
            self.assertEqual(self.protected[name], expected)
            self.assertEqual(sha((ROOT/name).read_bytes()), expected)
        for name, expected in self.protected.items():
            with self.subTest(original=name):
                self.assertTrue(name.endswith('.png'))
                self.assertEqual(sha((ROOT/name).read_bytes()), expected)

    def test_protection_snapshot_cannot_silently_drop_aldric_portraits_or_other_old_art(self):
        expected = set((ROOT/'assets/source/cinematics/regent_arrival/actors').glob('*_generated.png'))
        expected.update((ROOT/'assets/source/cinematics/regent_aerial/actors').glob('*_generated.png'))
        expected.update((ROOT/'assets/source/cinematics/regent_arrival/actors/aldric_side_walk').rglob('*.png'))
        for directory in (GROUND, AERIAL):
            for path in directory.rglob('*.png'):
                if path.parent.name == 'clerk' and (directory == AERIAL or
                                                    path.name not in ('stand_left.png', 'read_left.png')):
                    continue
                expected.add(path)
        self.assertEqual(set(self.protected), {path.relative_to(ROOT).as_posix() for path in expected})

    def test_authoring_and_joint_records_rebuild_in_memory_without_any_file_writes(self):
        with patch.object(Path, 'write_bytes', side_effect=AssertionError('test wrote bytes')), \
             patch.object(Path, 'write_text', side_effect=AssertionError('test wrote text')), \
             patch.object(Path, 'mkdir', side_effect=AssertionError('test created a directory')):
            outputs = author.build()
        self.assertEqual({path for path in outputs if path.is_relative_to(SOURCE)},
                         {path for path in SOURCE.rglob('*') if path.is_file()})
        for path, data in outputs.items():
            with self.subTest(rebuilt=path.relative_to(ROOT).as_posix()):
                self.assertEqual(path.read_bytes(), data)

    def test_exporters_are_read_only_in_check_mode_and_preserve_original_compression(self):
        with patch.object(Path, 'write_bytes', side_effect=AssertionError('export test wrote bytes')), \
             patch.object(Path, 'mkdir', side_effect=AssertionError('export test created a directory')):
            ground = ground_exporter.build()
            aerial = aerial_exporter.build()
        for directory, outputs in ((GROUND, ground), (AERIAL, aerial)):
            for name, data in outputs.items():
                with self.subTest(export=(directory/name).relative_to(ROOT).as_posix()):
                    self.assertEqual((directory/name).read_bytes(), data)
            for filename, expected in self.protected.items():
                path = ROOT/filename
                if path.is_relative_to(directory):
                    name = path.relative_to(directory).as_posix()
                    self.assertEqual(sha(outputs[name]), expected)

    def test_authorship_source_tool_and_export_provenance_match_current_files(self):
        for key in ('appearance_source', 'authoring_tool'):
            path = ROOT/self.native[key]
            self.assertEqual(sha(path.read_bytes()), self.native[key+'_sha256'])
        for directory in (GROUND, AERIAL):
            provenance = json.loads((directory/'provenance.json').read_text())
            for name, expected in provenance['exports'].items():
                self.assertEqual(sha((directory/name).read_bytes()), expected)
        aerial_provenance = json.loads((AERIAL/'provenance.json').read_text())
        for pose in ('overhead', 'oblique'):
            self.assertEqual(aerial_provenance['registrations']['clerk/'+pose+'.png']['scale'], 1.)
        for name, expected in aerial_provenance['native_clerk_sources'].items():
            self.assertEqual(sha((ROOT/name).read_bytes()), expected)


if __name__ == '__main__':
    unittest.main()