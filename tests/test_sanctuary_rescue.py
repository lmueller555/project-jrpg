"""Rescue acknowledgment, interruption and saved battle/worker ownership."""
from copy import deepcopy
import gc
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from tools.capture_sanctuary_rescue import make_game, press, advance_until, seed_victory
from sanctuary_boss import RECEIPT, valid_ticket
from sanctuary_rescue import SanctuaryRescue


class SanctuaryRescueTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='rescue-tests-')
        self.addCleanup(self.directory.cleanup)
        self.g=make_game(self.directory.name,embedded=False)
        self.owner=self.g.sanctuary_rescue
        self.addCleanup(self.cleanup_game)

    def cleanup_game(self):
        self.owner.reset()
        self.g.music.stop()
        self.owner=self.g=None
        pygame.quit();gc.collect()

    def tick(self,seconds=.05):self.g.update(seconds,(0,0),False)

    def until(self,predicate):advance_until(self.g,predicate)

    def before(self):
        self.assertTrue(self.owner.start_before(self.g.sanctuary_boss._begin_battle))

    def resource_state(self):
        return {key:member.to_dict() for key,member in self.g.party.characters.items()}

    def test_entry_offer_and_retreat_do_not_start_rescue_or_create_battle(self):
        boss=self.g.sanctuary_boss
        self.assertTrue(boss.offer())
        self.assertFalse(self.owner.active)
        self.assertEqual(self.owner.stage,'undiscovered')
        self.assertIsNone(boss.pending)
        self.g.social.cancel_script()
        boss._choose('leave')
        self.assertFalse(self.owner.active)
        self.assertEqual(self.owner.stage,'undiscovered')
        self.assertIsNone(boss.pending)
        self.assertFalse(self.g.combat.active)

    def test_confirmed_scene_finishes_before_ticket_and_preserves_resources(self):
        before=self.resource_state();rewards=self.g.battle_rewards.to_dict()
        self.g.sanctuary_boss._choose('enter')
        self.assertTrue(self.owner.active)
        self.assertIsNone(self.g.sanctuary_boss.pending)
        self.until(lambda:self.g.combat.active)
        ticket=self.g.sanctuary_boss.pending
        self.assertTrue(valid_ticket(ticket))
        self.assertEqual(ticket['position'],list(self.g.player.position))
        self.assertEqual(self.owner.stage,'confrontation')
        self.assertFalse(self.owner.active)
        self.assertEqual(before,self.resource_state())
        self.assertEqual(rewards,self.g.battle_rewards.to_dict())

    def test_pause_and_focus_freeze_clock_and_staging(self):
        self.before();self.tick(.5)
        def facts():
            return (self.owner.elapsed,self.owner.phase_time,self.owner.phase_index,
                    {key:tuple(actor.position) for key,actor in self.owner.actors.items()})
        press(self.g,pygame.K_ESCAPE)
        self.assertTrue(self.owner.paused)
        before=facts();self.tick(3)
        self.assertEqual(facts(),before)
        press(self.g,pygame.K_ESCAPE)
        self.assertFalse(self.owner.paused)
        self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        before=facts();self.tick(3)
        self.assertEqual(facts(),before)
        self.g.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.tick(.1)
        self.assertGreater(self.owner.elapsed,before[0])

    def test_missing_legacy_record_infers_departed_worker_without_replaying(self):
        journey=self.g.journey_snapshot()
        journey.pop('sanctuary_rescue',None)
        journey['sanctuary_cave']['lucan_departed']=True
        journey['sanctuary_boss'].update(defeated=True,intro_seen=True,pending=None)
        before=deepcopy(journey)
        self.assertTrue(self.owner.restore(None,journey=journey))
        self.assertEqual(self.owner.stage,'evacuated')
        self.assertFalse(self.owner.active)
        self.assertEqual(journey,before)

    def test_malformed_records_and_impossible_defeat_states_are_rejected(self):
        self.assertTrue(SanctuaryRescue.valid_snapshot({'version':1,'stage':'undiscovered'}))
        for record in (None,[],{}, {'version':True,'stage':'undiscovered'},
                       {'version':1,'stage':'unknown'}, {'version':1,'stage':'treated','extra':1}):
            with self.subTest(record=record):
                self.assertFalse(SanctuaryRescue.valid_snapshot(record))
        journey=self.g.journey_snapshot()
        for stage in ('freed','treated','greenwell','handoff','evacuated'):
            with self.subTest(stage=stage):
                candidate=deepcopy(journey)
                candidate['sanctuary_rescue']={'version':1,'stage':stage}
                self.assertFalse(SanctuaryRescue.valid_journey(candidate))
        before=self.owner.to_dict()
        self.assertFalse(self.owner.restore({'version':1,'stage':'unknown'}))
        self.assertEqual(self.owner.to_dict(),before)


    def after(self):
        seed_victory(self.g)
        self.assertTrue(self.owner.maybe_start())

    def test_fast_input_cannot_free_or_treat_before_physical_cues(self):
        self.after()
        self.until(lambda:self.owner.shot=='free_worker')
        before=self.owner.phase_time
        for _ in range(20):press(self.g)
        self.assertEqual(self.owner.shot,'free_worker')
        self.assertEqual(self.owner.phase_time,before)
        self.assertFalse(self.owner._worker_free)
        for _ in range(50):self.tick()
        self.assertFalse(self.owner._worker_free)
        self.until(lambda:self.owner.shot=='treatment')
        self.assertEqual(self.owner.stage,'freed')
        self.assertTrue(self.owner._worker_free)
        self.assertTrue(any(record['id']=='rescue_rock' for record in self.owner._sync_props()))
        for _ in range(20):press(self.g)
        self.assertEqual(self.owner.shot,'treatment')
        self.assertFalse(self.owner._treated)
        self.until(lambda:self.owner.stage=='greenwell' and not self.owner.active)
        self.assertTrue(self.owner._treated)

    def test_greenwell_prepare_keeps_worker_and_lucan_safe_without_rewards(self):
        self.after()
        resources=self.resource_state();rewards=deepcopy(self.g.battle_rewards.to_dict())
        self.until(lambda:self.owner.stage=='greenwell' and not self.owner.active)
        self.assertFalse(self.g._cave_encounters_available())
        self.assertFalse(self.g.elemental_bosses._available())
        self.assertFalse(self.g.sanctuary_cave.lucan_departed)
        self.assertIn('lucan',self.g.party.active_ids)
        self.g.player.position.update(1950,852)
        self.assertTrue(self.owner.interact())
        self.g.social.cancel_script();self.owner._choose_departure('prepare')
        self.tick()
        self.assertEqual(self.owner.stage,'greenwell')
        published=[actor for _,actor in self.owner._published]
        self.assertEqual(len(published),2)
        self.assertEqual(len({id(actor) for actor in published}),2)
        self.assertEqual({actor.key for actor in published},{'worker','lucan'})
        self.assertNotIn('lucan',{actor.identifier for actor in self.g.party_travel.actors()})
        for _ in range(3):self.owner.sync_waiting()
        self.assertEqual(sum(actor.key=='worker' for actor in self.g.world.npcs if hasattr(actor,'key')),1)
        self.assertEqual(resources,self.resource_state())
        self.assertEqual(rewards,self.g.battle_rewards.to_dict())

    def test_handoff_completes_before_guest_departure_and_survives_continue(self):
        self.after()
        self.until(lambda:self.owner.stage=='greenwell' and not self.owner.active)
        self.owner._choose_departure('return')
        self.until(lambda:self.owner.stage=='handoff')
        self.assertEqual(self.owner.stage,'handoff')
        self.assertEqual(self.g.world.data['id'],'elden_vale_sanctuary')
        self.assertFalse(self.g.sanctuary_cave.lucan_departed)
        self.until(lambda:self.owner.shot=='caretaker_receives')
        self.assertFalse(self.g.sanctuary_cave.lucan_departed)
        self.assertIn('lucan',self.g.party.active_ids)
        self.until(lambda:self.owner.stage=='evacuated' and not self.owner.active)
        self.assertTrue(self.g.sanctuary_cave.lucan_departed)
        self.assertNotIn('lucan',self.g.party.active_ids)
        before=deepcopy(self.g.battle_rewards.to_dict())
        self.assertTrue(self.g.save_progress())
        other=make_game(self.directory.name,seed=False,title=True,embedded=False)
        self.addCleanup(other.music.stop)
        self.assertTrue(other.begin_journey(True),other.save_error)
        self.assertEqual(other.sanctuary_rescue.stage,'evacuated')
        self.assertFalse(other.sanctuary_rescue.active)
        self.assertFalse(other.combat.active)
        self.assertIsNone(other.sanctuary_boss.pending)
        self.assertEqual(other.battle_rewards.to_dict(),before)
        self.assertTrue(other.sanctuary_cave.lucan_departed)
        other.sanctuary_rescue.sync_waiting()
        self.assertEqual(other.social.data['speakers']['rescue_worker']['name'],'Injured worker')
        other.world=other._scene_by_id('sanctuary_cave')
        other.sanctuary_rescue.sync_waiting()
        self.assertFalse(other.sanctuary_rescue._published)
        self.assertEqual(sum(record['id']=='rescue_rock' for record in other.world.entities),1)
        self.assertFalse(any(record['id']=='rescue_dressing' for record in other.world.entities))

    def test_partial_physical_work_reloads_from_last_acknowledged_stage(self):
        self.after()
        self.until(lambda:self.owner.shot=='free_worker')
        for _ in range(60):self.tick()
        self.assertTrue(self.owner._worker_free)
        self.assertEqual(self.owner.stage,'confrontation')
        self.assertTrue(self.g.save_progress())
        other=make_game(self.directory.name,seed=False,title=True,embedded=False)
        self.addCleanup(other.music.stop)
        self.assertTrue(other.begin_journey(True),other.save_error)
        self.assertEqual(other.sanctuary_rescue.stage,'confrontation')
        self.assertTrue(other.sanctuary_boss.defeated)
        self.assertIsNone(other.sanctuary_boss.pending)
        self.assertFalse(other.combat.active)
        other.opening_fade=other.transfer_cooldown=0.
        self.assertTrue(other.sanctuary_rescue.maybe_start())
        self.assertFalse(other.sanctuary_rescue._worker_free)
        self.assertEqual(other.sanctuary_rescue.shot,'aftermath')

    def test_failed_extraction_checkpoint_rolls_back_scene_and_guest(self):
        self.after()
        self.until(lambda:self.owner.stage=='greenwell' and not self.owner.active)
        before=self.g.journey_snapshot();origin=self.g.world
        with patch.object(self.g.save_store,'write',return_value=False):
            self.owner._choose_departure('return')
            self.until(lambda:not self.owner.active and self.g.social.active)
        self.assertEqual(self.owner.stage,'greenwell')
        self.assertIs(self.g.world,origin)
        self.assertEqual(list(self.g.player.position),before['player']['position'])
        self.assertFalse(self.g.sanctuary_cave.lucan_departed)
        self.assertEqual(self.g.party.to_dict(),before['party'])
        self.assertEqual(self.g.music.desired_track,'sanctuary_cave')


    def test_camera_holds_on_warning_and_reduced_motion_uses_stable_shots(self):
        self.assertTrue(self.owner.start_before(lambda:True))
        self.until(lambda:self.owner.shot=='warning')
        center=tuple(self.owner._camera_center);zoom=self.owner._camera_zoom
        for _ in range(20):self.tick()
        self.assertEqual(tuple(self.owner._camera_center),center)
        self.assertEqual(self.owner._camera_zoom,zoom)
        self.owner.reset();self.g.audio.reduced_motion=True
        self.assertTrue(self.owner.start_before(lambda:True))
        self.tick(.1);center=tuple(self.owner._camera_center)
        for _ in range(10):self.tick()
        self.assertEqual(tuple(self.owner._camera_center),center)

    def test_failed_final_handoff_checkpoint_keeps_guest_until_retry(self):
        self.after()
        self.until(lambda:self.owner.stage=='greenwell' and not self.owner.active)
        self.owner._choose_departure('return')
        self.until(lambda:self.owner.shot=='handoff_complete')
        party=deepcopy(self.g.party.to_dict())
        with patch.object(self.g.save_store,'write',return_value=False):
            self.until(lambda:bool(self.owner.error))
        self.assertEqual(self.owner.stage,'handoff')
        self.assertFalse(self.g.sanctuary_cave.lucan_departed)
        self.assertEqual(self.g.party.to_dict(),party)
        self.assertTrue(self.owner.active)
        press(self.g)
        self.assertEqual(self.owner.stage,'evacuated')
        self.assertFalse(self.owner.active)
        self.assertTrue(self.g.sanctuary_cave.lucan_departed)

    def test_reset_removes_waiting_worker_and_temporary_world_props(self):
        self.after()
        self.until(lambda:self.owner.stage=='greenwell' and not self.owner.active)
        published=[actor for _,actor in self.owner._published]
        self.assertEqual(len(published),2)
        world=self.g.world
        self.owner.reset()
        self.assertTrue(all(actor not in world.npcs for actor in published))
        self.assertFalse(self.owner._published)
        self.assertFalse(any(record['id'].startswith('rescue_') for record in world.entities))


    def test_missing_legacy_pending_record_resumes_committed_fight_without_reveal(self):
        journey=self.g.journey_snapshot();journey.pop('sanctuary_rescue')
        journey['sanctuary_boss']['pending']={'fixture':'already committed encounter'}
        self.assertTrue(self.owner.restore(None,journey=journey))
        self.assertEqual(self.owner.stage,'confrontation')
        self.assertFalse(self.owner.active)
        journey['sanctuary_arrival']['completed']=False
        self.assertTrue(self.owner.restore(None,journey=journey))
        self.assertEqual(self.owner.stage,'undiscovered')

    def test_failed_battle_start_retries_without_replaying_rescue(self):
        callback=Mock(return_value=False)
        self.assertTrue(self.owner.start_before(callback))
        self.until(lambda:bool(self.owner.error))
        self.assertEqual(self.owner.stage,'confrontation')
        self.assertTrue(self.owner.active)
        self.assertIsNone(self.g.sanctuary_boss.pending)
        callback.return_value=True
        press(self.g)
        self.assertEqual(callback.call_count,2)
        self.assertFalse(self.owner.active)
        self.assertEqual(self.owner.stage,'confrontation')
        for _ in range(3):self.owner.sync_waiting()
        self.assertEqual([actor.key for _,actor in self.owner._published],['worker'])
        self.assertEqual(sum(record['id']=='rescue_rock' for record in self.g.world.entities),1)
        self.assertFalse(self.owner._worker_free)

    def test_disabled_save_playtest_can_complete_the_caretaker_handoff(self):
        game=make_game()
        self.addCleanup(game.music.stop)
        seed_victory(game)
        owner=game.sanctuary_rescue
        self.assertFalse(game.save_store.enabled)
        self.assertTrue(owner.maybe_start())
        advance_until(game,lambda:owner.stage=='greenwell' and not owner.active)
        owner._choose_departure('return')
        advance_until(game,lambda:owner.stage=='evacuated' and not owner.active)
        self.assertTrue(game.sanctuary_cave.lucan_departed)
        self.assertNotIn('lucan',game.party.active_ids)


    def test_acknowledged_confrontation_can_leave_before_retry_without_corrupt_save(self):
        self.owner.stage='confrontation'
        self.g.sanctuary_boss.intro_seen=True
        self.g.world=self.g._scene_by_id('elden_vale_sanctuary')
        self.g.player.position.update(1008,406)
        journey=self.g.journey_snapshot()
        self.assertFalse(journey['sanctuary_boss']['defeated'])
        self.assertIsNone(journey['sanctuary_boss']['pending'])
        self.assertTrue(SanctuaryRescue.valid_journey(journey))
        self.assertTrue(self.g.save_progress())
        other=make_game(self.directory.name,seed=False,title=True,embedded=False)
        self.addCleanup(other.music.stop)
        self.assertTrue(other.begin_journey(True),other.save_error)
        self.assertEqual(other.sanctuary_rescue.stage,'confrontation')
        self.assertFalse(other.combat.active)

    def test_reduced_motion_escort_holds_shots_and_preserves_supported_spacing(self):
        self.g.audio.reduced_motion=True
        self.after()
        self.until(lambda:self.owner.shot=='evacuate_to_greenwell')
        changes=[];samples=0
        while self.owner.shot=='evacuate_to_greenwell':
            before=pygame.Vector2(self.owner._camera_center)
            self.tick()
            if self.owner.shot!='evacuate_to_greenwell':break
            changes.append(before.distance_to(self.owner._camera_center));samples+=1
            self.assertAlmostEqual(self.owner.actors['worker'].position.distance_to(
                self.owner.actors['lucan'].position),24.,places=5)
            self.assertLess(samples,2000)
        self.assertGreater(samples,50)
        self.assertTrue(all(delta<1e-7 or delta>=100. for delta in changes),changes)
        self.assertTrue(any(delta>=100. for delta in changes))


if __name__=='__main__':unittest.main()
