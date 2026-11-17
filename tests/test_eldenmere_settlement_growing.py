"""Venn's source plot adds native flat rows without claiming repair ownership."""
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

from tools.eldenmere_settlement_dressing import resolve_growing
from tools.eldenmere_settlement_inventory import inventory


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'assets/source/maps/eldenmere/settlement/recipe.json'
PLAN = 'assets/maps/eldenmere/terrain_foundation/adapted_plan.json'
PACK = ROOT/'assets/terrain/eldenmere/growing_fields'
REVIEW = ROOT/'docs/reviews/eldenmere_growing'
SCOPE = [1296, 624, 96, 168]
PREVIOUS_LEDGERS = ('settlement_dressing', 'settlement_workyards',
                    'settlement_commons', 'settlement_households')


def read(path):
    return json.loads(Path(path).read_text())


@lru_cache(None)
def catalogue():
    return inventory(ROOT, town=read(ROOT/'assets/maps/eldenmere/playable/map.json'))


def town():
    return {'id': 'eldenmere.playable', 'size_pixels': [1536, 1632],
            'player_probe_size': [24, 12], 'player_draw_anchor': [12, 30],
            'entities': [], 'doors': [],
            'grass': {'instances': [{'id': 'growing.fixture', 'position': [1368, 768],
                                     'variant': 'dense_hd', 'phase_ms': 200}]}}


def crate(**changes):
    return {'id': 'settlement.growing.crate', 'asset': 'workyard_props:empty_crate',
            'district': 'eastern_growing', 'position': [1304, 720],
            'collision': 'solid', 'footprint': [2, 12, 20, 6], 'occlusion': 'tall', **changes}


def field(**changes):
    return {'id': 'settlement.growing.field', 'asset': 'growing_fields:vegetables_east_west',
            'district': 'eastern_growing', 'position': [1320, 648],
            'collision': 'none', 'occlusion': 'ground', **changes}


def recipe(placements=None, **configuration):
    return {'version': 1, 'id': 'eldenmere.settlement', 'status': 'growing_dressing',
            'scene': 'eldenmere.playable',
            'districts': [{'id': 'eastern_growing', 'rect': [1104, 528, 432, 600]}],
            'placements': [crate()] if placements is None else placements,
            'growing_dressing': {'district': 'eastern_growing', 'scope_rect': SCOPE.copy(),
                                 'retire_grass_ids': [], 'ground_cells': [],
                                 'bed_contacts': [], **configuration}}


def bed_recipe(first=None):
    left = field() if first is None else first
    right = field(id='settlement.growing.field_east', position=[1344, 648], asset=left['asset'])
    return recipe([left, right], bed_contacts=[{'id': 'fixture_bed', 'rect': [1320, 648, 48, 24]}])


class GrowingRecipeTests(unittest.TestCase):
    def resolve(self, source=None, current=None, protections=(), root=ROOT):
        return resolve_growing(root, town() if current is None else current,
                               recipe() if source is None else source,
                               catalogue(), list(protections))

    def test_only_explicit_growing_stage_and_exact_source_plot_are_authorized(self):
        for status in ('framework_only', 'ground_only', 'courtyard_dressing',
                       'workyard_dressing', 'commons_dressing', 'household_dressing', 'active', None):
            source = recipe();source['status'] = status
            with self.subTest(status=status), self.assertRaises(ValueError):self.resolve(source)
        for change in ({'district': 'southern_arrival'}, {'scope_rect': [1296, 624, 120, 168]},
                       {'scope_rect': [1320, 624, 72, 168]}, {'scope_rect': [1104, 528, 432, 600]},
                       {'scope_source': 'another_plot.json'}, {'navigation': 'clear'}):
            with self.subTest(change=change), self.assertRaises(ValueError):self.resolve(recipe(**change))
        result = self.resolve()
        source = next(space for space in read(ROOT/PLAN)['spaces'] if space['id'] == 'venn_plots')
        self.assertEqual(result['scope_rect'], [value*24 for value in source['rect']])
        self.assertEqual(result['dependencies_sha256'][PLAN], sha256((ROOT/PLAN).read_bytes()).hexdigest())

    def test_missing_duplicate_rescaled_or_moved_source_plot_fails_before_art_resolution(self):
        for mutation in ('missing', 'duplicate', 'moved', 'rescaled'):
            plan = read(ROOT/PLAN)
            plot = next(space for space in plan['spaces'] if space['id'] == 'venn_plots')
            if mutation == 'missing':plan['spaces'].remove(plot)
            elif mutation == 'duplicate':plan['spaces'].append(copy.deepcopy(plot))
            elif mutation == 'moved':plot['rect'][0] += 1
            else:plan['tile_size_px'] = 12
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory);target = root/PLAN;target.parent.mkdir(parents=True)
                target.write_text(json.dumps(plan))
                with self.assertRaises(ValueError):self.resolve(root=root)

    def test_fields_are_typed_ground_entities_with_no_physics_or_instance_overrides(self):
        for asset in ('growing_fields:vegetables_east_west', 'growing_fields:furrows_east_west'):
            source = bed_recipe(field(asset=asset))
            report = self.resolve(source)
            self.assertEqual(report['entities'], [])
            self.assertEqual(report['solid_footprints'], [])
            self.assertEqual([entity['id'] for entity in report['ground_entities']],
                             [placement['id'] for placement in source['placements']])
        changes = ({'asset': 'growing_fields:unknown'}, {'collision': 'solid', 'footprint': [2, 12, 20, 6]},
                   {'footprint': [2, 12, 20, 6]}, {'occlusion': 'low'}, {'occlusion': 'tall'},
                   {'frames': ['replacement.png']}, {'frame_duration_ms': 1},
                   {'logical_size': [48, 24]}, {'interaction_cues': True},
                   {'asset': 'exteriors_hd:wood_shavings'})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(bed_recipe(field(**change)))

    def test_namespace_grid_and_complete_canvas_stay_inside_the_original_plot(self):
        for change in ({'id': 'well'}, {'id': 'settlement.households.field'},
                       {'id': 'settlement.growing.'}, {'district': 'workshop_mill'},
                       {'position': [1284, 648]}, {'position': [1380, 648]},
                       {'position': [1320.25, 648]}, {'position': [float('nan'), 648]},
                       {'position': [True, 648]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(bed_recipe(field(**change)))
        with self.assertRaises(ValueError):self.resolve(recipe([field(), field()]))

    def test_every_flat_tile_has_one_complete_authored_bed_without_contact_overrides(self):
        source = bed_recipe()
        self.assertEqual(self.resolve(source)['bed_contacts'][0]['rect'], [1320, 648, 48, 24])
        missing = copy.deepcopy(source);missing['growing_dressing'].pop('bed_contacts')
        with self.assertRaises(ValueError):self.resolve(missing)
        contacts = (None, [], [{'id': '', 'rect': [1320, 648, 48, 24]}],
                    [{'id': 'bed', 'rect': [1320, 648, 24, 24]}],
                    [{'id': 'bed', 'rect': [1321, 648, 48, 24]}],
                    [{'id': 'bed', 'rect': [1368, 648, 48, 24]}],
                    [{'id': 'bed', 'rect': [1320, 648, 48, 24], 'mask': 'replacement.png'}],
                    [{'id': 'bed', 'rect': [1320, 648, 48, 24]},
                     {'id': 'bed', 'rect': [1320, 696, 48, 24]}],
                    [{'id': 'bed', 'rect': [1320, 648, 48, 24]},
                     {'id': 'another', 'rect': [1320, 648, 48, 24]}])
        for value in contacts:
            invalid = copy.deepcopy(source);invalid['growing_dressing']['bed_contacts'] = value
            with self.subTest(contacts=value), self.assertRaises(ValueError):self.resolve(invalid)
        for mutation in ('missing_tile', 'extra_tile', 'mixed_crop', 'ordinary_prop'):
            invalid = copy.deepcopy(source)
            if mutation == 'missing_tile':invalid['placements'].pop()
            elif mutation == 'extra_tile':
                invalid['placements'].append(field(id='settlement.growing.unassigned', position=[1320, 696]))
            elif mutation == 'mixed_crop':invalid['placements'][1]['asset'] = 'growing_fields:furrows_east_west'
            else:invalid['placements'].append(crate(position=[1320, 648]))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):self.resolve(invalid)

    def test_the_storage_crate_keeps_supports_sightlines_and_other_owners_honest(self):
        for change in ({'collision': 'none'}, {'occlusion': 'low'}, {'footprint': [-1, 12, 20, 6]},
                       {'footprint': [2, 12, 24, 6]}, {'footprint': [2.5, 12, 20, 6]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe([crate(**change)]))
        missing = crate();missing.pop('footprint')
        with self.assertRaises(ValueError):self.resolve(recipe([missing]))
        for point, roles in (([1316, 735], ['movement']), ([1316, 760], ['sightline'])):
            protected = {'id': 'fixture.gate_contact', 'shape': 'point', 'geometry': point,
                         'padding': [12, 8], 'roles': roles}
            with self.subTest(roles=roles), self.assertRaises(ValueError):
                self.resolve(protections=[protected])
        current = town();current['entities'] = [{
            'id': 'existing_toolbox', 'position': [1304, 720], 'logical_size': [24, 20],
            'artwork_pixels_per_world_pixel': 2,
            'frames': ['assets/terrain/eldenmere/workyard_props/props/empty_crate/idle.png']}]
        with self.assertRaises(ValueError):self.resolve(current=current)

    def test_soil_transition_fringe_and_grass_retirements_cannot_leave_the_plot(self):
        valid = self.resolve(recipe(ground_cells=[[55, 27]], retire_grass_ids=['growing.fixture']))
        self.assertEqual(valid['ground_cells'], [[55, 27]])
        self.assertEqual(valid['retired_grass_records'], town()['grass']['instances'])
        for cells in ([[54, 26]], [[57, 27]], [[55, 32]], [[55.5, 27]], [[55, 27], [55, 27]]):
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                self.resolve(recipe(ground_cells=cells))
        for identifiers in (['missing'], ['growing.fixture', 'growing.fixture']):
            with self.subTest(identifiers=identifiers), self.assertRaises(ValueError):
                self.resolve(recipe(retire_grass_ids=identifiers))
        current = town();current['grass']['instances'][0]['position'] = [1390, 768]
        with self.assertRaises(ValueError):
            self.resolve(recipe(retire_grass_ids=['growing.fixture']), current)

    def test_rebuild_and_deactivation_track_both_world_and_baked_ground_owners(self):
        current = town();source = bed_recipe();source['placements'].append(crate())
        inputs = copy.deepcopy((current, source))
        first = self.resolve(source, current)
        self.assertEqual((current, source), inputs)
        rebuilt = copy.deepcopy(current);rebuilt['entities'] = first['entities']
        rebuilt['settlement_growing'] = first
        self.assertEqual(self.resolve(source, rebuilt), first)
        unowned = copy.deepcopy(current);unowned['entities'] = first['entities']
        with self.assertRaises(ValueError):self.resolve(source, unowned)
        for old_status in ('ground_only', 'household_dressing'):
            inactive = {'version': 1, 'scene': 'eldenmere.playable', 'status': old_status, 'placements': []}
            for previous in (first, {'ground_entities': first['ground_entities']}):
                with self.subTest(status=old_status, previous=previous.keys()), self.assertRaises(ValueError):
                    self.resolve(inactive, {**current, 'settlement_growing': previous})


class GrowingNativeBankTests(unittest.TestCase):
    def test_native_exports_are_exact_donor_bytes_with_palette_and_fine_detail_preserved(self):
        manifest = read(PACK/'manifest.json')
        self.assertEqual(manifest['artwork_pixels_per_world_pixel'], 2)
        self.assertEqual(manifest['recipe_sha256'], sha256((ROOT/manifest['recipe']).read_bytes()).hexdigest())
        for prop in manifest['props']:
            with self.subTest(prop=prop['id']):
                source, retained = prop['source'], prop['retained_source']
                target = PACK/prop['idle'];donor = ROOT/source['file']
                self.assertEqual(target.read_bytes(), donor.read_bytes())
                self.assertEqual(sha256(donor.read_bytes()).hexdigest(), source['sha256'])
                self.assertEqual(sha256(target.read_bytes()).hexdigest(), prop['output_sha256'])
                self.assertEqual(sha256((ROOT/retained['file']).read_bytes()).hexdigest(), retained['sha256'])
                self.assertFalse(prop['interaction_cues'])
                with Image.open(ROOT/retained['file']) as master:
                    native_crop = master.convert('RGBA').crop(retained['crop'])
                    self.assertEqual(sha256(native_crop.tobytes()).hexdigest(), retained['crop_pixels_sha256'])
                with Image.open(target) as picture, Image.open(donor) as donor_picture:
                    self.assertEqual(picture.size, (48, 48))
                    self.assertEqual(picture.size, tuple(value*2 for value in prop['logical_size']))
                    self.assertEqual(set(picture.convert('RGBA').getchannel('A').tobytes()), {255})
                    colors = {color for _, color in picture.convert('RGBA').getcolors(48*48)}
                    donor_colors = {color for _, color in donor_picture.convert('RGBA').getcolors(48*48)}
                    self.assertEqual(colors, donor_colors)
                    self.assertEqual(colors,
                                     {tuple(color) for color in prop['palette_rgba']})
                    self.assertEqual(len(prop['palette_rgba']), manifest['palette']['colors_per_tile'])
                    fine = sum(len({picture.getpixel((x+i, y+j)) for i in (0, 1) for j in (0, 1)}) > 1
                               for y in range(0, 48, 2) for x in range(0, 48, 2))
                    self.assertEqual(fine, prop['native_detail_blocks']);self.assertGreater(fine, 0)

    def test_whole_bed_contact_is_reproducible_binary_native_perimeter_coverage(self):
        manifest = read(PACK/'manifest.json');contact = manifest['bed_contact']
        path = PACK/contact['file']
        self.assertEqual(contact['artwork_pixels_per_world_pixel'], 2)
        self.assertEqual(contact['source_ref'], {'file': manifest['recipe'], 'path': ['bed_contact']})
        self.assertEqual(sha256(path.read_bytes()).hexdigest(), contact['sha256'])
        with Image.open(path) as image:
            self.assertEqual(image.mode, 'L');self.assertEqual(image.size, (96, 48))
            self.assertEqual(image.size, tuple(value*2 for value in contact['logical_size']))
            self.assertEqual(set(image.tobytes()), {0, 255})
            self.assertEqual(image.crop((2, 2, 94, 46)).getextrema(), (255, 255))
            for y in range(48):
                for x in range(96):
                    if image.getpixel((x, y)) == 0:
                        self.assertTrue(x < 2 or x >= 94 or y < 2 or y >= 46)

    def test_contact_source_cannot_erase_the_bed_interior(self):
        from tools import export_eldenmere_growing_fields as exporter
        source = read(ROOT/exporter.RECIPE)
        source['bed_contact']['edge_notches_artwork'].append([2, 2, 3, 1])
        original_path = exporter._path
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory)/'invalid_contact.json';invalid.write_text(json.dumps(source))
            def source_path(name):
                return invalid if name == exporter.RECIPE else original_path(name)
            with patch.object(exporter, '_path', side_effect=source_path), self.assertRaises(ValueError):
                exporter.products()

    def test_export_is_reproducible_and_does_not_rewrite_retained_donors(self):
        from tools.export_eldenmere_growing_fields import build, products
        manifest = read(PACK/'manifest.json')
        sources = {record[key]['file'] for record in manifest['props'] for key in ('source', 'retained_source')}
        before = {name: (ROOT/name).read_bytes() for name in sources}
        first = products();self.assertEqual(products(), first)
        for name, raw in first.items():self.assertEqual((ROOT/name).read_bytes(), raw, name)
        build(check=True)
        self.assertEqual({name: (ROOT/name).read_bytes() for name in sources}, before)


class LiveGrowingContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.town = read(ROOT/'assets/maps/eldenmere/playable/map.json')
        cls.source = read(SOURCE)
        cls.before = read(REVIEW/'before_town.json')

    def test_every_prior_entity_ledger_grass_street_and_gameplay_interface_is_preserved(self):
        for key in PREVIOUS_LEDGERS:self.assertEqual(self.town[key], self.before[key], key)
        self.assertEqual([entity for entity in self.town['entities']
                          if not entity['id'].startswith('settlement.growing.')], self.before['entities'])
        for key in ('grass', 'doors', 'destinations', 'overworld_exit', 'world_links', 'interior_scenes',
                    'interaction_cues', 'well_art', 'npcs', 'persistent_npcs', 'foreground',
                    'settlement_streets', 'cartography', 'art_replacements'):
            self.assertEqual(self.town.get(key), self.before.get(key), key)

    def test_growing_records_preserve_work_gate_and_cottage_source_protections(self):
        from tools.eldenmere_settlement import resolve_protections, validate_district_reports
        protections = resolve_protections(ROOT, self.town, self.source)
        names = {record['id'] for record in protections}
        for name in ('venn_gate_work', 'door.venn', 'liam_daisy_outdoor_play', 'well_gathering'):
            self.assertIn(name, names)
        gate = next(record for record in protections if record['id'] == 'venn_gate_work')
        self.assertEqual(gate['geometry'], [1388, 624, 90, 96])
        self.assertEqual(gate['source'], 'venn_visit.py')
        report = resolve_growing(ROOT, self.town, self.source, catalogue(), protections)
        self.assertEqual(report, self.town['settlement_growing'])
        validate_district_reports(*(self.town[key] for key in (*PREVIOUS_LEDGERS, 'settlement_growing')))
        ids = {record['id'] for record in [*report['entities'], *report['ground_entities']]}
        self.assertEqual(len(ids), len(report['entities'])+len(report['ground_entities']))
        self.assertFalse(ids & {record.get('entity') for record in self.town.get('interaction_cues', [])})

    def test_collision_is_source_plus_five_ledgers_and_navigation_remains_identical(self):
        with Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/collision.png') as image:
            expected = image.convert('L')
        painter = ImageDraw.Draw(expected)
        for key in (*PREVIOUS_LEDGERS, 'settlement_growing'):
            for support in self.town[key]['solid_footprints']:
                x, y, w, h = support['rect']
                self.assertTrue(all(type(value) is int for value in (x, y, w, h)))
                painter.rectangle((x, y, x+w-1, y+h-1), fill=255)
        with Image.open(ROOT/self.town['collision']) as image:
            self.assertIsNone(ImageChops.difference(expected, image.convert('L').crop((0, 0, *expected.size))).getbbox())
        observed = read(REVIEW/'before_observations.json')['production']
        original_nav_hash = observed['active_files'][self.before['navigation_allowed']]['sha256']
        self.assertEqual(sha256((ROOT/self.town['navigation_allowed']).read_bytes()).hexdigest(), original_nav_hash)

    def test_flat_crops_cannot_cover_the_working_gate_or_public_lane_inside_the_plot(self):
        from tools.eldenmere_settlement import resolve_protections
        protections = resolve_protections(ROOT, self.town, self.source)
        source = copy.deepcopy(self.source)
        source['placements'] = [record for record in source['placements']
                                if not record['id'].startswith('settlement.growing.')]
        # This complete bed fits the canonical plot, but intrudes into its
        # source-owned lane and the edge of the gate-work envelope. Flat paint
        # remains walkable; it must still read as a usable work route.
        source['placements'].extend([field(position=[1344, 648]),
            field(id='settlement.growing.field_east', position=[1368, 648])])
        source['growing_dressing']['bed_contacts'] = [{'id': 'intruding_bed', 'rect': [1344, 648, 48, 24]}]
        with self.assertRaises(ValueError):
            resolve_growing(ROOT, self.town, source, catalogue(), protections)

    def test_every_native_bed_texel_matches_donor_or_true_baseline_in_all_six_phases(self):
        from tools.capture_eldenmere_streets import native_ground
        report = self.town['settlement_growing']
        self.assertTrue(report['ground_entities'])
        world_ids = {entity['id'] for entity in self.town['entities']}
        for field_record in report['ground_entities']:
            self.assertNotIn(field_record['id'], world_ids)
            self.assertEqual(field_record['artwork_pixels_per_world_pixel'], 2)
        baseline = read(REVIEW/'before_bed_ground.json')
        self.assertEqual(baseline['source_revision'], read(REVIEW/'before_revision.json')['git_commit'])
        beds = {bed['id']: bed for bed in baseline['beds']}
        self.assertEqual(set(beds), {contact['id'] for contact in report['bed_contacts']})
        for phase in range(6):
            ground = native_ground(self.town, phase*200)
            for contact in report['bed_contacts']:
                with self.subTest(bed=contact['id'], phase=phase):
                    x, y, w, h = contact['rect'];body = Image.new('RGBA', (w*2, h*2))
                    for position in ([x, y], [x+24, y]):
                        tile = next(record for record in report['ground_entities'] if record['position'] == position)
                        with Image.open(ROOT/tile['frames'][0]) as image:
                            body.alpha_composite(image.convert('RGBA'), (round((position[0]-x)*2), 0))
                    before = beds[contact['id']]
                    self.assertEqual(before['rect'], contact['rect'])
                    witness = next(record for record in before['phases'] if record['phase'] == phase)
                    source_path = REVIEW/witness['image']
                    self.assertEqual(sha256(source_path.read_bytes()).hexdigest(), witness['png_sha256'])
                    with Image.open(source_path) as image:
                        expected = image.convert('RGBA')
                    self.assertEqual(expected.size, (96, 48))
                    self.assertEqual(sha256(expected.tobytes()).hexdigest(), witness['rgba_sha256'])
                    with Image.open(ROOT/contact['mask']) as mask:
                        expected.paste(body, (0, 0), mask)
                    actual = ground.crop((x*2, y*2, (x+w)*2, (y+h)*2))
                    self.assertEqual(actual.tobytes(), expected.tobytes())


class GrowingSaveCompatibility(unittest.TestCase):
    def test_old_clear_plot_checkpoint_recovers_from_new_crate_without_lost_progress(self):
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
                game.world = game.town;game.player.position.update(1368, 720)
                self.assertTrue(game.town.can_stand(game.player.position))
                self.assertTrue(game.save_progress(), game.save_error)
                saved = read(save)
                support = game.town.data['settlement_growing']['solid_footprints'][0]
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
                for key in (*PREVIOUS_LEDGERS, 'settlement_growing'):
                    self.assertEqual(restored.town.data[key], game.town.data[key])
            finally:
                game.music.stop()
                if restored is not None:restored.music.stop()
                pygame.quit()


if __name__ == '__main__':
    unittest.main()
