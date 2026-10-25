"""Real shared-doorway recovery with solid NPC feet and authored route progress."""
import copy
import os
import unittest

os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

import pygame
import main


class RoutineTrafficTests(unittest.TestCase):
    def setUp(self):
        self.game=main.Game(fullscreen=False,start_on_title=False)
        self.room=self.game._scene_by_id('sanctuary_dining')
        self.serene=next(n for n in self.game.persistent_npcs if n.data['id']=='mother_serene')
        self.tomas=next(n for n in self.game.persistent_npcs if n.data['id']=='tomas')
        self.serene.select_step('move_to_hall_door',position=(216,292.8))
        self.serene.waypoint_index=len(self.serene.step['waypoints'])-1
        self.tomas.select_step('walk_to_hall',position=(216,300))
        self.tomas.waypoint_index=len(self.tomas.step['waypoints'])-1

    def tearDown(self):pygame.quit()

    def assert_solid_feet(self,actor,player=None):
        self.assertTrue(self.room.can_stand(actor.position,actor.probe_size,actor,player))
        self.assertFalse(actor.blocker.colliderect(
            self.serene.blocker if actor is self.tomas else self.tomas.blocker))

    def test_loser_walks_aside_without_advancing_its_task_then_resumes_transfer(self):
        authored=copy.deepcopy(self.tomas.step)
        index=self.tomas.waypoint_index
        self.assertFalse(self.room.can_stand((216,294),self.tomas.probe_size,self.tomas))
        # Hold the nearer resident at its approach. Tomas must physically clear
        # the landing, then wait rather than pretending that he reached it.
        for _ in range(60):
            before=self.tomas.position.copy()
            self.tomas.update(1/60,self.room,None,self.game._transfer_routine_npc)
            self.assertLessEqual(self.tomas.position.distance_to(before),self.tomas.speed/60+1e-6)
            self.assert_solid_feet(self.tomas)
        self.assertEqual(self.tomas.step,authored)
        self.assertEqual(self.tomas.waypoint_index,index)
        self.assertNotEqual(tuple(self.tomas.position),(216,300))
        self.assertTrue(self.tomas.waiting)
        self.assertTrue(self.room.can_stand((216,294),self.serene.probe_size,self.serene))
        self.assertTrue(any(event['type']=='yield' for event in self.tomas.events))

        for _ in range(600):
            previous={actor:(actor.scene_id,actor.position.copy())
                      for actor in (self.serene,self.tomas)}
            self.game.update(1/60,(0,0),False)
            for actor in (self.serene,self.tomas):
                scene,position=previous[actor]
                if actor.scene_id==scene:
                    self.assertLessEqual(actor.position.distance_to(position),actor.speed/60+1e-6)
                world=self.game._routine_worlds[actor]
                self.assertTrue(world.can_stand(actor.position,actor.probe_size,actor))
                self.assertEqual(sum(w.npcs.count(actor) for w in self.game.scenes.values()),1)
            if self.tomas.scene_id!='sanctuary_dining':break
        self.assertNotEqual(self.tomas.scene_id,'sanctuary_dining')
        self.assertIsNone(self.tomas._yield_target)

    def test_yield_route_avoids_player_and_conversation_preserves_its_progress(self):
        player=self.room.probe_rect((198,300))
        self.assert_solid_feet(self.tomas,player)
        for _ in range(60):
            self.tomas.update(1/60,self.room,player,self.game._transfer_routine_npc)
            self.assert_solid_feet(self.tomas,player)
        self.assertGreater(self.tomas.position.x,216)
        self.assertTrue(self.tomas.waiting)
        before=(self.tomas.position.copy(),self.tomas.waypoint_index,self.tomas._yield_target)
        self.tomas.request_conversation('front')
        self.tomas.update(1,self.room,player,self.game._transfer_routine_npc)
        self.assertTrue(self.tomas.conversation_ready)
        self.assertEqual((self.tomas.position,self.tomas.waypoint_index,self.tomas._yield_target),before)
        self.tomas.end_conversation()
        self.tomas.update(1/60,self.room,player,self.game._transfer_routine_npc)
        self.assertEqual(self.tomas.waypoint_index,before[1])

    def test_new_authored_step_clears_old_yield(self):
        self.tomas.update(1/60,self.room,None,self.game._transfer_routine_npc)
        self.assertIsNotNone(self.tomas._yield_target)
        self.tomas.select_step('tinker',position=(104,262))
        self.assertIsNone(self.tomas._yield_target)
        self.assertIsNone(self.tomas._yield_peer)
        self.assertIsNone(self.tomas.path)


if __name__=='__main__':unittest.main()
