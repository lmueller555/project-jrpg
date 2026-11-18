"""Authoring contracts for the staged well; no live animation migration claimed."""
from contextlib import redirect_stdout
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'assets/terrain/eldenmere/well_hd'
SOURCE = ROOT / 'assets/source/terrain/eldenmere/well_hd'


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


def values(record):
    if isinstance(record, dict):
        for item in record.values():
            yield from values(item)
    elif isinstance(record, list):
        for item in record:
            yield from values(item)
    elif isinstance(record, str):
        yield record


class WellPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads((PACK / 'manifest.json').read_text())
        cls.recipe = json.loads((SOURCE / 'recipe.json').read_text())
        spec = importlib.util.spec_from_file_location(
            'staged_well_builder', ROOT / 'tools/build_eldenmere_well_pack.py')
        cls.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.builder)

    def test_staged_approval_and_runtime_state_remain_separate(self):
        self.assertEqual(self.pack['integration_status'], 'staged')
        self.assertEqual(self.pack['visual_approval'], 'pending_user_review')
        self.assertIs(self.pack['runtime_activation'], False)
        self.assertEqual(self.pack['artwork_pixels_per_world_pixel'], 2)
        for name in ('assets/maps/eldenmere/playable/map.json',
                     'assets/maps/eldenmere/town_hd/manifest.json'):
            live = json.loads((ROOT / name).read_text())
            self.assertFalse(any('assets/terrain/eldenmere/well_hd/' in item
                                 for item in values(live)), name)

    def test_assembly_canvas_and_registered_source_recipe(self):
        assembly = self.pack['assembly']
        self.assertEqual(assembly['artwork_size'],
                         [2 * n for n in assembly['logical_size']])
        self.assertEqual(rgba(PACK / assembly['file']).size,
                         tuple(assembly['artwork_size']))
        self.assertEqual(self.pack['source_recipe_sha256'],
                         sha256((SOURCE / 'recipe.json').read_bytes()).hexdigest())
        self.assertEqual(assembly['world_position'], [492, 800])
        self.assertEqual(assembly['draw_anchor_logical'], [0, 0])
        self.assertEqual(assembly['ground_anchor_logical'], [36, 64])

    def test_registry_geometry_provenance_and_export_hashes_match_sources(self):
        self.assertEqual(self.pack['geometry'], self.recipe['well'])
        self.assertEqual(self.pack['sources'], self.recipe['source_normalization'])
        exporter = ROOT / self.pack['exporter']
        self.assertEqual(sha256(exporter.read_bytes()).hexdigest(),
                         self.pack['exporter_sha256'])
        products = self.builder.products()
        recorded = set()
        for record in self.pack['exports']:
            with self.subTest(export=record['file']):
                relative = Path(record['file'])
                self.assertFalse(relative.is_absolute())
                self.assertNotIn('..', relative.parts)
                self.assertNotIn(relative.as_posix(), recorded)
                recorded.add(relative.as_posix())
                path = PACK / relative
                self.assertEqual(sha256(path.read_bytes()).hexdigest(), record['sha256'])
                with Image.open(path) as image:
                    self.assertEqual(list(image.size), record['artwork_size'])
                    self.assertEqual(image.mode, record['mode'])
        prefix = 'assets/terrain/eldenmere/well_hd/'
        self.assertEqual(recorded,
                         {name[len(prefix):] for name in products if name.endswith('.png')})

    def test_retained_masters_are_hashed_and_fitted_as_complete_drawings(self):
        for record in self.recipe['source_normalization']:
            with self.subTest(source=record['id']):
                path = SOURCE / record['file']
                self.assertEqual(sha256(path.read_bytes()).hexdigest(), record['sha256'])
                with Image.open(path) as original:
                    self.assertEqual(list(original.size), record['source_artwork_size'])
                left, top, right, bottom = record['crop_artwork']
                source_width, source_height = record['source_artwork_size']
                self.assertTrue(0 <= left < right <= source_width)
                self.assertTrue(0 <= top < bottom <= source_height)
                width, height = record['resize_artwork']
                # A complete retained drawing may round either output axis by
                # one artwork pixel; separately stretching its parts is invalid.
                self.assertLessEqual(abs(width * (bottom - top) - height * (right - left)),
                                     max(right - left, bottom - top))
                x, y = record['offset_artwork']
                canvas_width, canvas_height = record['canvas_artwork']
                self.assertTrue(0 <= x and 0 <= y)
                self.assertLessEqual(x + width, canvas_width)
                self.assertLessEqual(y + height, canvas_height)
                self.assertEqual(record['resampling'], 'nearest')

    def test_ground_and_stations_share_logical_coordinates_and_clear_probes(self):
        well = self.recipe['well']
        origin = well['world_position_logical']
        local = well['ground_rect_logical']
        actual = [origin[0] + local[0], origin[1] + local[1], *local[2:]]
        layout = json.loads((ROOT / well['ground_source']['file']).read_text())
        self.assertEqual(actual, layout[well['ground_source']['field']])
        self.assertEqual(actual, well['ground_rect_world_logical'])
        self.assertEqual([origin[i] + well['ground_anchor_logical'][i] for i in (0, 1)],
                         well['ground_anchor_world_logical'])
        town = json.loads((ROOT / 'assets/maps/eldenmere/playable/map.json').read_text())
        collision = gray(ROOT / town['collision'])
        for station in well['stations']:
            with self.subTest(station=station['id']):
                self.assertEqual([origin[i] + station['feet_local_logical'][i]
                                  for i in (0, 1)], station['feet_world_logical'])
                self.assertIn(station['contact_anchor'], well['anchors_logical'])
                for probe_key in ('gardener_probe_logical', 'player_probe_logical'):
                    width, height = station[probe_key]
                    x, y = station['feet_world_logical']
                    box = (x - width // 2, y - height // 2,
                           x - width // 2 + width, y - height // 2 + height)
                    self.assertGreaterEqual(box[0], 0)
                    self.assertGreaterEqual(box[1], 0)
                    self.assertLessEqual(box[2], collision.width)
                    self.assertLessEqual(box[3], collision.height)
                    self.assertIsNone(collision.crop(box).getbbox(), probe_key)

    def test_mechanism_targets_are_centered_and_do_not_claim_moving_frames(self):
        well = self.recipe['well']
        anchors = well['anchors_logical']
        reference = well['mechanism_reference']
        orbit = reference['crank_orbit']
        self.assertEqual(orbit['center_logical'], anchors['crank_pivot'])
        self.assertTrue(all(value > 0 for value in orbit['radii_logical']))
        self.assertEqual(anchors['shaft_center'][0], anchors['rope_exit'][0])
        self.assertEqual(anchors['shaft_center'][0], anchors['water_contact'][0])
        self.assertEqual(orbit['rendered_animation_frames'], 0)
        self.assertIs(reference['motion_durations_authored'], False)
        self.assertLessEqual(reference['maximum_preferred_handoff_snap_logical'], 4)

    def test_authored_layers_and_masks_have_hard_native_edges(self):
        size = tuple(self.pack['assembly']['artwork_size'])
        for record in self.pack['layers']:
            with self.subTest(layer=record['id']):
                image = rgba(PACK / record['file'])
                self.assertEqual(image.size, size)
                self.assertLessEqual(set(image.getchannel('A').tobytes()), {0, 255})
                self.assertIsNotNone(image.getbbox())
                self.assertGreater(record['opacity'], 0)
                self.assertLessEqual(record['opacity'], 1)
        for record in self.pack['masks']:
            with self.subTest(mask=record['id']):
                image = gray(PACK / record['file'])
                self.assertEqual(image.size, size)
                self.assertLessEqual(set(image.tobytes()), {0, 255})
                self.assertIsNotNone(image.getbbox())

    def test_shaped_water_aperture_and_occluder_masks_are_separate(self):
        masks = {record['id']: gray(PACK / record['file'])
                 for record in self.pack['masks']}
        aperture, water = masks['aperture'], masks['water']
        self.assertIsNone(ImageChops.subtract(water, aperture).getbbox())
        self.assertIsNone(ImageChops.multiply(water, masks['near_wall']).getbbox())
        self.assertIsNone(ImageChops.multiply(water, masks['canopy']).getbbox())
        box = aperture.getbbox()
        self.assertIsNotNone(box)
        self.assertLess(sum(value != 0 for value in aperture.tobytes()),
                        (box[2] - box[0]) * (box[3] - box[1]))
        layers = {record['id']: rgba(PACK / record['file'])
                  for record in self.pack['layers']}
        self.assertIsNotNone(layers['water'].getbbox())
        self.assertIsNone(ImageChops.subtract(
            layers['water'].getchannel('A'), water).getbbox())
        # Water remains visible in the actual static assembly rather than
        # being repainted by a near-rim slice, the original live well defect.
        actual = rgba(PACK / self.pack['assembly']['file'])
        covered = ImageChops.multiply(changed_mask(actual, layers['water']),
                                      layers['water'].getchannel('A'))
        self.assertIsNone(covered.getbbox())

    def test_water_partition_excludes_the_retained_masters_near_right_stone_edge(self):
        layers = {record['id']: rgba(PACK / record['file'])
                  for record in self.pack['layers']}
        masks = {record['id']: gray(PACK / record['file'])
                 for record in self.pack['masks']}
        structure = rgba(PACK / 'structure.png')
        assembly = rgba(PACK / self.pack['assembly']['file'])
        # These actual warm masonry pixels were incorrectly assigned to the
        # first water polygon. Protect material ownership at that boundary,
        # without imposing a hue rule that could reject legitimate reflections.
        for point in ((96, 135), (93, 139)):
            with self.subTest(artwork_point=point):
                self.assertEqual(masks['water'].getpixel(point), 0)
                self.assertEqual(layers['water'].getpixel(point)[3], 0)
                stone = layers['stone_far'].getpixel(point)
                self.assertEqual(stone[3], 255)
                self.assertEqual(stone, structure.getpixel(point))
                self.assertEqual(stone, assembly.getpixel(point))

    def test_declared_layers_reconstruct_assembly_and_own_translucency(self):
        size = tuple(self.pack['assembly']['artwork_size'])
        assembled = Image.new('RGBA', size)
        translucent_support = Image.new('L', size)
        for record in self.pack['layers']:
            image = rgba(PACK / record['file'])
            opacity = record['opacity']
            if opacity < 1:
                translucent_support = ImageChops.lighter(
                    translucent_support, image.getchannel('A'))
                image.putalpha(image.getchannel('A').point(
                    lambda value: round(value * opacity)))
            assembled.alpha_composite(image)
        actual = rgba(PACK / self.pack['assembly']['file'])
        self.assertEqual(assembled.tobytes(), actual.tobytes())
        alpha = actual.getchannel('A')
        fractional = alpha.point(lambda value: 255 if 0 < value < 255 else 0)
        self.assertIsNone(ImageChops.subtract(
            fractional, translucent_support).getbbox())

    def test_pail_fill_is_confined_to_interior_and_keeps_wood_and_handle(self):
        pail = self.pack['pail']
        self.assertEqual(pail['artwork_size'], [2 * n for n in pail['logical_size']])
        interior = gray(PACK / pail['masks']['interior'])
        mouth = gray(PACK / pail['masks']['mouth'])
        handle = gray(PACK / pail['masks']['handle'])
        body = gray(PACK / pail['masks']['body'])
        self.assertIsNotNone(interior.getbbox())
        self.assertIsNotNone(handle.getbbox())
        self.assertIsNone(ImageChops.subtract(interior, mouth).getbbox())
        self.assertIsNone(ImageChops.multiply(interior, handle).getbbox())
        self.assertIsNone(ImageChops.multiply(interior, body).getbbox())
        variants = {record['units']: rgba(PACK / record['file'])
                    for record in pail['variants']}
        self.assertEqual(set(variants), set(range(7)))
        empty = variants[0]
        changed = []
        for units, image in sorted(variants.items()):
            with self.subTest(units=units):
                self.assertEqual(image.size, tuple(pail['artwork_size']))
                self.assertLessEqual(set(image.getchannel('A').tobytes()), {0, 255})
                self.assertEqual(image.getchannel('A').tobytes(),
                                 empty.getchannel('A').tobytes())
                delta = changed_mask(image, empty)
                self.assertIsNone(ImageChops.multiply(
                    delta, ImageChops.invert(interior)).getbbox())
                changed.append(delta.tobytes())
        self.assertNotEqual(changed[0], changed[-1])
        for units in range(pail['capacity_units']):
            self.assertNotEqual(variants[units].tobytes(), variants[units + 1].tobytes())

    def test_generated_outputs_are_deterministic_and_match_exports(self):
        first = self.builder.products()
        self.assertEqual(first, self.builder.products())
        prefix = 'assets/terrain/eldenmere/well_hd/'
        self.assertTrue(first)
        for name, raw in first.items():
            self.assertTrue(name.startswith(prefix), name)
            self.assertEqual((ROOT / name).read_bytes(), raw, name)

    def test_check_mode_never_calls_a_writer(self):
        def forbidden(*args, **kwargs):
            raise AssertionError('A readonly pack check attempted a filesystem write')
        with patch.object(Path, 'write_bytes', forbidden), \
                patch.object(Path, 'write_text', forbidden), \
                patch.object(Path, 'mkdir', forbidden), redirect_stdout(io.StringIO()):
            self.builder.build(check=True)

    def test_check_detects_a_stale_export_without_repairing_it(self):
        original = Path.read_bytes
        target = PACK / self.pack['assembly']['file']
        def stale(path):
            return b'stale export fixture' if path == target else original(path)
        def forbidden(*args, **kwargs):
            raise AssertionError('A stale readonly check attempted to repair an export')
        with patch.object(Path, 'read_bytes', stale), \
                patch.object(Path, 'write_bytes', forbidden), \
                patch.object(Path, 'write_text', forbidden), \
                patch.object(Path, 'mkdir', forbidden), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.builder.build(check=True)


if __name__ == '__main__':
    unittest.main()
