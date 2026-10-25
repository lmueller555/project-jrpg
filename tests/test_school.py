"""School placement, real door travel, classroom access and authored art."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
from collections import deque
import json
import unittest

import pygame
from PIL import Image
import main
from npc_routines import find_path

ROOT=main.ROOT


def read(path):return json.loads(path.read_text())


class EldenmereSchoolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game=main.Game(fullscreen=False,start_on_title=False)
        cls.town=cls.game.town;cls.room=cls.game._scene_by_id('school')
        cls.layout=read(ROOT/'assets/maps/eldenmere/school/layout.json')
        cls.objects=read(ROOT/cls.room.data['source_room'])['objects']
        # Architectural checks need empty landings and do not exercise ambient
        # schedules; their own integration tests cover yielding and ownership.
        cls.game.persistent_npcs.clear();cls.game._routine_worlds.clear()
        cls.game.play_routines.clear();cls.game.block_routines.clear();cls.game.bone_routines.clear()
        for world in cls.game.scenes.values():world.npcs.clear()

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def setUp(self):
        self.game.world=self.town;self.game.player=main.Player(self.town)
        self.game.map_open=False;self.game.transfer_cooldown=0

    def test_school_sits_on_lower_ground_without_moving_existing_landmarks(self):
        world=self.town;footprint=pygame.Rect(600,624,144,96)
        self.assertEqual(self.layout['position'],[576,528])
        self.assertEqual(self.layout['ground_rect'],list(footprint))
        self.assertEqual(self.layout['approach'],[672,738])
        self.assertGreater(footprint.top,384)
        self.assertLess(footprint.right,800)  # Buffer west of the stream bank.
        original=read(ROOT/'assets/maps/eldenmere/terrain_foundation/scene.json')
        for building in original['buildings']:
            self.assertFalse(footprint.colliderect(building['ground_rect_pixels']),building['id'])
        by_id={entity['id']:entity for entity in world.entities}
        expected={'sanctuary':[252,84],'mill':[936,204],'liam_house':[204,384],
                  'well':[486,792],'venn':[1164,576],'home_b':[444,528]}
        for identifier,position in expected.items():self.assertEqual(by_id[identifier]['position'],position)
        self.assertFalse(world.can_stand(footprint.center))
        self.assertTrue(world.can_stand(self.layout['approach']))
        self.assertIn('school',{landmark['id'] for landmark in world.data['landmarks']})
        self.assertEqual(len(world.doors),11)
        self.assertEqual(len(world.data['interior_scenes']),13)

    def test_well_to_school_route_and_entrance_remain_walkable(self):
        start=(600,816);goal=self.layout['approach'];world=self.town
        self.assertTrue(world.can_stand(start))
        self.assertIsNotNone(find_path(world,start,goal,world.probe_size,None))
        door=next(d for d in world.doors if d.data['id']=='school')
        self.assertEqual(door.data['anchor'],[672,726])
        self.assertTrue(world.can_stand(door.data['anchor']))
        self.assertIsNotNone(find_path(world,goal,door.data['anchor'],world.probe_size,None))

    def _walk_through(self,door):
        self.game.player.position.update(pygame.Vector2(door.data['anchor'])+(0,12 if door.data['entry_side']=='north' else -12))
        origin=self.game.world;self.game.update(.5,(0,0),False)
        direction=(0,-1 if door.data['entry_side']=='north' else 1)
        for _ in range(90):
            self.game.update(1/60,direction,False)
            if self.game.world is not origin:return
        self.fail(f'Walk-in did not transfer through {door.data["id"]}')

    def test_proximity_door_and_actual_round_trip_use_distinct_school_scene(self):
        game=self.game;door=next(d for d in self.town.doors if d.data['id']=='school')
        door.progress=0;door.target_open=False
        near=pygame.Vector2(door.data['anchor'])+(0,12)
        game.player.position.update(near);game.update(.2,(0,0),False)
        self.assertEqual(door.state,'opening');self.assertIs(game.world,self.town)
        game.update(.6,(0,0),False);self.assertEqual(door.state,'open')
        game.update(1,(0,0),False);self.assertEqual(door.state,'open')
        game.player.position.update(near+(0,80));game.update(1,(0,0),False)
        self.assertEqual(door.state,'closed')
        self._walk_through(door)
        self.assertIs(game.world,self.room)
        self.assertTrue(self.room.can_stand(game.player.position))
        self.assertEqual(game.player.facing,'back')
        game.update(.3,(0,0),False)
        exit_door=next(d for d in self.room.doors if d.data['id']=='courtyard')
        self._walk_through(exit_door)
        self.assertIs(game.world,self.town)
        self.assertEqual(tuple(game.player.position),tuple(exit_door.data['spawn']))
        self.assertEqual(game.player.facing,'front')
        self.assertTrue(self.town.can_stand(game.player.position))
        self.assertIs(game._scene_by_id('school'),self.room)

    def test_room_has_six_seats_and_reachable_teacher_and_learning_areas(self):
        room=self.room
        self.assertEqual(room.size,(432,384));self.assertEqual(room.data['size_tiles'],[16,12])
        self.assertEqual(room.data['floor_rect'],[24,72,384,288])
        ids={entity['id'] for entity in room.entities}
        self.assertTrue({f'pupil_desk_{i}' for i in range(1,4)}<=ids)
        self.assertTrue({f'pupil_chair_{i}' for i in range(1,7)}<=ids)
        self.assertTrue({'teacher_desk','teacher_chair','writing_board','bookshelf','festival_corner',
                         'village_map','reading_bench','coat_pegs','child_drawings','hearth'}<=ids)
        targets={tuple(p) for p in room.data['destinations'].values()}
        targets.update(tuple(d.data['anchor']) for d in room.doors)
        queue=deque([tuple(room.data['spawn'])]);visited=set(queue);remaining=set(targets)
        while queue and remaining:
            point=queue.popleft();remaining.discard(point)
            for candidate in ((point[0]-2,point[1]),(point[0]+2,point[1]),(point[0],point[1]-2),(point[0],point[1]+2)):
                if candidate not in visited:
                    visited.add(candidate)
                    if room.can_stand(candidate):queue.append(candidate)
        self.assertFalse(remaining)
        for obj in self.objects:
            if obj['id'].startswith(('pupil_desk_','pupil_chair_')):
                self.assertTrue(obj.get('floor_rect'),obj['id'])
                self.assertFalse(room.can_stand(pygame.Rect(obj['floor_rect']).center),obj['id'])
        for y in range(84,343,2):self.assertTrue(room.can_stand((216,y)),y)

    def test_exterior_animation_and_door_patches_match_at_native_scale(self):
        entity=next(e for e in self.town.entities if e['id']=='school')
        self.assertEqual(entity['position'],[576,528]);self.assertEqual(entity['sort_y'],720)
        self.assertEqual(len(entity['surfaces']),18);self.assertEqual(entity['frame_duration_ms'],300)
        self.assertTrue(all(im.get_size()==(192,192) for im in entity['surfaces']))
        self.assertGreater(len({pygame.image.tobytes(im,'RGBA') for im in entity['surfaces']}),1)
        door=next(d for d in self.town.doors if d.data['id']=='school')
        self.assertEqual(len(door.frames),5)
        self.assertEqual(len({pygame.image.tobytes(im,'RGBA') for im in door.frames}),5)
        rect=pygame.Rect(door.data['position'],door.frames[0].get_size())
        rect.move_ip(-entity['position'][0],-entity['position'][1])
        self.assertEqual(rect,pygame.Rect(86,150,20,34))
        self.assertEqual(pygame.image.tobytes(entity['surfaces'][0].subsurface(rect),'RGBA'),pygame.image.tobytes(door.frames[0],'RGBA'))
        for relative in dict.fromkeys(entity['frames']):
            with Image.open(ROOT/relative) as im:self.assertTrue(set(im.convert('RGBA').getchannel('A').tobytes())<={0,255})
        self.assertGreater(len(set(self.room.data['ground_frames'])),1)

    def test_teacher_role_is_registered_without_starting_unapproved_schedules(self):
        self.assertEqual(self.room.data['teacher'],'liam_mother')
        self.assertEqual(self.room.data['npcs'],[])
        family=read(ROOT/'assets/characters/liam_family/family.json')
        mother=next(m for m in family['members'] if m['character']=='liam_mother')
        self.assertEqual(mother['occupation'],'teacher')
        self.assertEqual(mother['role'],'mother')
        self.assertEqual(self.room.data['quests'],[])


if __name__=='__main__':unittest.main()
