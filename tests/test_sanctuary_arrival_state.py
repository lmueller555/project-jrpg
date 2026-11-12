"""Acknowledged rescue beats, durable handoff and interrupted-save recovery."""
from pathlib import Path
from copy import deepcopy
import json,os,tempfile,unittest
from unittest.mock import patch
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy');os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from main import Game
from sanctuary_arrival import SanctuaryArrival
from cutscene_gallery import _regent_checkpoint,_station

class SanctuaryArrivalStateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.addCleanup(pygame.quit)
        self.path=Path(self.temp.name)/'journey.json';self.settings=Path(self.temp.name)/'settings.json'
        self.g=self.game(False)
        _regent_checkpoint(self.g,'sanctuary_arrival_pending')
        self.g._sync_story_party()
        _station(self.g,self.g._scene_by_id('elden_vale_sanctuary'),(444,642),'back')
        self.assertTrue(self.g.save_progress())
    def game(self,title=True):
        g=Game(fullscreen=False,start_on_title=title,save_path=self.path,settings_path=self.settings)
        g.audio.set_music(0);g.audio.set_effects(0);return g
    def tick(self,seconds=.2):self.g.update(seconds,(0,0),False)
    def press(self):
        self.g.handle_events([pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE,repeat=False),pygame.event.Event(pygame.KEYUP,key=pygame.K_SPACE)])
    def until(self,predicate,limit=2400):
        for _ in range(limit):
            if predicate():return
            self.tick()
            if predicate():return
            if self.g.sanctuary_arrival.dialogue:self.press()
        self.fail(('Scene did not settle',self.g.sanctuary_arrival.beat,self.g.sanctuary_arrival.error))
    def test_completed_handoff_is_durable_and_never_completes_mq03_or_heals_members(self):
        before={key:(m.current_hp,m.current_mp) for key,m in self.g.party.characters.items()}
        self.until(lambda:self.g.sanctuary_arrival.completed)
        self.assertEqual(self.g.party.active_ids,('caelan','mira','lucan'))
        self.assertEqual(self.g.regent_quest.stage,'sanctuary_arrival_pending')
        self.assertFalse(self.g.regent_quest.sanctuary_escort_active)
        self.assertEqual(before,{key:(m.current_hp,m.current_mp) for key,m in self.g.party.characters.items()})
        self.assertEqual(list(self.g.player.position),[1008,406])
        self.assertEqual({a.identifier for a in self.g.party_travel.actors()},{'mira','lucan'})
        facings={key:actor.facing for key,actor in self.g.sanctuary_arrival.actors.items()}
        self.assertEqual(self.g.regent_quest.clerk.pose,'read')
        self.assertEqual(self.g.regent_quest.clerk.facing,facings['page'])
        self.assertTrue(self.g.sanctuary_arrival.rail.opened)
        other=self.game();self.assertTrue(other.has_saved_journey,other.save_error)
        self.assertTrue(other.begin_journey(True),other.save_error)
        self.assertTrue(other.sanctuary_arrival.completed)
        self.assertEqual({key:actor.facing for key,actor in other.sanctuary_arrival.actors.items()},facings)
        self.assertEqual(other.regent_quest.clerk.pose,'read')
        self.assertTrue(other.sanctuary_arrival.rail.opened)
        self.assertEqual(other.party.active_ids,('caelan','mira','lucan'))
        other.opening_fade=other.transfer_cooldown=0;other.update(.2,(0,0),False)
        self.assertFalse(other.sanctuary_arrival.active)
        self.assertEqual({a.identifier for a in other.party_travel.actors()},{'mira','lucan'})
        self.assertTrue(other.sanctuary_cave.interact())
        self.assertEqual(other.world.data['id'],'sanctuary_cave')
        self.assertTrue(other.sanctuary_arrival.cave_entered)
        self.assertEqual(other.party.active_ids,('caelan','mira','lucan'))
        self.assertEqual(other.music.desired_track,'sanctuary_cave')
        self.assertTrue(other.has_saved_journey,other.save_error)
    def test_older_standing_spot_covered_by_the_new_closed_rope_resumes_on_clear_apron(self):
        self.g.player.position.update(1008,396)
        self.assertTrue(self.g.save_progress())
        other=self.game();self.assertTrue(other.begin_journey(True),other.save_error)
        self.assertEqual(tuple(other.player.position),(1008,406))
        self.assertTrue(other.world.can_stand(other.player.position))
        self.assertFalse(other.sanctuary_arrival.completed)

    def test_partial_dialogue_restarts_only_its_unacknowledged_beat_after_continue(self):
        self.until(lambda:self.g.sanctuary_arrival.beat==3)
        self.until(lambda:self.g.sanctuary_arrival.dialogue is not None)
        self.press();self.assertTrue(self.g.save_progress())
        other=self.game();self.assertTrue(other.begin_journey(True),other.save_error)
        self.g=other;self.g.opening_fade=self.g.transfer_cooldown=0
        self.tick()
        self.assertTrue(other.sanctuary_arrival.active)
        self.assertEqual(other.sanctuary_arrival.beat,3)
        self.assertEqual(other.sanctuary_arrival.dialogue_index,0)
        self.assertFalse(other.sanctuary_arrival.completed)
    def test_continue_during_rope_operation_rebuilds_the_unacknowledged_final_beat(self):
        self.until(lambda:self.g.sanctuary_arrival.beat==7)
        self.until(lambda:.2<self.g.sanctuary_arrival.rail.progress<.8)
        self.assertTrue(self.g.save_progress())
        other=self.game();self.assertTrue(other.begin_journey(True),other.save_error)
        self.g=other;self.g.opening_fade=self.g.transfer_cooldown=0
        self.tick()
        owner=self.g.sanctuary_arrival
        self.assertTrue(owner.active);self.assertEqual(owner.beat,7)
        self.assertEqual(owner.rail.progress,0.)
        self.assertFalse(owner.completed)
        self.until(lambda:owner.completed)
        self.assertTrue(owner.rail.opened)
        self.assertEqual(self.g.party.active_ids,('caelan','mira','lucan'))

    def test_failed_final_checkpoint_rolls_back_recruitment_and_retries_without_replaying_scene(self):
        self.until(lambda:self.g.sanctuary_arrival.beat==7)
        self.until(lambda:self.g.sanctuary_arrival.dialogue is not None)
        owner=self.g.sanctuary_arrival;before=deepcopy(self.g.party.to_dict());raw=self.path.read_bytes()
        with patch.object(self.g.save_store,'write',return_value=False):
            self.until(lambda:bool(owner.error))
        self.assertFalse(owner.completed);self.assertTrue(owner.active)
        self.assertEqual(self.g.party.to_dict(),before);self.assertEqual(self.path.read_bytes(),raw)
        self.press();self.assertTrue(owner.completed);self.assertFalse(owner.active)
        self.assertIn('lucan',self.g.party.active_ids)
    def test_earlier_cave_visit_releases_music_without_skipping_the_later_arrival(self):
        self.g.sanctuary_arrival.cave_entered=True
        self.g.music.play('eldenmere',fade_ms=0)
        self.tick()
        self.assertTrue(self.g.sanctuary_arrival.active)
        self.assertEqual(self.g.music.desired_track,'eldenmere')
        self.until(lambda:self.g.sanctuary_arrival.completed)
        self.assertTrue(self.g.sanctuary_arrival.cave_entered)

    def test_new_record_validation_rejects_impossible_or_malformed_beats(self):
        good={'version':1,'beat':0,'completed':False,'cave_entered':False}
        self.assertTrue(SanctuaryArrival.valid_snapshot(good))
        for change in ({'beat':True},{'beat':8},{'completed':True},{'version':True},{'cave_entered':1}):
            self.assertFalse(SanctuaryArrival.valid_snapshot({**good,**change}))
        data=json.loads(self.path.read_text());data['sanctuary_arrival']={**good,'beat':3};data['regent_quest']['stage']='idle'
        self.assertFalse(SanctuaryArrival.valid_journey(data))
