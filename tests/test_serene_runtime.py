"""Persistent Mother Serene schedule, room transfers and action selection."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

import unittest

import pygame
import main
from npc_routines import find_path


class SereneRuntime(unittest.TestCase):
    def setUp(self):
        self.game=main.Game()
        self.serene=next(n for n in self.game.persistent_npcs if n.data['id']=='mother_serene')

    def tearDown(self):pygame.quit()

    def scene(self,scene_id):return self.game._scene_by_id(scene_id)

    def memberships(self):
        return [(world,world.npcs.count(self.serene)) for world in self.game.scenes.values()
                if self.serene in world.npcs]

    def place(self,step_id,scene_id,position,facing=None):
        destination=self.scene(scene_id)
        for world in self.game.scenes.values():
            while self.serene in world.npcs:world.npcs.remove(self.serene)
        self.serene.select_step(step_id,position=position,scene_id=scene_id,facing=facing)
        destination.npcs.append(self.serene)
        self.game._routine_worlds[self.serene]=destination
        return destination

    def test_serene_is_one_persistent_instance_in_exactly_one_room(self):
        dining=self.scene('sanctuary_dining');hall=self.scene('sanctuary_hall')
        self.assertEqual(len([n for n in self.game.persistent_npcs if n.data['id']=='mother_serene']),1)
        self.assertEqual(self.serene.scene_id,'sanctuary_dining')
        self.assertEqual(tuple(self.serene.position),(288,228))
        self.assertEqual(self.memberships(),[(dining,1)])
        self.assertNotIn(self.serene,self.game.town.npcs)
        self.assertNotIn(self.serene,hall.npcs)

        # Merely visiting and caching either room must not clone or reset her.
        self.game.world=hall;self.game.update(.25,(0,0),False)
        self.game.world=dining;self.game.update(.25,(0,0),False)
        self.assertEqual(self.memberships(),[(dining,1)])
        self.assertIs(self.game._routine_worlds[self.serene],dining)

    def test_game_advances_persistent_action_once_per_frame(self):
        self.place('sort_provisions','sanctuary_dining',(288,228),'back')
        self.assertEqual(self.serene.state_ms,0)
        self.game.world=self.game.town
        self.game.update(.1,(0,0),False)
        self.assertAlmostEqual(self.serene.state_ms,100,places=5)
        self.game.update(.05,(0,0),False)
        self.assertAlmostEqual(self.serene.state_ms,150,places=5)

    def test_forward_and_return_transfers_move_the_same_object_once(self):
        dining=self.place('enter_sanctuary_hall','sanctuary_dining',(216,294),'back')
        hall=self.scene('sanctuary_hall')
        self.game.world=self.game.town
        self.game.update(1/60,(0,0),False)
        self.assertEqual(self.serene.scene_id,'sanctuary_hall')
        self.assertEqual(tuple(self.serene.position),(264,90))
        self.assertEqual(self.serene.state,'move_to_hall_table')
        self.assertNotIn(self.serene,dining.npcs)
        self.assertEqual(self.memberships(),[(hall,1)])

        self.place('return_to_sanctuary_dining','sanctuary_hall',(264,90),'front')
        self.game.update(1/60,(0,0),False)
        self.assertEqual(self.serene.scene_id,'sanctuary_dining')
        self.assertEqual(tuple(self.serene.position),(216,294))
        self.assertEqual(self.serene.state,'return_to_provisions')
        self.assertEqual(self.memberships(),[(dining,1)])
        self.assertNotIn(self.serene,hall.npcs)

    def test_player_on_destination_makes_transfer_wait_without_duplication(self):
        dining=self.place('enter_sanctuary_hall','sanctuary_dining',(216,294),'back')
        hall=self.scene('sanctuary_hall')
        destination=(264,90)
        self.game.world=hall
        self.game.player.position.update(destination)
        self.game.update(.1,(0,0),False)
        self.assertEqual(self.serene.state,'enter_sanctuary_hall')
        self.assertEqual(self.serene.scene_id,'sanctuary_dining')
        self.assertTrue(self.serene.waiting)
        self.assertEqual(self.memberships(),[(dining,1)])
        self.assertNotIn(self.serene,hall.npcs)

        self.game.player.position.update(72,204)
        self.game.update(1/60,(0,0),False)
        self.assertEqual(self.serene.scene_id,'sanctuary_hall')
        self.assertEqual(tuple(self.serene.position),destination)
        self.assertFalse(self.serene.waiting)
        self.assertEqual(self.memberships(),[(hall,1)])

    def test_every_station_and_transfer_route_is_reachable_and_doors_stay_clear(self):
        behavior=self.serene.behavior
        scene_id=behavior['start_scene'];point=tuple(behavior['start_position'])
        station_positions={
            (record['scene'],tuple(record['station']))
            for record in behavior['review'].values()
        }
        station_positions.add(('sanctuary_dining',(336,228)))
        for station_scene,station in station_positions:
            world=self.scene(station_scene)
            self.assertTrue(world.can_stand(station,self.serene.probe_size,self.serene),
                            (station_scene,station))
            blocker=world.probe_rect(station,self.serene.probe_size)
            for door in world.doors:
                doorway=world.probe_rect(door.data['anchor'],self.serene.probe_size)
                self.assertFalse(blocker.colliderect(doorway),(station_scene,station,door.data['id']))

        for step in behavior['steps']:
            world=self.scene(scene_id)
            if step['type']=='move':
                for destination in map(tuple,step['waypoints']):
                    self.assertTrue(world.can_stand(destination,self.serene.probe_size,self.serene),
                                    (scene_id,step['id'],destination))
                    self.assertIsNotNone(find_path(world,point,destination,self.serene.probe_size,self.serene),
                                         (scene_id,step['id'],point,destination))
                    point=destination
            elif step['type']=='transfer':
                destination_scene=step['scene'];destination=tuple(step['position'])
                destination_world=self.scene(destination_scene)
                self.assertTrue(destination_world.can_stand(
                    destination,self.serene.probe_size,self.serene),
                    (destination_scene,step['id'],destination))
                scene_id=destination_scene;point=destination

    def test_select_step_chooses_each_authored_action_and_its_sprite(self):
        choices=(
            ('sort_provisions','sort_provisions','sanctuary_dining',(288,228),'back'),
            ('sort_second_provision_table','sort_provisions','sanctuary_dining',(336,228),'back'),
            ('consult_list','consult_list','sanctuary_dining',(288,116),'back'),
            ('tend_hearth','tend_hearth','sanctuary_dining',(384,110),'back'),
            ('arrange_hall','arrange_hall','sanctuary_hall',(264,228),'back'),
        )
        for step_id,action_id,scene_id,position,facing in choices:
            with self.subTest(action=action_id,step=step_id):
                self.place(step_id,scene_id,position,facing)
                self.assertEqual(self.serene.state,step_id)
                self.assertEqual(self.serene.step['type'],'action')
                self.assertEqual(self.serene.action_id,action_id)
                self.assertEqual(self.serene.facing,facing)
                self.assertEqual(self.serene.state_ms,0)
                self.assertEqual(self.serene.sprite(0).get_size(),(48,48))


if __name__=='__main__':unittest.main()
