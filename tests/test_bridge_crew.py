"""Production Game coverage for regional crew ownership and durable beats."""
import copy
import os
from pathlib import Path
import tempfile
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from main import Game
from bridge_crew import SOURCE, SCENE_ID, valid_state
from tools.capture_lantern_quest import seed_previous_quests


class BridgeCrewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.g=self.make_game()
        self.g.world=self.g.overworld_world;self.g.player.position.update(-2340,644)
        self.c=self.g.world.bridge_crew

    def tearDown(self):pygame.quit()

    def make_game(self,title=False):
        g=Game(fullscreen=False,start_on_title=title,save_path=self.root/'journey.json',settings_path=self.root/'settings.json')
        g.audio.set_music(0);g.audio.set_effects(0);g.opening_fade=g.transfer_cooldown=0
        return g

    def tick(self,count=1):
        for _ in range(count):self.g.update(1/30,(0,0),False)

    def until(self,predicate,limit=2400):
        for _ in range(limit):
            if predicate():return
            self.tick()
        self.fail((self.c.stage,self.c.state,[list(a.position) for a in self.c.actors]))

    def ready(self):self.until(lambda:self.c.stage=='ready')

    def dialogue(self):
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertEqual(self.g.social.script_identifier,SCENE_ID)
        while self.g.social.active:self.g.social.advance()

    def scene(self):
        self.ready();self.g.player.position.update(-2376,642)
        self.assertTrue(self.g.overworld_travel.interact())
        self.until(lambda:self.c.stage=='request');self.dialogue()
        self.until(lambda:self.c.stage=='exchange');self.dialogue()
        self.until(lambda:self.c.state['tea_beat']==5)

    def test_finite_batch_then_maintenance_no_story_mutation(self):
        flags=set(self.g.social.flags);quests=copy.deepcopy(self.g.quests.to_dict())
        self.ready();self.tick(1200)
        self.assertEqual(self.c.state['sorted'],3)
        self.assertEqual(self.c.state['tea_beat'],0)
        self.assertFalse(self.g.social.locked)
        self.assertEqual(flags,self.g.social.flags);self.assertEqual(quests,self.g.quests.to_dict())
        self.assertEqual(len(self.c.props()),13)

    def test_full_scene_and_repeat_greeting(self):
        self.scene()
        self.assertTrue(self.g.overworld_travel.interact())
        self.assertNotEqual(self.g.social.script_identifier,SCENE_ID)

    def test_blocked_carry_waits_and_recovers(self):
        self.until(lambda:self.c.stage=='carry')
        self.g.player.position.update(-2352,616);self.tick(100)
        p=self.c.mason.position.copy();self.tick(100)
        self.assertEqual(p,self.c.mason.position)
        self.assertFalse(self.c.mason.blocker.colliderect(self.g.world.probe_rect(self.g.player.position)))
        self.assertEqual(self.c.state['sorted'],0)
        self.g.player.position.update(-2340,644);self.ready()

    def test_no_worker_overlap_during_scene(self):
        self.ready();self.g.player.position.update(-2376,642)
        self.g.overworld_travel.interact()
        for _ in range(3000):
            self.assertFalse(self.c.mason.blocker.colliderect(self.c.tender.blocker))
            if self.c.stage in ('request','exchange'):self.dialogue()
            if self.c.state['tea_beat']==5:break
            self.tick()
        self.assertEqual(self.c.state['tea_beat'],5)

    def test_pause_map_journal_and_town_suspend(self):
        for owner,field in [(self.g,'map_open'),(self.g.quest_ui,'journal_open'),(self.g.pause,'is_open'),(self.g,'on_title')]:
            before=(self.c.timer,[a.clock for a in self.c.actors])
            setattr(owner,field,True);self.tick(60);setattr(owner,field,False)
            self.assertEqual(before,(self.c.timer,[a.clock for a in self.c.actors]))
        world=self.g.world;self.g.world=self.g.town;before=self.c.timer;self.tick(60)
        self.assertEqual(before,self.c.timer);self.g.world=world

    def test_continue_at_each_completed_tea_beat(self):
        seed_previous_quests(self.g);self.g.world=self.g.overworld_world
        for beat in range(1,6):
            self.c.restore({'sorted':3,'tea_beat':beat,'greeted':[]})
            self.g.player.position.update(-2376,642);self.assertTrue(self.g.save_progress())
            other=self.make_game(True);self.assertTrue(other.begin_journey(True))
            self.g=other;self.c=other.world.bridge_crew
            other.opening_fade=other.transfer_cooldown=0
            self.assertEqual(self.c.state['tea_beat'],beat)
            self.assertEqual(len([a for a in other.world.npcs if a.data['id'].startswith('bridge_')]),2)
            if beat<5:
                for _ in range(2400):
                    if self.c.stage in ('request','exchange'):self.dialogue()
                    if self.c.state['tea_beat']==5:break
                    self.tick()
                self.assertEqual(self.c.state['tea_beat'],5)

    def test_continue_unplaced_stone_returns_to_source(self):
        seed_previous_quests(self.g);self.g.world=self.g.overworld_world;self.g.player.position.update(-2340,644)
        self.until(lambda:self.c.state['sorted']==1 and self.c.stage=='carry')
        self.assertTrue(self.g.save_progress())
        other=self.make_game(True);self.assertTrue(other.begin_journey(True))
        self.assertEqual(other.world.bridge_crew.state['sorted'],1)
        self.assertEqual(tuple(other.world.bridge_crew.mason.position),SOURCE)

    def test_cancelled_dialogue_keeps_physical_beat(self):
        self.ready();self.g.player.position.update(-2376,642);self.g.overworld_travel.interact()
        self.until(lambda:self.c.stage=='request');self.g.overworld_travel.interact()
        self.g.social.cancel();self.tick()
        self.assertEqual(self.c.stage,'request');self.assertEqual(self.c.state['tea_beat'],1)
        self.dialogue()

    def test_schema_rejects_corrupt_payload(self):
        for key,value in [('sorted',True),('sorted',4),('tea_beat',-1),('tea_beat',True),('tea_beat',1),('greeted',[{}]),('greeted',['mason','mason'])]:
            record=self.c.to_dict();record[key]=value;self.assertFalse(valid_state(record))

    def test_chunk_eviction_does_not_own_crew(self):
        actors=list(self.c.actors);world=self.g.world
        for cache in (world._collision_cache,world._metadata_cache,world._render_cache):cache.clear()
        self.ready();self.assertEqual(actors,self.c.actors)
        self.assertFalse(any(a in scene.npcs for a in actors for scene in self.g.scenes.values()))

    def test_handoff_reservation_does_not_trap_player(self):
        self.ready();self.g.player.position.update(-2352,616)
        self.g.overworld_travel.interact()
        self.assertEqual(self.c.state['tea_beat'],0)
        self.g.social.cancel();self.g.player.position.update(-2376,642)
        self.g.overworld_travel.interact()
        self.assertEqual(self.c.state['tea_beat'],1)
        self.assertFalse(self.g.world.can_stand((-2352,616)))
        self.assertTrue(self.g.world.can_stand((-2376,642)))

    def test_main_road_and_approach_remain_clear(self):
        for point in [(-2352,672),(-2328,672),(-2304,672),(-2400,696)]:
            self.assertTrue(self.g.world.can_stand(point),point)
        for beat in range(1,6):
            self.c.restore({'sorted':3,'tea_beat':beat,'greeted':[]})
            self.assertTrue(self.g.world.can_stand((-2352,672)))
