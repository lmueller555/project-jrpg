"""Named household parcels preserve civic ownership, access and old checkpoints."""
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

from tools.eldenmere_settlement_dressing import (
    resolve_commons, resolve_dressing, resolve_households, resolve_workyards,
)
from tools.eldenmere_settlement_inventory import inventory


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/maps/eldenmere/settlement/recipe.json'
REVIEW = ROOT/'docs/reviews/eldenmere_households'
DISTRICT = [144, 480, 672, 696]
PARCEL = [432, 480, 192, 192]
PREVIOUS_LEDGERS = ('settlement_dressing', 'settlement_workyards', 'settlement_commons')


def read(path):
    return json.loads(Path(path).read_text())


@lru_cache(None)
def catalogue():
    return inventory(ROOT, town=read(ROOT/'assets/maps/eldenmere/playable/map.json'))


def town():
    return {'id': 'eldenmere.playable', 'size_pixels': [1536, 1632],
            'player_probe_size': [24, 12], 'player_draw_anchor': [12, 30],
            'entities': [], 'doors': [],
            'grass': {'instances': [{'id': 'household.fixture', 'position': [552, 624],
                                     'variant': 'dense_hd', 'phase_ms': 200}]}}


def placement(**changes):
    return {'id': 'settlement.households.planter', 'parcel': 'home_b',
            'asset': 'exteriors_hd:flowerpot_pair', 'district': 'commons_households',
            'position': [480, 552], 'collision': 'solid',
            'footprint': [2, 18, 20, 4], 'occlusion': 'tall', **changes}


def recipe(placements=None, **configuration):
    return {'version': 1, 'id': 'eldenmere.settlement', 'status': 'household_dressing',
            'scene': 'eldenmere.playable',
            'districts': [{'id': 'commons_households', 'rect': DISTRICT.copy()},
                          {'id': 'serene_terrace', 'rect': [120, 120, 600, 336]},
                          {'id': 'workshop_mill', 'rect': [552, 264, 552, 288]}],
            'placements': [placement()] if placements is None else placements,
            'courtyard_dressing': {'district': 'serene_terrace',
                                   'scope_rect': [120, 120, 600, 336],
                                   'retire_grass_ids': [], 'garden_cells': []},
            'workyard_dressing': {'district': 'workshop_mill',
                                  'scope_rect': [552, 264, 552, 288],
                                  'retire_grass_ids': [], 'ground_cells': []},
            'commons_dressing': {'district': 'commons_households',
                                 'scope_rect': [384, 720, 384, 288],
                                 'retire_grass_ids': [], 'ground_cells': []},
            'household_dressing': {'district': 'commons_households',
                                   'scope_rect': DISTRICT.copy(), 'retire_grass_ids': [],
                                   'ground_cells': [],
                                   'parcels': [{'id': 'home_b', 'scope_rect': PARCEL.copy()}],
                                   **configuration}}


class HouseholdRecipeTests(unittest.TestCase):
    def resolve(self, source=None, current=None, protections=()):
        return resolve_households(ROOT, town() if current is None else current,
                                  recipe() if source is None else source,
                                  catalogue(), list(protections))

    def test_only_explicit_household_stage_and_cottage_district_can_activate(self):
        for status in ('framework_only', 'ground_only', 'courtyard_dressing',
                       'workyard_dressing', 'commons_dressing', 'active', None):
            source = recipe();source['status'] = status
            with self.subTest(status=status), self.assertRaises(ValueError):self.resolve(source)
        for change in ({'district': 'eastern_growing'}, {'scope_rect': [0, 0, 1536, 1632]},
                       {'navigation': 'clear'}, {'ground_cells': [[True, 23]]}):
            with self.subTest(change=change), self.assertRaises(ValueError):self.resolve(recipe(**change))

    def test_named_parcels_are_unique_disjoint_bounded_native_rectangles(self):
        invalid = ([], [{'id': 'school', 'scope_rect': PARCEL}],
                   [{'id': 'home_b', 'scope_rect': PARCEL}]*2,
                   [{'id': 'home_b', 'scope_rect': PARCEL},
                    {'id': 'home_a', 'scope_rect': [600, 500, 48, 48]}],
                   [{'id': 'home_b', 'scope_rect': [120, 480, 48, 48]}],
                   [{'id': 'home_b', 'scope_rect': [432, 480, 0, 192]}],
                   [{'id': 'home_b', 'scope_rect': [432.25, 480, 192, 192]}],
                   [{'id': 'home_b', 'scope_rect': PARCEL, 'collision': 'none'}])
        for parcels in invalid:
            with self.subTest(parcels=parcels), self.assertRaises(ValueError):
                self.resolve(recipe(parcels=parcels))
        adjacent = [{'id': 'home_b', 'scope_rect': PARCEL},
                    {'id': 'home_a', 'scope_rect': [624, 480, 144, 192]}]
        self.assertEqual(self.resolve(recipe(parcels=adjacent))['parcels'], adjacent)

    def test_every_canvas_must_fit_its_named_parcel_even_inside_the_district(self):
        for change in ({'parcel': 'elira'}, {'parcel': None}, {'position': [624, 552]},
                       {'position': [612, 552]}, {'position': [480.25, 552]},
                       {'position': [float('nan'), 552]}, {'position': [True, 552]},
                       {'district': 'serene_terrace'}, {'id': 'settlement.households.'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe([placement(**change)]))
        missing = placement();missing.pop('parcel')
        with self.assertRaises(ValueError):self.resolve(recipe([missing]))
        with self.assertRaises(ValueError):self.resolve(recipe([placement(), placement()]))
        # A non-household namespace must fail in the complete delivery rather
        # than disappear while the two owners partition their shared district.
        for name in ('well', 'settlement.misc.planter'):
            source = recipe([placement(id=name)])
            with self.subTest(name=name), self.assertRaises(ValueError):
                for resolver in (resolve_dressing, resolve_workyards, resolve_commons, resolve_households):
                    resolver(ROOT, town(), source, catalogue(), [])

    def test_decorative_solids_need_honest_supports_and_no_instance_art_overrides(self):
        changes = ({'collision': 'none'}, {'occlusion': 'low'}, {'frames': ['made_up.png']},
                   {'frame_duration_ms': 1}, {'interaction_cues': True}, {'logical_size': [8, 8]},
                   {'asset': 'missing:prop'}, {'footprint': [-1, 18, 20, 4]},
                   {'footprint': [2, 18, 24, 4]}, {'footprint': [2.5, 18, 20, 4]})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe([placement(**change)]))
        missing = placement();missing.pop('footprint')
        with self.assertRaises(ValueError):self.resolve(recipe([missing]))
        flat = placement(asset='exteriors_hd:wood_shavings', collision='none', occlusion='ground')
        flat.pop('footprint')
        with self.assertRaises(ValueError):self.resolve(recipe([flat]))

    def test_work_stations_sightlines_and_existing_occupied_art_remain_clear(self):
        for geometry, roles in (([492, 572], ['movement']), ([492, 590], ['sightline'])):
            protection = {'id': 'fixture.family_contact', 'shape': 'point',
                          'geometry': geometry, 'padding': [12, 8], 'roles': roles}
            with self.subTest(roles=roles), self.assertRaises(ValueError):
                self.resolve(protections=[protection])
        current = town();current['entities'] = [{
            'id': 'settlement.commons.existing', 'position': [480, 552],
            'logical_size': [24, 24], 'artwork_pixels_per_world_pixel': 2,
            'frames': ['assets/terrain/eldenmere/exteriors_hd/props/flowerpot_pair/idle.png']}]
        with self.assertRaises(ValueError):self.resolve(current=current)
        overlapping = placement(id='settlement.households.second', position=[492, 552])
        with self.assertRaises(ValueError):self.resolve(recipe([placement(), overlapping]))
        overlapping['position'] = [528, 552]
        self.assertEqual(len(self.resolve(recipe([placement(), overlapping]))['entities']), 2)

    def test_ground_transition_rim_and_retired_grass_fit_one_named_parcel(self):
        source = recipe(ground_cells=[[21, 23]], retire_grass_ids=['household.fixture'])
        current = town();first = self.resolve(source, current)
        self.assertEqual(first['retired_grass_records'], current['grass']['instances'])
        rebuilt = copy.deepcopy(current);rebuilt['grass']['instances'] = []
        rebuilt['settlement_households'] = first
        self.assertEqual(self.resolve(source, rebuilt)['retired_grass_records'], first['retired_grass_records'])
        for cells in ([[18, 20]], [[30, 28]], [[21.5, 23]], [[21, 23], [21, 23]]):
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                self.resolve(recipe(ground_cells=cells))
        current['grass']['instances'][0]['position'] = [630, 624]
        with self.assertRaises(ValueError):self.resolve(source, current)
        for identifiers in (['missing'], ['household.fixture', 'household.fixture']):
            with self.subTest(identifiers=identifiers), self.assertRaises(ValueError):
                self.resolve(recipe(retire_grass_ids=identifiers))

    def test_laundry_uses_authored_cloth_frames_and_reduced_motion_idle(self):
        laundry = placement(asset='exteriors_hd:laundry_line', footprint=[2, 20, 36, 3])
        report = self.resolve(recipe([laundry]));entity = report['entities'][0]
        manifest = 'assets/terrain/eldenmere/exteriors_hd/manifest.json'
        source = next(prop for prop in read(ROOT/manifest)['props'] if prop['id'] == 'laundry_line')
        parent = Path(manifest).parent
        self.assertEqual(entity['frames'], [(parent/frame).as_posix() for frame in source['frames']])
        self.assertEqual(entity['frame_duration_ms'], source['frame_duration_ms'])
        self.assertEqual(len(entity['frames'])*entity['frame_duration_ms'], source['cycle_ms'])
        self.assertEqual(entity['reduced_motion_image'], (parent/source['idle']).as_posix())
        self.assertEqual(entity['reduced_motion_frame'], 0)
        self.assertGreater(len({(ROOT/frame).read_bytes() for frame in entity['frames']}), 1)
        for frame in [*entity['frames'], entity['reduced_motion_image']]:
            self.assertEqual(report['dependencies_sha256'][frame], sha256((ROOT/frame).read_bytes()).hexdigest())
            with Image.open(ROOT/frame) as image:
                self.assertEqual(image.size, tuple(value*2 for value in source['logical_size']))
                self.assertLessEqual(set(image.getchannel('A').tobytes()), {0, 255})

    def test_source_owners_rebuild_stably_and_cannot_be_silently_deactivated(self):
        current = town();source = recipe();inputs = copy.deepcopy((current, source))
        first = self.resolve(source, current)
        self.assertEqual((current, source), inputs)
        unowned = copy.deepcopy(current);unowned['entities'] = first['entities']
        with self.assertRaises(ValueError):self.resolve(source, unowned)
        rebuilt = copy.deepcopy(unowned);rebuilt['settlement_households'] = first
        self.assertEqual(self.resolve(source, rebuilt), first)
        rebuilt['entities'].append({**first['entities'][0], 'id': 'settlement.households.unowned'})
        with self.assertRaises(ValueError):self.resolve(source, rebuilt)
        for status in ('ground_only', 'commons_dressing'):
            inactive = {'version': 1, 'scene': 'eldenmere.playable', 'status': status, 'placements': []}
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.resolve(inactive, {**current, 'settlement_households': first})
            with self.subTest(status=status, stray=True), self.assertRaises(ValueError):
                self.resolve(inactive, unowned)


class LiveHouseholdContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.town = read(ROOT/'assets/maps/eldenmere/playable/map.json')
        cls.source = read(SOURCE)
        cls.before = read(REVIEW/'before_town.json')

    def test_every_prior_entity_ledger_street_and_gameplay_interface_is_preserved(self):
        for key in PREVIOUS_LEDGERS:
            self.assertEqual(self.town[key], self.before[key], key)
        self.assertEqual([e for e in self.town['entities']
                          if not e['id'].startswith('settlement.households.')], self.before['entities'])
        for key in ('doors', 'destinations', 'overworld_exit', 'world_links', 'interior_scenes',
                    'interaction_cues', 'well_art', 'npcs', 'persistent_npcs', 'foreground',
                    'settlement_streets', 'cartography'):
            self.assertEqual(self.town.get(key), self.before.get(key), key)
        ids = [entity['id'] for entity in self.town['entities']]
        self.assertEqual(len(ids), len(set(ids)))

    def test_live_households_resolve_without_claiming_the_civic_owner(self):
        from tools.eldenmere_settlement import resolve_protections, validate_district_reports
        protections = resolve_protections(ROOT, self.town, self.source)
        names = {record['id'] for record in protections}
        for identifier in ('liam_daisy_outdoor_play', 'well_gathering', 'entity.well', 'entity.school.bench'):
            self.assertIn(identifier, names)
        for parcel in self.source['household_dressing']['parcels']:
            self.assertIn('door.'+parcel['id'], names)
        report = resolve_households(ROOT, self.town, self.source, catalogue(), protections)
        self.assertEqual(report, self.town['settlement_households'])
        self.assertEqual(resolve_commons(ROOT, self.town, self.source, catalogue(), protections),
                         self.before['settlement_commons'])
        validate_district_reports(*(self.town[key] for key in (*PREVIOUS_LEDGERS, 'settlement_households')))
        household_ids = {entity['id'] for entity in report['entities']}
        cues = {record.get('entity') for record in self.town.get('interaction_cues', [])}
        self.assertFalse(household_ids & cues)

    def test_collision_is_the_original_source_plus_four_explicit_ledgers_and_nav_is_identical(self):
        with Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/collision.png') as image:
            expected = image.convert('L')
        painter = ImageDraw.Draw(expected)
        for key in (*PREVIOUS_LEDGERS, 'settlement_households'):
            for support in self.town[key]['solid_footprints']:
                x, y, w, h = support['rect']
                self.assertTrue(all(type(value) is int for value in (x, y, w, h)))
                painter.rectangle((x, y, x+w-1, y+h-1), fill=255)
        with Image.open(ROOT/self.town['collision']) as image:
            self.assertIsNone(ImageChops.difference(expected, image.convert('L').crop((0, 0, *expected.size))).getbbox())
        observed = read(REVIEW/'before_observations.json')['production']
        original_nav_hash = observed['active_files'][self.before['navigation_allowed']]['sha256']
        self.assertEqual(sha256((ROOT/self.town['navigation_allowed']).read_bytes()).hexdigest(), original_nav_hash)


class HouseholdSaveCompatibility(unittest.TestCase):
    def test_preexisting_checkpoint_inside_new_support_recovers_without_losing_progress(self):
        import pygame
        from main import Game
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory);save = folder/'journey.json';settings = folder/'settings.json'
            game = Game(fullscreen=False, start_on_title=True, save_path=save, settings_path=settings)
            restored = None
            try:
                game.audio.set_music(0);game.audio.set_effects(0);game.on_title = False
                game.opening.restore({'version': 1, 'stage': 'disabled'})
                game.opening_fade = game.transfer_cooldown = 0
                game.world = game.town;game.player.position.update(528, 900)
                self.assertTrue(game.town.can_stand(game.player.position))
                self.assertTrue(game.save_progress(), game.save_error)
                saved = read(save)
                support = game.town.data['settlement_households']['solid_footprints'][0]
                x, y, w, h = support['rect'];occupied = [x+w/2, y+h/2]
                with Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/collision.png') as image:
                    previous = image.convert('L')
                painter = ImageDraw.Draw(previous)
                for key in PREVIOUS_LEDGERS:
                    for old_support in read(REVIEW/'before_town.json')[key]['solid_footprints']:
                        px, py, pw, ph = old_support['rect']
                        painter.rectangle((px, py, px+pw-1, py+ph-1), fill=255)
                probe = game.town.probe_rect(occupied)
                self.assertIsNone(previous.crop((*probe.topleft, *probe.bottomright)).getbbox())
                self.assertFalse(game.town.can_stand(occupied))
                saved['player']['position'] = occupied;saved['exterior_position'] = occupied.copy()
                self.assertTrue(game.save_store.write(saved), game.save_store.error)
                progress = {key: copy.deepcopy(saved[key]) for key in ('quests', 'party', 'inventory')}
                restored = Game(fullscreen=False, start_on_title=True, save_path=save, settings_path=settings)
                restored.audio.set_music(0);restored.audio.set_effects(0)
                self.assertTrue(restored.begin_journey(True), restored.save_error)
                self.assertIs(restored.world, restored.town)
                self.assertNotEqual(list(restored.player.position), occupied)
                self.assertTrue(restored.town.can_stand(restored.player.position))
                for key, value in progress.items():self.assertEqual(getattr(restored, key).to_dict(), value)
                self.assertEqual(restored.social.flags, game.social.flags)
                for key in (*PREVIOUS_LEDGERS, 'settlement_households'):
                    self.assertEqual(restored.town.data[key], game.town.data[key])
                ids = [entity['id'] for entity in restored.town.data['settlement_households']['entities']]
                self.assertEqual(len(ids), len(set(ids)))
            finally:
                game.music.stop()
                if restored is not None:restored.music.stop()
                pygame.quit()


if __name__ == '__main__':
    unittest.main()
