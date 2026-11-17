"""Purposeful room art, exact new occupancy, real stairs and legacy restoration."""
from copy import deepcopy
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

from PIL import Image, ImageChops
import pygame

from tools.eldenmere_interior_architecture import (
    ROOT, recipe, apply_interior_architecture, _drivetrain)
from tools.build_eldenmere_hd import Export, fit


def read(path):return json.loads((ROOT/path).read_text())


def fixture():
    town=read('assets/maps/eldenmere/playable/map.json')
    paths={'town':'assets/maps/eldenmere/playable/map.json',
           **{k:v for k,v in town['interior_scenes'].items() if k in recipe()['rooms']}}
    maps={k:read(v) for k,v in paths.items()}
    # This is the same native furnishing bank supplied by the live composer.
    bank={r['id']:r for r in read('assets/terrain/eldenmere/sanctuary_dining_hd/manifest.json')['props']
          +read('assets/terrain/eldenmere/sanctuary_home_hd/manifest.json')['props']}
    def furnishing(name,size):
        # The live builder has a dedicated bedside-table specialist. For pure
        # geometry/registration tests a retained household table is equivalent.
        actual='chest' if name=='bedside_table' else name
        im=Image.open(ROOT/bank[actual]['image']).convert('RGBA')
        return im if im.size==tuple(v*2 for v in size) else fit(im,size)
    return maps,paths,Export(),furnishing


def original_collision(name, data):
    """Retained geometry, not a newly generated mask used as its own baseline."""
    baseline=read('assets/source/maps/eldenmere/town_hd/baseline_maps.json')
    if name!='inn':return Image.open(ROOT/baseline.get(name,data)['collision']).convert('L')
    from PIL import ImageDraw
    old=Image.new('L',(432,336),255);draw=ImageDraw.Draw(old)
    draw.rectangle((24,72,407,311),fill=0)
    draw.rectangle((204,276,227,335),fill=0)
    for e in data['entities']:
        if e['id'] in ('inn.hearth','inn.stairs'):continue
        x,y=e['position'];w,h=e['logical_size']
        draw.rectangle((x+3,y+h//2,x+w-4,y+h-1),fill=255)
    return old


class InteriorRecipeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.maps,cls.paths,cls.ex,cls.furnishing=fixture()
        cls.before=deepcopy(cls.maps)
        cls.review=apply_interior_architecture(cls.maps,cls.paths,cls.ex,cls.furnishing)

    def test_all_buildings_and_three_serene_rooms_are_explicitly_reviewed(self):
        rec=recipe();schedule=read(rec['architecture_schedule'])
        scenes={name for b in schedule['buildings'] for name in b['interior_scenes']} - {'inn_guest_floor'}
        self.assertEqual(set(rec['rooms']),scenes)
        self.assertEqual(len(rec['rooms']),15)
        self.assertEqual(set(self.review['rooms']),scenes|{'inn_guest_floor'})
        self.assertEqual(self.review['new_scenes'],['inn_guest_floor'])

    def test_original_fixture_positions_ids_state_images_npcs_and_routes_survive(self):
        for name,before in self.before.items():
            if name=='town':continue
            after=self.maps[name]
            current={e['id']:e for e in after['entities']}
            for e in before['entities']:
                with self.subTest(room=name,entity=e['id']):
                    self.assertIn(e['id'],current)
                    for field in ('position','sort_y','sort_priority','state_images'):
                        if field in e:self.assertEqual(current[e['id']].get(field),e[field])
            for field in ('id','spawn','npcs','quests','destinations','interaction_cues',
                          'world_map_display','rest_profile'):
                self.assertEqual(after.get(field),before.get(field),(name,field))
            # Existing exterior/household portals retain every behavioral field.
            for old in before['doors']:
                actual=next(d for d in after['doors'] if d['id']==old['id'])
                self.assertEqual(actual,old,(name,old['id']))

    def test_south_exits_cut_the_wall_and_extend_floor_through_every_retained_room(self):
        for name in recipe()['rooms']:
            data=self.maps[name];ground=self.ex.load(data['ground_frames'][0])
            for door in data['doors']:
                if door['entry_side']!='south' or door['frames']:continue
                x=int(door['anchor'][0])*2;y=(door['entry_y']+7)*2
                with self.subTest(room=name,door=door['id']):
                    # Threshold and paired returns replace the old continuous
                    # horizontal base rail, and open floor continues beyond it.
                    self.assertNotEqual(ground.getpixel((x,y)),ground.getpixel((x-34,y)))
                    self.assertNotEqual(ground.getpixel((x,y+13)),ground.getpixel((x-34,y+13)))
                    self.assertFalse(door['requires_open'])
                    self.assertEqual(door['frames'],[])

    def test_south_exit_sill_marks_sensor_and_landing_matches_destination_family(self):
        samples={}
        palette=recipe()['palette']
        sill=tuple(bytes.fromhex(palette['stone'][1:]))
        cap=tuple(bytes.fromhex(palette['oak_light'][1:]))
        for name in recipe()['rooms']:
            data=self.maps[name]
            door=next(d for d in data['doors'] if d['entry_side']=='south')
            ground=self.ex.load(data['ground_frames'][0]).convert('RGB')
            x,y=map(int,door['anchor'])
            at=lambda dx,dy:ground.getpixel(((x+dx)*2,(y+dy)*2))
            with self.subTest(room=name):
                self.assertEqual(at(0,2),sill)
                self.assertNotEqual(at(0,-8),sill)
                self.assertEqual(at(-15,-7),cap)
                self.assertEqual(at(15,-7),cap)
                self.assertEqual(at(0,22),(36,48,45))
                samples[name]=ground.crop(((x-10)*2,(y+6)*2,(x+10)*2,(y+14)*2)).tobytes()
        self.assertEqual(len({samples[n] for n in ('liam_house','school','sanctuary_bedroom')}),3)

    def test_all_new_art_uses_native_density_and_hard_alpha(self):
        for path,raw in self.ex.out.items():
            if not path.endswith('.png'):continue
            im=Image.open(BytesIO(raw)).convert('RGBA')
            self.assertLessEqual(set(im.getchannel('A').tobytes()),{0,255},path)
        for name,data in self.maps.items():
            if name=='town':continue
            self.assertEqual(self.ex.load(data['ground_frames'][0]).size,
                             tuple(v*2 for v in data['size_pixels']))
            for e in data['entities']:
                if e['frames'][0] not in self.ex.out:continue
                self.assertEqual(self.ex.load(e['frames'][0]).size,
                                 tuple(v*2 for v in e['logical_size']),(name,e['id']))

    def test_collision_changes_are_exactly_the_named_minimal_additions(self):
        additions=recipe()['collision_additions']
        for name,before in self.before.items():
            if name=='town':continue
            after=self.maps[name]
            old=original_collision(name,before)
            actual=self.ex.load(after['collision']).convert('L')
            expected=old.copy()
            from PIL import ImageDraw
            d=ImageDraw.Draw(expected)
            for r in additions.get(name,[]):
                x,y,w,h=r['rect'];d.rectangle((x,y,x+w-1,y+h-1),fill=255)
            self.assertEqual(actual.tobytes(),expected.tobytes(),name)
            if name in additions:
                self.assertEqual(after['architecture_occupancy'],additions[name])
            else:self.assertEqual(after['collision'],before['collision'])

    def test_stair_reserves_landings_and_original_fixture_access_are_clear(self):
        from PIL import ImageDraw
        for name in ('inn','inn_guest_floor'):
            collision=self.ex.load(self.maps[name]['collision']).convert('L')
            landing=collision.crop((336,288,396,312))
            self.assertIsNone(landing.getbbox(),name)
            self.assertFalse(collision.getpixel((366,282)),name)
            self.assertFalse(collision.getpixel((366,300)),name)
        inn=self.maps['inn']
        for identifier,position in (('guest_bed',[36,96]),('guest_bed_east',[342,96]),
                                    ('table',[264,216]),('counter',[144,102])):
            self.assertEqual(next(e for e in inn['entities'] if e['id']==identifier)['position'],position)
        self.assertEqual(inn['npcs'][0]['position'],[168,122])
        self.assertEqual(next(e for e in inn['entities'] if e['id']=='inn.hearth')['position'],[350,24])

    def test_guest_floor_is_one_registered_scene_with_four_bays_and_no_extra_service(self):
        upper=self.maps['inn_guest_floor'];stairs=recipe()['stairs']
        self.assertEqual(self.maps['town']['interior_scenes']['inn_guest_floor'],self.paths['inn_guest_floor'])
        self.assertEqual(len([e for e in upper['entities'] if e['id'].startswith('guest_bed_')]),4)
        self.assertNotIn('rest_profile',upper)
        self.assertEqual(upper['npcs'],[]);self.assertEqual(upper['quests'],[])
        self.assertEqual(upper['interaction_cues'],[])
        lower=next(d for d in self.maps['inn']['doors'] if d['id']=='guest_stairs')
        back=upper['doors'][0]
        self.assertEqual(lower['destination'],self.paths['inn_guest_floor'])
        self.assertEqual(back['destination'],self.paths['inn'])
        self.assertEqual(lower['arrival_door'],back['id'])
        self.assertEqual(back['arrival_door'],lower['id'])
        for d in (lower,back):
            self.assertEqual(d['spawn'],[366,300])
            self.assertEqual(d['anchor'],[366,282])
            self.assertEqual(d['arrival_facing'],'front')
            self.assertEqual(d['rearm_after_exit'],stairs['rearm_after_exit'])

    def test_mill_processing_explains_the_east_wheel_and_solid_supports_do_not_move(self):
        rec=recipe();machine=rec['mill_processing'];frames=[_drivetrain(rec['palette'],i) for i in range(12)]
        self.assertEqual(machine['wheel_entry_world'],[408,128])
        self.assertEqual(machine['animation_driver'],'mill_wheel')
        self.assertGreater(len({im.tobytes() for im in frames}),4)
        self.assertEqual(frames[0].tobytes(),_drivetrain(rec['palette'],12).tobytes())
        # East wall bearing and trestle foot are not rotating image components.
        for box in ((228,30,252,74),(194,86,228,100)):
            self.assertEqual(len({im.crop(box).tobytes() for im in frames}),1)
        self.assertTrue(all(im.getpixel((242,48))[3] for im in frames))
        data=self.maps['mill'];fixture=next(e for e in data['entities'] if e['id']=='sorting_table')
        self.assertEqual(fixture['position'],[264,180])
        self.assertEqual(next(e for e in data['entities'] if e['id']=='hearth')['position'],[326,24])

    def test_household_storage_and_bedding_are_differentiated_without_touching_owned_props(self):
        colors=[]
        for name in ('home_a','home_b','home_c','halden','venn','liam_house'):
            data=self.maps[name]
            bed=next(e for e in data['entities'] if e['id'] in ('bed','parents_bed'))
            colors.append(self.ex.load(bed['frames'][0]).tobytes())
        self.assertEqual(len(set(colors)),len(colors))
        for name,ids in {'elira':['lantern_shelf','step_stool'],
                         'liam_house':['liam_block_box','daisy_food_bowl','daisy_water_bowl','daisy_rug'],
                         'school':['writing_board','village_map','teacher_desk','pupil_desk_1']}.items():
            for identifier in ids:
                old=next(e for e in self.before[name]['entities'] if e['id']==identifier)
                actual=next(e for e in self.maps[name]['entities'] if e['id']==identifier)
                self.assertEqual(actual,old,(name,identifier))

    def test_owned_lantern_phase_art_is_not_replaced_with_generic_paper_stock(self):
        art=read('assets/story/lantern/art.json')
        surface=next(p for p in art['props'] if p['id']=='craft_surface')
        aliases=self.maps['town']['art_replacements']
        for state,legacy in surface['states'].items():
            actual=self.ex.load(aliases[legacy]['file'])
            expected=Image.open(ROOT/legacy).convert('RGBA').resize((128,112),Image.Resampling.NEAREST)
            self.assertEqual(actual.tobytes(),expected.tobytes(),state)
        empty_path=read('assets/story/lantern/rest_art.json')['workshop_collected']
        self.assertNotIn(empty_path,aliases,'Keep the upstream canonical empty contents surface')
        self.assertIsNone(Image.open(ROOT/empty_path).convert('RGBA').getbbox())
        table=next(p for p in art['props'] if p['id']=='craft_table')
        actual=self.ex.load(aliases[table['states']['rest']]['file'])
        self.assertEqual(actual.size,(128,56))
        self.assertGreaterEqual(actual.getbbox()[2]-actual.getbbox()[0],120,
                                'The real support remains full-width, not a vanished/undersized table')
        self.assertTrue(all(p['id'] in ('craft_table','craft_surface','school_drawing') for p in art['props']))

    def test_schedule_validates_complete_in_memory_scenes_without_prior_guest_exports(self):
        from unittest.mock import patch
        from tools.eldenmere_architecture_contracts import validate_schedule
        schedule=read(recipe()['architecture_schedule'])
        with patch('pathlib.Path.read_text',side_effect=AssertionError('Prior generated room read')):
            self.assertTrue(validate_schedule(schedule,self.maps['town'],scene_records=self.maps))

    def test_source_extension_is_deterministic_for_identical_inputs(self):
        maps,paths,ex,furnishing=fixture()
        apply_interior_architecture(maps,paths,ex,furnishing)
        self.assertEqual(ex.out,self.ex.out)
        self.assertEqual(maps,self.maps)


class InteriorGameplayTests(unittest.TestCase):
    """No fake room/controller is used: movement, Game.enter, saves, Continue and
    actor ownership all run through the same application paths as live play.
    """
    def setUp(self):
        from main import Game
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.g=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
                    save_path=Path(self.temp.name)/'journey.json',
                    settings_path=Path(self.temp.name)/'settings.json')
        self.addCleanup(self.g.music.stop);self.addCleanup(pygame.quit)
        g=self.g;g.on_title=False;g.opening.stage='disabled'
        g.opening_fade=g.transfer_cooldown=0
        g.audio.set_music(0);g.audio.set_effects(0)
        self.assertIn('inn_guest_floor',g.town.data['interior_scenes'],
                      'Wire apply_interior_architecture into the live builder before gameplay tests')
        self.station('inn',(366,300))

    def station(self,scene,point):
        g=self.g;g.world=g._scene_by_id(scene);g.player.position.update(point)
        g.player.facing='back';g.opening_fade=g.transfer_cooldown=0
        self.assertTrue(g.world.can_stand(point),(scene,point))

    def walk(self,direction,frames=1,running=False):
        for _ in range(frames):self.g.update(1/60,direction,running)

    def stair(self):
        return next(d for d in self.g.world.doors if d.data.get('rearm_after_exit'))

    def test_walk_run_reciprocity_and_held_north_never_bounces(self):
        g=self.g
        for running in (False,True):
            self.station('inn',(366,300));self.stair().entry_armed=True
            self.walk((0,-1),30,running)
            self.assertEqual(g.world.data['id'],'inn_guest_floor')
            self.assertEqual(g.player.facing,'back' if g.player.moving else 'front')
            self.walk((0,-1),150,running)
            self.assertEqual(g.world.data['id'],'inn_guest_floor')
            # Leave the landing laterally and then deliberately re-approach.
            self.station('inn_guest_floor',(366,300));self.stair().disarm_on_arrival()
            self.walk((-1,0),35)
            self.assertTrue(self.stair().entry_armed)
            self.walk((1,0),35)
            self.walk((0,-1),20)
            self.assertEqual(g.world.data['id'],'inn')
            self.walk((0,-1),120)
            self.assertEqual(g.world.data['id'],'inn')

    def test_arrival_is_safe_facing_cooldown_and_disarmed_until_excursion(self):
        g=self.g;door=self.stair()
        self.assertTrue(g.enter(door))
        self.assertEqual(tuple(g.player.position),(366,300))
        self.assertEqual(g.player.facing,'front')
        self.assertEqual(g.transfer_cooldown,.25)
        self.assertFalse(self.stair().entry_armed)
        self.assertTrue(g.world.can_stand(g.player.position))
        self.assertFalse(self.stair().can_enter((366,282),(0,-1)))
        # A resident outside the stair reserve must not rearm the player's gate.
        self.stair().update(None,.1,((300,300),))
        self.assertFalse(self.stair().entry_armed)
        self.stair().update((320,300),.1)
        self.assertTrue(self.stair().entry_armed)
        self.assertTrue(self.stair().can_enter((366,282),(0,-1)))

    def test_continue_both_floors_keeps_state_and_requires_new_stair_excursion(self):
        g=self.g;g.inventory.add('potion',2);g.wallet.gold=29
        self.assertTrue(g.party.recruit('rhea'))
        for scene in ('inn','inn_guest_floor'):
            self.station(scene,(366,300))
            before=g.journey_snapshot();self.assertIsNotNone(g._validate_journey(deepcopy(before)))
            self.assertTrue(g.saves.eligible(manual=True))
            self.assertTrue(g.saves.manual(1))
            row=next(row for row in g.saves.entries() if row[2]==('manual',1))
            self.assertTrue(g.saves.load(row))
            self.assertEqual(g.world.data['id'],scene)
            self.assertFalse(self.stair().entry_armed)
            self.assertTrue(g.save_progress())
            from main import Game
            other=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
                save_path=Path(self.temp.name)/'journey.json',
                settings_path=Path(self.temp.name)/'settings.json')
            self.addCleanup(other.music.stop)
            other.audio.set_music(0);other.audio.set_effects(0);pygame.event.clear()
            self.assertTrue(other.has_saved_journey)
            self.assertTrue(other.begin_journey(True))
            g=self.g=other
            self.assertEqual(g.world.data['id'],scene)
            self.assertEqual(tuple(g.player.position),(366,300))
            self.assertFalse(self.stair().entry_armed)
            self.assertEqual(g.inventory.to_dict(),before['inventory'])
            self.assertEqual(g.party.to_dict(),before['party'])
            self.assertEqual(g.quests.to_dict(),before['quests'])
            self.assertEqual(g.wallet.gold,29)
            self.walk((0,-1),60)
            self.assertEqual(g.world.data['id'],scene)

    def test_old_downstairs_saves_at_each_new_occupancy_use_checked_fallback(self):
        g=self.g;g.inventory.add('ether',2);g.wallet.gold=17
        base=g.journey_snapshot()
        cases=(('inn',(337,270)),('inn',(394,250)),('inn',(366,80)),('mill',(310,148)))
        for scene,point in cases:
            world=g._scene_by_id(scene)
            old=original_collision(scene,world.data)
            x,y=point
            self.assertIsNone(old.crop((x-12,y-6,x+12,y+6)).getbbox(),(scene,point))
            saved=deepcopy(base);saved['player'].update(scene=scene,position=list(point),facing='left')
            self.assertIsNotNone(g._validate_journey(saved))
            g.saved_journey=saved;self.assertTrue(g.begin_journey(True))
            self.assertEqual(g.world.data['id'],scene)
            self.assertTrue(g.world.can_stand(g.player.position))
            self.assertEqual(tuple(g.player.position),tuple(world.data['spawn']))
            for field,actual in (('inventory',g.inventory.to_dict()),('quests',g.quests.to_dict()),
                                 ('party',g.party.to_dict())):
                self.assertEqual(actual,saved[field])
            self.assertEqual(g.wallet.gold,17)
        # A valid old standing spot is not moved merely because stairs exist.
        saved=deepcopy(base);saved['player'].update(scene='inn',position=[300,294])
        g.saved_journey=saved;self.assertTrue(g.begin_journey(True))
        self.assertEqual(tuple(g.player.position),(300,294))

    def test_companions_and_persistent_owners_are_not_duplicated_across_stairs(self):
        g=self.g;self.assertTrue(g.party.recruit('rhea'))
        original={id(actor):sum(actor in scene.npcs for scene in g.scenes.values())
                  for actor in g.persistent_npcs}
        self.assertTrue(g.enter(self.stair()))
        self.walk((-1,0),60)
        companions=g.party_travel.actors()
        self.assertTrue(companions)
        for actor in companions:
            self.assertTrue(g.world.can_stand(actor.position))
            self.assertFalse(any(actor in scene.npcs for scene in g.scenes.values()))
        for actor in g.persistent_npcs:
            self.assertEqual(sum(actor in scene.npcs for scene in g.scenes.values()),original[id(actor)])

    def test_story_mira_uses_the_same_reciprocal_stairs_and_restores_one_owner(self):
        from tests.test_mill_quest import MillQuestTests
        from main import Game
        flow=MillQuestTests(methodName='runTest')
        flow.g=self.g;flow.c=self.g.mill_quest;flow.temp=self.temp
        flow.path=Path(self.temp.name)/'journey.json'
        flow.handoff();flow.recruit()
        g=self.g;mira=g.mill_quest.mira
        self.assertTrue(g.enter(next(d for d in g.town.doors if d.data['id']=='inn')))
        def arrive(scene):
            for _ in range(1200):
                if g.mill_quest._mira_world.data['id']==scene:break
                g.update(.05,(0,0),False)
            self.assertEqual(g.mill_quest._mira_world.data['id'],scene)
            self.assertEqual(sum(g.mill_quest.mira in w.npcs for w in g.scenes.values()),1)
        arrive('inn')
        self.station('inn',(366,300));self.stair().entry_armed=True
        self.walk((0,-1),20);self.assertEqual(g.world.data['id'],'inn_guest_floor')
        arrive('inn_guest_floor');self.assertIs(g.mill_quest.mira,mira)
        self.assertFalse(self.stair().entry_armed,'NPC arrival must not rearm the player sensor')
        g.player.position.update(366,300);self.assertTrue(g.save_progress())
        other=Game(fullscreen=False,start_on_title=True,save_path=flow.path,
                   settings_path=Path(self.temp.name)/'settings.json')
        self.addCleanup(other.music.stop);self.assertTrue(other.begin_journey(True))
        g=self.g=other;self.assertEqual(g.world.data['id'],'inn_guest_floor')
        arrive('inn_guest_floor')
        self.assertEqual(sum(g.mill_quest.mira in w.npcs for w in g.scenes.values()),1)
        self.station('inn_guest_floor',(320,300));self.walk((0,0),40)
        self.walk((1,0),38);self.walk((0,-1),20)
        self.assertEqual(g.world.data['id'],'inn');arrive('inn')

    def test_mill_stop_before_load_loaded_update_and_continue_share_existing_flag(self):
        g=self.g;owner=g.opening_conclusion
        owner.stage='waiting'
        mill=g._scene_by_id('mill')
        machine=next(e for e in mill.entities if e.get('animation_driver')=='mill_wheel')
        self.assertTrue(machine['animation_stopped'])
        owner.stage='idle';owner._stop_mill();self.assertFalse(machine['animation_stopped'])
        owner.stage='waiting';owner._stop_mill();self.assertTrue(machine['animation_stopped'])
        # A real valid stopped-wheel checkpoint, not a new independent flag.
        from quests import OPENING_QUEST
        g.accept_quest(OPENING_QUEST)
        for objective in ('halden','elira','venn'):g.quests.complete_objective(OPENING_QUEST,objective)
        g.halden_visit.restore();g.elira_visit.restore();g.venn_visit.restore()
        self.station('mill',(252,294));saved=g.journey_snapshot()
        self.assertIsNotNone(g._validate_journey(deepcopy(saved)))
        g.saved_journey=saved;self.assertTrue(g.begin_journey(True))
        machine=next(e for e in g.world.entities if e.get('animation_driver')=='mill_wheel')
        self.assertTrue(machine['animation_stopped'])
        self.assertNotIn('mill_drivetrain',saved)

    def test_lantern_pickup_interruption_continue_and_home_rest_keep_exactly_one_frame(self):
        # Reuse the existing production-action harness: no stage/credit is
        # invented by this regression, and pickups/placement still use cues.
        from tests.test_lantern_rest import LanternRestTests
        from tools.capture_lantern_rest import seed_elira_checkpoint
        flow=LanternRestTests(methodName='runTest')
        flow.temp=self.temp;flow.path=Path(self.temp.name)/'journey.json'
        flow.g=self.g;flow.c=self.g.lantern_quest
        seed_elira_checkpoint(flow.g)
        def assert_owner(expected):
            c=flow.c;workshop=flow.frame_surface()
            home=next(p for p in c.rest.surface_props if p['id']=='home_frame')
            self.assertEqual(c.rest.frame_location,expected)
            self.assertEqual(c.rest.surface_prop_visible(home),expected=='home')
            if expected=='workshop':self.assertIs(workshop['surface'],workshop['states']['ready'])
            else:
                self.assertIs(workshop['surface'],c.rest.workshop_empty)
                self.assertEqual(c.rest.workshop_empty.get_bounding_rect().width,0)
                support=next(p for p in c.surface_props if p['id']=='craft_table')
                self.assertTrue(c.surface_prop_visible(support))
                self.assertGreater(support['surface'].get_bounding_rect().width,0)
                self.assertIsNot(workshop['surface'],workshop['states']['ready'])
            if expected=='held':self.assertTrue(hasattr(c.liam,'story_sprite'))
            # No duplicate source or NPC/prop is created to repair the surface.
            self.assertEqual(sum(p['id']=='craft_surface' for p in c.surface_props),1)
            self.assertEqual(sum(p['id']=='home_frame' for p in c.rest.surface_props),1)
        assert_owner('workshop')
        flow.leave_elira();flow.position('collection');flow.scene('collect_frame')
        self.assertEqual(flow.c.action,'rest_pickup');assert_owner('workshop')
        flow.reload();self.addCleanup(flow.g.music.stop)
        assert_owner('workshop')
        flow.scene('collect_frame')
        flow.until(lambda:flow.c.stage=='materials_collected')
        assert_owner('held')
        flow.reload();self.addCleanup(flow.g.music.stop);assert_owner('held')
        flow.position('home','liam_house');flow.scene('home_welcome')
        self.assertEqual(flow.c.action,'rest_place');assert_owner('held')
        flow.reload();self.addCleanup(flow.g.music.stop);assert_owner('held')
        flow.scene('home_welcome');flow.until(lambda:flow.c.stage=='materials_home')
        assert_owner('home')
        flow.scene('snack');self.assertEqual(flow.c.stage,'rested');assert_owner('home')
        flow.reload();self.addCleanup(flow.g.music.stop);assert_owner('home')
        self.assertEqual(flow.g.quests.objective_status('CH01_MQ04','finish_lantern'),'queued')
        self.g=flow.g

    def test_ground_rest_and_shop_service_contract_remain_identical(self):
        g=self.g;self.station('inn',(168,160))
        self.assertTrue(g.services.nearby('inn'))
        self.assertEqual(g.services.rest_profile()['entity'],'guest_bed')
        self.assertEqual(g.services.rest_profile()['price'],read('assets/services/eldenmere.json')['inn']['price'])
        self.station('inn',(60,181));self.assertTrue(g.bed_rest.nearby())
        self.station('inn_guest_floor',(66,181));self.assertFalse(g.bed_rest.nearby())
        self.station('item_shop',(216,188));self.assertTrue(g.services.nearby('shop'))
        self.assertEqual(g.services.data['shop']['stock'],read('assets/services/eldenmere.json')['shop']['stock'])

    def test_retained_mill_sorting_station_stays_reachable_beside_drivetrain(self):
        from npc_routines import find_path
        self.station('mill',(252,294))
        world=self.g.world
        target=world.data['destinations']['sorting_table']
        self.assertEqual(target,[288,168])
        self.assertTrue(world.can_stand(target))
        route=find_path(world,self.g.player.position,target,world.probe_size,None)
        self.assertIsNotNone(route)
        for point in route:
            goal=pygame.Vector2(point)
            for _ in range(600):
                delta=goal-self.g.player.position
                if delta.length()<.1:break
                self.g.update(min(1/60,delta.length()/72),delta,False)
            else:self.fail(('Blocked mill work approach',list(self.g.player.position),point))
        self.assertLess(self.g.player.position.distance_to(target),.1)


if __name__=='__main__':unittest.main()
