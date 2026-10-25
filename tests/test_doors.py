"""Proximity doors, actual walk-in transfers and every furnished room's access."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

from collections import deque
from pathlib import Path
import unittest

import pygame
import main


class BuildingDoors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.game=main.Game(fullscreen=False,start_on_title=False)

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def setUp(self):
        self.game.world=self.game.town
        self.game.player=main.Player(self.game.town)
        self.game.transfer_cooldown=0
        self.game.elapsed_ms=0
        self.game.map_open=False
        # Door geometry/transfer checks need empty landings. Persistent NPC
        # schedules otherwise continue between tests and can occupy a doorway
        # as more buildings are exercised. Routine tests cover NPC yielding.
        self.game.persistent_npcs.clear()
        self.game._routine_worlds.clear()
        for scene in self.game.scenes.values():
            scene.npcs.clear()
            for door in scene.doors:door.progress=0;door.target_open=False
        pygame.event.clear()

    def approach_and_enter(self,door):
        self.game.player.position.update(pygame.Vector2(door.data['anchor'])+(0,12 if door.data['entry_side']=='north' else -12))
        before=self.game.world
        self.game.update(.5,(0,0),False)
        direction=(0,-1 if door.data['entry_side']=='north' else 1)
        for _ in range(90):
            self.game.update(1/60,direction,False)
            if self.game.world is not before:return
        self.fail(f'Walk-in did not transfer through {door.data["id"]}')

    def test_all_ten_doors_animate_hold_close_and_reverse(self):
        self.assertEqual(len(self.game.town.doors),10)
        for door in self.game.town.doors:
            with self.subTest(door=door.data['id']):
                self.assertEqual(len(door.frames),5)
                near=pygame.Vector2(door.data['anchor'])+(0,12)
                door.update(near,.2);self.assertEqual(door.state,'opening')
                door.update(near,.5);self.assertEqual(door.state,'open')
                opened=door.image()
                door.update(near,2);self.assertIs(door.image(),opened)
                door.update(near+(0,80),.1);self.assertEqual(door.state,'closing')
                progress=door.progress
                door.update(near,.05);self.assertGreater(door.progress,progress)
                self.assertEqual(door.state,'opening')
                door.update(None,1);self.assertEqual(door.state,'closed')
                self.assertNotEqual(pygame.image.tobytes(door.frames[0],'RGBA'),pygame.image.tobytes(door.frames[4],'RGBA'))

    def test_proximity_hysteresis_and_front_side_only(self):
        door=self.game.town.doors[0];x,y=door.data['anchor']
        door.update((x,y-20),1);self.assertEqual(door.state,'closed')
        door.update((x,y+31),1);self.assertEqual(door.state,'closed')
        door.update((x,y+29),1);self.assertEqual(door.state,'open')
        door.update((x,y+37),1);self.assertEqual(door.state,'open')
        door.update((x,y+39),1);self.assertEqual(door.state,'closed')

    def test_proximity_alone_does_not_enter_and_closed_door_waits(self):
        door=self.game.town.doors[0]
        self.game.player.position.update(pygame.Vector2(door.data['anchor'])+(0,12))
        self.game.update(1,(0,0),False)
        self.assertEqual(door.state,'open');self.assertIs(self.game.world,self.game.town)
        door.progress=0;door.target_open=False
        self.game.player.position.update(door.data['anchor'])
        self.game.update(.1,(0,-1),False)
        self.assertIs(self.game.world,self.game.town)
        self.assertEqual(door.state,'opening')
        self.game.update(.3,(0,-1),False)
        self.assertEqual(self.game.world.data['id'],'sanctuary_hall')

    def test_every_exterior_enters_distinct_interior_and_returns_to_same_door(self):
        for door in self.game.town.doors:
            with self.subTest(door=door.data['id']):
                self.game.world=self.game.town;self.game.transfer_cooldown=0
                self.approach_and_enter(door)
                self.assertEqual(self.game.world.path,(main.ROOT/door.data['destination']).resolve())
                self.assertTrue(self.game.world.can_stand(self.game.player.position))
                self.assertEqual(self.game.player.facing,'back')
                interior=self.game.world
                self.game.update(.8,(0,0),False)
                self.assertIs(self.game.world,interior)
                exit_door=next(d for d in interior.doors if d.data['id']=='courtyard')
                self.approach_and_enter(exit_door)
                self.assertIs(self.game.world,self.game.town)
                self.assertEqual(self.game.player.position,pygame.Vector2(exit_door.data['spawn']))
                self.assertTrue(self.game.world.can_stand(self.game.player.position))
                self.assertEqual(self.game.player.facing,'front')
                self.assertEqual(door.state,'open')
                self.game.update(.8,(0,0),False)
                self.assertIs(self.game.world,self.game.town)
                for _ in range(60):self.game.update(1/60,(0,1),False)
                self.game.update(.5,(0,0),False)
                self.assertEqual(door.state,'closed')

    def test_sanctuary_bedroom_and_dining_links_work_both_ways(self):
        sanctuary=next(d for d in self.game.town.doors if d.data['id']=='sanctuary')
        self.approach_and_enter(sanctuary)
        hall=self.game.world
        for name in ('bedroom','dining'):
            self.game.transfer_cooldown=0
            door=next(d for d in hall.doors if d.data['id']==name)
            self.approach_and_enter(door)
            self.assertEqual(self.game.world.data['id'],'sanctuary_'+name)
            self.game.update(.5,(0,0),False)
            self.approach_and_enter(self.game.world.doors[0])
            self.assertIs(self.game.world,hall)
            self.assertEqual(self.game.player.facing,'front')

    def test_all_twelve_rooms_have_reachable_exits_and_furnishings(self):
        scenes=self.game.town.data['interior_scenes']
        self.assertEqual(len(scenes),12)
        for name,path in scenes.items():
            with self.subTest(room=name):
                world=main.World(main.ROOT/path,self.game.town._images)
                self.assertTrue(all(n['kind'] in ('stationary','daisy_routine') for n in world.data['npcs']))
                self.assertEqual(world.data['quests'],[])
                start=tuple(world.data['spawn']);self.assertTrue(world.can_stand(start))
                targets={tuple(d.data['anchor']) for d in world.doors}
                targets.update(tuple(p) for p in world.data['destinations'].values())
                queue=deque([start]);seen={start};remaining=set(targets)
                while queue and remaining:
                    point=queue.popleft();remaining.discard(point);x,y=point
                    for candidate in ((x-2,y),(x+2,y),(x,y-2),(x,y+2)):
                        if candidate in seen:continue
                        seen.add(candidate)
                        if world.can_stand(candidate):queue.append(candidate)
                self.assertFalse(remaining,(name,remaining))
                fx,fy,fw,fh=world.data['floor_rect']
                for point in [(0,0),(fx,fy+24),(fx+fw,fy+24),(fx+24,fy),(fx+24,fy+fh)]:
                    self.assertFalse(world.can_stand(point))
                for record in world.entities:
                    self.assertTrue(all((main.ROOT/p).is_file() for p in record['frames']))

    def test_interior_map_and_small_room_centering(self):
        self.approach_and_enter(next(d for d in self.game.town.doors if d.data['id']=='elira'))
        self.game.draw()
        self.assertLess(main.camera_for(self.game.player.position,self.game.world.size)[0],0)
        self.assertEqual(self.game.canvas.get_at((0,200))[:3],(36,48,45))
        before=self.game.player.position.copy()
        self.game.map_open=True;self.game.update(.1,(1,0),True);self.game.draw()
        self.assertEqual(self.game.player.position,before)
        self.assertEqual(self.game.world.data['id'],'elira')
        self.assertEqual(self.game.exterior_position,pygame.Vector2(next(d for d in self.game.town.doors if d.data['id']=='elira').data['anchor']))


if __name__=='__main__':unittest.main()
