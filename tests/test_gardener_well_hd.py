"""Contracts for the staged gardener performance and canonical-pail bindings.

These checks cover exported state, registration and ownership boundaries. They
do not substitute for reviewing the authored poses or claim live integration.
"""
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import make_dataclass
from hashlib import sha256
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/characters/npcs/female_02/gardener_well_hd'
PACK = ROOT/'assets/characters/npcs/female_02/gardener_well_hd'
WELL_PACK = ROOT/'assets/terrain/eldenmere/well_hd'


def rgba(path):
    with Image.open(path) as source:
        return source.convert('RGBA')


def gray(path):
    with Image.open(path) as source:
        return source.convert('L')


def changed_mask(first, second):
    difference = ImageChops.difference(first.convert('RGB'), second.convert('RGB'))
    red, green, blue = difference.split()
    return ImageChops.lighter(ImageChops.lighter(red, green), blue).point(
        lambda value: 255 if value else 0)


def strings(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)
    elif isinstance(value, str):
        yield value


def module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(specification)
    sys.modules[name] = result
    specification.loader.exec_module(result)
    return result


class GardenerWellHDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((PACK/'animations.json').read_text())
        cls.recipe = json.loads((SOURCE/'recipe.json').read_text())
        cls.builder = module('gardener_well_hd_builder', ROOT/'tools/build_gardener_well_hd.py')
        cls.presentation = module('gardener_well_hd_presentation', ROOT/'gardener_well_presentation.py')

    @staticmethod
    def snapshot(**changes):
        """Local schema-1 authoring fixture; it does not import PR 2 code."""
        data = dict(schema_version=1, operation_id=1,
                    operator_id='sanctuary_gardener', pail_id='gardener_pail',
                    phase_id='fill', phase_elapsed_ms=800, phase_progress=.5,
                    total_elapsed_ms=7400, required_station=None, ready=True,
                    crank_turns=-1/9, crank_phase=8/9, crank_direction=0,
                    crank_sample=14, bucket_grip_local=(36, 72),
                    rope_origin_local=(36, 53), rope_end_local=(36, 71),
                    rope_length=18, rope_deployed=True, hook_visible=True,
                    pail_owner='well', water_units=3, bucket_region='shaft',
                    water_contact=True, bucket_submerged=True,
                    mouth_submerged=True, completed=False, cancelled=False)
        data.update(changes)
        return data

    def test_original_character_delivery_stays_staged_while_pails_are_reused(self):
        self.assertEqual(self.manifest['integration_status'], 'staged')
        self.assertIs(self.manifest['runtime_activation'], False)
        self.assertEqual(self.manifest['visual_approval'], 'pending_user_review')
        for relative in ('assets/maps/eldenmere/playable/map.json',
                         'assets/maps/eldenmere/routines/gardener.json',
                         'assets/characters/npcs/female_02/gardener/animations.json'):
            current = json.loads((ROOT/relative).read_text())
            if relative.endswith('playable/map.json'):
                # PR4 keeps the newer adult_woman_02 body identity. It reuses
                # only this original delivery's canonical rigid pail variants.
                binding = current['well_runtime']
                self.assertEqual(binding['canonical_pail_manifest'],
                                 'assets/characters/npcs/female_02/gardener_well_hd/animations.json')
                self.assertIn('/adult_woman_02/', binding['actor']['action_bank'])
                current = deepcopy(current)
                current['well_runtime'].pop('canonical_pail_manifest')
            self.assertFalse(any('gardener_well_hd/' in value for value in strings(current)), relative)

    def test_explicit_native_density_keeps_draw_and_foot_registration_distinct(self):
        data = self.manifest
        self.assertEqual(data['artwork_pixels_per_world_pixel'], 2)
        self.assertEqual(data['artwork_size'], [2*n for n in data['logical_size']])
        self.assertEqual(data['logical_size'], [48, 48])
        self.assertEqual(data['draw_anchor_logical'], [24, 36])
        self.assertEqual(data['foot_anchor_logical'], [24, 40])
        self.assertNotEqual(data['draw_anchor_logical'], data['foot_anchor_logical'])
        for anchor in ('draw_anchor_logical', 'foot_anchor_logical'):
            self.assertTrue(all(0 <= coordinate < limit for coordinate, limit
                                in zip(data[anchor], data['logical_size'])))

    def test_new_pose_images_are_native_hard_alpha_and_registered(self):
        size = tuple(self.manifest['artwork_size'])
        self.assertTrue(self.manifest['poses'])
        for name, pose in self.manifest['poses'].items():
            with self.subTest(pose=name):
                path = PACK/pose['file']
                image = rgba(path)
                self.assertEqual(image.size, size)
                self.assertLessEqual(set(image.getchannel('A').tobytes()), {0, 255})
                bounds = image.getbbox()
                self.assertIsNotNone(bounds)
                self.assertGreater(bounds[0], 0)
                self.assertGreater(bounds[1], 0)
                self.assertLess(bounds[2], size[0])
                self.assertLess(bounds[3], size[1])
                grip = pose['hand_grip_logical']
                self.assertEqual(len(grip), 2)
                self.assertTrue(all(0 <= coordinate < limit for coordinate, limit
                                    in zip(grip, self.manifest['logical_size'])))

    def test_operating_cycles_have_authored_samples_and_steady_foot_support(self):
        for name in ('lower', 'raise'):
            with self.subTest(clip=name):
                clip = self.manifest['clips'][name]
                frames = clip['frames']
                self.assertEqual(len(frames), 16)
                images = [rgba(PACK/self.manifest['poses'][pose]['file']) for pose in frames]
                # Opposite crank phases require different authored poses. This
                # is deliberately weaker than a claim of good motion quality.
                self.assertNotEqual(images[0].tobytes(), images[8].tobytes())
                bottoms = [image.getbbox()[3] for image in images]
                self.assertLessEqual(max(bottoms)-min(bottoms), 1,
                                     'Stationary support may quantize by at most one artwork pixel')

    def test_every_clip_resolves_to_registered_complete_poses(self):
        poses = self.manifest['poses']
        for name, clip in self.manifest['clips'].items():
            with self.subTest(clip=name):
                self.assertTrue(clip['frames'])
                self.assertTrue(set(clip['frames']) <= set(poses))
                self.assertIn(clip['facing'], ('front', 'back', 'left', 'right'))

    def test_retained_sources_have_hashes_and_complete_frame_provenance(self):
        for name, record in self.recipe['poses'].items():
            with self.subTest(pose=name):
                relative = record['source_file']
                source = (ROOT if relative.startswith('assets/') else SOURCE)/relative
                self.assertEqual(sha256(source.read_bytes()).hexdigest(),
                                 record['source_sha256'])
                original = rgba(source)
                exported = rgba(PACK/record['file'])
                if record['provenance'] == 'explicit_legacy_body_compatibility':
                    self.assertEqual(record['source_density'], 1)
                    original = original.resize(exported.size, Image.Resampling.NEAREST)
                else:
                    self.assertEqual(record['provenance'], 'new_complete_image_authored_frame')
                    self.assertEqual(original.size, tuple(self.recipe['artwork_size']))
                self.assertEqual(original.tobytes(), exported.tobytes())

    def test_retained_masters_use_one_uniform_scale_per_authored_strip(self):
        # Re-fitting each changing silhouette would erase deliberate bends and
        # introduce the height twitch that this work is intended to prevent.
        for record in self.recipe['source_metadata']:
            metadata_path = SOURCE/record['file']
            self.assertEqual(sha256(metadata_path.read_bytes()).hexdigest(), record['sha256'])
            metadata = json.loads(metadata_path.read_text())
            scales = {}
            if 'sources' in metadata:
                for master in metadata['sources']:
                    source = metadata_path.parent/master['file']
                    self.assertEqual(sha256(source.read_bytes()).hexdigest(), master['sha256'])
                    scales[master['file']] = {master['uniform_scale']}
                for frame in metadata['frames']:
                    scales[frame['source_master']].add(frame['uniform_scale'])
            else:
                for frame in metadata['records']:
                    source = metadata_path.parent/frame['source']
                    self.assertEqual(sha256(source.read_bytes()).hexdigest(), frame['source_sha256'])
                    scales.setdefault(frame['source'], set()).add(frame['whole_frame_uniform_scale'])
            self.assertTrue(scales)
            for master, values in scales.items():
                self.assertEqual(len(values), 1, master)

    def test_heavier_raising_has_its_own_authored_performance(self):
        poses = self.manifest['poses']
        banks = []
        for name in ('lower', 'raise'):
            banks.append({rgba(PACK/poses[pose]['file']).tobytes()
                          for pose in self.manifest['clips'][name]['frames']})
        self.assertNotEqual(banks[0], banks[1],
                            'A separate raising performance cannot just reverse lowering frames')

    def test_carry_compatibility_retains_cadence_grips_and_directional_depth(self):
        legacy = json.loads((ROOT/self.recipe['legacy_bank']).read_text())
        for load in ('empty', 'full'):
            for facing in ('front', 'back', 'left', 'right'):
                with self.subTest(load=load, facing=facing):
                    clip = self.manifest['clips'][f'carry_{load}_{facing}']
                    previous = legacy['animations'][f'carry_{load}.{facing}']
                    self.assertEqual(clip['provenance'], 'explicit_legacy_body_compatibility')
                    self.assertEqual(len(clip['frames']), len(previous))
                    self.assertEqual(clip['duration_ms'], sum(v['duration_ms'] for v in previous))
                    self.assertTrue(all(v['duration_ms'] == clip['frame_duration_ms'] for v in previous))
                    for pose_id, old_frame in zip(clip['frames'], previous):
                        pose = self.manifest['poses'][pose_id]
                        old_pose = legacy['poses'][old_frame['pose']]
                        # Back carry deliberately gains torso occlusion. The
                        # other directions retain their established depth.
                        expected_order = 'before' if facing == 'back' else old_pose['order']
                        self.assertEqual(pose['pail_order'], expected_order)
                        expected_grip = [a+b for a, b in zip(old_pose['grip'], legacy['body_offset'])]
                        self.assertEqual(pose['hand_grip_logical'], expected_grip)

    def test_all_four_carry_directions_sample_without_changing_water(self):
        for facing in ('front', 'back', 'left', 'right'):
            for units in range(7):
                for frame in range(4):
                    with self.subTest(facing=facing, units=units, frame=frame):
                        selected = self.presentation.carry_pose(facing, frame/4, units)
                        mode = 'full' if units else 'empty'
                        clip = self.manifest['clips'][f'carry_{mode}_{facing}']
                        self.assertEqual(selected['pose_id'], clip['frames'][frame])
                        self.assertEqual(selected['water_units'], units)
                        self.assertEqual(selected['pail']['units'], units)
                        self.assertTrue(selected['pail_visible'])
                        self.assertEqual(selected['pail_owner'], 'actor')
                        self.assertEqual(selected, self.presentation.carry_pose(facing, frame/4+2, units))

    def test_body_pail_composites_apply_real_directional_occlusion(self):
        for facing in ('front', 'back', 'left', 'right'):
            for units in (0, 6):
                with self.subTest(facing=facing, units=units):
                    selection = self.presentation.carry_pose(facing, 0, units)
                    body = rgba(PACK/selection['body_file'])
                    pail = rgba(PACK/selection['pail']['file'])
                    grip, anchor = selection['hand_grip_logical'], selection['pail']['grip_logical']
                    offset = tuple(round(2*(grip[i]-anchor[i])) for i in (0, 1))
                    pail_layer = Image.new('RGBA', body.size)
                    pail_layer.alpha_composite(pail, offset)
                    overlap = ImageChops.multiply(body.getchannel('A'), pail_layer.getchannel('A'))
                    if facing == 'back':
                        self.assertIsNotNone(overlap.getbbox(), 'Back carry must exercise torso occlusion')
                    result = self.presentation.render_pose(selection)
                    expected_top = body if selection['pail_order'] == 'before' else pail_layer
                    self.assertIsNone(ImageChops.multiply(
                        changed_mask(result, expected_top), overlap).getbbox())

    def test_operating_contacts_stay_near_the_shared_crank_orbit(self):
        contract = json.loads((SOURCE/self.recipe['mechanism_contract']['file']).read_text())
        self.assertEqual(sha256((SOURCE/self.recipe['mechanism_contract']['file']).read_bytes()).hexdigest(),
                         self.recipe['mechanism_contract']['sha256'])
        origin = contract['well_world_origin']
        station = contract['stations']['operator']['feet_world_logical']
        pivot = contract['geometry']['crank_pivot_local']
        radii = contract['geometry']['crank_radii_local']
        anchor = self.manifest['draw_anchor_logical']
        for family in ('lower', 'raise'):
            for sample, pose_id in enumerate(self.manifest['clips'][family]['frames']):
                with self.subTest(family=family, sample=sample):
                    pose = self.manifest['poses'][pose_id]
                    phase = sample*math.tau/16
                    crank = [origin[0]+pivot[0]+radii[0]*math.cos(phase),
                             origin[1]+pivot[1]+radii[1]*math.sin(phase)]
                    hand = [station[i]-anchor[i]+pose['hand_grip_logical'][i] for i in (0, 1)]
                    self.assertEqual(pose['crank_sample'], sample)
                    self.assertLessEqual(math.dist(hand, crank), 4,
                                         'Keep natural hands within a small reach of the actual knob')

    def test_handoff_reaches_and_holds_the_shared_loading_grip_at_the_cue(self):
        contract = json.loads((SOURCE/self.recipe['mechanism_contract']['file']).read_text())
        origin = contract['well_world_origin']
        station = contract['stations']['loading']['feet_world_logical']
        hook = [origin[i]+contract['geometry']['loading_grip_local'][i] for i in (0, 1)]
        anchor = self.manifest['draw_anchor_logical']
        for phase, cue, before_owner, after_owner in (
                ('attach', .70, 'actor', 'well'), ('detach', .65, 'well', 'actor')):
            contacts = []
            for progress, owner in ((cue-.001, before_owner), (cue, after_owner)):
                selection = self.presentation.select_pose(self.snapshot(
                    phase_id=phase, phase_progress=progress, pail_owner=owner,
                    water_units=6 if phase == 'detach' else 0))
                hand = [station[i]-anchor[i]+selection['hand_grip_logical'][i] for i in (0, 1)]
                self.assertLessEqual(math.dist(hand, hook), 4)
                contacts.append(hand)
            self.assertLessEqual(math.dist(*contacts), 4, 'Transfer must not snap to a remote hand')

    def test_four_authored_pour_modes_follow_progress_and_keep_external_water(self):
        for facing in ('left', 'right'):
            for raised in (False, True):
                for frame in range(8):
                    with self.subTest(facing=facing, raised=raised, frame=frame):
                        selected = self.presentation.pour_pose(facing, raised, (frame+.5)/8, 4)
                        family = f'pour_{"trough" if raised else "ground"}_{facing}'
                        self.assertEqual(selected['pose_id'], self.manifest['clips'][family]['frames'][frame])
                        self.assertEqual(selected['water_units'], 4)
                        self.assertEqual(selected['pail']['units'], 4)
                        self.assertEqual(selected['pail_owner'], 'actor')
                        self.assertTrue(selected['pail_visible'])
                        self.assertIs(selected['stream_visible'], frame in (3, 4))
                        self.assertEqual(self.presentation.render_pose(selected).size, (96, 96))

    def test_pickup_and_setdown_show_one_pail_and_meet_the_station_at_transfer(self):
        for depositing in (False, True):
            clip = self.manifest['clips']['setdown_left' if depositing else 'pickup_left']
            for frame in range(8):
                progress = (frame+.5)/8
                selection = self.presentation.pickup_pose(progress, 4, depositing)
                self.assertEqual(selection['pose_id'], clip['frames'][frame])
                self.assertEqual(selection['water_units'], 4)
                self.assertNotEqual(selection['pail_visible'], selection['station_pail_visible'])
                expected_held = progress < .5 if depositing else progress >= .5
                self.assertIs(selection['pail_visible'], expected_held)
            for progress in (.4999, .5):
                selection = self.presentation.pickup_pose(progress, 4, depositing)
                self.assertLessEqual(math.dist(selection['hand_grip_logical'],
                                               selection['station_grip_logical']), 1)

    def test_selection_reads_dict_and_frozen_snapshots_without_advancing_work(self):
        state = self.snapshot()
        before = deepcopy(state)
        selected = self.presentation.select_pose(state)
        self.assertEqual(state, before)
        self.assertEqual(selected, self.presentation.select_pose(state))
        self.assertIn(selected['pose_id'], self.manifest['poses'])
        self.assertEqual(selected['water_units'], state['water_units'])
        self.assertEqual(selected['pail_owner'], state['pail_owner'])
        FrozenSnapshot = make_dataclass(
            'AuthoringSnapshot', [(key, object) for key in state], frozen=True)
        frozen = FrozenSnapshot(**state)
        self.assertEqual(selected, self.presentation.select_pose(frozen))
        self.assertEqual(vars(frozen), before)

    def test_phase_facing_cannot_be_overridden_by_a_contradictory_caller(self):
        for phase, required, contradictory in (('lower', 'left', 'back'),
                                                ('attach', 'back', 'left')):
            state = self.snapshot(phase_id=phase)
            before = deepcopy(state)
            self.assertEqual(self.presentation.select_pose(state),
                             self.presentation.select_pose(state, facing=required))
            with self.assertRaises(ValueError):
                self.presentation.select_pose(state, facing=contradictory)
            self.assertEqual(state, before)

    def test_warmed_render_uses_cache_and_callers_cannot_poison_pixels_or_metadata(self):
        selection = self.presentation.carry_pose('back', .25, 6)
        before = deepcopy(selection)
        first = self.presentation.render_pose(selection)
        pixels = first.tobytes()
        first.putpixel((0, 0), (255, 0, 255, 255))
        with patch.object(self.presentation.Image, 'open',
                          side_effect=AssertionError('A warmed pose reopened an image')):
            self.assertEqual(self.presentation.render_pose(selection).tobytes(), pixels)
            self.assertEqual(self.presentation.render_pose(selection).tobytes(), pixels)
        self.assertEqual(selection, before)
        external_bank = self.presentation.bank()
        external_bank['poses'].clear()
        selection['hand_grip_logical'][0] = -100
        selection['pail']['grip_logical'][0] = -100
        self.assertEqual(self.presentation.carry_pose('back', .25, 6), before)
        self.assertEqual(self.presentation.bank()['poses'], self.manifest['poses'])

    def test_pour_stream_starts_at_the_canonical_mouth_without_mutating_selection(self):
        contract = json.loads((SOURCE/self.recipe['mechanism_contract']['file']).read_text())
        source_grip = contract['pail']['grip_anchor_local']
        source_mouth = contract['pail']['mouth_anchor_local']
        for facing, raised in (('left', False), ('right', True)):
            selection = self.presentation.pour_pose(facing, raised, .45, 4)
            before = deepcopy(selection)
            pouring = self.presentation.render_pose(selection)
            dry = self.presentation.render_pose(dict(selection, stream_visible=False))
            changed = changed_mask(pouring, dry)
            self.assertIsNotNone(changed.getbbox())
            grip, pail = selection['hand_grip_logical'], selection['pail']
            offset = [round(2*(grip[i]-pail['grip_logical'][i])) for i in (0, 1)]
            start = [offset[i]+round(2*pail['stream_origin_logical'][i]) for i in (0, 1)]
            self.assertTrue(any(changed.getpixel((start[0]+dx, start[1]))
                                for dx in (-1, 0, 1)))
            angle = math.radians(pail['angle'])
            dx, dy = [source_mouth[i]-source_grip[i] for i in (0, 1)]
            mouth = [pail['grip_logical'][0]+dx*math.cos(angle)+dy*math.sin(angle),
                     pail['grip_logical'][1]-dx*math.sin(angle)+dy*math.cos(angle)]
            self.assertLessEqual(math.dist(pail['stream_origin_logical'], mouth), 3.1,
                                 'The stream must start at the turned mouth lip, not the pail base')
            self.assertEqual(selection, before)

    def test_empty_pours_have_no_visible_water_stream(self):
        for facing in ('left', 'right'):
            for raised in (False, True):
                for frame in range(8):
                    selection = self.presentation.pour_pose(facing, raised, (frame+.5)/8, 0)
                    self.assertFalse(selection['stream_visible'])
                    self.assertEqual(self.presentation.render_pose(selection).tobytes(),
                                     self.presentation.render_pose(dict(selection, stream_visible=False)).tobytes())

    def test_pours_face_the_mouth_and_lower_outside_lip_toward_the_target(self):
        canonical = json.loads((WELL_PACK/'manifest.json').read_text())['pail']
        source_grip = [2*value for value in canonical['grip_logical']]
        # Actual left/right lip points of the retained 24x36 canonical pail.
        lips = {'left': (6, 17), 'right': (18, 17)}
        for facing in ('left', 'right'):
            side = -1 if facing == 'left' else 1
            for raised in (False, True):
                for frame in (2, 3, 4, 5):
                    with self.subTest(facing=facing, raised=raised, frame=frame):
                        selected = self.presentation.pour_pose(facing, raised, (frame+.5)/8, 4)
                        pail = selected['pail']
                        angle = math.radians(pail['angle'])
                        # In screen coordinates the upright mouth normal (0,-1)
                        # turns to (-sin(a),-cos(a)). The hanging mass swings in
                        # the opposite horizontal direction; it is not the aim.
                        self.assertGreater(side*(-math.sin(angle)), 0)
                        def turn(point):
                            dx, dy = [point[i]-source_grip[i] for i in (0, 1)]
                            return [pail['grip_logical'][0]+(dx*math.cos(angle)+dy*math.sin(angle))/2,
                                    pail['grip_logical'][1]+(-dx*math.sin(angle)+dy*math.cos(angle))/2]
                        outside = turn(lips[facing])
                        opposite = turn(lips['right' if facing == 'left' else 'left'])
                        self.assertGreater(side*(outside[0]-opposite[0]), 0)
                        self.assertGreater(outside[1], opposite[1], 'Water exits the lower screen-space rim')
                        for actual, expected in zip(pail['stream_origin_logical'], outside):
                            self.assertAlmostEqual(actual, expected)

    def test_stopped_fill_keeps_the_actual_crank_sample(self):
        early = self.snapshot(phase_progress=.1, phase_elapsed_ms=100)
        late = self.snapshot(phase_progress=.9, phase_elapsed_ms=900)
        first = self.presentation.select_pose(early)
        final = self.presentation.select_pose(late)
        self.assertEqual(first['pose_id'], final['pose_id'])
        self.assertEqual(first['clip'], 'brace')
        self.assertEqual(first['crank_sample'], early['crank_sample'])
        self.assertEqual(final['crank_sample'], early['crank_sample'])
        # A different actual stopped phase selects the corresponding hand pose;
        # the fill timer itself does not reset the crank to sample zero.
        other = self.presentation.select_pose(self.snapshot(crank_sample=6, crank_phase=6/16))
        self.assertNotEqual(first['pose_id'], other['pose_id'])
        for sample in (14, 15, 0):
            braking = self.presentation.select_pose(self.snapshot(
                phase_id='secure', crank_sample=sample, crank_phase=sample/16))
            self.assertEqual(braking['clip'], 'brake')
            self.assertEqual(braking['crank_sample'], sample)

    def test_operating_selection_uses_the_shared_crank_sample(self):
        for family, direction in (('lower', 1), ('raise', -1)):
            frames = self.manifest['clips'][family]['frames']
            for sample in range(16):
                with self.subTest(phase=family, sample=sample):
                    state = self.snapshot(
                        phase_id=family, phase_progress=sample/16,
                        crank_phase=sample/16, crank_sample=sample,
                        crank_direction=direction,
                        water_units=6 if family == 'raise' else 0,
                        water_contact=False, bucket_submerged=False)
                    selected = self.presentation.select_pose(state)
                    self.assertEqual(selected['pose_id'], frames[sample])
                    self.assertEqual(selected['crank_sample'], sample)
                    # Global elapsed time is not a second presentation clock.
                    later = dict(state, total_elapsed_ms=1000000,
                                 phase_elapsed_ms=900000)
                    self.assertEqual(selected, self.presentation.select_pose(later))

    def test_handoffs_render_the_pail_for_exactly_its_reported_owner(self):
        cases = (
            ('attach', .69, 'actor', 0, True),
            ('attach', .70, 'well', 0, False),
            ('lower', .5, 'well', 0, False),
            ('fill', .5, 'well', 3, False),
            ('raise', .5, 'well', 6, False),
            ('detach', .64, 'well', 6, False),
            ('detach', .65, 'actor', 6, True),
            ('complete', 1, 'actor', 6, True),
        )
        for phase, progress, owner, water, visible in cases:
            with self.subTest(phase=phase, progress=progress):
                state = self.snapshot(phase_id=phase, phase_progress=progress,
                                      pail_owner=owner, water_units=water,
                                      bucket_region='actor_held' if owner == 'actor' else 'shaft',
                                      water_contact=phase == 'fill',
                                      bucket_submerged=phase == 'fill',
                                      crank_direction=-1 if phase == 'raise' else 1 if phase == 'lower' else 0,
                                      completed=phase == 'complete')
                before = deepcopy(state)
                selected = self.presentation.select_pose(state)
                self.assertIs(selected['pail_visible'], visible)
                self.assertEqual(selected['pail_owner'], owner)
                self.assertEqual(selected['water_units'], water)
                self.assertEqual(state, before)

    def test_actual_mechanism_trace_is_only_read_by_the_presentation(self):
        """Offline PR2/PR3 compatibility; this does not select a live routine."""
        mechanism = module('gardener_joint_mechanism', ROOT/'well_mechanism.py')
        reference = SOURCE/self.recipe['mechanism_contract']['file']
        self.assertEqual(reference.read_bytes(), mechanism.CONTRACT_PATH.read_bytes())
        model = mechanism.WellMechanism()
        token = model.reserve('sanctuary_gardener', 'gardener_pail')
        self.assertIsNotNone(token)
        gates = {'await_loading': 'loading', 'await_operator': 'operator',
                 'await_retrieval': 'loading'}
        phases, samples, stopped = set(), {'lower': set(), 'raise': set()}, set()
        contract = model.contract
        origin, geometry = contract['well_world_origin'], contract['geometry']
        station = contract['stations']['operator']['feet_world_logical']
        for _ in range(5000):
            snapshot = model.snapshot()
            before = snapshot.to_dict()
            selected = self.presentation.select_pose(snapshot)
            self.assertEqual(selected, self.presentation.select_pose(before))
            self.assertEqual(selected, self.presentation.select_pose(snapshot))
            self.assertEqual(model.snapshot().to_dict(), before)
            self.assertEqual(snapshot.to_dict(), before)
            self.assertEqual(selected['pail_owner'], snapshot.pail_owner)
            self.assertEqual(selected['water_units'], snapshot.water_units)
            self.assertIs(selected['pail_visible'], snapshot.pail_owner == 'actor')
            phases.add(snapshot.phase_id)
            if snapshot.phase_id in samples:
                samples[snapshot.phase_id].add(selected['frame_index'])
                self.assertEqual(selected['frame_index'], snapshot.crank_sample)
            if snapshot.phase_id == 'fill':
                stopped.add((selected['pose_id'], selected['crank_sample']))
                self.assertEqual(snapshot.crank_direction, 0)
            if snapshot.phase_id in ('guide_into_shaft', 'lower', 'fill', 'raise', 'secure'):
                phase = snapshot.crank_phase*math.tau
                knob = [origin[0]+geometry['crank_pivot_local'][0]
                        +geometry['crank_radii_local'][0]*math.cos(phase),
                        origin[1]+geometry['crank_pivot_local'][1]
                        +geometry['crank_radii_local'][1]*math.sin(phase)]
                hand = [station[i]-selected['draw_anchor_logical'][i]
                        +selected['hand_grip_logical'][i] for i in (0, 1)]
                self.assertLessEqual(math.dist(hand, knob), 4,
                                     'Operating and held support must fit the real stopped/moving angle')
            if snapshot.completed:
                break
            if snapshot.phase_id in gates:
                self.assertTrue(model.signal_ready(token, gates[snapshot.phase_id]))
            model.update(1/60)
        else:
            self.fail('The bounded authoring trace did not finish')
        self.assertEqual(phases, set(model.contract['phase_order']))
        self.assertEqual(samples, {'lower': set(range(16)), 'raise': set(range(16))})
        self.assertEqual(len(stopped), 1)
        self.assertNotEqual(next(iter(stopped))[1], 0,
                            'The real fill hold exercises an actual nonzero crank stop')

    def test_cancelled_pre_attach_snapshot_keeps_the_actor_owned_pail_visible(self):
        mechanism = module('gardener_cancel_mechanism', ROOT/'well_mechanism.py')
        model = mechanism.WellMechanism()
        token = model.reserve('sanctuary_gardener', 'gardener_pail')
        model.abort(token)
        state = model.snapshot()
        before = state.to_dict()
        self.assertTrue(state.cancelled)
        self.assertEqual(state.pail_owner, 'actor')
        self.assertTrue(self.presentation.select_pose(state)['pail_visible'])
        self.assertEqual(model.snapshot().to_dict(), before)

    def test_fresh_and_reset_idle_snapshots_do_not_invent_a_pail(self):
        mechanism = module('gardener_idle_mechanism', ROOT/'well_mechanism.py')
        model = mechanism.WellMechanism()
        for reset in (False, True):
            if reset:
                model.reserve('sanctuary_gardener', 'gardener_pail')
                model.reset()
            state = model.snapshot()
            before = state.to_dict()
            self.assertEqual(state.phase_id, 'idle')
            self.assertIsNone(state.pail_id)
            self.assertFalse(self.presentation.select_pose(state)['pail_visible'])
            self.assertEqual(model.snapshot().to_dict(), before)

    def test_fill_variants_keep_each_tilt_exterior_and_alpha_unchanged(self):
        grouped = {}
        for variant in self.manifest['pails']['variants']:
            grouped.setdefault(variant['angle'], {})[variant['units']] = variant
        self.assertIn(0, grouped)
        self.assertTrue(any(angle < 0 for angle in grouped))
        self.assertTrue(any(angle > 0 for angle in grouped))
        for angle, variants in grouped.items():
            self.assertEqual(set(variants), set(range(7)), angle)
            empty = rgba(PACK/variants[0]['file'])
            for units, variant in variants.items():
                with self.subTest(angle=angle, units=units):
                    image = rgba(PACK/variant['file'])
                    interior = gray(PACK/variant['interior_mask'])
                    self.assertEqual(image.size, empty.size)
                    self.assertEqual(interior.size, image.size)
                    self.assertEqual(image.getchannel('A').tobytes(),
                                     empty.getchannel('A').tobytes())
                    self.assertLessEqual(set(image.getchannel('A').tobytes()), {0, 255})
                    self.assertIsNone(ImageChops.multiply(
                        changed_mask(image, empty), ImageChops.invert(interior)).getbbox())
                    self.assertEqual(variant['grip_logical'], variants[0]['grip_logical'])

    def test_pail_tilts_are_rigid_turns_of_the_canonical_well_drawing(self):
        canonical = json.loads((WELL_PACK/'manifest.json').read_text())['pail']
        for variant in self.manifest['pails']['variants']:
            with self.subTest(angle=variant['angle'], units=variant['units']):
                image = rgba(PACK/variant['file'])
                source = rgba(WELL_PACK/next(record['file'] for record in canonical['variants']
                                            if record['units'] == variant['units']))
                anchor = variant['grip_logical']
                original_anchor = canonical['grip_logical']
                offset = tuple(round(2*(anchor[i]-original_anchor[i])) for i in (0, 1))
                expected = Image.new('RGBA', image.size)
                expected.alpha_composite(source, offset)
                expected = expected.rotate(variant['angle'], resample=Image.Resampling.NEAREST,
                                           center=tuple(2*value for value in anchor))
                self.assertEqual(image.tobytes(), expected.tobytes())
                bounds = image.getbbox()
                self.assertGreater(min(bounds), 0)
                self.assertLess(bounds[2], image.width)
                self.assertLess(bounds[3], image.height)

    def test_exports_are_deterministic_and_match_the_staged_bank(self):
        first = self.builder.products()
        self.assertEqual(first, self.builder.products())
        self.assertTrue(first)
        prefix = 'assets/characters/npcs/female_02/gardener_well_hd/'
        for relative, raw in first.items():
            self.assertTrue(relative.startswith(prefix), relative)
            self.assertEqual((ROOT/relative).read_bytes(), raw, relative)

    def test_check_mode_is_read_only(self):
        def forbidden(*args, **kwargs):
            raise AssertionError('A read-only gardener check attempted a filesystem write')
        with patch.object(Path, 'write_bytes', forbidden), \
                patch.object(Path, 'write_text', forbidden), \
                patch.object(Path, 'mkdir', forbidden), redirect_stdout(io.StringIO()):
            self.builder.build(check=True)

    def test_stale_check_fails_without_repairing_the_output(self):
        original = Path.read_bytes
        target = PACK/'animations.json'
        def stale(path):
            return b'stale output fixture' if path == target else original(path)
        with patch.object(Path, 'read_bytes', stale), \
                patch.object(Path, 'write_bytes', side_effect=AssertionError('Attempted repair')):
            with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()):
                self.builder.build(check=True)


if __name__ == '__main__':
    unittest.main()
