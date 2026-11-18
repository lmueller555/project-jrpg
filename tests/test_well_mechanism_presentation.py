"""Native staged-mechanism exports and bounded, observational presentation."""
from contextlib import redirect_stdout
from copy import deepcopy
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops

from tools import build_eldenmere_well_mechanism as builder
from well_mechanism import WellMechanism
from well_mechanism_presentation import WellMechanismPresentation


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / builder.PACK
BASE_PACK = ROOT / 'assets/terrain/eldenmere/well_hd'
CONTRACT = ROOT / 'assets/source/terrain/eldenmere/well_hd/mechanism/contract.json'


def load(path, mode='RGBA'):
    with Image.open(path) as source:
        return source.convert(mode)


def delta_mask(first, second):
    channels = ImageChops.difference(first.convert('RGBA'), second.convert('RGBA')).split()
    result = channels[0]
    for channel in channels[1:]:
        result = ImageChops.lighter(result, channel)
    return result.point(lambda value: 255 if value else 0)


def fixture(phase='await_loading', progress=0, *, owner='actor', grip=None,
            region='loading_foreground', units=0, crank=0):
    contract = json.loads(CONTRACT.read_text())
    geometry = contract['geometry']
    grip = geometry['loading_grip_local'] if grip is None else grip
    offset = geometry['hook_rope_offset_logical']
    rope_end = [grip[i]+offset[i] for i in (0, 1)]
    return {'phase_id': phase, 'phase_progress': progress,
            'bucket_grip_local': list(grip),
            'rope_origin_local': geometry['rope_origin_local'],
            'rope_end_local': rope_end, 'rope_deployed': True, 'hook_visible': True,
            'pail_owner': owner, 'water_units': units, 'bucket_region': region,
            'crank_sample': crank, 'bucket_submerged': False, 'water_contact': False}


class WellMechanismExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((PACK/'manifest.json').read_text())
        cls.recipe = json.loads((ROOT/builder.SOURCE).read_text())
        cls.contract = json.loads(CONTRACT.read_text())

    def test_staged_registry_has_exact_source_and_output_provenance(self):
        manifest = self.manifest
        self.assertEqual(manifest['integration_status'], 'staged')
        self.assertIs(manifest['runtime_activation'], False)
        self.assertEqual(manifest['visual_approval'], 'pending_user_review')
        self.assertEqual(manifest['contract_schema_version'], self.contract['schema_version'])
        for path, expected in manifest['sources'].items():
            self.assertEqual(sha256((ROOT/path).read_bytes()).hexdigest(), expected, path)
        self.assertEqual(sha256((ROOT/manifest['exporter']).read_bytes()).hexdigest(),
                         manifest['exporter_sha256'])
        seen = set()
        for record in manifest['exports']:
            relative = Path(record['file'])
            self.assertFalse(relative.is_absolute())
            self.assertNotIn('..', relative.parts)
            self.assertNotIn(record['file'], seen)
            seen.add(record['file'])
            raw = (PACK/relative).read_bytes()
            self.assertEqual(sha256(raw).hexdigest(), record['sha256'])
            with Image.open(io.BytesIO(raw)) as image:
                self.assertEqual(list(image.size), record['artwork_size'])
                self.assertEqual(image.mode, record['mode'])
                alpha = image.getchannel('A') if image.mode == 'RGBA' else image
                self.assertLessEqual(set(alpha.tobytes()), {0, 255})

    def test_crank_orbit_is_centered_and_spindle_uses_the_same_phase_samples(self):
        crank = self.manifest['crank']
        self.assertEqual(crank['pivot_logical'], self.contract['geometry']['crank_pivot_local'])
        self.assertEqual(crank['radii_logical'], self.contract['geometry']['crank_radii_local'])
        cx, cy = crank['pivot_logical']; rx, ry = crank['radii_logical']
        handles = [record['handle_logical'] for record in crank['frames']]
        self.assertAlmostEqual(sum(p[0] for p in handles)/len(handles), cx, places=10)
        self.assertAlmostEqual(sum(p[1] for p in handles)/len(handles), cy, places=10)
        for record in crank['frames']:
            x, y = record['handle_logical']
            self.assertAlmostEqual(((x-cx)/rx)**2+((y-cy)/ry)**2, 1, places=10)
            self.assertAlmostEqual(record['phase'], record['sample']/len(handles), places=10)
        self.assertEqual(len(self.manifest['spindle']['frames']), len(crank['frames']))

    def test_water_marks_are_confined_to_the_actual_painted_water_mask(self):
        water = self.manifest['water']
        allowed = load(ROOT/water['mask'], 'L')
        for path in (*water['ambient_frames'], *water['contact_frames']):
            image = load(PACK/path)
            self.assertIsNone(ImageChops.subtract(image.getchannel('A'), allowed).getbbox(), path)
        # These source pixels were the concrete PR1 regression: tan coping
        # must never be part of the animated surface or its contact effects.
        for point in ((96, 135), (93, 139)):
            self.assertEqual(allowed.getpixel(point), 0)

    def test_spindle_marks_remain_on_the_authored_drum(self):
        drum = load(BASE_PACK/'layers/windlass.png').getchannel('A')
        coverage = load(PACK/self.manifest['spindle']['coverage_mask'], 'L')
        self.assertIsNone(ImageChops.subtract(coverage, drum).getbbox())
        for path in self.manifest['spindle']['frames']:
            alpha = load(PACK/path).getchannel('A')
            self.assertIsNone(ImageChops.subtract(alpha, coverage).getbbox())

    def test_hook_art_and_controller_use_the_same_rope_attachment(self):
        hook = self.manifest['hook']
        expected = self.contract['geometry']['hook_rope_offset_logical']
        self.assertEqual([(hook['rope_anchor_artwork'][i]-hook['attachment_anchor_artwork'][i])/2
                          for i in (0, 1)], expected)

    def test_deterministic_exports_and_check_mode_do_not_write(self):
        first = builder.products()
        self.assertEqual(first, builder.products())
        self.assertTrue(first)
        for path, raw in first.items():
            self.assertTrue(path.startswith(builder.PACK+'/'))
            self.assertEqual((ROOT/path).read_bytes(), raw)
        def forbidden(*args, **kwargs):
            raise AssertionError('Read-only export check called a writer')
        with patch.object(Path, 'write_bytes', forbidden), \
                patch.object(Path, 'write_text', forbidden), \
                patch.object(Path, 'mkdir', forbidden), redirect_stdout(io.StringIO()):
            builder.build(check=True)

    def test_stale_check_fails_without_repairing_the_export(self):
        actual_read = Path.read_bytes
        target = PACK/self.manifest['crank']['frames'][0]['file']
        def read_bytes(path):
            return b'corrupted staged fixture' if path == target else actual_read(path)
        def forbidden(*args, **kwargs):
            raise AssertionError('Stale read-only check tried to repair a file')
        with patch.object(Path, 'read_bytes', read_bytes), \
                patch.object(Path, 'write_bytes', forbidden), \
                patch.object(Path, 'mkdir', forbidden), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                builder.build(check=True)


class WellMechanismPresentationTests(unittest.TestCase):
    def setUp(self):
        self.presentation = WellMechanismPresentation()

    def test_native_size_and_reduced_ambient_still(self):
        presentation = self.presentation
        snapshot = fixture()
        first = presentation.render(snapshot, ambient_ms=0, reduced_motion=True)
        later = presentation.render(snapshot, ambient_ms=1000, reduced_motion=True)
        self.assertEqual(first.size, (144, 176))
        self.assertEqual(first.mode, 'RGBA')
        self.assertEqual(first.tobytes(), later.tobytes())
        self.assertEqual(presentation.cache_info()['density'], 2)

    def test_idle_ambient_changes_only_visible_water(self):
        snapshot = fixture()
        first = self.presentation.render(snapshot, ambient_ms=0)
        later = self.presentation.render(snapshot, ambient_ms=400)
        delta = delta_mask(first, later)
        allowed = load(ROOT/self.presentation.manifest['water']['mask'], 'L')
        self.assertIsNotNone(delta.getbbox())
        self.assertIsNone(ImageChops.subtract(delta, allowed).getbbox())

    def test_only_the_well_owner_draws_one_canonical_loading_pail(self):
        actor = fixture(owner='actor', units=6)
        well = {**actor, 'pail_owner': 'well'}
        actor_image = self.presentation.render(actor, reduced_motion=True)
        expected = actor_image.copy()
        grip = actor['bucket_grip_local']
        pail_grip = self.presentation.pail_grip
        point = tuple(round((grip[i]-pail_grip[i])*2) for i in (0, 1))
        expected.alpha_composite(self.presentation.pails[6], point)
        actual = self.presentation.render(well, reduced_motion=True)
        self.assertEqual(expected.tobytes(), actual.tobytes())
        self.assertNotEqual(actor_image.tobytes(), actual.tobytes())

    def test_declared_dynamic_regions_preserve_every_other_structural_pixel(self):
        original = load(BASE_PACK/'assembled.png')
        geometry = json.loads(CONTRACT.read_text())['geometry']
        for phase, start_key, end_key in (
                ('guide_into_shaft', 'loading_grip_local', 'guided_grip_local'),
                ('lower', 'guided_grip_local', 'lowered_grip_local'),
                ('raise', 'lowered_grip_local', 'guided_grip_local'),
                ('secure', 'guided_grip_local', 'loading_grip_local')):
            for progress in (0, .25, .5, .75, 1):
                with self.subTest(phase=phase, progress=progress):
                    grip = [geometry[start_key][i]+(geometry[end_key][i]-geometry[start_key][i])*progress
                            for i in (0, 1)]
                    snapshot = fixture(phase, progress, owner='well', grip=grip,
                                       region='shaft' if phase in ('lower', 'raise') else 'loading_foreground',
                                       units=6 if phase in ('raise', 'secure') else 0,
                                       crank=int(progress*15))
                    image = self.presentation.render(snapshot, ambient_ms=400)
                    coverage = self.presentation.dynamic_mask(snapshot)
                    delta = delta_mask(original, image)
                    self.assertIsNone(ImageChops.subtract(delta, coverage).getbbox())
                    self.assertLess(sum(bool(value) for value in coverage.tobytes()),
                                    coverage.width*coverage.height)
                    for point in ((96, 135), (93, 139)):
                        self.assertEqual(image.getpixel(point), original.getpixel(point))

    def test_returned_images_cannot_poison_the_bounded_frame_cache(self):
        snapshot = fixture()
        first = self.presentation.render(snapshot)
        expected = first.tobytes()
        first.putpixel((0, 0), (255, 0, 255, 255))
        again = self.presentation.render(snapshot)
        self.assertEqual(again.tobytes(), expected)
        self.assertGreaterEqual(self.presentation.cache_info()['hits'], 1)
        limit = self.presentation.cache_info()['limit']
        for index in range(limit*3):
            pose = fixture('lower', index/(limit*3), owner='well',
                           grip=(36, 54+index/(limit*3)*18), region='shaft',
                           crank=index % 16)
            self.presentation.render(pose, ambient_ms=index*37)
        info = self.presentation.cache_info()
        self.assertLessEqual(info['entries'], info['limit'])
        self.assertLessEqual(info['composite_bytes'], info['limit']*144*176*4)

    def test_presentation_does_not_modify_the_snapshot_mapping(self):
        snapshot = fixture('fill', .5, owner='well', grip=(36, 72), region='shaft', units=3)
        before = deepcopy(snapshot)
        self.presentation.render(snapshot, ambient_ms=400)
        self.presentation.dynamic_mask(snapshot)
        self.assertEqual(snapshot, before)

    def test_actual_controller_snapshots_and_trace_mappings_render_identically(self):
        model = WellMechanism()
        token = model.reserve('gardener', 'garden_pail')
        gates = {'await_loading': 'loading', 'await_operator': 'operator',
                 'await_retrieval': 'loading'}
        seen = set()
        original = load(BASE_PACK/'assembled.png')
        for _ in range(3000):
            snapshot = model.snapshot()
            if snapshot.phase_id in gates:
                model.signal_ready(token, gates[snapshot.phase_id])
                snapshot = model.snapshot()
            if snapshot.phase_id not in seen:
                model.drain_events()
                image = self.presentation.render(snapshot, ambient_ms=300)
                mapping_image = self.presentation.render(snapshot.to_dict(), ambient_ms=300)
                self.assertEqual(image.tobytes(), mapping_image.tobytes())
                self.assertEqual(model.snapshot(), snapshot)
                self.assertEqual(model.drain_events(), ())
                delta = delta_mask(original, image)
                self.assertIsNone(ImageChops.subtract(
                    delta, self.presentation.dynamic_mask(snapshot)).getbbox())
                seen.add(snapshot.phase_id)
            if snapshot.phase_id == 'complete':
                break
            model.update(1/60)
        else:
            self.fail('Staged model trace failed to complete')
        self.assertTrue({'attach', 'guide_into_shaft', 'lower', 'fill', 'raise',
                         'secure', 'detach', 'complete'} <= seen)


if __name__ == '__main__':
    unittest.main()
