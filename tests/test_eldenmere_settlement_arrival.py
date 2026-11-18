"""Arrival pockets preserve the extended exit, existing owners and checkpoints."""
import copy
from functools import lru_cache
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops, ImageDraw

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from tools.eldenmere_settlement_dressing import resolve_arrival
from tools.eldenmere_settlement_inventory import inventory


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/maps/eldenmere/settlement/recipe.json'
REVIEW = ROOT/'docs/reviews/eldenmere_arrival'
SCOPE = [72, 1104, 744, 528]
PARCEL = [96, 1200, 144, 144]
PREVIOUS_LEDGERS = ('settlement_dressing', 'settlement_workyards', 'settlement_commons',
                    'settlement_households', 'settlement_growing')
ALL_LEDGERS = (*PREVIOUS_LEDGERS, 'settlement_arrival')


def read(path):
    return json.loads(Path(path).read_text())


@lru_cache(None)
def catalogue():
    return inventory(ROOT, town=read(ROOT/'assets/maps/eldenmere/playable/map.json'))


def town():
    return {'id': 'eldenmere.playable', 'size_pixels': [1536, 1632],
            'player_probe_size': [24, 12], 'player_draw_anchor': [12, 30],
            'entities': [], 'doors': [],
            'grass': {'instances': [{'id': 'arrival.fixture', 'position': [204, 1308],
                                     'variant': 'dense_hd', 'phase_ms': 200}]}}


def placement(**changes):
    return {'id': 'settlement.arrival.planter', 'parcel': 'inn_frontage',
            'asset': 'exteriors_hd:flowerpot_pair', 'district': 'southern_arrival',
            'position': [144, 1248], 'collision': 'solid',
            'footprint': [2, 18, 20, 4], 'occlusion': 'tall', **changes}


def flower(**changes):
    result = placement(**({'asset': 'vegetation_hd:flowers_white', 'collision': 'none',
                           'occlusion': 'low', **changes}))
    result.pop('footprint')
    return result


def recipe(placements=None, **configuration):
    return {'version': 1, 'id': 'eldenmere.settlement', 'status': 'arrival_dressing',
            'scene': 'eldenmere.playable',
            'districts': [{'id': 'southern_arrival', 'rect': SCOPE.copy()},
                          {'id': 'serene_terrace', 'rect': [120, 120, 600, 336]},
                          {'id': 'workshop_mill', 'rect': [552, 264, 552, 288]},
                          {'id': 'commons_households', 'rect': [144, 480, 672, 696]},
                          {'id': 'eastern_growing', 'rect': [1104, 528, 432, 600]}],
            'placements': [placement()] if placements is None else placements,
            'arrival_dressing': {'district': 'southern_arrival', 'scope_rect': SCOPE.copy(),
                                 'retire_grass_ids': [], 'ground_cells': [],
                                 'parcels': [{'id': 'inn_frontage', 'scope_rect': PARCEL.copy()}],
                                 **configuration}}


def baseline_collision():
    before = read(REVIEW/'before_town.json')
    observed = read(REVIEW/'before_observations.json')['production']
    path = REVIEW/'before_collision.png'
    expected = observed['active_files'][before['collision']]['sha256']
    if sha256(path.read_bytes()).hexdigest() != expected:
        raise AssertionError('Arrival collision witness does not match the captured extended town')
    with Image.open(path) as source:
        result = source.convert('L')
    if result.size != tuple(before['size_pixels']):
        raise AssertionError('Arrival collision witness omits the extended business district')
    return result


class ArrivalRecipeTests(unittest.TestCase):
    def resolve(self, source=None, current=None, protections=()):
        return resolve_arrival(ROOT, town() if current is None else current,
                               recipe() if source is None else source,
                               catalogue(), list(protections))

    def test_explicit_arrival_stage_and_fixed_district_are_required(self):
        for status in ('framework_only', 'ground_only', 'courtyard_dressing', 'workyard_dressing',
                       'commons_dressing', 'household_dressing', 'growing_dressing', 'active', None):
            source = recipe();source['status'] = status
            with self.subTest(status=status), self.assertRaises(ValueError):self.resolve(source)
        for change in ({'district': 'eastern_growing'}, {'scope_rect': [0, 0, 1536, 1632]},
                       {'scope_rect': [72, 1104, 744, 504]}, {'navigation': 'clear'}):
            with self.subTest(change=change), self.assertRaises(ValueError):self.resolve(recipe(**change))
        changed = recipe();changed['districts'][0]['rect'] = [0, 0, 1536, 1632]
        changed['arrival_dressing']['scope_rect'] = [0, 0, 1536, 1632]
        with self.assertRaises(ValueError):self.resolve(changed)

    def test_pockets_are_named_unique_disjoint_and_native_bounded(self):
        invalid = ([], [{'id': 'new_gate', 'scope_rect': PARCEL}],
                   [{'id': 'inn_frontage', 'scope_rect': PARCEL}]*2,
                   [{'id': 'inn_frontage', 'scope_rect': PARCEL},
                    {'id': 'shop_frontage', 'scope_rect': [216, 1224, 96, 96]}],
                   [{'id': 'inn_frontage', 'scope_rect': [48, 1200, 144, 144]}],
                   [{'id': 'inn_frontage', 'scope_rect': [96, 1200, 0, 144]}],
                   [{'id': 'inn_frontage', 'scope_rect': [96.25, 1200, 144, 144]}],
                   [{'id': 'inn_frontage', 'scope_rect': PARCEL, 'collision': 'none'}])
        for parcels in invalid:
            with self.subTest(parcels=parcels), self.assertRaises(ValueError):
                self.resolve(recipe(parcels=parcels))
        adjacent = [{'id': 'inn_frontage', 'scope_rect': PARCEL},
                    {'id': 'shop_frontage', 'scope_rect': [240, 1200, 144, 144]}]
        self.assertEqual(self.resolve(recipe(parcels=adjacent))['parcels'], adjacent)

    def test_each_instance_keeps_its_namespace_district_and_named_canvas(self):
        for change in ({'id': 'inn'}, {'id': 'settlement.arrival.'},
                       {'id': 'settlement.growing.planter'}, {'id': 'settlement.misc.planter'},
                       {'district': 'commons_households'}, {'parcel': 'shop_frontage'},
                       {'parcel': None}, {'position': [230, 1248]}, {'position': [144.25, 1248]},
                       {'position': [True, 1248]}, {'position': [float('nan'), 1248]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe([placement(**change)]))
        missing = placement();missing.pop('parcel')
        with self.assertRaises(ValueError):self.resolve(recipe([missing]))
        with self.assertRaises(ValueError):self.resolve(recipe([placement(), placement()]))

    def test_solids_need_explicit_integer_world_supports_without_source_overrides(self):
        for change in ({'collision': 'none'}, {'occlusion': 'low'}, {'frames': ['replacement.png']},
                       {'frame_duration_ms': 1}, {'logical_size': [4, 4]}, {'sort_y': 0},
                       {'interaction_cues': True}, {'asset': 'missing:prop'},
                       {'footprint': [-1, 18, 20, 4]}, {'footprint': [2, 18, 24, 4]},
                       {'footprint': [2.5, 18, 20, 4]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe([placement(**change)]))
        missing = placement();missing.pop('footprint')
        with self.assertRaises(ValueError):self.resolve(recipe([missing]))
        for asset in ('exteriors_hd:wood_shavings', 'growing_fields:vegetables_east_west'):
            flat = flower(asset=asset, occlusion='ground')
            with self.subTest(asset=asset), self.assertRaises(ValueError):self.resolve(recipe([flat]))

    def test_even_nonblocking_plants_cannot_cover_reserved_operating_or_travel_space(self):
        source = recipe([flower()])
        for shape, geometry, roles in (
                ('point', [156, 1260], ['movement']),
                ('point', [156, 1260], ['sightline']),
                ('route', [[156, 1212], [156, 1308]], ['movement'])):
            protected = {'id': 'fixture.reserved_use', 'shape': shape, 'geometry': geometry,
                         'padding': [2, 2], 'roles': roles}
            with self.subTest(shape=shape, roles=roles), self.assertRaises(ValueError):
                self.resolve(source, protections=[protected])
        protected = {'id': 'fixture.remote_use', 'shape': 'point', 'geometry': [600, 1300],
                     'padding': [12, 8], 'roles': ['movement', 'sightline']}
        self.assertTrue(self.resolve(source, protections=[protected])['entities'])

    def test_existing_and_proposed_occupied_art_cannot_be_overpainted(self):
        current = town();current['entities'] = [{
            'id': 'inn.existing_flowerpots', 'position': [144, 1248], 'logical_size': [24, 24],
            'artwork_pixels_per_world_pixel': 2,
            'frames': ['assets/terrain/eldenmere/exteriors_hd/props/flowerpot_pair/idle.png']}]
        with self.assertRaises(ValueError):self.resolve(current=current)
        second = placement(id='settlement.arrival.second', position=[156, 1248])
        with self.assertRaises(ValueError):self.resolve(recipe([placement(), second]))
        second['position'] = [192, 1248]
        self.assertEqual(len(self.resolve(recipe([placement(), second]))['entities']), 2)

    def test_ground_fringe_and_retirement_art_must_fit_one_pocket(self):
        source = recipe(ground_cells=[[6, 53]], retire_grass_ids=['arrival.fixture'])
        current = town();first = self.resolve(source, current)
        self.assertEqual(first['retired_grass_records'], current['grass']['instances'])
        rebuilt = copy.deepcopy(current);rebuilt['grass']['instances'] = []
        rebuilt['settlement_arrival'] = first
        self.assertEqual(self.resolve(source, rebuilt)['retired_grass_records'], first['retired_grass_records'])
        for cells in ([[4, 50]], [[6.5, 53]], [[True, 53]], [[6, 53], [6, 53]]):
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                self.resolve(recipe(ground_cells=cells))
        current['grass']['instances'][0]['position'] = [245, 1308]
        with self.assertRaises(ValueError):self.resolve(source, current)
        for ids in (['missing'], ['arrival.fixture', 'arrival.fixture']):
            with self.subTest(ids=ids), self.assertRaises(ValueError):self.resolve(recipe(retire_grass_ids=ids))

    def test_source_frames_depth_reduced_idle_and_provenance_survive_rebuild(self):
        source = recipe([placement(), flower(id='settlement.arrival.flowers', position=[192, 1248])])
        current = town();inputs = copy.deepcopy((current, source))
        first = self.resolve(source, current)
        self.assertEqual((current, source), inputs)
        self.assertEqual(self.resolve(source, current), first)
        static, animated = first['entities']
        prop = next(p for p in read(ROOT/'assets/terrain/eldenmere/exteriors_hd/manifest.json')['props']
                    if p['id'] == 'flowerpot_pair')
        self.assertEqual(static['sort_y'], 1248+prop['depth_baseline_logical'])
        self.assertEqual(static['logical_size'], prop['logical_size'])
        bank = ROOT/'assets/terrain/vegetation_hd/plants.json'
        plant = next(p for p in read(bank)['plants'] if p['id'] == 'flowers_white')
        self.assertEqual(animated['frames'], [(bank.parent/record['file']).relative_to(ROOT).as_posix()
                                              for record in plant['frames']])
        self.assertEqual(animated['frame_duration_ms'], plant['frames'][0]['duration_ms'])
        self.assertEqual(animated['reduced_motion_image'], (bank.parent/plant['idle']).relative_to(ROOT).as_posix())
        self.assertEqual(animated['reduced_motion_frame'], 0)
        self.assertGreater(len({(ROOT/frame).read_bytes() for frame in animated['frames']}), 1)
        for entity in first['entities']:
            for path in [*entity['frames'], *([entity['reduced_motion_image']] if entity.get('reduced_motion_image') else [])]:
                self.assertEqual(first['dependencies_sha256'][path], sha256((ROOT/path).read_bytes()).hexdigest())
                with Image.open(ROOT/path) as picture:
                    self.assertEqual(picture.size, tuple(value*2 for value in entity['logical_size']))
                    self.assertLessEqual(set(picture.getchannel('A').tobytes()), {0, 255})

    def test_unknown_owners_and_deactivation_cannot_leave_visible_props_or_supports(self):
        current = town();first = self.resolve(current=current)
        unowned = copy.deepcopy(current);unowned['entities'] = first['entities']
        with self.assertRaises(ValueError):self.resolve(current=unowned)
        rebuilt = copy.deepcopy(unowned);rebuilt['settlement_arrival'] = first
        self.assertEqual(self.resolve(current=rebuilt), first)
        rebuilt['entities'].append({**first['entities'][0], 'id': 'settlement.arrival.unowned'})
        with self.assertRaises(ValueError):self.resolve(current=rebuilt)
        for status in ('ground_only', 'household_dressing', 'growing_dressing'):
            inactive = {'version': 1, 'scene': 'eldenmere.playable', 'status': status, 'placements': []}
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.resolve(inactive, {**current, 'settlement_arrival': first})
            with self.subTest(status=status, stray=True), self.assertRaises(ValueError):self.resolve(inactive, unowned)


class LiveArrivalContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.town = read(ROOT/'assets/maps/eldenmere/playable/map.json')
        cls.source = read(SOURCE)
        cls.before = read(REVIEW/'before_town.json')

    def test_all_prior_owners_and_runtime_contracts_remain_unchanged(self):
        report = self.town['settlement_arrival'];owned = {e['id'] for e in report['entities']}
        self.assertEqual([e for e in self.town['entities'] if e['id'] not in owned], self.before['entities'])
        self.assertEqual([e for e in self.town['entities'] if e['id'] in owned], report['entities'])
        for key in PREVIOUS_LEDGERS:self.assertEqual(self.town[key], self.before[key], key)
        for key in self.before:
            if key != 'entities':self.assertEqual(self.town[key], self.before[key], key)
        self.assertEqual(set(self.town)-set(self.before), {'settlement_arrival'})
        ids = [e['id'] for e in self.town['entities']]
        self.assertEqual(len(ids), len(set(ids)))
        cues = {record.get('entity') for record in self.town.get('interaction_cues', [])}
        self.assertFalse(owned & cues)

    def test_extended_collision_is_baseline_plus_only_declared_arrival_supports(self):
        expected = baseline_collision();painter = ImageDraw.Draw(expected)
        placements = {p['id']: p for p in self.town['settlement_arrival']['placements']}
        for support in self.town['settlement_arrival']['solid_footprints']:
            x, y, w, h = support['rect'];placed = placements[support['id']]
            self.assertTrue(all(type(value) is int for value in (x, y, w, h)))
            px, py = placed['position'];fx, fy, fw, fh = placed['footprint']
            self.assertEqual([x, y, w, h], [px+fx, py+fy, fw, fh])
            painter.rectangle((x, y, x+w-1, y+h-1), fill=255)
        with Image.open(ROOT/self.town['collision']) as picture:
            self.assertEqual(picture.convert('L').tobytes(), expected.tobytes())
        observed = read(REVIEW/'before_observations.json')['production']
        expected_nav = observed['active_files'][self.before['navigation_allowed']]['sha256']
        self.assertEqual(sha256((ROOT/self.town['navigation_allowed']).read_bytes()).hexdigest(), expected_nav)

    def test_live_pockets_resolve_without_covering_southern_exit_or_business_contacts(self):
        from tools.eldenmere_settlement import resolve_protections, validate_district_reports
        protections = resolve_protections(ROOT, self.town, self.source)
        names = {record['id'] for record in protections}
        for name in ('door.inn', 'door.item_shop', 'travel.southern_exit', 'travel.southern_return',
                     'southern_business_roads.0', 'southern_business_roads.1'):
            self.assertIn(name, names)
        self.assertEqual(resolve_arrival(ROOT, self.town, self.source, catalogue(), protections),
                         self.town['settlement_arrival'])
        validate_district_reports(*(self.town[key] for key in ALL_LEDGERS))
        self.assertEqual(self.town['overworld_exit'], self.before['overworld_exit'])
        for point in ([516, 1596], [516, 1560]):
            source = recipe([flower(parcel='east_approach', position=point)],
                            parcels=[{'id': 'east_approach', 'scope_rect': [492, 1548, 84, 84]}])
            self.assertTrue(self.resolve_fixture(source)['entities'])
            with self.subTest(point=point), self.assertRaises(ValueError):
                self.resolve_fixture(source, protections)

    @staticmethod
    def resolve_fixture(source, protections=()):
        return resolve_arrival(ROOT, town(), source, catalogue(), list(protections))


class ArrivalProducerContracts(unittest.TestCase):
    def test_source_reconstruction_covers_the_complete_expanded_physics(self):
        from tools.build_eldenmere_hd import SRC, source_town_physics
        source = read(SRC/'recipe.json');before = read(REVIEW/'before_town.json')
        collision, allowed = source_town_physics(source)
        self.assertEqual(collision.size, tuple(before['size_pixels']))
        painter = ImageDraw.Draw(collision)
        for key in PREVIOUS_LEDGERS:
            for support in before[key]['solid_footprints']:
                x, y, w, h = support['rect']
                painter.rectangle((x, y, x+w-1, y+h-1), fill=255)
        self.assertEqual(collision.tobytes(), baseline_collision().tobytes())
        with Image.open(ROOT/before['navigation_allowed']) as picture:
            self.assertEqual(allowed.tobytes(), picture.convert('L').tobytes())

    def test_producer_rejects_unowned_collision_change_beyond_original_height(self):
        from tools.build_eldenmere_hd import products
        current = read(ROOT/'assets/maps/eldenmere/playable/map.json')
        path = (ROOT/current['collision']).resolve();digest = sha256(path.read_bytes()).hexdigest()
        real_open = Image.open
        with real_open(path) as picture:
            altered = picture.convert('L')
        # The original retained mask ended at y1344. This unrelated southern
        # point must be validated, rather than cropped out of the producer guard.
        point = (96, 1600)
        altered.putpixel(point, 0 if altered.getpixel(point) else 255)

        def open_image(value, *args, **kwargs):
            try:
                selected = Path(value).resolve() == path
            except (TypeError, ValueError):
                selected = False  # Native export readers also open BytesIO.
            return altered.copy() if selected else real_open(value, *args, **kwargs)

        with patch('tools.build_eldenmere_hd.Image.open', side_effect=open_image):
            with self.assertRaisesRegex(ValueError, 'Review changed collision registration'):
                products()
        self.assertEqual(sha256(path.read_bytes()).hexdigest(), digest)


class ArrivalSaveCompatibility(unittest.TestCase):
    def test_old_checkpoints_inside_each_new_support_recover_without_lost_progress(self):
        import pygame
        from main import Game
        previous = baseline_collision()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory);path = folder/'journey.json';settings = folder/'settings.json'
            options = dict(fullscreen=False, start_on_title=True, save_path=path, settings_path=settings)
            game = Game(**options);restored = None
            try:
                game.audio.set_music(0);game.audio.set_effects(0);game.on_title = False
                game.opening.restore({'version': 1, 'stage': 'disabled'})
                game.opening_fade = game.transfer_cooldown = 0
                game.world = game.town;game.player.position.update(528, 1512)
                self.assertTrue(game.town.can_stand(game.player.position))
                self.assertTrue(game.save_progress(), game.save_error)
                saved = read(path)
                for support in game.town.data['settlement_arrival']['solid_footprints']:
                    with self.subTest(support=support['id']):
                        x, y, w, h = support['rect'];occupied = [x+w/2, y+h/2]
                        probe = game.town.probe_rect(occupied)
                        self.assertGreaterEqual(probe.left, 0);self.assertGreaterEqual(probe.top, 0)
                        self.assertLessEqual(probe.right, previous.width);self.assertLessEqual(probe.bottom, previous.height)
                        self.assertIsNone(previous.crop((*probe.topleft, *probe.bottomright)).getbbox())
                        self.assertFalse(game.town.can_stand(occupied))
                        payload = copy.deepcopy(saved);payload['player']['position'] = occupied
                        payload['exterior_position'] = occupied.copy()
                        self.assertTrue(game.save_store.write(payload), game.save_store.error)
                        restored = Game(**options)
                        restored.audio.set_music(0);restored.audio.set_effects(0)
                        self.assertTrue(restored.begin_journey(True), restored.save_error)
                        self.assertIs(restored.world, restored.town)
                        self.assertNotEqual(list(restored.player.position), occupied)
                        self.assertTrue(restored.town.can_stand(restored.player.position))
                        for key in ('quests', 'party', 'inventory'):
                            self.assertEqual(getattr(restored, key).to_dict(), saved[key])
                        self.assertEqual(restored.social.flags, game.social.flags)
                        for key in ALL_LEDGERS:self.assertEqual(restored.town.data[key], game.town.data[key])
                        ids = [e['id'] for e in restored.town.data['settlement_arrival']['entities']]
                        self.assertEqual(len(ids), len(set(ids)))
                        restored.music.stop();restored = None
            finally:
                game.music.stop()
                if restored is not None:restored.music.stop()
                pygame.quit()


if __name__ == '__main__':
    unittest.main()
