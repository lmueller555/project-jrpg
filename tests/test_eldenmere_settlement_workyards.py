"""Workyard stock preserves source owners, clear staging and native registration."""
import copy
from functools import lru_cache
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageChops, ImageDraw

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from tools.eldenmere_settlement_dressing import resolve_dressing, resolve_workyards
from tools.eldenmere_settlement_inventory import inventory


ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT/'assets/source/maps/eldenmere/settlement/recipe.json'
PACK = ROOT/'assets/terrain/eldenmere/workyard_props'
SCOPE = [552, 264, 552, 288]


def read(path):
    return json.loads(Path(path).read_text())


@lru_cache(None)
def catalogue():
    # Read the producer catalogue, even before the first live workyard build.
    return inventory(ROOT, town=read(ROOT/'assets/maps/eldenmere/playable/map.json'))


def fixture_town():
    return {'id': 'eldenmere.playable', 'size_pixels': [1536, 1632],
            'player_probe_size': [24, 12], 'player_draw_anchor': [12, 30],
            'entities': [], 'doors': [],
            'grass': {'instances': [{'id': 'workyard.fixture', 'position': [780, 536],
                                     'variant': 'dense_hd', 'phase_ms': 500}]}}


def placement(**extra):
    return {'id': 'settlement.workyards.stock', 'asset': 'workyard_props:empty_crate',
            'district': 'workshop_mill', 'position': [756, 396],
            'collision': 'solid', 'footprint': [2, 12, 20, 6],
            'occlusion': 'tall', **extra}


def recipe(placements=None, **config):
    return {'version': 1, 'id': 'eldenmere.settlement', 'status': 'workyard_dressing',
            'scene': 'eldenmere.playable',
            'districts': [{'id': 'workshop_mill', 'rect': SCOPE.copy()},
                          {'id': 'serene_terrace', 'rect': [120, 120, 600, 336]}],
            'placements': [placement()] if placements is None else placements,
            'workyard_dressing': {'district': 'workshop_mill', 'scope_rect': SCOPE.copy(),
                                  'retire_grass_ids': [], 'ground_cells': [], **config}}


def protected_point(position, roles):
    return {'id': 'fixture.work_station', 'shape': 'point', 'geometry': list(position),
            'padding': [12, 8], 'roles': list(roles)}


class WorkyardRecipeTests(unittest.TestCase):
    def resolve(self, config=None, current=None, protections=()):
        return resolve_workyards(ROOT, fixture_town() if current is None else current,
                                 recipe() if config is None else config,
                                 catalogue(), list(protections))

    def test_only_reviewed_workyard_activation_and_namespace_are_allowed(self):
        for status in ('framework_only', 'ground_only', 'courtyard_dressing', 'active', None):
            config = recipe();config['status'] = status
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.resolve(config)
        for change in ({'district': 'eastern_growing'}, {'scope_rect': [0, 0, 1536, 1632]},
                       {'scope_rect': [552, 264, 0, 288]}, {'navigation': 'clear'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe(**change))
        for change in ({'id': 'workshop.workbench'}, {'id': 'settlement.courtyard.stock'},
                       {'district': 'southern_arrival'}, {'position': [540, 396]},
                       {'position': [1090, 396]}, {'position': [float('nan'), 396]},
                       {'position': [True, 396]}, {'frames': ['unregistered.png']},
                       {'interaction_cues': True}, {'asset': 'missing:stock'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe([placement(**change)]))
        with self.assertRaises(ValueError):
            self.resolve(recipe([placement(), placement()]))

    def test_stock_requires_explicit_supports_and_honest_visibility(self):
        for change in ({'collision': 'none'}, {'occlusion': 'low'},
                       {'footprint': [0, 0, 0, 4]}, {'footprint': [-1, 12, 20, 6]},
                       {'footprint': [2, 12, 28, 6]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe([placement(**change)]))
        missing = placement();missing.pop('footprint')
        with self.assertRaises(ValueError):
            self.resolve(recipe([missing]))
        shavings = {'id': 'settlement.workyards.shavings', 'asset': 'exteriors_hd:wood_shavings',
                    'district': 'workshop_mill', 'position': [718, 434],
                    'collision': 'none', 'occlusion': 'ground'}
        flat = self.resolve(recipe([shavings]))
        self.assertEqual(flat['solid_footprints'], [])
        self.assertEqual(flat['entities'], [])
        self.assertEqual([e['id'] for e in flat['ground_entities']], [shavings['id']])
        self.assertEqual(flat['placements'][0]['id'], shavings['id'])
        rebuilt = fixture_town();rebuilt['settlement_workyards'] = flat
        self.assertEqual(self.resolve(recipe([shavings]), rebuilt), flat)
        inactive = {'version':1,'scene':'eldenmere.playable','status':'ground_only','placements':[]}
        with self.assertRaises(ValueError):self.resolve(inactive, rebuilt)
        with self.assertRaises(ValueError):
            self.resolve(recipe([{**shavings, 'collision': 'solid', 'footprint': [2, 5, 10, 3]}]))

    def test_stock_cannot_block_a_working_actor_or_hide_a_clear_station(self):
        with self.assertRaises(ValueError):
            self.resolve(protections=[protected_point([768, 410], ('movement',))])
        with self.assertRaises(ValueError):
            self.resolve(protections=[protected_point([768, 430], ('sightline',))])
        self.assertEqual(len(self.resolve(protections=[protected_point([1000, 400], ('movement',))])['entities']), 1)

    def test_existing_foreign_art_and_pairwise_stock_remain_separate(self):
        current = fixture_town()
        current['entities'] = [{'id': 'settlement.courtyard.existing', 'position': [756, 396],
                                'logical_size': [24, 16], 'artwork_pixels_per_world_pixel': 2,
                                'frames': ['assets/terrain/eldenmere/exteriors_hd/props/herb_planter/idle.png']}]
        with self.assertRaises(ValueError):
            self.resolve(current=current)
        second = placement(id='settlement.workyards.second', position=[766, 396])
        with self.assertRaises(ValueError):
            self.resolve(recipe([placement(), second]))
        second['position'] = [756, 432]
        self.assertEqual(len(self.resolve(recipe([placement(), second]))['entities']), 2)

    def test_ground_cells_and_grass_retirements_stay_owned_and_reconstructible(self):
        current = fixture_town()
        config = recipe(retire_grass_ids=['workyard.fixture'], ground_cells=[[31, 16], [32, 16]])
        first = self.resolve(config, current)
        self.assertEqual(first['retired_grass_records'], current['grass']['instances'])
        self.assertEqual(first['ground_cells'], [[31, 16], [32, 16]])
        rebuilt = copy.deepcopy(current);rebuilt['grass']['instances'] = []
        rebuilt['settlement_workyards'] = first
        self.assertEqual(self.resolve(config, rebuilt)['retired_grass_records'], first['retired_grass_records'])
        for cells in ([[31.5, 16]], [[True, 16]], [[31, 16], [31, 16]], [[46, 16]], [[31, 10]]):
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                self.resolve(recipe(ground_cells=cells))
        for ids in (['unknown'], ['workyard.fixture', 'workyard.fixture']):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.resolve(recipe(retire_grass_ids=ids))

    def test_repeat_build_reconciles_only_recorded_ownership_and_cannot_deactivate(self):
        current = fixture_town();first = self.resolve(current=current)
        untrusted = copy.deepcopy(current);untrusted['entities'] = first['entities']
        with self.assertRaises(ValueError):
            self.resolve(current=untrusted)
        rebuilt = copy.deepcopy(untrusted);rebuilt['settlement_workyards'] = first
        self.assertEqual(self.resolve(current=rebuilt), first)
        rebuilt['entities'].append({**first['entities'][0], 'id': 'settlement.workyards.unowned'})
        with self.assertRaises(ValueError):
            self.resolve(current=rebuilt)
        for status in ('ground_only', 'courtyard_dressing'):
            inactive = {'version': 1, 'scene': 'eldenmere.playable', 'status': status, 'placements': []}
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.resolve(inactive, {**current, 'settlement_workyards': first})
            with self.subTest(status=status, unregistered=True), self.assertRaises(ValueError):
                self.resolve(inactive, untrusted)

    def test_native_sources_keep_depth_hashes_and_half_unit_registration(self):
        current = fixture_town();config = recipe([placement(position=[756.5, 396.5],
                                                          footprint=[1.5, 11.5, 20, 6])])
        before = copy.deepcopy((current, config));first = self.resolve(config, current)
        self.assertEqual(self.resolve(config, current), first)
        self.assertEqual((current, config), before)
        self.assertEqual(first['solid_footprints'], [{'id': 'settlement.workyards.stock', 'rect': [758, 408, 20, 6]}])
        entity = first['entities'][0];source = next(p for p in read(PACK/'manifest.json')['props'] if p['id']=='empty_crate')
        self.assertEqual(entity['sort_y'], entity['position'][1]+source['depth_baseline_logical'])
        self.assertEqual(entity['logical_size'], source['logical_size'])
        self.assertEqual(entity['artwork_pixels_per_world_pixel'], 2)
        for path in entity['frames']:
            self.assertEqual(first['dependencies_sha256'][path], sha256((ROOT/path).read_bytes()).hexdigest())
            with Image.open(ROOT/path) as picture:
                self.assertEqual(picture.size, tuple(v*2 for v in source['logical_size']))
                self.assertLessEqual(set(picture.getchannel('A').tobytes()), {0, 255})

    def test_cross_district_reports_reject_overlapping_art_and_duplicate_ids(self):
        from tools.eldenmere_settlement import validate_district_reports
        court = {'placements': [{'id': 'settlement.courtyard.fixture', 'occupied_rect': [560, 280, 20, 20]}],
                 'entities': [{'id': 'settlement.courtyard.fixture'}]}
        work = {'placements': [{'id': 'settlement.workyards.fixture', 'occupied_rect': [570, 280, 20, 20]}],
                'entities': [{'id': 'settlement.workyards.fixture'}]}
        with self.assertRaises(ValueError):validate_district_reports(court, work)
        work['placements'][0]['occupied_rect'] = [620, 280, 20, 20]
        validate_district_reports(court, work)
        work['entities'][0]['id'] = court['entities'][0]['id']
        with self.assertRaises(ValueError):validate_district_reports(court, work)
        work['ground_entities'] = work.pop('entities')
        with self.assertRaises(ValueError):validate_district_reports(court, work)


class WorkyardNativeBankTests(unittest.TestCase):
    def test_source_bank_is_native_hard_alpha_and_independently_reproducible(self):
        from tools.export_eldenmere_workyard_props import build
        manifest = read(PACK/'manifest.json')
        self.assertEqual(manifest['artwork_pixels_per_world_pixel'], 2)
        self.assertEqual(manifest['recipe_sha256'], sha256((ROOT/manifest['recipe']).read_bytes()).hexdigest())
        for prop in manifest['props']:
            with self.subTest(prop=prop['id']):
                path = PACK/prop['idle']
                self.assertEqual(prop['output_sha256'], sha256(path.read_bytes()).hexdigest())
                self.assertEqual(prop['source']['sha256'], sha256((ROOT/prop['source']['file']).read_bytes()).hexdigest())
                self.assertFalse(prop['interaction_cues'])
                with Image.open(path) as picture:
                    self.assertEqual(picture.size, tuple(v*2 for v in prop['logical_size']))
                    self.assertLessEqual(set(picture.getchannel('A').tobytes()), {0, 255})
                    self.assertEqual(picture.getbbox()[3]/2, prop['depth_baseline_logical'])
                    self.assertTrue(any(len({picture.getpixel((x+i,y+j)) for i in (0,1) for j in (0,1)})>1
                                        for y in range(0,picture.height,2) for x in range(0,picture.width,2)))
        build(check=True)


class LiveWorkyardContracts(unittest.TestCase):
    def test_existing_courtyard_ledger_and_work_owners_survive_combined_activation(self):
        town = read(ROOT/'assets/maps/eldenmere/playable/map.json');source = read(RECIPE)
        from tools.eldenmere_settlement import resolve_protections, validate_district_reports
        protections = resolve_protections(ROOT, town, source)
        expected = resolve_dressing(ROOT, town, source, catalogue(), protections)
        self.assertEqual(expected, town['settlement_dressing'])
        isolated = {**source, 'status': 'courtyard_dressing',
                    'placements': [p for p in source['placements'] if p['district']=='serene_terrace']}
        self.assertEqual(resolve_dressing(ROOT, town, isolated, catalogue(), protections), expected)
        workyards = resolve_workyards(ROOT, town, source, catalogue(), protections)
        self.assertEqual(workyards, town['settlement_workyards'])
        validate_district_reports(expected, workyards)
        by_id = {e['id']: e for e in town['entities']}
        for report in (expected, workyards):
            for entity in report['entities']:self.assertEqual(by_id[entity['id']], entity)
        protected_names = {record['id'] for record in protections}
        for name in ('workshop.workbench','workshop.timber_rack','workshop.spare_cog_fittings','workshop.stool_watering_can'):
            self.assertIn(name, by_id);self.assertIn('entity.'+name, protected_names)
        cues = {record.get('entity') for record in town.get('interaction_cues', [])}
        self.assertFalse(cues.intersection(entity['id'] for entity in workyards['entities']))
        self.assertEqual(town['overworld_exit'], read(ROOT/'assets/source/maps/eldenmere/town_hd/recipe.json')['overworld_exit'])

    def test_flat_materials_are_baked_into_native_ground_not_sorted_actor_entities(self):
        from tools.capture_eldenmere_streets import native_ground
        town = read(ROOT/'assets/maps/eldenmere/playable/map.json')
        ground = native_ground(town, 0)
        world_ids = {entity['id'] for entity in town['entities']}
        flat = town['settlement_workyards']['ground_entities']
        self.assertTrue(flat)
        for entity in flat:
            with self.subTest(entity=entity['id']):
                self.assertNotIn(entity['id'], world_ids)
                self.assertEqual(entity['artwork_pixels_per_world_pixel'], 2)
                x,y = [round(v*2) for v in entity['position']]
                with Image.open(ROOT/entity['frames'][0]) as picture:
                    native = picture.convert('RGBA')
                actual = ground.crop((x,y,x+native.width,y+native.height))
                opaque = native.getchannel('A')
                delta = ImageChops.difference(native.convert('RGB'), actual.convert('RGB'))
                self.assertIsNone(ImageChops.multiply(delta, opaque.convert('RGB')).getbbox())

    def test_town_collision_is_original_source_plus_all_declared_support_ledgers(self):
        town = read(ROOT/'assets/maps/eldenmere/playable/map.json')
        with Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/collision.png') as picture:
            expected = picture.convert('L')
        draw = ImageDraw.Draw(expected)
        for key in ('settlement_dressing', 'settlement_workyards', 'settlement_commons'):
            for support in town[key]['solid_footprints']:
                x,y,w,h = support['rect'];self.assertTrue(all(type(v) is int for v in (x,y,w,h)))
                draw.rectangle((x,y,x+w-1,y+h-1), fill=255)
        with Image.open(ROOT/town['collision']) as picture:
            self.assertIsNone(ImageChops.difference(expected, picture.convert('L').crop((0,0,*expected.size))).getbbox())
        with Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/navigation_allowed.png') as picture:
            original = picture.convert('L')
        with Image.open(ROOT/town['navigation_allowed']) as picture:
            self.assertEqual(original.tobytes(), picture.convert('L').crop((0,0,*original.size)).tobytes())


class WorkyardSaveCompatibility(unittest.TestCase):
    def test_old_save_on_new_stock_support_recovers_without_lost_progress_or_duplicates(self):
        import pygame
        from main import Game
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory);path = folder/'journey.json';settings = folder/'settings.json'
            game = Game(fullscreen=False, start_on_title=True, save_path=path, settings_path=settings)
            restored = None
            try:
                game.audio.set_music(0);game.audio.set_effects(0);game.on_title = False
                game.opening.restore({'version':1,'stage':'disabled'});game.opening_fade = game.transfer_cooldown = 0
                game.world = game.town;game.player.position.update(744, 396)
                self.assertTrue(game.town.can_stand(game.player.position));self.assertTrue(game.save_progress(), game.save_error)
                saved = read(path);support = game.town.data['settlement_workyards']['solid_footprints'][0]
                x,y,w,h = support['rect'];occupied = [x+w/2,y+h/2]
                with Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/collision.png') as picture:
                    before = picture.convert('L')
                draw = ImageDraw.Draw(before)
                for prop in game.town.data['settlement_dressing']['solid_footprints']:
                    px,py,pw,ph = prop['rect'];draw.rectangle((px,py,px+pw-1,py+ph-1), fill=255)
                probe = game.town.probe_rect(occupied)
                self.assertIsNone(before.crop((*probe.topleft,*probe.bottomright)).getbbox())
                self.assertFalse(game.town.can_stand(occupied))
                saved['player']['position'] = occupied;saved['exterior_position'] = occupied.copy()
                self.assertTrue(game.save_store.write(saved), game.save_store.error)
                progress = {key: copy.deepcopy(saved[key]) for key in ('quests','party','inventory')}
                restored = Game(fullscreen=False, start_on_title=True, save_path=path, settings_path=settings)
                restored.audio.set_music(0);restored.audio.set_effects(0)
                self.assertTrue(restored.begin_journey(True), restored.save_error)
                self.assertIs(restored.world, restored.town);self.assertNotEqual(list(restored.player.position), occupied)
                self.assertTrue(restored.world.can_stand(restored.player.position))
                for key, value in progress.items():self.assertEqual(getattr(restored,key).to_dict(), value)
                ids = [e['id'] for e in restored.town.data['entities'] if e['id'].startswith('settlement.workyards.')]
                self.assertEqual(len(ids),len(set(ids)))
                self.assertEqual(set(ids), {e['id'] for e in restored.town.data['settlement_workyards']['entities']})
            finally:
                game.music.stop()
                if restored is not None:restored.music.stop()
                pygame.quit()

