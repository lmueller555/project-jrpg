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
        self.game=main.Game(fullscreen=False,start_on_title=False)
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

    def canvas_click(self,position):
        width,height=self.game.window.get_size()
        scale=max(1,min(width//480,height//320))
        self.click((round((width-480*scale)/2+position[0]*scale),
                    round((height-320*scale)/2+position[1]*scale)))

    def reach_choice(self):
        for _ in range(40):
            if self.game.social.choosing:return
            self.assertTrue(self.game.social.active)
            self.click()
        self.fail('Quest offer never reached its deliberate choice')

    def finish(self):
        for _ in range(40):
            if not self.game.social.active:return
            if self.game.social.choosing:
                self.canvas_click(self.game.social.choice_rects[1].center)
            else:self.click()
        self.fail('Conversation did not finish')

    def test_approach_opens_correct_speaker_and_pauses_only_the_npc(self):
        self.approach()
        self.assertTrue(self.game.social.active)
        self.assertEqual(self.game.social.page['speaker'],'serene')
        position=self.game.player.position.copy()
        clock=self.actor.state_ms
        gardener=self.game.town.npcs[1]
        gardener_clock=gardener.state_ms
        elapsed=self.game.elapsed_ms
        # Stay within speaking distance while proving the player retains
        # control. A longer retreat intentionally ends the conversation.
        for _ in range(6):self.game.update(1/60,(1,0),False)
        self.assertGreater(self.game.player.position.x,position.x)
        self.assertTrue(self.game.social.active)
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
        self.finish()
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
        self.assertEqual(self.game.social.conversation['id'],'serene_quest_offer')

    def test_acceptance_requires_a_deliberate_choice_not_more_advancing(self):
        self.approach();self.reach_choice()
        self.assertEqual(self.game.quests.status('CH01_MQ01'),'available')
        self.assertEqual(self.game.quests.marker_for('mother_serene'),'!')
        page=self.game.social.page_index
        for key in (pygame.K_SPACE,pygame.K_e):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=key,repeat=False))
            self.game.handle_events()
        self.click((1,1))
        self.assertTrue(self.game.social.choosing)
        self.assertEqual(self.game.social.page_index,page)
        self.assertEqual(self.game.quests.status('CH01_MQ01'),'available')
        self.game.draw()
        self.canvas_click(self.game.social.choice_rects[0].center)
        self.assertFalse(self.game.social.locked)
        self.assertEqual(self.game.quests.status('CH01_MQ01'),'active')
        self.assertIsNone(self.game.quests.marker_for('mother_serene'))

    def test_decline_releases_serene_and_reoffers_after_leaving(self):
        self.approach();self.reach_choice()
        self.canvas_click(self.game.social.choice_rects[1].center)
        self.assertFalse(self.game.social.locked)
        self.assertEqual(self.game.quests.status('CH01_MQ01'),'available')
        self.assertIn(self.actor,self.game.social.blocked)
        self.game.player.position.update(288,270)
        self.game.social.update((0,0))
        self.assertNotIn(self.actor,self.game.social.blocked)
        self.game.player.position.update(288,231)
        self.approach()
        self.assertEqual(self.game.social.conversation['id'],'serene_quest_offer')

    def test_serene_reminders_follow_objectives_without_completing_them(self):
        quest='CH01_MQ01'
        self.game.quests.accept(quest)
        self.game.social.start(self.actor)
        self.assertEqual(self.game.social.conversation['id'],'serene_quest_halden')
        self.finish()
        self.assertEqual(self.game.quests.objective_status(quest,'halden'),'active')
        self.game.quests.complete_objective(quest,'halden')
        self.game.social.start(self.actor)
        self.assertEqual(self.game.social.conversation['id'],'serene_quest_remaining')
        self.finish()
        self.game.quests.complete_objective(quest,'venn')
        self.game.social.start(self.actor)
        self.assertEqual(self.game.social.conversation['id'],'serene_quest_elira')
        self.finish()
        self.assertEqual(self.game.quests.status(quest),'active')

    def test_final_report_page_starts_arrival_without_early_completion(self):
        quest='CH01_MQ01'
        self.game.quests.accept(quest)
        for objective in ('halden','elira','venn'):
            self.game.quests.complete_objective(quest,objective)
        self.assertEqual(self.game.quests.marker_for('mother_serene'),'?')
        self.game.social.start(self.actor)
        self.assertEqual(self.game.social.conversation['id'],'serene_quest_report')
        self.click()
        self.assertEqual(self.game.quests.status(quest),'ready')
        self.finish()
        self.assertEqual(self.game.quests.status(quest),'ready')
        self.assertEqual(self.game.opening_conclusion.stage,'arrival')
        self.assertIsNone(self.game.quest_ui._marker_for('mother_serene'))
        self.assertFalse(self.game.social.start(self.actor))
        self.assertFalse(self.game.social.choosing)

    def test_choice_hitboxes_follow_integer_scaled_letterboxed_canvas(self):
        self.approach();self.reach_choice()
        for size in ((1100,750),(1440,810),(800,800)):
            self.game.window=pygame.display.set_mode(size)
            self.game.draw()
            self.click((0,0))
            self.assertTrue(self.game.social.choosing)
            self.assertEqual(self.game.quests.status('CH01_MQ01'),'available')
        self.canvas_click(self.game.social.choice_rects[0].center)
        self.assertEqual(self.game.quests.status('CH01_MQ01'),'active')

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

    def test_portrait_bubble_wraps_within_three_lines_and_resize_accepts_clicks(self):
        self.approach()
        self.game.window=pygame.display.set_mode((1100,750))
        self.game.draw()
        for page in self.game.social.pages:
            self.assertLessEqual(len(page['lines']),3)
            for line in page['lines']:self.assertLessEqual(self.game.social.font.size(line)[0],224)
        self.click((1099,749))
        self.assertEqual(self.game.social.page_index,1)


if __name__=='__main__':unittest.main()
