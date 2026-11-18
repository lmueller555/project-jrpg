"""Full-town migration protects old gameplay and exercises the southern expansion."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageChops
import pygame
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'assets/source/maps/eldenmere/town_hd'
def read(path):return json.loads(Path(path).read_text())

class TownHDContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=read(SRC/'baseline_maps.json');cls.town=read(ROOT/'assets/maps/eldenmere/playable/map.json');cls.manifest=read(ROOT/'assets/maps/eldenmere/town_hd/manifest.json')
    def test_live_building_windows_stay_steady_through_full_ambient_cycles(self):
        from tools import build_eldenmere_exteriors_hd as exterior
        from tools.build_world_water_hd import load
        rec=exterior.recipe()
        sources={r['file']:load(exterior.SOURCE/r['file']) for r in rec['sources']}
        packs=('assets/terrain/eldenmere/exteriors_hd/', 'assets/terrain/eldenmere/business_exteriors_hd/')
        masks={}
        for pack in packs:
            for r in read(ROOT/pack/'manifest.json')['buildings']:
                masks[r['id']]=Image.open(ROOT/pack/r['window_mask']).convert('L')
                if r.get('display'):
                    x,y,w,h=[v*2 for v in r['display']['rect_logical']]
                    masks[r['id']].paste(255,(x,y,x+w,y+h))
        sanctuary=next(r for r in rec['designs'] if r['id']=='sanctuary')
        sources['landmarks_authored.png']=load(ROOT/'assets/source/maps/eldenmere/courtyard_hd/structure_authored.png')
        _,masks['sanctuary']=exterior.building_structure(sanctuary,sources,rec)
        bindings=read(ROOT/packs[0]/'manifest.json')['bindings']
        designs={r['entity']:r['new_design'] for r in bindings}
        # Live business bindings come from the retained town recipe.
        for r in read(SRC/'recipe.json')['businesses']:
            designs[r['id']]=r['design']
        checked=0
        for e in self.town['entities']:
            if e['id'] not in designs:continue
            mask=masks[designs[e['id']]]
            self.assertIsNotNone(mask.getbbox(),e['id'])
            with Image.open(ROOT/e['frames'][0]) as raw:first=raw.convert('RGBA')
            phases=set()
            for path in e['frames']:
                with Image.open(ROOT/path) as raw:frame=raw.convert('RGBA')
                delta=ImageChops.difference(first,frame).convert('RGB')
                self.assertIsNone(ImageChops.multiply(delta,mask.convert('RGB')).getbbox(),(e['id'],path))
                phases.add(frame.tobytes())
            if e['id']=='sanctuary':self.assertGreater(len(phases),1,'Smoke and bell must still animate')
            checked+=1
        self.assertEqual(checked,13)

    def test_expansion_preserves_source_collision_plus_declared_district_supports(self):
        self.assertEqual(self.town['size_pixels'],[1536,1632]);self.assertEqual(self.town['size_tiles'],[64,68])
        after=Image.open(ROOT/self.town['collision']).convert('L')
        from tools.build_eldenmere_hd import source_town_physics, courtyard_collision, workyard_collision, commons_collision, household_collision, growing_collision, arrival_collision
        expected,expected_nav=source_town_physics(read(SRC/'recipe.json'))
        expected=courtyard_collision(expected,self.town.get('settlement_dressing'))
        expected=workyard_collision(expected,self.town.get('settlement_workyards'))
        expected=commons_collision(expected,self.town.get('settlement_commons'))
        expected=household_collision(expected,self.town.get('settlement_households'))
        expected=growing_collision(expected,self.town.get('settlement_growing'))
        expected=arrival_collision(expected,self.town.get('settlement_arrival'))
        self.assertEqual(expected.size,after.size);self.assertEqual(expected.tobytes(),after.tobytes())
        nav=Image.open(ROOT/self.town['navigation_allowed']).convert('L');oldnav=Image.open(SRC/'navigation_allowed.png').convert('L')
        self.assertEqual(expected_nav.tobytes(),nav.tobytes())
        self.assertEqual(nav.crop((0,0,*oldnav.size)).tobytes(),oldnav.tobytes())
    def test_existing_quest_routes_entrances_and_npc_records_are_preserved(self):
        old=self.old['town'];data=self.town
        for key in ('spawn','player_probe_size','player_draw_anchor','npcs','persistent_npcs','quests','world_links','exterior_scenes'):self.assertEqual(data[key],old[key],key)
        for key in ('destinations','interior_scenes'):
            retained={k:v for k,v in old[key].items() if key!='destinations' or k!='southern_exit'}
            self.assertEqual({k:data[key][k] for k in retained},retained)
        self.assertEqual(data['destinations']['southern_exit'],data['overworld_exit']['position'])
        for d,previous in zip(data['doors'],old['doors']):
            for key,value in previous.items():
                if key not in ('frames','artwork_pixels_per_world_pixel','logical_size'):self.assertEqual(d[key],value,(d['id'],key))
        current={e['id']:e for e in data['entities']}
        for e in old['entities']:
            for key in ('position','sort_y','phase_offset'):self.assertEqual(current[e['id']][key],e[key],(e['id'],key))
    def test_every_original_entity_keeps_its_physical_canvas(self):
        for name,previous in self.old.items():
            path=self.manifest['scenes'][name];data=read(ROOT/path);current={e['id']:e for e in data['entities']}
            for e in previous['entities']:
                oldsize=tuple(e.get('logical_size') or Image.open(ROOT/e['frames'][0]).size);new=current[e['id']]
                with self.subTest(scene=name,entity=e['id']):
                    self.assertEqual(tuple(new['logical_size']),oldsize);self.assertEqual(new['artwork_pixels_per_world_pixel'],2)
                    self.assertEqual(Image.open(ROOT/new['frames'][0]).size,tuple(v*2 for v in oldsize))
    def test_existing_rooms_and_upstream_keep_collision_and_transition_contracts(self):
        for name,previous in self.old.items():
            if name=='town':continue
            data=read(ROOT/self.manifest['scenes'][name])
            if name=='mill':
                additions=read(SRC/'interior_architecture/recipe.json')['collision_additions']['mill']
                from PIL import ImageDraw
                expected=Image.open(ROOT/previous['collision']).convert('L')
                draw=ImageDraw.Draw(expected)
                for item in additions:
                    x,y,w,h=item['rect'];draw.rectangle((x,y,x+w-1,y+h-1),fill=255)
                self.assertEqual(Image.open(ROOT/data['collision']).convert('L').tobytes(),expected.tobytes())
                self.assertEqual(data['architecture_occupancy'],additions)
            else:self.assertEqual(data['collision'],previous['collision'])
            for key in ('size_pixels','spawn','player_probe_size','player_draw_anchor','quests'):
                if key in previous:self.assertEqual(data[key],previous[key],(name,key))
            for current,old in zip(data.get('doors',[]),previous.get('doors',[])):
                for key,value in old.items():
                    if key not in ('frames','logical_size','artwork_pixels_per_world_pixel'):self.assertEqual(current[key],value,(name,key))
    def test_grass_instance_identity_and_interaction_registration_survive(self):
        for name in ('town','upstream'):
            data=read(ROOT/self.manifest['scenes'][name]);before=self.old[name]['grass'];after=data['grass']
            retired=set(data.get('settlement_dressing',{}).get('retired_grass_ids',[]))
            self.assertEqual([{k:v for k,v in r.items() if k!='variant'} for r in before['instances'] if r['id'] not in retired], [{k:v for k,v in r.items() if k!='variant'} for r in after['instances']])
            self.assertTrue(all(r['variant'].endswith('_hd') for r in after['instances']))
            pack=read(ROOT/after['manifest'])['tall_grass'];self.assertEqual(pack['anchor'],[12,28]);self.assertEqual(pack['frame_size'],[24,32]);self.assertEqual(pack['contact_rect'],[-10,-8,20,12])
    def test_chunks_cover_each_scene_once_and_keep_artwork_native(self):
        for name in ('town','upstream'):
            data=read(ROOT/self.manifest['scenes'][name]);coverage=Image.new('L',tuple(data['size_pixels']))
            for r in data['ground_overlays']:
                x,y=r['position'];w,h=r['logical_size'];self.assertIsNone(coverage.crop((x,y,x+w,y+h)).getbbox());coverage.paste(255,(x,y,x+w,y+h))
                self.assertLessEqual(w,192);self.assertLessEqual(h,192);self.assertIn(len(r['frames']),(1,6))
                self.assertEqual(Image.open(ROOT/r['image']).size,(w*2,h*2))
            self.assertEqual(coverage.getextrema(),(255,255))
    def test_source_and_export_hashes_are_reproducible(self):
        recipe=read(SRC/'recipe.json')
        for r in recipe['sources']:self.assertEqual(sha256((SRC/r['file']).read_bytes()).hexdigest(),r['sha256'])
        for r in self.manifest['exports']:self.assertEqual(sha256((ROOT/r['file']).read_bytes()).hexdigest(),r['sha256'],r['file'])
    def test_businesses_are_new_destinations_with_clear_thresholds(self):
        self.assertEqual(len(self.town['doors']),13);self.assertEqual(len(self.town['interior_scenes']),18)
        for name in ('inn','item_shop'):
            door=next(d for d in self.town['doors'] if d['id']==name);self.assertGreater(door['anchor'][1],1344)
            room=read(ROOT/door['destination']);self.assertEqual(room['id'],name);self.assertTrue(room['entities']);self.assertTrue(room['npcs'])
            self.assertEqual(room['doors'][0]['arrival_door'],name)

class TownHDGameplay(unittest.TestCase):
    def setUp(self):
        from main import Game
        self.temp=tempfile.TemporaryDirectory();p=Path(self.temp.name)
        self.g=Game(fullscreen=False,start_on_title=True,save_path=p/'save.json',settings_path=p/'settings.json')
        g=self.g;g.on_title=False;g.opening.restore({'version':1,'stage':'disabled'});g.opening_fade=0;g.transfer_cooldown=0;g.world=g.town
    def tearDown(self):self.g.music.stop();pygame.quit();self.temp.cleanup()
    def enter(self,door):
        g=self.g;old=g.world;direction=-1 if door.data['entry_side']=='north' else 1
        g.transfer_cooldown=0;g.player.position.update(pygame.Vector2(door.data['anchor'])+(0,-direction*12));g.update(.5,(0,0),False)
        for _ in range(90):
            g.update(1/60,(0,direction),False)
            if g.world is not old:return
        self.fail('Door failed to transfer '+door.data['id'])
    def test_both_new_buildings_have_safe_actual_round_trips(self):
        g=self.g;inventory=g.inventory.to_dict()
        for name in ('inn','item_shop'):
            g.world=g.town;self.enter(next(d for d in g.town.doors if d.data['id']==name));self.assertEqual(g.world.data['id'],name);self.assertTrue(g.world.can_stand(g.player.position))
            self.enter(g.world.doors[0]);self.assertIs(g.world,g.town);self.assertTrue(g.world.can_stand(g.player.position));self.assertEqual(g.player.facing,'front')
        self.assertEqual(g.inventory.to_dict(),inventory)
    def test_southern_lane_connects_to_existing_town_and_both_approaches(self):
        g=self.g
        for x,y0,y1 in [(528,1104,1488)]:
            for y in range(y0,y1+1,2):self.assertTrue(g.world.can_stand((x,y)),(x,y))
        for x in range(288,708,2):self.assertTrue(g.world.can_stand((x,1488)),x)
        for name in ('inn','item_shop'):
            door=next(d for d in g.world.doors if d.data['id']==name);x,y=door.data['anchor']
            for yy in range(round(y),1489,2):self.assertTrue(g.world.can_stand((x,yy)),(name,x,yy))
    def test_native_ground_animation_and_reduced_motion_share_controller_sampling(self):
        g=self.g;rect=pygame.Rect(816,912,72,72)
        def sample(t):return pygame.image.tobytes(g.town.ground_region(rect,t).native,'RGBA')
        self.assertNotEqual(sample(0),sample(400));g.town.update_grass(0,reduced_motion=True);self.assertEqual(sample(0),sample(400))
        before=[sha256(pygame.image.tobytes(r['surfaces'][0].native,'RGBA')).hexdigest() for r in g.town.ground_overlays]
        g.venn_visit.repaired=True;g.venn_visit.flow_seconds=20;g.venn_visit._update_art(force=True)
        self.assertEqual(before,[sha256(pygame.image.tobytes(r['surfaces'][0].native,'RGBA')).hexdigest() for r in g.town.ground_overlays])
    def test_inn_rest_uses_confirmed_recovery_and_cancel_leaves_resources_alone(self):
        g=self.g;g.world=g._scene_by_id('inn');g.player.position.update(96,150);g.attributes.set_current(hp=1,mp=0)
        self.assertTrue(g.bed_rest.nearby());self.assertTrue(g.bed_rest.interact());self.assertEqual(g.attributes.current_hp,1)
        profile=g.bed_rest._profile();g.social.cancel_script();g.bed_rest._choose('leave',profile);self.assertEqual(g.attributes.current_hp,1)
        g.bed_rest._choose('rest',profile);self.assertEqual(g.attributes.current_hp,g.attributes.value('hp'));self.assertEqual(g.attributes.current_mp,g.attributes.value('mp'))
    def test_checkpoint_reloads_inside_the_new_inn(self):
        from main import Game
        g=self.g;g.world=g._scene_by_id('inn');g.player.position.update(96,150)
        self.assertTrue(g.save_progress(),g.save_error)
        other=Game(fullscreen=False,start_on_title=True,save_path=Path(self.temp.name)/'save.json',settings_path=Path(self.temp.name)/'settings.json')
        try:
            self.assertTrue(other.has_saved_journey,other.save_error)
            self.assertTrue(other.begin_journey(True),other.save_error)
            self.assertEqual(other.world.data['id'],'inn');self.assertEqual(tuple(other.player.position),(96,150))
        finally:other.music.stop()

    def test_mill_wheel_uses_separate_clock_and_shared_story_stop(self):
        g=self.g;wheel=next(e for e in g.town.entities if e['id']=='mill.wheel');self.assertEqual(len(wheel['surfaces']),48);self.assertEqual(wheel['frame_duration_ms'],200)
        g.opening_conclusion._stop_mill();host=next(e for e in g.town.entities if e['id']=='mill');self.assertEqual(wheel['animation_stopped'],host['animation_stopped'])
    def test_stateful_native_objects_keep_distinct_consumed_states(self):
        g=self.g;home=g._scene_by_id('liam_house')
        for identifier,states in [('liam_block_box',('0','5')),('daisy_food_bowl',('full','empty')),('daisy_water_bowl',('full','half_full'))]:
            pixels=[]
            for state in states:
                self.assertTrue(home.set_entity_state(identifier,state));e=next(e for e in home.entities if e['id']==identifier);pixels.append(sha256(pygame.image.tobytes(e['surfaces'][0].native,'RGBA')).hexdigest())
            self.assertNotEqual(*pixels,identifier)
    def test_ground_textures_load_on_demand_with_a_bounded_cache(self):
        g=self.g;self.assertEqual(g.town._ground_cache.bytes,0)
        g.town.ground_region((120,72,480,320),0)
        self.assertGreater(g.town._ground_cache.bytes,0)
        for r in g.town.ground_overlays:
            r['surfaces'][0]
        self.assertLessEqual(g.town._ground_cache.bytes,g.town._ground_cache.budget)
        self.assertFalse(any(key[0].startswith('assets/maps/eldenmere/town_hd/town/chunks') for key in g.town._images))

    def test_focus_pause_freezes_the_expanded_town(self):
        g=self.g;g.player.position.update(528,1488);before=(g.elapsed_ms,tuple(g.player.position));g._music_focused=False;g.update(.5,(1,0),True);self.assertEqual((g.elapsed_ms,tuple(g.player.position)),before)

if __name__=='__main__':unittest.main()
