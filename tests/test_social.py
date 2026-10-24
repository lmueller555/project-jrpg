"""Gameplay contracts for automatic conversations and real input events."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import unittest
import pygame
import main
from social import clear_sight


class SocialTests(unittest.TestCase):
    def setUp(self):
        self.game=main.Game()
        self.actor=self.game.persistent_npcs[0]
        self.game.world=self.game._scene_by_id('sanctuary_dining')
        self.game.player.position.update(288,231)
        self.game.player.facing='back'
        pygame.event.clear()

    def tearDown(self):pygame.quit()

    def approach(self):
        self.game.update(1/60,(0,-1),False)
        self.assertTrue(self.game.social.locked)

    def click(self,position=(1,1)):
        for kind in (pygame.MOUSEBUTTONDOWN,pygame.MOUSEBUTTONUP):
            pygame.event.post(pygame.event.Event(kind,button=1,pos=position))
        self.assertTrue(self.game.handle_events())

    def finish(self):
        while self.game.social.active:self.click()

    def test_approach_opens_correct_speaker_and_locks_only_participants(self):
        self.approach()
        self.assertTrue(self.game.social.active)
        self.assertEqual(self.game.social.page['speaker'],'serene')
        position=self.game.player.position.copy()
        clock=self.actor.state_ms
        gardener=self.game.town.npcs[1]
        gardener_clock=gardener.state_ms
        elapsed=self.game.elapsed_ms
        for _ in range(60):self.game.update(1/60,(1,0),True)
        self.assertEqual(self.game.player.position,position)
        self.assertEqual(self.actor.state_ms,clock)
        self.assertGreater(self.game.elapsed_ms,elapsed)
        self.assertNotEqual(gardener.state_ms,gardener_clock)
        self.assertEqual(self.actor.sprite(0),self.actor.idles['front'])

    def test_click_anywhere_switches_portraits_and_no_held_button_skip(self):
        self.approach()
        self.click((959,1))
        self.assertEqual(self.game.social.page['speaker'],'caelan')
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(1,639)))
        self.game.handle_events()
        self.assertEqual(self.game.social.page_index,2)
        for _ in range(4):
            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(1,1)))
            self.game.handle_events()
        self.assertTrue(self.game.social.active)
        self.assertEqual(self.game.social.page_index,2)
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=(1,1)))
        self.game.handle_events()
        self.click()
        self.assertFalse(self.game.social.locked)

    def test_exit_requires_leaving_radius_then_repeat_lines(self):
        self.approach();self.finish()
        self.assertIn('serene_greeted',self.game.social.flags)
        for _ in range(10):self.game.update(1/60,(0,-1),False)
        self.assertFalse(self.game.social.locked)
        self.game.player.position.update(288,256)
        self.game.update(1/60,(0,0),False)
        self.assertNotIn(self.actor,self.game.social.blocked)
        self.game.player.position.update(288,231)
        self.approach()
        self.assertEqual(self.game.social.conversation['id'],'serene_repeat')

    def test_no_trigger_from_stationary_player_facing_away_or_map(self):
        self.game.player.position.update(288,229)
        self.game.update(1/60,(0,0),False)
        self.assertFalse(self.game.social.locked)
        self.game.update(1/60,(0,1),False)
        self.assertFalse(self.game.social.locked)
        self.game.map_open=True
        self.game.update(1/60,(0,-1),False)
        self.assertFalse(self.game.social.locked)

    def test_solid_wall_blocks_interaction(self):
        self.game.world.blocked.set_at((288,224),1)
        self.assertFalse(clear_sight(self.game.world,self.game.player.position,self.actor.position))
        self.game.update(1/60,(0,-1),False)
        self.assertFalse(self.game.social.locked)

    def test_nearest_eligible_speaker_is_selected(self):
        from npc_routines import RoutineNPC
        extra_record=dict(self.actor.data,id='second_serene',position=[300,214])
        extra=RoutineNPC(extra_record,self.game.world,'sanctuary_dining')
        self.game.world.npcs.insert(0,extra)
        self.game.social.profiles['second_serene']=self.game.social.profiles['mother_serene']
        self.game.player.position.update(288,229)
        self.approach()
        self.assertIs(self.game.social.actor,self.actor)

    def test_paused_walking_actor_keeps_path_and_room_membership(self):
        self.actor.select_step('return_to_provisions',position=(288,256))
        self.game.player.position.update(288,273)
        self.approach()
        state=(self.actor.state,self.actor.waypoint_index,tuple(self.actor.position))
        for _ in range(60):self.game.update(1/60,(0,0),False)
        self.assertEqual((self.actor.state,self.actor.waypoint_index,tuple(self.actor.position)),state)
        self.assertEqual(self.game.world.npcs.count(self.actor),1)
        self.finish()
        self.game.update(1/60,(0,0),False)
        self.assertNotEqual(tuple(self.actor.position),state[2])

    def test_held_prop_finishes_handoff_then_freezes_and_resumes_same_clock(self):
        self.actor.state_ms=1100
        self.assertEqual(self.actor.current_action_record['prop_owner'],'actor')
        self.approach()
        self.assertTrue(self.game.social.pending)
        self.click()
        self.assertEqual(self.game.social.page_index,0)
        for _ in range(300):
            self.game.update(1/60,(0,0),False)
            if self.game.social.active:break
        self.assertTrue(self.game.social.active)
        self.assertEqual(self.actor.current_action_record['prop_owner'],'surface')
        before=(self.actor.step_index,self.actor.state_ms,tuple(self.actor.position))
        for _ in range(60):self.game.update(1/60,(0,0),False)
        self.assertEqual((self.actor.step_index,self.actor.state_ms,tuple(self.actor.position)),before)
        self.finish()
        self.game.update(1/60,(0,0),False)
        self.assertEqual(self.actor.step_index,before[0])
        self.assertAlmostEqual(self.actor.state_ms,before[1]+1000/60)

    def test_hearth_finishes_before_turning_and_keyboard_repeat_is_ignored(self):
        self.actor.select_step('tend_hearth')
        self.game.player.position.update(384,127)
        self.approach()
        self.assertTrue(self.game.social.pending)
        for _ in range(300):
            self.game.update(1/60,(0,0),False)
            if self.game.social.active:break
        self.assertTrue(self.game.social.active)
        self.assertEqual(self.actor.state,'move_to_hall_door')
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE,repeat=True))
        self.game.handle_events()
        self.assertEqual(self.game.social.page_index,0)

    def test_portrait_box_wraps_within_three_lines_and_resize_accepts_clicks(self):
        self.approach()
        self.game.window=pygame.display.set_mode((1100,750))
        self.game.draw()
        for page in self.game.social.pages:
            self.assertLessEqual(len(page['lines']),3)
            for line in page['lines']:self.assertLessEqual(self.game.social.font.size(line)[0],332)
        self.click((1099,749))
        self.assertEqual(self.game.social.page_index,1)


if __name__=='__main__':unittest.main()
