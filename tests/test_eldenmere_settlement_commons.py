"""Civic composition preserves the functional well, earlier districts and access."""
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

from tools.eldenmere_settlement_dressing import resolve_commons
from tools.eldenmere_settlement_inventory import inventory


ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT/'assets/source/maps/eldenmere/settlement/recipe.json'
SCOPE = [384, 720, 384, 288]
DISTRICT = [144, 480, 672, 696]


def read(path):
    return json.loads(Path(path).read_text())


def before_town():
    return read(ROOT/'docs/reviews/eldenmere_commons/before_town.json')


def before_observations():
    return read(ROOT/'docs/reviews/eldenmere_commons/before_observations.json')


@lru_cache(None)
def catalogue():
    return inventory(ROOT, town=read(ROOT/'assets/maps/eldenmere/playable/map.json'))


def fixture_town():
    return {'id': 'eldenmere.playable', 'size_pixels': [1536, 1632],
            'player_probe_size': [24, 12], 'player_draw_anchor': [12, 30],
            'entities': [], 'doors': [],
            'grass': {'instances': [{'id': 'commons.fixture', 'position': [744, 984],
                                     'variant': 'dense_hd', 'phase_ms': 500}]}}


def placement(**extra):
    return {'id': 'settlement.commons.planter', 'asset': 'exteriors_hd:flowerpot_pair',
            'district': 'commons_households', 'position': [600, 900],
            'collision': 'solid', 'footprint': [2, 18, 20, 4], 'occlusion': 'tall', **extra}


def recipe(placements=None, **config):
    return {'version': 1, 'id': 'eldenmere.settlement', 'status': 'commons_dressing',
            'scene': 'eldenmere.playable',
            'districts': [{'id': 'commons_households', 'rect': DISTRICT.copy()},
                          {'id': 'serene_terrace', 'rect': [120, 120, 600, 336]},
                          {'id': 'workshop_mill', 'rect': [552, 264, 552, 288]}],
            'placements': [placement()] if placements is None else placements,
            'commons_dressing': {'district': 'commons_households', 'scope_rect': SCOPE.copy(),
                                 'retire_grass_ids': [], 'ground_cells': [], **config}}


def station(position, roles):
    return {'id': 'fixture.civic_contact', 'shape': 'point', 'geometry': list(position),
            'padding': [12, 8], 'roles': list(roles)}


class CommonsRecipeTests(unittest.TestCase):
    def resolve(self, config=None, current=None, protections=()):
        return resolve_commons(ROOT, fixture_town() if current is None else current,
                               recipe() if config is None else config,
                               catalogue(), list(protections))

    def test_explicit_civic_activation_namespace_and_district_are_required(self):
        for status in ('framework_only', 'ground_only', 'courtyard_dressing', 'workyard_dressing', 'active', None):
            config = recipe();config['status'] = status
            with self.subTest(status=status), self.assertRaises(ValueError):self.resolve(config)
        for config in ({'district': 'eastern_growing'}, {'scope_rect': [0, 0, 1536, 1632]},
                       {'scope_rect': [384, 720, 0, 288]}, {'navigation': 'clear'}):
            with self.subTest(config=config), self.assertRaises(ValueError):self.resolve(recipe(**config))
        for change in ({'id': 'well'}, {'id': 'settlement.workyards.new_bench'},
                       {'district': 'southern_arrival'}, {'position': [380, 900]},
                       {'position': [756, 900]}, {'position': [600.25, 900]},
                       {'position': [float('nan'), 900]}, {'position': [True, 900]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe([placement(**change)]))
        with self.assertRaises(ValueError):self.resolve(recipe([placement(),placement()]))

    def test_source_animation_interaction_and_collision_cannot_be_overridden(self):
        changes = ({'frames': ['unregistered.png']}, {'logical_size': [4,4]},
                   {'sort_y': 1}, {'interaction_cues': True}, {'asset': 'missing:prop'},
                   {'collision': 'none'}, {'occlusion': 'ground'},
                   {'footprint': [-1,18,20,4]}, {'footprint': [2,18,24,4]})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.resolve(recipe([placement(**change)]))
        missing = placement();missing.pop('footprint')
        with self.assertRaises(ValueError):self.resolve(recipe([missing]))
        shavings = placement(asset='exteriors_hd:wood_shavings', collision='none', occlusion='ground')
        shavings.pop('footprint')
        with self.assertRaises(ValueError):self.resolve(recipe([shavings]))

    def test_working_contacts_and_actor_sightlines_reject_even_small_props(self):
        with self.assertRaises(ValueError):
            self.resolve(protections=[station([612,920], ('movement',))])
        with self.assertRaises(ValueError):
            self.resolve(protections=[station([612,938], ('sightline',))])
        self.assertTrue(self.resolve(protections=[station([528,864], ('movement','sightline'))])['entities'])

    def test_existing_owned_artwork_and_other_proposals_cannot_be_cloned_over(self):
        current = fixture_town()
        current['entities'] = [{'id': 'school.bench', 'position': [600,900],
                                'logical_size': [24,24], 'artwork_pixels_per_world_pixel': 2,
                                'frames': ['assets/terrain/eldenmere/exteriors_hd/props/flowerpot_pair/idle.png']}]
        with self.assertRaises(ValueError):self.resolve(current=current)
        second = placement(id='settlement.commons.second', position=[612,900])
        with self.assertRaises(ValueError):self.resolve(recipe([placement(),second]))
        second['position'] = [648,900]
        self.assertEqual(len(self.resolve(recipe([placement(),second]))['entities']),2)

    def test_low_plants_keep_source_breeze_and_remain_nonblocking(self):
        flower = placement(asset='vegetation_hd:flowers_white', collision='none', occlusion='low')
        flower.pop('footprint')
        report = self.resolve(recipe([flower]));entity = report['entities'][0]
        self.assertEqual(report['solid_footprints'],[])
        self.assertGreater(len(entity['frames']),1)
        self.assertEqual(entity['reduced_motion_frame'],0)
        with self.assertRaises(ValueError):
            self.resolve(recipe([{**flower,'collision':'solid','footprint':[2,18,20,4]}]))

    def test_retired_grass_and_ground_cells_are_explicit_scoped_and_reconstructible(self):
        current = fixture_town();cells = [[25,37],[26,37]]
        config = recipe(retire_grass_ids=['commons.fixture'],ground_cells=cells)
        first = self.resolve(config,current)
        self.assertEqual(first['ground_cells'],cells)
        self.assertEqual(first['retired_grass_records'],current['grass']['instances'])
        rebuilt = copy.deepcopy(current);rebuilt['grass']['instances']=[];rebuilt['settlement_commons']=first
        self.assertEqual(self.resolve(config,rebuilt)['retired_grass_records'],first['retired_grass_records'])
        for invalid in ([[25.5,37]],[[True,37]],[[25,37],[25,37]],[[31,42]],[[15,37]]):
            with self.subTest(cells=invalid), self.assertRaises(ValueError):self.resolve(recipe(ground_cells=invalid))
        for ids in (['missing'],['commons.fixture','commons.fixture']):
            with self.subTest(ids=ids), self.assertRaises(ValueError):self.resolve(recipe(retire_grass_ids=ids))

    def test_rebuild_requires_declared_ownership_and_deactivation_cannot_leave_objects(self):
        current = fixture_town();first = self.resolve(current=current)
        untrusted = copy.deepcopy(current);untrusted['entities']=copy.deepcopy(first['entities'])
        with self.assertRaises(ValueError):self.resolve(current=untrusted)
        rebuilt = copy.deepcopy(untrusted);rebuilt['settlement_commons']=first
        self.assertEqual(self.resolve(current=rebuilt),first)
        rebuilt['entities'].append({**first['entities'][0],'id':'settlement.commons.unowned'})
        with self.assertRaises(ValueError):self.resolve(current=rebuilt)
        for status in ('ground_only','courtyard_dressing','workyard_dressing'):
            inactive = {'version':1,'scene':'eldenmere.playable','status':status,'placements':[]}
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.resolve(inactive,{**current,'settlement_commons':first})
            with self.subTest(status=status,unowned=True), self.assertRaises(ValueError):self.resolve(inactive,untrusted)

    def test_native_frames_depth_and_provenance_are_stable_without_input_mutation(self):
        current = fixture_town();config = recipe([placement(position=[600.5,900.5],footprint=[1.5,17.5,20,4])])
        original = copy.deepcopy((current,config));first = self.resolve(config,current)
        self.assertEqual(self.resolve(config,current),first);self.assertEqual((current,config),original)
        self.assertEqual(first['solid_footprints'],[{'id':'settlement.commons.planter','rect':[602,918,20,4]}])
        entity = first['entities'][0]
        prop = next(p for p in read(ROOT/'assets/terrain/eldenmere/exteriors_hd/manifest.json')['props'] if p['id']=='flowerpot_pair')
        self.assertEqual(entity['logical_size'],prop['logical_size'])
        self.assertEqual(entity['sort_y'],900.5+prop['depth_baseline_logical'])
        for path in entity['frames']:
            self.assertEqual(first['dependencies_sha256'][path],sha256((ROOT/path).read_bytes()).hexdigest())
            with Image.open(ROOT/path) as image:
                self.assertEqual(image.size,tuple(v*2 for v in prop['logical_size']))
                self.assertLessEqual(set(image.getchannel('A').tobytes()),{0,255})


class CommonsWellUnderlayTests(unittest.TestCase):
    def setUp(self):
        self.town=read(ROOT/'assets/maps/eldenmere/playable/map.json')
        self.config=read(RECIPE);self.config['placements']=[]
        self.underlay=next(p for p in self.config['ground_treatments']
                           if p['id']=='settlement.street.commons.well_base')
        self.config['ground_treatments']=[self.underlay]

    def test_only_canonical_well_underlay_can_bypass_the_visual_blocked_mask(self):
        from tools.eldenmere_settlement_streets import resolve_streets
        layout=read(ROOT/self.town['layout_source'])
        self.assertEqual(self.underlay['rect'],layout['well_ground_rect'])
        self.assertEqual(self.underlay['source_ref'],
                         {'file':self.town['layout_source'],'path':['well_ground_rect']})
        self.assertEqual(resolve_streets(ROOT,self.town,self.config)[0],self.underlay)
        changes=({'rect':[480,840,72,48]}, {'rect':[504,840,48,72]},
                 {'under_fixture':'school.bench'}, {'material':'dirt'},
                 {'id':'settlement.street.commons.forged'},
                 {'source_ref':{'file':self.town['layout_source'],'path':['plaza_rect_tiles']}})
        for change in changes:
            config=copy.deepcopy(self.config);config['ground_treatments'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                resolve_streets(ROOT,self.town,config)
        for status in ('ground_only','courtyard_dressing','workyard_dressing'):
            config=copy.deepcopy(self.config);config['status']=status
            with self.subTest(status=status),self.assertRaises(ValueError):
                resolve_streets(ROOT,self.town,config)

    def test_underlay_cannot_authorize_a_missing_moved_or_duplicate_well(self):
        from tools.eldenmere_settlement_streets import resolve_streets
        for mutation in ('missing','moved','duplicate'):
            current=copy.deepcopy(self.town)
            well=next(e for e in current['entities'] if e['id']=='well')
            if mutation=='missing':current['entities'].remove(well)
            elif mutation=='moved':well['position'][0]+=24
            else:current['entities'].append(copy.deepcopy(well))
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                resolve_streets(ROOT,current,self.config)

    def test_native_stone_covers_only_the_authorized_well_base_without_changing_physics(self):
        from tools.eldenmere_hd_materials import Materials
        from tools.eldenmere_settlement_streets import paint_streets
        current=copy.deepcopy(self.town);current['size_pixels']=[600,912]
        current['entities']=[e for e in current['entities'] if e['id']=='well']
        base=Image.new('RGBA',(1200,1824),(1,2,3,255));blocked=Image.new('L',(600,912),255)
        config=copy.deepcopy(self.config)
        config['ground_treatments'].append({'id':'settlement.street.commons.blocked_probe',
            'material':'stone','role':'junction','shape':'rect','rect':[0,0,24,24]})
        inputs=(copy.deepcopy(current),copy.deepcopy(config),base.tobytes(),blocked.tobytes())
        after,report=paint_streets(base,ROOT,current,config,Materials(),blocked)
        x,y,w,h=self.underlay['rect'];bounds=(x*2,y*2,(x+w)*2,(y+h)*2)
        self.assertEqual(report['coverage_mask'].getbbox(),bounds)
        self.assertEqual(report['painted_native_pixels'],w*h*4)
        self.assertNotEqual(after.crop(bounds).tobytes(),base.crop(bounds).tobytes())
        difference=ImageChops.difference(after,base).convert('RGB')
        self.assertIsNone(ImageChops.multiply(difference,
            ImageChops.invert(report['coverage_mask']).convert('RGB')).getbbox())
        # The exception reveals the same world-phased paving as ordinary clear
        # ground. It grants no permission to the adjacent blocked probe.
        ordinary=copy.deepcopy(self.config);ordinary['ground_treatments'][0].pop('under_fixture')
        expected,_=paint_streets(base,ROOT,current,ordinary,Materials(),Image.new('L',(600,912)))
        self.assertEqual(after.crop(bounds).tobytes(),expected.crop(bounds).tobytes())
        self.assertEqual((current,config,base.tobytes(),blocked.tobytes()),inputs)


class LiveCommonsContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.town=read(ROOT/'assets/maps/eldenmere/playable/map.json');cls.recipe=read(RECIPE)
        cls.before=before_town()

    def test_previous_district_ledgers_and_every_prior_entity_are_unchanged(self):
        for key in ('settlement_dressing','settlement_workyards'):
            current_ledger=copy.deepcopy(self.town[key])
            earlier_ledger=self.before[key]
            exterior_source='assets/terrain/eldenmere/exteriors_hd/manifest.json'
            # A roof-art rebuild changes the tracked source hash, not the
            # placements or supports made from it. Require that the refreshed
            # value is the real live source; every other ledger byte stays pinned.
            self.assertEqual(current_ledger['dependencies_sha256'][exterior_source],
                             sha256((ROOT/exterior_source).read_bytes()).hexdigest())
            current_ledger['dependencies_sha256'][exterior_source]=(
                earlier_ledger['dependencies_sha256'][exterior_source])
            self.assertEqual(current_ledger,earlier_ledger,key)
        current={record['id']:record for record in self.town['entities']}
        for previous in self.before['entities']:
            self.assertEqual(current[previous['id']],previous,previous['id'])
        report=self.town['settlement_commons']
        for entity in report['entities']:self.assertEqual(current[entity['id']],entity)
        ids=[record['id'] for record in self.town['entities']]
        self.assertEqual(len(ids),len(set(ids)))
        for key in ('doors','overworld_exit','world_links','interaction_cues','well_art'):
            self.assertEqual(self.town.get(key),self.before.get(key),key)

    def test_well_contacts_gathering_and_school_owners_remain_protected(self):
        from tools.eldenmere_settlement import resolve_protections,validate_district_reports
        protections=resolve_protections(ROOT,self.town,self.recipe)
        names={record['id'] for record in protections}
        for name in ('entity.well','entity.school.bench','well_gathering','door.school',
                     'lantern_school_approach','lantern_school_workshop_route','liam_daisy_outdoor_play'):
            self.assertIn(name,names)
        well_contacts=[record for record in protections if record['id'].startswith('well_approaches.')]
        self.assertTrue(well_contacts)
        base=[p for p in self.recipe['placements'] if p['district']!='commons_households']
        for contact in well_contacts:
            x,y=contact['geometry'];blocked=placement(position=[x-12,y-12])
            with self.subTest(contact=contact['id']),self.assertRaises(ValueError):
                resolve_commons(ROOT,self.town,{**self.recipe,'placements':base+[blocked]},catalogue(),protections)
        report=resolve_commons(ROOT,self.town,self.recipe,catalogue(),protections)
        self.assertEqual(report,self.town['settlement_commons'])
        validate_district_reports(self.town['settlement_dressing'],self.town['settlement_workyards'],report)

    def test_collision_is_original_source_plus_all_declared_ledgers_and_navigation_is_identical(self):
        with Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/collision.png') as image:expected=image.convert('L')
        draw=ImageDraw.Draw(expected)
        for key in ('settlement_dressing','settlement_workyards','settlement_commons','settlement_households'):
            for support in self.town[key]['solid_footprints']:
                x,y,w,h=support['rect'];self.assertTrue(all(type(v) is int for v in (x,y,w,h)))
                draw.rectangle((x,y,x+w-1,y+h-1),fill=255)
        with Image.open(ROOT/self.town['collision']) as image:
            self.assertIsNone(ImageChops.difference(expected,image.convert('L').crop((0,0,*expected.size))).getbbox())
        expected_nav=before_observations()['production']['active_files'][self.before['navigation_allowed']]['sha256']
        self.assertEqual(sha256((ROOT/self.town['navigation_allowed']).read_bytes()).hexdigest(),expected_nav)
        # Also compare the complete retained original navigation geometry.
        with Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/navigation_allowed.png') as image:source=image.convert('L')
        with Image.open(ROOT/self.town['navigation_allowed']) as image:
            self.assertEqual(source.tobytes(),image.convert('L').crop((0,0,*source.size)).tobytes())

    def test_civic_stone_and_cartography_share_scoped_source_geometry(self):
        from tools.eldenmere_settlement_streets import resolve_streets
        resolved={p['id']:p for p in resolve_streets(ROOT,self.town,self.recipe)}
        civic=[p for p in self.recipe['ground_treatments'] if p['id'].startswith('settlement.street.commons.')]
        self.assertTrue(civic)
        sx,sy,sw,sh=self.recipe['commons_dressing']['scope_rect']
        network={record['id']:record for record in self.town['cartography']['street_network']}
        for treatment in civic:
            self.assertEqual(treatment['material'],'stone');self.assertIn('source_ref',treatment)
            record=resolved[treatment['id']]
            self.assertTrue(record['id'] in network,record['id']+' is missing from compiled civic cartography')
            if record['shape']=='rect':
                x,y,w,h=record['rect'];self.assertTrue(sx<=x and sy<=y and x+w<=sx+sw and y+h<=sy+sh)
                self.assertEqual(network[record['id']]['rect'],record['rect'])
            else:
                half=record['width']/2
                self.assertTrue(all(sx<=x-half and sy<=y-half and x+half<=sx+sw and y+half<=sy+sh for x,y in record['points']))
                self.assertEqual(network[record['id']]['points'],record['points'])
                self.assertEqual(network[record['id']]['width'],record['width'])

    def test_compiled_ground_has_native_paving_under_the_still_solid_well(self):
        layout=read(ROOT/self.town['layout_source']);x,y,w,h=layout['well_ground_rect']
        chunks=[]
        for record in self.town['ground_overlays']:
            px,py=record['position'];pw,ph=record['logical_size']
            if px<=x and py<=y and x+w<=px+pw and y+h<=py+ph:chunks.append(record)
        self.assertEqual(len(chunks),1)
        bank_path=ROOT/'assets/terrain/eldenmere/stone_paving_hd/tileset.json'
        full=next(record for record in read(bank_path)['tiles'] if record['mask']==255)
        expected=Image.new('RGBA',(w*2,h*2))
        for tx in range(x//24,(x+w)//24):
            for ty in range(y//24,(y+h)//24):
                phase=tx%2+2*(ty%2)
                with Image.open(bank_path.parent/full['body_files'][phase]) as tile:
                    expected.alpha_composite(tile.convert('RGBA'),((tx*24-x)*2,(ty*24-y)*2))
        chunk=chunks[0];px,py=chunk['position']
        crop=((x-px)*2,(y-py)*2,(x+w-px)*2,(y+h-py)*2)
        for frame in chunk['frames']:
            with self.subTest(frame=frame),Image.open(ROOT/frame) as image:
                self.assertEqual(image.convert('RGBA').crop(crop).tobytes(),expected.tobytes())
        with Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/collision.png') as image:
            before=image.convert('L').crop((x,y,x+w,y+h))
        with Image.open(ROOT/self.town['collision']) as image:
            self.assertEqual(image.convert('L').crop((x,y,x+w,y+h)).tobytes(),before.tobytes())
        self.assertIsNotNone(before.getbbox())


class CommonsSaveCompatibility(unittest.TestCase):
    def test_old_save_on_new_civic_support_loads_clear_without_lost_progress_or_duplicates(self):
        import pygame
        from main import Game
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);path=folder/'journey.json';settings=folder/'settings.json'
            game=Game(fullscreen=False,start_on_title=True,save_path=path,settings_path=settings);restored=None
            try:
                game.audio.set_music(0);game.audio.set_effects(0);game.on_title=False
                game.opening.restore({'version':1,'stage':'disabled'});game.opening_fade=game.transfer_cooldown=0
                game.world=game.town;game.player.position.update(528,900)
                self.assertTrue(game.town.can_stand(game.player.position));self.assertTrue(game.save_progress(),game.save_error)
                saved=read(path);support=game.town.data['settlement_commons']['solid_footprints'][0]
                x,y,w,h=support['rect'];occupied=[x+w/2,y+h/2]
                with Image.open(ROOT/'assets/source/maps/eldenmere/town_hd/collision.png') as image:prior=image.convert('L')
                prior_draw=ImageDraw.Draw(prior)
                for key in ('settlement_dressing','settlement_workyards'):
                    for old_support in before_town()[key]['solid_footprints']:
                        px,py,pw,ph=old_support['rect'];prior_draw.rectangle((px,py,px+pw-1,py+ph-1),fill=255)
                probe=game.town.probe_rect(occupied)
                self.assertIsNone(prior.crop((*probe.topleft,*probe.bottomright)).getbbox())
                self.assertFalse(game.town.can_stand(occupied))
                saved['player']['position']=occupied;saved['exterior_position']=occupied.copy()
                self.assertTrue(game.save_store.write(saved),game.save_store.error)
                progress={key:copy.deepcopy(saved[key]) for key in ('quests','party','inventory')}
                restored=Game(fullscreen=False,start_on_title=True,save_path=path,settings_path=settings)
                restored.audio.set_music(0);restored.audio.set_effects(0)
                self.assertTrue(restored.begin_journey(True),restored.save_error)
                self.assertIs(restored.world,restored.town);self.assertNotEqual(list(restored.player.position),occupied)
                self.assertTrue(restored.world.can_stand(restored.player.position))
                for key,value in progress.items():self.assertEqual(getattr(restored,key).to_dict(),value)
                ids=[e['id'] for e in restored.town.data['entities'] if e['id'].startswith('settlement.commons.')]
                self.assertEqual(len(ids),len(set(ids)))
                self.assertEqual(set(ids),{e['id'] for e in restored.town.data['settlement_commons']['entities']})
            finally:
                game.music.stop()
                if restored is not None:restored.music.stop()
                pygame.quit()

