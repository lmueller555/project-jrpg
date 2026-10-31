"""Production-world coverage for finite regional work and interruption safety."""
import copy
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from main import Game
from garden_orchard import INITIAL, SCENE_ID, valid_state
from tools.capture_lantern_quest import seed_previous_quests


class GardenOrchardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.g=self.make_game()
        self.g.world=self.g.overworld_world;self.c=self.g.world.garden_orchard
        self.visit('gardener')

    def tearDown(self):pygame.quit()

    def make_game(self,title=False):
        game=Game(fullscreen=False,start_on_title=title,
                  save_path=self.root/'journey.json',settings_path=self.root/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade=game.transfer_cooldown=0
        return game

    def visit(self,role):
        self.g.player.position.update((-508,1206) if role=='gardener' else (-135,-230))

    def tick(self,count=1):
        for _ in range(count):self.g.update(1/30,(0,0),False)

    def until(self,predicate,limit=4800):
        for _ in range(limit):
            if predicate():return
            self.tick()
        self.fail((self.c.to_dict(),[list(a.position) for a in self.c.actors]))

    def finish_work(self,role):
        self.visit(role);self.until(lambda:self.c.state[role]['phase']!='work')

    def read_scene(self):
        self.finish_work('gardener');self.g.player.position.update(-526,1204)
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertEqual(self.g.social.script_identifier,SCENE_ID)
        while self.g.social.active:self.g.social.advance()

    def continue_journey(self):
        self.assertTrue(self.g.world.can_stand(self.g.player.position),tuple(self.g.player.position))
        self.assertTrue(self.g.save_progress())
        other=self.make_game(True);self.assertTrue(other.begin_journey(True))
        other.opening_fade=other.transfer_cooldown=0
        self.g=other;self.c=other.world.garden_orchard

    def positions(self):
        return {k:tuple(p) for k,(p,_) in self.c.portable_positions().items()}

    def test_finite_batches_keep_unique_objects_and_story_state(self):
        flags=set(self.g.social.flags);quests=copy.deepcopy(self.g.quests.to_dict())
        for role in ('gardener','picker'):
            self.finish_work(role)
            before=self.positions();self.tick(900)
            self.assertEqual(before,self.positions())
            self.assertEqual(set(before),set(INITIAL))
            self.assertFalse(self.g.social.locked)
        self.assertEqual(flags,self.g.social.flags)
        self.assertEqual(quests,self.g.quests.to_dict())
        self.assertNotEqual(self.positions()['turnip_0'],INITIAL['turnip_0'])
        self.assertNotEqual(self.positions()['apple_1'],INITIAL['apple_1'])
        self.assertNotEqual(self.positions()['apple_0'],self.positions()['apple_1'])

    def test_routes_are_clear_and_workers_remain_region_owned(self):
        actors=list(self.c.actors)
        for role in ('gardener','picker'):
            self.visit(role);actor=next(a for a in actors if a.role==role)
            for _ in range(4800):
                self.assertTrue(self.g.world.can_stand(actor.position,actor.probe_size,actor),
                                (role,tuple(actor.position),self.c.state[role]))
                if self.c.state[role]['phase']!='work':break
                self.tick()
            self.assertNotEqual(self.c.state[role]['phase'],'work')
        self.assertEqual(len([a for a in self.g.world.npcs if a.data['id'] in {x.data['id'] for x in actors}]),2)
        self.assertFalse(any(a in scene.npcs for a in actors for scene in self.g.scenes.values()))

    def test_player_obstruction_yields_then_recovers(self):
        self.until(lambda:(self.c.action('gardener') or {}).get('target')==(-526,1158))
        self.g.player.position.update(-526,1176);self.tick(120)
        before=self.c.actors[0].position.copy();self.tick(90)
        self.assertEqual(before,self.c.actors[0].position)
        self.assertFalse(self.c.actors[0].blocker.colliderect(self.g.world.probe_rect(self.g.player.position)))
        self.visit('gardener');self.finish_work('gardener')

    def test_pause_interfaces_region_exit_and_distance_suspend(self):
        for owner,field in [(self.g,'map_open'),(self.g.quest_ui,'journal_open'),
                            (self.g.pause,'is_open'),(self.g,'on_title')]:
            before=self.c.to_dict();setattr(owner,field,True);self.tick(30);setattr(owner,field,False)
            self.assertEqual(before,self.c.to_dict())
        before=self.c.to_dict();world=self.g.world;self.g.world=self.g.town
        self.tick(30);self.assertEqual(before,self.c.to_dict());self.g.world=world
        self.g.player.position.update(300,500);self.tick(30);self.assertEqual(before,self.c.to_dict())

    def test_continue_mid_carry_preserves_feet_and_all_props(self):
        seed_previous_quests(self.g);self.g.world=self.g.overworld_world;self.visit('gardener')
        self.until(lambda:(self.c.action('gardener') or {}).get('carry')=='can')
        self.tick(15);state=self.c.to_dict();props=self.positions()
        self.continue_journey()
        self.assertEqual(state,self.c.to_dict());self.assertEqual(props,self.positions())
        self.finish_work('gardener')

    def test_continue_mid_watering_preserves_time_and_never_replays_contact(self):
        seed_previous_quests(self.g);self.g.world=self.g.overworld_world;self.visit('gardener')
        self.until(lambda:(self.c.action('gardener') or {}).get('pour') and self.c.state['gardener']['elapsed']>.8)
        step=self.c.state['gardener']['step'];state=self.c.to_dict();props=self.positions()
        self.continue_journey();self.assertEqual(state,self.c.to_dict());self.assertEqual(props,self.positions())
        with mock.patch.object(self.g.regional_audio,'emit') as emit:
            self.until(lambda:self.c.state['gardener']['step']!=step)
            self.assertFalse(emit.called)

    def test_continue_before_contact_emits_exactly_once_at_actor_position(self):
        seed_previous_quests(self.g);self.g.world=self.g.overworld_world;self.visit('gardener')
        self.until(lambda:(self.c.action('gardener') or {}).get('pour') and self.c.state['gardener']['elapsed']>.3)
        step=self.c.state['gardener']['step'];self.continue_journey()
        with mock.patch.object(self.g.regional_audio,'emit') as emit:
            self.until(lambda:self.c.state['gardener']['step']!=step)
            self.assertEqual(emit.call_count,1)
            self.assertEqual(emit.call_args.args[2],tuple(self.c.actors[0].position))

    def test_scene_read_checkpoint_commits_before_physical_payoff(self):
        seed_previous_quests(self.g);self.g.world=self.g.overworld_world
        self.read_scene();self.assertTrue(self.c.state['gardener']['read'])
        self.assertEqual(self.c.state['gardener']['phase'],'scene')
        self.continue_journey();self.assertTrue(self.c.state['gardener']['read'])
        self.assertFalse(self.g.social.active)
        self.until(lambda:self.c.state['gardener']['phase']=='rest')
        self.assertNotEqual(self.positions()['plant'],INITIAL['plant'])
        self.g.player.position.update(self.c.actors[0].position+(22,0))
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertNotEqual(self.g.social.script_identifier,SCENE_ID)

    def test_continue_mid_plant_carry_keeps_single_plant(self):
        seed_previous_quests(self.g);self.g.world=self.g.overworld_world
        self.read_scene()
        self.until(lambda:(self.c.action('gardener') or {}).get('carry')=='plant')
        self.tick(12);state=self.c.to_dict();props=self.positions();self.continue_journey()
        self.assertEqual(state,self.c.to_dict());self.assertEqual(props,self.positions())
        self.until(lambda:self.c.state['gardener']['phase']=='rest')
        self.assertEqual(len(self.positions()),len(INITIAL))

    def test_cancelled_dialogue_does_not_commit_or_move_plant(self):
        self.finish_work('gardener');self.g.player.position.update(-526,1204)
        self.assertTrue(self.g.overworld_travel.interact());self.g.social.cancel();self.tick(30)
        self.assertFalse(self.c.state['gardener']['read'])
        self.assertEqual(self.positions()['plant'],INITIAL['plant'])
        self.assertEqual(self.c.state['gardener']['phase'],'ready')

    def test_audio_events_are_finite_and_paused_work_is_silent(self):
        for role in ('gardener','picker'):
            self.visit(role)
            with mock.patch.object(self.g.regional_audio,'emit') as emit:
                self.g.map_open=True;self.tick(60);self.assertFalse(emit.called);self.g.map_open=False
                self.finish_work(role);self.assertTrue(emit.called)
                emit.reset_mock();self.tick(300);self.assertFalse(emit.called)

    def test_eviction_keeps_identity_and_does_not_duplicate_harvest(self):
        self.tick(90);before=self.c.to_dict();props=self.positions();actors=list(self.c.actors)
        for cache in (self.g.world._collision_cache,self.g.world._metadata_cache,self.g.world._render_cache):cache.clear()
        self.assertEqual(before,self.c.to_dict());self.assertEqual(props,self.positions());self.assertEqual(actors,self.c.actors)

    def test_schema_rejects_malformed_data_and_accepts_legacy_journeys(self):
        for field,value in [('step',True),('step',-1),('step',999),('phase','elsewhere'),
                            ('elapsed',float('nan')),('elapsed',float('inf')),('elapsed',-1),
                            ('position',[0,0]),('position',[True,1190]),('read',1),('greeted',[])]:
            state=self.c.to_dict();state['gardener'][field]=value
            self.assertFalse(valid_state(state),(field,value))
        self.assertTrue(valid_state(self.c.to_dict()))
        self.assertTrue(self.g.overworld_travel.valid_journey({'player':{'scene':'eldenmere'},
            'overworld':{'version':1,'region':'elden_vale_start','discovered':['eldenmere']}}))

    def test_new_audio_materials_are_bounded_and_finite(self):
        from regional_audio import DURATIONS,samples
        for name in ('water','leaves','basket'):
            pcm=samples(name,8000,2)
            self.assertEqual(len(pcm),round(DURATIONS[name]*8000)*2)
            self.assertGreater(max(abs(v) for v in pcm),0)
            self.assertLess(max(abs(v) for v in pcm),12000)
            self.assertLess(abs(pcm[-1]),20)

    def test_real_contact_uses_allocator_and_hard_distance_cutoff(self):
        self.until(lambda:(self.c.action('gardener') or {}).get('pour') and self.c.state['gardener']['elapsed']>.3)
        self.g.audio.set_effects(1)
        actor=self.c.actors[0]
        self.g.player.position.update(actor.position+(30,0))
        self.until(lambda:self.c.state['gardener']['elapsed']>.8)
        key='garden_gardener_water'
        self.assertIn(key,self.g.regional_audio.voices)
        source=self.g.regional_audio.voices[key][0]
        self.assertEqual(tuple(source.point()),tuple(actor.position))
        self.assertLessEqual(len(self.g.regional_audio.voices),4)
        self.g.player.position.update(actor.position+(181,0));self.tick()
        self.assertNotIn(key,self.g.regional_audio.voices)

    def test_complete_scene_and_harvest_continue_stays_quiet(self):
        seed_previous_quests(self.g);self.g.world=self.g.overworld_world
        self.read_scene();self.until(lambda:self.c.state['gardener']['phase']=='rest')
        self.finish_work('picker');before=self.positions();self.continue_journey()
        with mock.patch.object(self.g.regional_audio,'emit') as emit:
            for role in ('gardener','picker'):
                self.visit(role);self.tick(120)
            self.assertFalse(emit.called)
        self.assertEqual(before,self.positions())

    def test_continue_mid_fruit_carry_keeps_sort_destination(self):
        seed_previous_quests(self.g);self.g.world=self.g.overworld_world;self.visit('picker')
        self.until(lambda:(self.c.action('picker') or {}).get('carry')=='apple_1')
        self.tick(12);before=self.c.to_dict();props=self.positions();self.continue_journey()
        self.assertEqual(before,self.c.to_dict());self.assertEqual(props,self.positions())
        self.finish_work('picker')
        self.assertNotEqual(self.positions()['apple_1'],self.positions()['apple_0'])

    def test_scene_phase_validation_rejects_unread_completion(self):
        for role,phase,read in [('gardener','scene',False),('gardener','rest',False),
                                ('gardener','work',True),('picker','scene',True),('picker','ready',False)]:
            data=self.c.to_dict();data[role].update(phase=phase,read=read,step=0)
            self.assertFalse(valid_state(data),(role,phase,read))
