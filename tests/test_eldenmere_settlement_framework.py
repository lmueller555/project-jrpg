"""Build-time settlement safety uses source geometry, not painted road pixels."""
import copy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from tools.eldenmere_settlement import (framework, resolve_protections,
                                       resolve_street_network, validate_placements)

ROOT = Path(__file__).resolve().parents[1]
RECIPE = 'assets/source/maps/eldenmere/settlement/recipe.json'


def read(path):
    return json.loads(Path(path).read_text())


def fixture_town():
    return {'id': 'eldenmere.playable', 'size_pixels': [320, 240],
            'player_probe_size': [24, 12], 'player_draw_anchor': [12, 30],
            'doors': [], 'world_links': [], 'entities': [], 'destinations': {}}


def fixture_recipe(selectors):
    return {'version': 1, 'id': 'eldenmere.settlement',
            'status': 'framework_only', 'coordinate_space': 'logical',
            'district_geometry': 'Composition envelopes are not collision.',
            'districts': [], 'protected_selectors': selectors,
            'reviewed_regions': [], 'placements': [], 'ground_treatments': []}


def selector(**extra):
    return {'id': 'fixture.route', 'source': 'fixture.json', 'path': ['route'],
            'shape': 'route', 'units': 'logical', 'padding': [12, 6],
            'scene': 'eldenmere.playable', 'roles': ['movement'], **extra}


def catalogue():
    return {'assets': [{'id': 'fixture:planter', 'image': 'fixture/planter.png',
                        'logical_size': [16, 16], 'artwork_pixels_per_world_pixel': 2,
                        'reuse_status': 'candidate'}]}


def placement(position, **extra):
    return {'id': 'settlement.fixture.planter', 'asset': 'fixture:planter',
            'position': list(position), 'collision': 'solid',
            'footprint': [0, 0, 16, 16], 'occlusion': 'low', **extra}


class SettlementProtectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.town = fixture_town()

    def resolve(self, data, selectors):
        (self.root/'fixture.json').write_text(json.dumps(data))
        return resolve_protections(self.root, self.town, fixture_recipe(selectors))

    def test_route_protection_follows_legs_instead_of_filling_its_bounding_box(self):
        protections = self.resolve({'route': [[40, 40], [160, 40], [160, 160]]},
                                   [selector()])
        # The lawn inside this L-shaped route remains available for dressing.
        accepted = validate_placements([placement((70, 90))], protections,
                                       catalogue(), self.town)
        self.assertEqual(len(accepted), 1)
        for point in ((70, 35), (155, 95), (152, 35)):
            with self.subTest(point=point), self.assertRaises(ValueError):
                validate_placements([placement(point)], protections,
                                    catalogue(), self.town)

    def test_tile_coordinates_scale_but_logical_footprint_padding_does_not(self):
        protections = self.resolve({'route': [[2, 2], [4, 2]]},
                                   [selector(units='tiles')])
        with self.assertRaises(ValueError):
            validate_placements([placement((64, 42))], protections,
                                catalogue(), self.town)
        # A twelve-unit safety margin is not twelve 24-unit terrain tiles.
        self.assertEqual(len(validate_placements([placement((64, 96))],
                                                protections, catalogue(), self.town)), 1)

    def test_entrance_safety_tracks_the_loaded_map_instead_of_a_stale_coordinate(self):
        town = fixture_town()
        door = {'id': 'new_house', 'anchor': [160, 160], 'open_radius': 20,
                'close_radius': 30, 'entry_half_width': 8}
        town['doors'] = [door]
        original = resolve_protections(self.root, town, fixture_recipe([]))
        with self.assertRaises(ValueError):
            validate_placements([placement((155, 155))], original, catalogue(), town)
        door['anchor'] = [260, 160]
        moved = resolve_protections(self.root, town, fixture_recipe([]))
        self.assertEqual(len(validate_placements([placement((155, 155))], moved,
                                                catalogue(), town)), 1)
        with self.assertRaises(ValueError):
            validate_placements([placement((255, 155))], moved, catalogue(), town)

    def test_named_source_selection_rejects_missing_paths_and_disappearing_records(self):
        chosen = selector(path=['roads', '*'], geometry_path=['points'],
                          filter={'field': 'id', 'values': ['public_lane']})
        data = {'roads': [{'id': 'private_path', 'points': [[20, 160], [100, 160]]},
                          {'id': 'public_lane', 'points': [[40, 40], [160, 40]]}]}
        protections = self.resolve(data, [chosen])
        self.assertEqual(len(validate_placements([placement((50, 150))], protections,
                                                catalogue(), self.town)), 1)
        with self.assertRaises(ValueError):
            validate_placements([placement((50, 35))], protections,
                                catalogue(), self.town)
        with self.assertRaises(ValueError):
            self.resolve({'roads': data['roads'][:1]}, [chosen])
        with self.assertRaises(ValueError):
            self.resolve(data, [selector(path=['missing'])])

    def test_tall_dressing_cannot_hide_a_protected_actor_even_when_its_feet_are_clear(self):
        protections = self.resolve({'station': [100, 100]},
                                   [selector(path=['station'], shape='point',
                                             padding=[12, 6],
                                             roles=['movement', 'sightline'])])
        # The small support is clear; the upper artwork would cover the actor.
        prop = placement((94, 70), collision='none', occlusion='tall')
        prop.pop('footprint')
        with self.assertRaises(ValueError):
            validate_placements([prop], protections, catalogue(), self.town)
        prop['occlusion'] = 'ground'
        self.assertEqual(len(validate_placements([prop], protections,
                                                catalogue(), self.town)), 1)

    def test_interior_coordinates_cannot_be_registered_as_town_protections(self):
        with self.assertRaisesRegex(ValueError, 'eldenmere.playable'):
            self.resolve({'station': [100, 100]},
                         [selector(path=['station'], shape='point', scene='inn')])

    def test_code_owned_envelope_needs_review_when_its_source_changes(self):
        source = self.root/'actor.py'
        source.write_text('TRACK_CENTER = (160, 160)\n')
        recipe = fixture_recipe([])
        recipe['reviewed_regions'] = [{
            'id': 'fixture.code_track', 'source': 'actor.py',
            'scene': 'eldenmere.playable',
            'symbol': 'TRACK_CENTER', 'source_sha256': sha256(source.read_bytes()).hexdigest(),
            'rect': [140, 140, 40, 40], 'padding': [12, 6],
            'roles': ['movement'], 'note': 'Reviewed outdoor routine envelope',
        }]
        interior = copy.deepcopy(recipe)
        interior['reviewed_regions'][0]['scene'] = 'inn'
        with self.assertRaisesRegex(ValueError, 'eldenmere.playable'):
            resolve_protections(self.root, self.town, interior)
        protections = resolve_protections(self.root, self.town, recipe)
        with self.assertRaises(ValueError):
            validate_placements([placement((160, 160))], protections,
                                catalogue(), self.town)
        source.write_text('TRACK_CENTER = (220, 160)\n')
        with self.assertRaisesRegex(ValueError, 'code-owned geometry changed'):
            resolve_protections(self.root, self.town, recipe)

    def test_invalid_binding_density_footprints_and_off_map_instances_fail_closed(self):
        for change in ({'asset': 'fixture:missing'},
                       {'id': 'existing_town_object'},
                       {'position': [float('nan'), 160]},
                       {'position': [-1, 160]},
                       {'position': [305, 160]},
                       {'footprint': [0, 0, 0, 16]},
                       {'footprint': [0, 0, -1, 16]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                invalid = placement((220, 160))
                invalid.update(change)
                validate_placements([invalid], [], catalogue(), self.town)
        solid = placement((220, 160))
        solid.pop('footprint')
        with self.assertRaises(ValueError):
            validate_placements([solid], [], catalogue(), self.town)
        wrong_scale = catalogue()
        wrong_scale['assets'][0]['artwork_pixels_per_world_pixel'] = 1
        with self.assertRaises(ValueError):
            validate_placements([placement((220, 160))], [], wrong_scale, self.town)
        duplicate = placement((220, 160))
        with self.assertRaises(ValueError):
            validate_placements([duplicate, copy.deepcopy(duplicate)], [],
                                catalogue(), self.town)

    def test_clear_half_unit_placement_does_not_mutate_its_input(self):
        props = [placement((220.5, 160.5))]
        before = copy.deepcopy(props)
        result = validate_placements(props, [], catalogue(), self.town)
        self.assertEqual(len(result), 1)
        self.assertEqual(props, before)

    def test_cartography_requires_declared_units_and_finite_widths(self):
        (self.root/'fixture.json').write_text(json.dumps({'points': [[40, 40], [160, 40]]}))
        source = {'id': 'settlement.street.fixture', 'material': 'dirt',
                  'role': 'secondary', 'source_ref': {'file': 'fixture.json', 'path': ['points']},
                  'geometry': 'points', 'units': 'logical', 'width': 24}
        config = {'street_network': [source]}
        roads, files = resolve_street_network(self.root, self.town, config, [])
        self.assertEqual(roads[0]['points'], [[40, 40], [160, 40]])
        self.assertEqual(files, {'fixture.json'})
        for change in ({'units': 'artwork'}, {'width': float('nan')},
                       {'width': True}, {'width': -1}):
            invalid = {**source, **change}
            with self.subTest(change=change), self.assertRaises(ValueError):
                resolve_street_network(self.root, self.town, {'street_network': [invalid]}, [])

    def test_cartography_cannot_publish_a_missing_or_overridden_ground_treatment(self):
        for item in ({'treatment': 'settlement.street.missing'},
                     {'treatment': 'settlement.street.missing', 'width': 99}):
            with self.subTest(item=item), self.assertRaises(ValueError):
                resolve_street_network(self.root, self.town, {'street_network': [item]}, [])

    def test_reordered_source_roads_require_explicit_identity_review(self):
        (self.root/'fixture.json').write_text(json.dumps({'roads': [
            {'id': 'other_lane', 'points': [[40,40],[160,40]], 'width': 2}]}))
        item = {'id': 'settlement.street.expected_lane', 'material': 'dirt',
                'role': 'residential', 'source_id': 'expected_lane',
                'source_ref': {'file': 'fixture.json', 'path': ['roads',0]},
                'geometry': 'road', 'units': 'tiles'}
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            resolve_street_network(self.root, self.town, {'street_network': [item]}, [])


class LiveSettlementFrameworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.town = read(ROOT/'assets/maps/eldenmere/playable/map.json')
        cls.recipe = read(ROOT/RECIPE)
        cls.protections = resolve_protections(ROOT, cls.town, cls.recipe)

    def test_every_live_entrance_exit_and_well_work_contact_rejects_new_blockers(self):
        points = [(door['id'], door['anchor']) for door in self.town['doors']]
        points.append(('southern_exit', self.town['overworld_exit']['position']))
        points.append(('southern_return', self.town['overworld_exit']['return_position']))
        points.extend((link['id'], link['position']) for link in self.town['world_links'])
        well = read(ROOT/'assets/maps/eldenmere/well_square/layout.json')
        points.extend(well['approaches'].items())
        # Protect the owned structure itself, including roof/canvas areas that
        # lie outside the four operating contacts.
        owned_well = next(record for record in self.town['entities'] if record['id'] == 'well')
        points.append(('owned well upper structure',
                       (owned_well['position'][0]+18, owned_well['position'][1])))
        workshop = read(ROOT/'assets/source/terrain/eldenmere/workshop/recipe.json')
        points.extend(('workshop.'+record['id'], record['position'])
                      for record in workshop['props']
                      if record['id'] in ('workbench', 'timber_rack',
                                          'spare_cog_fittings', 'stool_watering_can'))
        for name, (x, y) in points:
            with self.subTest(place=name), self.assertRaises(ValueError):
                validate_placements([placement((x-8, y-8))], self.protections,
                                    catalogue(), self.town)

    def test_current_story_town_staging_is_reserved(self):
        lantern = read(ROOT/'assets/story/lantern/layout.json')
        regent = read(ROOT/'assets/story/regent/layout.json')
        for owner, fields in ((lantern, ('workshop', 'workshop_mira', 'workshop_liam',
                                         'workshop_tomas')),
                              (regent, ('arrival', 'driver_arrival', 'lucan_arrival',
                                        'outside_courtyard'))):
            for key in fields:
                x, y = owner[key]
                source = ('assets/story/lantern/layout.json' if owner is lantern
                          else 'assets/story/regent/layout.json')
                self.assertTrue(any(record['source'] == source and record['source_path'] == [key]
                                    for record in self.protections), (source, key))
                with self.subTest(station=key), self.assertRaises(ValueError):
                    validate_placements([placement((x-8, y-8))], self.protections,
                                        catalogue(), self.town)

    def test_framework_is_deterministic_and_does_not_mutate_the_town(self):
        before = copy.deepcopy(self.town)
        first = framework(ROOT, self.town, RECIPE)
        second = framework(ROOT, self.town, RECIPE)
        self.assertEqual(first, second)
        self.assertEqual(self.town, before)
        self.assertEqual(self.recipe['status'], 'workyard_dressing')
        self.assertEqual(first['active_placements'], len(self.recipe['placements']))
        self.assertEqual(first['dressing'], self.town['settlement_dressing'])
        self.assertEqual(first['workyards'], self.town['settlement_workyards'])
        self.assertEqual(first['active_ground_treatments'], len(self.recipe['ground_treatments']))
        self.assertEqual(first['street_network'], self.town['cartography']['street_network'])

    def test_real_catalogued_native_asset_is_accepted_by_the_placement_validator(self):
        catalogue = framework(ROOT, self.town, RECIPE)['inventory']
        for generated_output in ('assets/maps/eldenmere/playable/map.json',
                                 'assets/maps/eldenmere/town_hd/manifest.json',
                                 'assets/maps/eldenmere/settlement/manifest.json'):
            self.assertNotIn(generated_output, catalogue['dependencies_sha256'])
        # Validate the actual producer schema, not only a handcrafted test asset.
        prop = placement((0, 0), asset='exteriors_hd:herb_planter',
                         collision='none', occlusion='low')
        prop.pop('footprint')
        result = validate_placements([prop], [], catalogue, self.town)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['asset'], 'exteriors_hd:herb_planter')

    def test_framework_rejects_silent_activation_of_placements_or_ground_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            path = temporary_root/'settlement.json'
            for field in ('placements', 'ground_treatments'):
                changed = copy.deepcopy(self.recipe)
                changed['status'] = 'framework_only'
                changed[field] = [{'id': 'settlement.future_content'}]
                path.write_text(json.dumps(changed))
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'cannot activate'):
                    framework(temporary_root, self.town, 'settlement.json')
