"""Ground-only streets preserve physical interfaces and native material phase."""
import copy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageChops, ImageDraw

from tools.eldenmere_hd_materials import Materials
from tools.eldenmere_settlement_streets import paint_streets, resolve_streets

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT/'assets/source/maps/eldenmere/settlement/recipe.json'


def read(path):
    return json.loads(Path(path).read_text())


def town():
    return {'id': 'eldenmere.playable', 'size_pixels': [128, 96], 'tile_size': 24,
            'player_probe_size': [24, 12], 'player_draw_anchor': [12, 30],
            'doors': [{'id': 'cottage', 'anchor': [64, 32], 'entry_side': 'north',
                       'open_radius': 30, 'close_radius': 38, 'entry_half_width': 8}],
            'entities': [], 'world_links': []}


def treatment(**extra):
    return {'id': 'settlement.street.fixture', 'material': 'dirt',
            'role': 'primary', 'shape': 'route',
            'points': [[16, 32], [112, 32]], 'width': 16, **extra}


def recipe(treatments):
    return {'version': 1, 'id': 'eldenmere.settlement.framework',
            'status': 'ground_only', 'scene': 'eldenmere.playable',
            'placements': [], 'ground_treatments': treatments}


def base_image():
    # Spatial variation makes accidental broad repainting or rephasing visible.
    image = Image.new('RGBA', (256, 192))
    image.putdata([(18+x % 43, 78+y % 47, 31+(x+y) % 29, 255)
                   for y in range(192) for x in range(256)])
    return image


class StreetRecipeTests(unittest.TestCase):
    def test_only_explicit_ground_only_activation_accepts_treatments(self):
        for status in ('framework_only', 'active', None):
            config = recipe([treatment()])
            config['status'] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                resolve_streets(ROOT, town(), config)
        for field in ('placements',):
            config = recipe([treatment()])
            config[field] = [{'id': 'settlement.not_ground'}]
            with self.subTest(field=field), self.assertRaises(ValueError):
                resolve_streets(ROOT, town(), config)
        self.assertEqual(resolve_streets(ROOT, town(), recipe([])), [])

    def test_unsupported_mutations_invalid_materials_and_malformed_shapes_fail_closed(self):
        changes = ({'collision': True}, {'navigation': [0, 0, 8, 8]}, {'entities': []},
                   {'material': 'water'}, {'role': 'unregistered_yard'},
                   {'shape': 'polygon'}, {'id': 'existing_lane'},
                   {'width': 11}, {'width': 73}, {'width': float('nan')},
                   {'points': [[16, 32]]}, {'points': [[-1, 32], [112, 32]]},
                   {'points': [[16.25, 32], [112, 32]]},
                   {'points': [[16, True], [112, 32]]})
        for change in changes:
            invalid = treatment()
            invalid.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                resolve_streets(ROOT, town(), recipe([invalid]))
        duplicate = treatment()
        with self.assertRaises(ValueError):
            resolve_streets(ROOT, town(), recipe([duplicate, copy.deepcopy(duplicate)]))
        for rect in ([16, 16, 0, 12], [16, 16, -12, 12], [120, 16, 24, 12]):
            invalid = {'id': 'settlement.street.rect', 'shape': 'rect',
                       'material': 'stone', 'role': 'junction', 'rect': rect}
            with self.subTest(rect=rect), self.assertRaises(ValueError):
                resolve_streets(ROOT, town(), recipe([invalid]))

    def test_doorstep_geometry_follows_its_loaded_entrance(self):
        config = recipe([{'id': 'settlement.street.threshold', 'shape': 'doorstep',
                          'door': 'cottage', 'width': 24, 'depth': 24,
                          'material': 'stone', 'role': 'doorstep'}])
        current = town()
        first = resolve_streets(ROOT, current, config)[0]
        self.assertEqual(first['rect'], [52, 26, 24, 24])
        self.assertEqual(first['source_shape'], 'doorstep')
        current['doors'][0]['anchor'] = [88.5, 48.5]
        second = resolve_streets(ROOT, current, config)[0]
        self.assertEqual(second['rect'], [76.5, 42.5, 24, 24])
        self.assertEqual(config['ground_treatments'][0]['door'], 'cottage')
        for change in ({'door': 'missing'}, {'width': 23}, {'width': 49},
                       {'depth': 11}, {'depth': 37}):
            broken = copy.deepcopy(config)
            broken['ground_treatments'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                resolve_streets(ROOT, current, broken)

    def test_source_evidence_must_resolve_without_escaping_the_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'owner.json').write_text(json.dumps({'road': [[16, 32], [112, 32]]}))
            valid = treatment(source_ref={'file': 'owner.json', 'path': ['road']})
            self.assertEqual(len(resolve_streets(root, town(), recipe([valid]))), 1)
            for evidence in ({'file': 'missing.json', 'path': ['road']},
                             {'file': 'owner.json', 'path': ['missing']},
                             {'file': '../owner.json', 'path': ['road']}):
                with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                    resolve_streets(root, town(), recipe([treatment(source_ref=evidence)]))


class StreetNativePaintingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.materials = Materials()

    def paint(self, treatments, blocked=None, base=None):
        if base is None:
            base = base_image()
        if blocked is None:
            blocked = Image.new('L', (128, 96))
        return paint_streets(base, ROOT, town(), recipe(treatments),
                             self.materials, blocked)

    def test_empty_recipe_is_an_identical_native_copy(self):
        before = base_image()
        after, report = self.paint([], base=before)
        self.assertEqual(after.size, before.size)
        self.assertEqual(after.tobytes(), before.tobytes())
        self.assertEqual(report['painted_native_pixels'], 0)
        self.assertIsNone(report['coverage_mask'].getbbox())

    def test_logical_or_wrong_mode_surfaces_are_rejected_before_painting(self):
        invalid = ((Image.new('RGBA', (128, 96)), Image.new('L', (128, 96))),
                   (Image.new('RGB', (256, 192)), Image.new('L', (128, 96))),
                   (base_image(), Image.new('L', (256, 192))),
                   (base_image(), Image.new('RGBA', (128, 96))))
        for base, blocked in invalid:
            with self.subTest(base=(base.mode, base.size), blocked=(blocked.mode, blocked.size)):
                with self.assertRaises(ValueError):
                    self.paint([treatment()], base=base, blocked=blocked)

    def test_paint_is_native_masked_deterministic_and_preserves_blocked_pixels(self):
        before = base_image()
        original = before.tobytes()
        blocked = Image.new('L', (128, 96))
        ImageDraw.Draw(blocked).rectangle((60, 0, 65, 95), fill=1)
        blocked_before = blocked.tobytes()
        config = [treatment()]
        config_before = copy.deepcopy(config)
        first, report = self.paint(config, blocked=blocked, base=before)
        second, again = self.paint(config, blocked=blocked, base=before)
        self.assertEqual(first.size, (256, 192))
        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertEqual(before.tobytes(), original)
        self.assertEqual(blocked.tobytes(), blocked_before)
        self.assertEqual(config, config_before)
        mask = report['coverage_mask']
        self.assertEqual(mask.mode, 'L')
        self.assertEqual(mask.size, first.size)
        self.assertLessEqual(set(mask.tobytes()), {0, 255})
        self.assertGreater(report['painted_native_pixels'], 0)
        self.assertEqual(report['painted_native_pixels'], mask.histogram()[255])
        self.assertEqual(report['painted_logical_area'], mask.histogram()[255]/4)
        self.assertEqual(report['coverage_sha256'], sha256(mask.tobytes()).hexdigest())
        self.assertEqual(report['coverage_sha256'], again['coverage_sha256'])
        difference = ImageChops.difference(first, before).convert('RGB')
        self.assertIsNone(ImageChops.multiply(difference, ImageChops.invert(mask).convert('RGB')).getbbox())
        blocked_native = blocked.point(lambda value: 255 if value else 0).resize(
            first.size, Image.Resampling.NEAREST)
        self.assertIsNone(ImageChops.multiply(difference, blocked_native.convert('RGB')).getbbox())
        self.assertEqual(set(first.getchannel('A').tobytes()), {255})
        # A clear interior patch must retain artwork pixels finer than a
        # nearest-neighbour enlargement of the logical mirror.
        enlarged = first.resize((128, 96), Image.Resampling.NEAREST).resize(
            first.size, Image.Resampling.NEAREST)
        self.assertNotEqual(first.crop((40, 56, 96, 72)).tobytes(),
                            enlarged.crop((40, 56, 96, 72)).tobytes())

    def test_paving_phase_and_contacts_do_not_depend_on_recipe_partitioning(self):
        whole = [{'id': 'settlement.street.whole', 'shape': 'rect', 'material': 'stone',
                  'role': 'junction', 'rect': [16, 16, 72, 48]}]
        split = [{'id': 'settlement.street.west', 'shape': 'rect', 'material': 'stone',
                  'role': 'junction', 'rect': [16, 16, 36, 48]},
                 {'id': 'settlement.street.east', 'shape': 'rect', 'material': 'stone',
                  'role': 'junction', 'rect': [52, 16, 36, 48]}]
        first, first_report = self.paint(whole)
        second, second_report = self.paint(split)
        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertEqual(first_report['coverage_mask'].tobytes(),
                         second_report['coverage_mask'].tobytes())


class LiveSettlementStreetContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.town = read(ROOT/'assets/maps/eldenmere/playable/map.json')
        cls.source = read(RECIPE)

    def test_live_streets_keep_all_architectural_entrances_during_district_dressing(self):
        self.assertEqual(self.source['status'], 'household_dressing')
        self.assertTrue(all(p['district'] in ('serene_terrace','workshop_mill','commons_households') for p in self.source['placements']))
        self.assertTrue(self.source['ground_treatments'])
        authored = read(ROOT/'assets/source/maps/eldenmere/town_hd/recipe.json')
        architecture = read(ROOT/authored['architecture_schedule'])
        actual = {door['id']: door for door in self.town['doors']}
        self.assertEqual(len(actual), 13)
        for building in architecture['buildings']:
            expected = building['entrance']
            door = actual[building['id']]
            for field in ('anchor', 'entry_y', 'entry_side', 'entry_half_width',
                          'open_radius', 'close_radius', 'destination', 'spawn',
                          'arrival_door'):
                if field in expected:
                    self.assertEqual(door[field], expected[field], (building['id'], field))
        self.assertEqual(self.town['overworld_exit'], architecture['protected_southern_exit'])

    def test_every_exported_street_ground_chunk_remains_native(self):
        # Coverage still belongs to native 2x ground; physics remains logical.
        for field in ('collision', 'navigation_allowed'):
            with Image.open(ROOT/self.town[field]) as image:
                self.assertEqual(image.size, tuple(self.town['size_pixels']))
        for record in self.town['ground_overlays']:
            with self.subTest(chunk=record['id']):
                self.assertEqual(record['artwork_pixels_per_world_pixel'], 2)
                for frame in record['frames']:
                    with Image.open(ROOT/frame) as image:
                        self.assertEqual(image.size, tuple(value*2 for value in record['logical_size']))
                        self.assertLessEqual(set(image.getchannel('A').tobytes()), {255})

    def test_active_native_recipe_and_cartography_share_one_exported_network(self):
        report = read(ROOT/'assets/maps/eldenmere/settlement/manifest.json')
        live = read(ROOT/'assets/maps/eldenmere/town_hd/manifest.json')
        treatments = resolve_streets(ROOT, self.town, self.source)
        self.assertEqual(report['status'], 'household_dressing')
        self.assertEqual(report['active_placements'], len(self.source['placements']))
        self.assertEqual(report['active_ground_treatments'], len(treatments))
        self.assertEqual(report['ground_treatments'], treatments)
        self.assertTrue(report['street_network'])
        self.assertEqual(self.town['cartography']['street_network'], report['street_network'])
        self.assertEqual(live['settlement_framework']['active_ground_treatments'], len(treatments))
