"""Courtyard composition keeps native art, explicit supports and source access."""
import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageChops, ImageDraw

from tools.eldenmere_settlement_dressing import resolve_dressing

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')


ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT/'assets/source/maps/eldenmere/settlement/recipe.json'
SCOPE = [120, 120, 600, 336]


def read(path):
    return json.loads(Path(path).read_text())


def catalogue():
    return read(ROOT/'assets/maps/eldenmere/settlement/manifest.json')['inventory']


def town():
    return {'id': 'eldenmere.playable', 'size_pixels': [1536, 1632],
            'player_probe_size': [24, 12], 'player_draw_anchor': [12, 30],
            'entities': [], 'doors': [],
            'grass': {'instances': [{'id': 'sanctuary_meadow.fixture',
                                     'position': [650, 400], 'variant': 'dense_hd',
                                     'phase_ms': 500}]}}


def placement(**extra):
    return {'id': 'settlement.courtyard.herb_box',
            'asset': 'exteriors_hd:herb_planter', 'district': 'serene_terrace',
            'position': [500, 280], 'collision': 'solid',
            'footprint': [2, 10, 20, 4], 'occlusion': 'tall', **extra}


def recipe(placements=None, **config):
    return {'version': 1, 'id': 'eldenmere.settlement',
            'status': 'courtyard_dressing', 'scene': 'eldenmere.playable',
            'districts': [{'id': 'serene_terrace', 'rect': SCOPE.copy()}],
            'placements': [placement()] if placements is None else placements,
            'courtyard_dressing': {'district': 'serene_terrace',
                                   'scope_rect': SCOPE.copy(),
                                   'retire_grass_ids': [], 'garden_cells': [],
                                   **config}}


def protected_point(position, roles=('movement', 'sightline')):
    return {'id': 'fixture.working_station', 'shape': 'point',
            'geometry': list(position), 'padding': [12, 8], 'roles': list(roles)}


class CourtyardRecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = catalogue()

    def resolve(self, config=None, current=None, protections=()):
        return resolve_dressing(ROOT, town() if current is None else current,
                                recipe() if config is None else config,
                                self.catalogue, list(protections))

    def test_only_explicit_courtyard_activation_can_publish_dressing(self):
        for status in ('framework_only', 'ground_only', 'active', None):
            config = recipe();config['status'] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.resolve(config)
        for change in ({'district': 'workshop_mill'},
                       {'scope_rect': [0, 0, 1536, 1632]},
                       {'scope_rect': [120, 120, 0, 336]},
                       {'collision': 'clear_existing'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe(**change))

    def test_owned_props_or_retired_grass_cannot_be_silently_deactivated(self):
        for status in ('framework_only', 'ground_only'):
            inactive = {'version': 1, 'status': status, 'scene': 'eldenmere.playable',
                        'placements': [], 'ground_treatments': []}
            for previous in ({'entities': [{'id': 'settlement.courtyard.old_prop'}]},
                             {'retired_grass_ids': ['sanctuary_meadow.fixture']},
                             {'retired_grass_records': town()['grass']['instances']}):
                current = town();current['settlement_dressing'] = previous
                with self.subTest(status=status, previous=previous), self.assertRaisesRegex(
                        ValueError, 'deactivation requires explicit'):
                    self.resolve(inactive, current)

    def test_unknown_mutation_keys_nonfinite_geometry_and_other_districts_fail_closed(self):
        changes = ({'id': 'sanctuary.replacement'},
                   {'id': 'settlement.workshop.herb_box'},
                   {'district': 'workshop_mill'},
                   {'position': [119, 280]},
                   {'position': [710, 280]},
                   {'position': [float('nan'), 280]},
                   {'position': [True, 280]},
                   {'navigation': [500, 280, 24, 16]},
                   {'interaction_cues': True},
                   {'frames': ['unregistered.png']},
                   {'asset': 'missing:prop'})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe([placement(**change)]))
        with self.assertRaises(ValueError):
            self.resolve(recipe([placement(), placement()]))

    def test_solid_props_require_registered_local_supports_and_tall_visibility_review(self):
        changes = ({'collision': 'none'}, {'collision': 'solid', 'occlusion': 'low'},
                   {'footprint': [0, 0, 0, 4]}, {'footprint': [-1, 10, 20, 4]},
                   {'footprint': [2, 10, 30, 4]})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe([placement(**change)]))
        absent = placement();absent.pop('footprint')
        with self.assertRaises(ValueError):
            self.resolve(recipe([absent]))
        flowers = {'id': 'settlement.courtyard.low_flowers',
                   'asset': 'vegetation_hd:flowers_white', 'district': 'serene_terrace',
                   'position': [500, 320], 'collision': 'none', 'occlusion': 'low'}
        report = self.resolve(recipe([flowers]))
        self.assertEqual(report['solid_footprints'], [])

    def test_ground_support_and_upper_art_cannot_cover_working_actors(self):
        # At this station the herb box's support blocks the protected movement.
        with self.assertRaises(ValueError):
            self.resolve(protections=[protected_point([512, 292], ('movement',))])
        # A different station is clear of the support but its standing body
        # would still be covered by the upper part of the new artwork.
        with self.assertRaises(ValueError):
            self.resolve(protections=[protected_point([512, 310], ('sightline',))])
        self.assertEqual(len(self.resolve(protections=[protected_point([650, 350])])['entities']), 1)

    def test_existing_and_pairwise_occupied_artwork_cannot_be_overlapped(self):
        existing = town()
        existing['entities'] = [{'id': 'existing.planter', 'position': [500, 280],
                                 'logical_size': [24, 16],
                                 'artwork_pixels_per_world_pixel': 2,
                                 'frames': ['assets/terrain/eldenmere/exteriors_hd/props/herb_planter/idle.png']}]
        with self.assertRaises(ValueError):
            self.resolve(current=existing)
        second = placement(id='settlement.courtyard.second_box', position=[510, 280])
        with self.assertRaises(ValueError):
            self.resolve(recipe([placement(), second]))
        second['position'] = [540, 280]
        self.assertEqual(len(self.resolve(recipe([placement(), second]))['entities']), 2)

    def test_grass_retirement_must_be_known_in_scope_and_reconstructible_on_rebuild(self):
        current = town()
        config = recipe(retire_grass_ids=['sanctuary_meadow.fixture'])
        first = self.resolve(config, current)
        self.assertEqual(first['retired_grass_ids'], ['sanctuary_meadow.fixture'])
        self.assertEqual(first['retired_grass_records'], current['grass']['instances'])
        rebuilt = copy.deepcopy(current)
        rebuilt['grass']['instances'] = []
        rebuilt['settlement_dressing'] = copy.deepcopy(first)
        second = self.resolve(config, rebuilt)
        self.assertEqual(second['retired_grass_records'], first['retired_grass_records'])
        for ids in (['missing'], ['sanctuary_meadow.fixture', 'sanctuary_meadow.fixture']):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.resolve(recipe(retire_grass_ids=ids))
        outside = town();outside['grass']['instances'][0]['position'] = [800, 300]
        with self.assertRaises(ValueError):
            self.resolve(config, outside)

    def test_garden_cells_use_unique_logical_tiles_fully_inside_the_scope(self):
        valid = [[20, 12], [21, 12]]
        self.assertEqual(self.resolve(recipe(garden_cells=valid))['garden_cells'], valid)
        for cells in ([[19.5, 12]], [[True, 12]], [[60, 12]], [[20, 4]],
                      [[20, 12], [20, 12]]):
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                self.resolve(recipe(garden_cells=cells))

    def test_source_registered_frames_depth_and_half_unit_supports_are_preserved(self):
        current = town();config = recipe([placement(position=[500.5, 280.5],
                                                   footprint=[1.5, 9.5, 20, 4])])
        before_town, before_recipe = copy.deepcopy(current), copy.deepcopy(config)
        first = self.resolve(config, current)
        second = self.resolve(config, current)
        self.assertEqual(first, second)
        self.assertEqual(current, before_town)
        self.assertEqual(config, before_recipe)
        self.assertEqual([record['rect'] for record in first['solid_footprints']], [[502, 290, 20, 4]])
        self.assertEqual(first['solid_footprints'][0]['id'], 'settlement.courtyard.herb_box')
        entity = first['entities'][0]
        self.assertEqual(entity['position'], [500.5, 280.5])
        self.assertEqual(entity['sort_y'], 294.5)
        self.assertEqual(entity['logical_size'], [24, 16])
        self.assertEqual(entity['artwork_pixels_per_world_pixel'], 2)
        self.assertTrue(entity['frames'])
        self.assertIn('assets/terrain/eldenmere/exteriors_hd/manifest.json', first['dependencies_sha256'])
        for path in entity['frames']:
            self.assertEqual(first['dependencies_sha256'][path], sha256((ROOT/path).read_bytes()).hexdigest())
            with Image.open(ROOT/path) as picture:
                self.assertEqual(picture.size, (48, 32))
                self.assertLessEqual(set(picture.getchannel('A').tobytes()), {0, 255})

    def test_repeat_build_reconciles_only_declared_owned_instances_without_duplicates(self):
        original = town()
        first = self.resolve(current=original)
        untrusted = copy.deepcopy(original)
        untrusted['entities'].extend(copy.deepcopy(first['entities']))
        with self.assertRaises(ValueError):
            self.resolve(current=untrusted)
        rebuilt = copy.deepcopy(original)
        rebuilt['settlement_dressing'] = copy.deepcopy(first)
        rebuilt['entities'].extend(copy.deepcopy(first['entities']))
        second = self.resolve(current=rebuilt)
        self.assertEqual(second, first)
        self.assertEqual(len(second['entities']), 1)
        rebuilt['entities'].append({**copy.deepcopy(first['entities'][0]),
                                    'id': 'settlement.courtyard.unowned'})
        with self.assertRaises(ValueError):
            self.resolve(current=rebuilt)

    def test_native_manifest_frames_cannot_lie_about_density_or_alpha(self):
        source = next(asset for asset in self.catalogue['assets'] if asset['id'] == 'exteriors_hd:herb_planter')
        manifest = read(ROOT/source['manifest'])
        original = manifest['props'][source['source_selector'][-1]]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);pack = root/'assets/fixture';pack.mkdir(parents=True)
            record = {**original, 'idle': 'idle.png', 'frames': ['frame_00.png']}
            (pack/'manifest.json').write_text(json.dumps({**manifest, 'props': [record]}))
            asset = {**source, 'manifest': 'assets/fixture/manifest.json',
                     'source_selector': ['props', 0], 'image': 'assets/fixture/idle.png'}
            fake_catalogue = {'assets': [asset]}
            for size, alpha in (((48, 32), 128), ((24, 16), 255)):
                picture = Image.new('RGBA', size, (60, 80, 40, alpha))
                picture.save(pack/'idle.png');picture.save(pack/'frame_00.png')
                with self.subTest(size=size, alpha=alpha), self.assertRaises(ValueError):
                    resolve_dressing(root, town(), recipe(), fake_catalogue, [])


class LiveCourtyardContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.town = read(ROOT/'assets/maps/eldenmere/playable/map.json')
        cls.recipe = read(RECIPE)
        cls.manifest = read(ROOT/'assets/maps/eldenmere/settlement/manifest.json')

    def test_source_owned_gardener_stations_and_household_fixtures_are_reserved(self):
        from tools.eldenmere_settlement import resolve_protections
        protections = resolve_protections(ROOT, self.town, self.recipe)
        names = {record['id'] for record in protections}
        for name in ('entity.sanctuary.bench', 'entity.sanctuary.provision_basket',
                     'gardener_rest_position', 'gardener_trough_via',
                     'gardener_garden_crossing', 'tomas_town_arrival',
                     'regent_outside_courtyard', 'regent_survivor_start'):
            self.assertIn(name, names)
        gardener = read(ROOT/'assets/maps/eldenmere/routines/gardener.json')
        for bed in gardener['beds']:
            self.assertTrue(any(record['source'] == 'assets/maps/eldenmere/routines/gardener.json'
                                and record['shape'] == 'point' and record['geometry'] == bed['position']
                                for record in protections), bed['id'])
        entities = {record['id']: record for record in self.town['entities']}
        for name in ('sanctuary.bench', 'sanctuary.provision_basket'):
            self.assertNotIn(name, {record['id'] for record in self.recipe['placements']})
            self.assertIn(name, entities)

    def test_live_collision_is_the_retained_source_plus_only_declared_supports(self):
        original = Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/collision.png').convert('L')
        expected = original.copy()
        report = self.town['settlement_dressing']
        draw = ImageDraw.Draw(expected)
        for district in (report,self.town.get('settlement_workyards',{}),self.town.get('settlement_commons',{}),self.town.get('settlement_households',{}),self.town.get('settlement_growing',{}),self.town.get('settlement_arrival',{})):
            for record in district.get('solid_footprints',[]):
                x, y, width, height = record['rect']
                self.assertTrue(all(float(value).is_integer() for value in (x, y, width, height)))
                draw.rectangle((int(x), int(y), int(x+width)-1, int(y+height)-1), fill=255)
        with Image.open(ROOT/self.town['collision']) as source:
            current = source.convert('L').crop((0, 0, *expected.size))
        self.assertIsNone(ImageChops.difference(expected, current).getbbox())
        self.assertEqual(report['retired_grass_ids'], self.recipe['courtyard_dressing']['retire_grass_ids'])
        retired = set(report['retired_grass_ids'])
        self.assertFalse(retired.intersection(item['id'] for item in self.town['grass']['instances']))
        self.assertTrue(all(record['district'] == 'serene_terrace' for record in report['placements']))


class CourtyardSaveCompatibility(unittest.TestCase):
    def test_old_save_on_previously_clear_support_ground_recovers_without_progress_loss(self):
        import pygame
        from main import Game

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            path = temporary/'journey.json';settings = temporary/'settings.json'
            game = Game(fullscreen=False, start_on_title=True,
                        save_path=path, settings_path=settings)
            restored = None
            try:
                game.audio.set_music(0);game.audio.set_effects(0)
                game.on_title = False
                game.opening.restore({'version': 1, 'stage': 'disabled'})
                game.opening_fade = game.transfer_cooldown = 0
                game.world = game.town
                game.player.position.update(384, 320)
                self.assertTrue(game.world.can_stand(game.player.position))
                self.assertTrue(game.save_progress(), game.save_error)
                saved = read(path)
                support = game.town.data['settlement_dressing']['solid_footprints'][0]
                x, y, width, height = support['rect']
                occupied = [x+width/2, y+height/2]
                # This is the pre-PR3 save condition: the original physical map
                # was clear here, while the newly authored support now blocks it.
                with Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/collision.png') as source:
                    probe = game.town.probe_rect(occupied)
                    self.assertIsNone(source.convert('L').crop((*probe.topleft, *probe.bottomright)).getbbox())
                self.assertFalse(game.town.can_stand(occupied))
                saved['player']['position'] = occupied
                saved['exterior_position'] = occupied.copy()
                self.assertTrue(game.save_store.write(saved), game.save_store.error)
                expected = {key: copy.deepcopy(saved[key]) for key in ('quests', 'party', 'inventory')}

                restored = Game(fullscreen=False, start_on_title=True,
                                save_path=path, settings_path=settings)
                restored.audio.set_music(0);restored.audio.set_effects(0)
                self.assertTrue(restored.has_saved_journey, restored.save_error)
                self.assertTrue(restored.begin_journey(True), restored.save_error)
                self.assertIs(restored.world, restored.town)
                self.assertNotEqual(list(restored.player.position), occupied)
                self.assertTrue(restored.world.can_stand(restored.player.position))
                self.assertEqual(restored.quests.to_dict(), expected['quests'])
                self.assertEqual(restored.party.to_dict(), expected['party'])
                self.assertEqual(restored.inventory.to_dict(), expected['inventory'])
                ids = [entity['id'] for entity in restored.town.data['entities']
                       if entity['id'].startswith('settlement.courtyard.')]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual(set(ids), {entity['id'] for entity in
                                          restored.town.data['settlement_dressing']['entities']})
            finally:
                game.music.stop()
                if restored is not None:restored.music.stop()
                pygame.quit()

