"""Exercise farm work through Game, including persistence and interruption."""
import copy
import os
from pathlib import Path
import tempfile
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from main import Game
from grain_farm import MILL_FLAG, SOURCE, SCENE_ID, valid_state
from tools.capture_lantern_quest import seed_previous_quests


class GrainFarmTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.g=self.make_game()
        self.g.world=self.g.overworld_world
        self.g.player.position.update(-876,232)
        self.f=self.g.world.grain_farm

    def tearDown(self):pygame.quit()

    def make_game(self,title=False):
        g=Game(fullscreen=False,start_on_title=title,save_path=self.root/'journey.json',settings_path=self.root/'settings.json')
        g.audio.set_music(0);g.audio.set_effects(0)
        g.opening_fade=g.transfer_cooldown=0
        return g

    def tick(self,count=1):
        for _ in range(count):self.g.update(1/30,(0,0),False)

    def until(self,predicate,limit=1800):
        for _ in range(limit):
            if predicate():return
            self.tick()
        self.fail((self.f.stage,self.f.state,[list(a.position) for a in self.f.actors]))

    def ready(self):
        self.g.social.flags.add(MILL_FLAG)
        self.until(lambda:self.f.stage=='ready' and self.f.coworker_stop==6)

    def finish_dialogue(self):
        while self.g.social.active:self.g.social.advance()

    def test_waits_for_physical_repair_and_has_finite_load(self):
        self.g.social.flags.add('CH01_MQ02_COMPLETE')
        self.tick(600)
        self.assertEqual(self.f.state['loaded'],0)
        self.assertEqual(len(self.f.props()),3)
        self.ready()
        self.tick(600)
        self.assertEqual(self.f.state['loaded'],2)
        self.assertFalse(self.f.state['exchange_read'])
        self.assertEqual(len(self.f.props()),3)
        self.assertFalse(self.g.social.locked)

    def test_blocking_loader_waits_without_losing_sack_then_recovers(self):
        self.g.social.flags.add(MILL_FLAG)
        self.until(lambda:self.f.stage=='carry')
        self.g.player.position.update(-824,210)
        self.tick(90)
        stopped=self.f.loader.position.copy()
        self.tick(90)
        self.assertEqual(self.f.loader.position,stopped)
        self.assertFalse(self.f.loader.blocker.colliderect(self.g.world.probe_rect(self.g.player.position)))
        self.assertEqual(self.f.state['loaded'],0)
        self.assertEqual(len(self.f.props()),3)
        self.g.player.position.update(-876,232)
        self.until(lambda:self.f.state['loaded']==2)

    def test_optional_exchange_commits_after_read_and_physical_payoff(self):
        self.ready();self.g.player.position.update(-870,203)
        flags=set(self.g.social.flags);quests=self.g.quests.to_dict()
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertEqual(self.g.social.script_identifier,SCENE_ID)
        self.g.social.cancel();self.tick()
        self.assertFalse(self.f.state['exchange_read'])
        self.assertTrue(self.g.overworld_travel.interact())
        self.finish_dialogue()
        self.assertTrue(self.f.state['exchange_read'])
        self.assertFalse(self.f.state['scene_done'])
        self.until(lambda:self.f.state['scene_done'])
        self.assertEqual(len(self.f.props()),3)
        self.assertEqual(flags,self.g.social.flags)
        self.assertEqual(quests,self.g.quests.to_dict())
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertNotEqual(self.g.social.script_identifier,SCENE_ID)

    def test_map_and_journal_freeze_all_local_clocks(self):
        for field in ('map_open','journal_open'):
            owner=self.g if field=='map_open' else self.g.quest_ui
            before=(self.f.timer,[a.clock for a in self.f.actors],[tuple(a.position) for a in self.f.actors])
            setattr(owner,field,True);self.tick(60);setattr(owner,field,False)
            self.assertEqual(before,(self.f.timer,[a.clock for a in self.f.actors],[tuple(a.position) for a in self.f.actors]))

    def test_continue_rolls_back_unplaced_sack_and_keeps_committed_work(self):
        seed_previous_quests(self.g);self.g.social.flags.add(MILL_FLAG);self.g.world=self.g.overworld_world;self.g.player.position.update(-876,232)
        self.until(lambda:self.f.state['loaded']==1 and self.f.stage=='carry')
        self.assertTrue(self.g.save_progress())
        other=self.make_game(True)
        self.assertTrue(other.has_saved_journey)
        self.assertTrue(other.begin_journey(True))
        farm=other.world.grain_farm
        self.assertEqual(farm.state['loaded'],1)
        self.assertEqual(tuple(farm.loader.position),SOURCE)
        self.assertEqual(len(farm.props()),3)
        self.assertEqual(sum(a.data['id']=='grain_loader' for a in other.world.npcs),1)
        self.assertFalse(any(a in world.npcs for a in farm.actors for world in other.scenes.values()))

    def test_continue_does_not_repeat_read_exchange_or_completed_scene(self):
        seed_previous_quests(self.g);self.g.social.flags.add(MILL_FLAG);self.g.world=self.g.overworld_world;self.g.player.position.update(-876,232)
        self.ready();self.g.player.position.update(-870,203)
        self.g.overworld_travel.interact();self.finish_dialogue()
        other=self.make_game(True);self.assertTrue(other.begin_journey(True))
        self.g=other;self.f=other.world.grain_farm;other.opening_fade=other.transfer_cooldown=0
        self.until(lambda:self.f.state['scene_done'])
        self.assertTrue(other.save_progress())
        again=self.make_game(True);self.assertTrue(again.begin_journey(True))
        self.assertTrue(again.world.grain_farm.state['scene_done'])
        self.assertEqual(again.world.grain_farm.state['loaded'],2)

    def test_invalid_save_payloads_rejected_without_exceptions(self):
        original=self.f.to_dict()
        for field,value in [('loaded',True),('loaded',3),('greeted',[{}]),('greeted',['loader','loader']),('exchange_read',True),('scene_done',True)]:
            data=copy.deepcopy(original);data[field]=value
            self.assertFalse(valid_state(data),(field,value))

    def test_cache_eviction_and_leaving_keep_single_controller(self):
        self.ready();actors=list(self.f.actors);before=self.f.to_dict()
        world=self.g.world
        world._render_cache.clear();world._metadata_cache.clear();world._collision_cache.clear()
        self.g.world=self.g.town;self.tick(30);self.g.world=world
        self.assertEqual(actors,world.grain_farm.actors)
        self.assertEqual(before,self.f.to_dict())
        self.assertEqual(len([a for a in world.npcs if a.data['id'].startswith('grain_')]),2)
