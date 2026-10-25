"""Stationary household, no social actions, and a walkable rug beneath Daisy."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

from collections import deque
from pathlib import Path
import json
import unittest

import pygame
from PIL import Image
import main


def read(path):return json.loads(path.read_text())


class LiamHouseholdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game=main.Game(fullscreen=False,start_on_title=False)
        cls.room=cls.game._scene_by_id('liam_house')
        cls.recipe=read(main.ROOT/'assets/maps/eldenmere/liam_house/house.json')

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def setUp(self):
        self.game.world=self.room;self.game.player=main.Player(self.game.town)
        self.game.player.position.update(self.room.data['spawn'])
        self.game.map_open=False;self.game.transfer_cooldown=0

    def test_exactly_four_stationary_residents_load_once_and_stay_home(self):
        actors=self.room.npcs
        self.assertEqual([n.data['id'] for n in actors],['liam','liam_mother','liam_father','daisy'])
        self.assertTrue(all(isinstance(n,main.StationaryNPC) for n in actors))
        self.assertIs(self.game._scene_by_id('liam_house'),self.room)
        self.assertEqual([n.data['id'] for n in self.game.persistent_npcs],['mother_serene','tomas'])
        before=[(id(n),tuple(n.position),n.sprite(0)) for n in actors]
        for i in range(10):self.game.update(.5,(0,0),False)
        self.assertEqual(before,[(id(n),tuple(n.position),n.sprite(999999)) for n in actors])
        for actor in actors:
            self.assertTrue(self.room.can_stand(actor.position,actor.data['probe_size'],ignore_npc=actor))
            self.assertNotIn(actor,self.game.town.npcs)

    def test_no_routines_dialogue_or_conversation_lock(self):
        for actor in self.room.npcs:
            self.assertFalse({'routine','behavior','animation'}&actor.data.keys())
            self.assertFalse(hasattr(actor,'request_conversation'))
            self.assertNotIn(actor.data['id'],self.game.social.profiles)
            # At a close facing approach, proximity cannot request dialogue.
            self.game.player.position.update(actor.position-pygame.Vector2(28,0))
            self.game.player.facing='right'
            self.game.social.update((1,0))
            self.assertFalse(self.game.social.locked)

    def test_residents_have_solid_footprints_and_player_cannot_walk_through(self):
        mother=next(n for n in self.room.npcs if n.data['id']=='liam_mother')
        self.assertFalse(self.room.can_stand(mother.position))
        self.game.player.position.update(280,170)
        self.assertTrue(self.room.can_stand(self.game.player.position))
        self.game.player.update((1,0),1,self.room)
        self.assertLess(self.game.player.position.x,mother.position.x)
        self.assertFalse(self.room.probe_rect(self.game.player.position).colliderect(mother.blocker))
        self.assertTrue(self.room.can_stand(self.game.player.position))

    def test_entry_exit_and_every_furniture_access_remain_reachable_with_residents(self):
        start=tuple(self.room.data['spawn']);queue=deque([start]);visited={start}
        targets={tuple(p) for p in self.room.data['destinations'].values()}
        targets.update(tuple(d.data['anchor']) for d in self.room.doors)
        remaining=set(targets)
        while queue and remaining:
            point=queue.popleft();remaining.discard(point);x,y=point
            for candidate in ((x-2,y),(x+2,y),(x,y-2),(x,y+2)):
                if candidate not in visited:
                    visited.add(candidate)
                    if self.room.can_stand(candidate):queue.append(candidate)
        self.assertFalse(remaining)

    def test_daisy_lies_on_a_nonblocking_floor_rug_with_correct_depth(self):
        rug=self.recipe['rug'];daisy=next(n for n in self.room.npcs if n.data['id']=='daisy')
        entity=next(e for e in self.room.entities if e['id']=='daisy_rug')
        self.assertLess(entity['sort_y'],0)
        self.assertFalse(rug['solid'])
        self.assertEqual(tuple(daisy.position),tuple(self.recipe['daisy_rest_space']))
        self.assertTrue(self.room.can_stand(daisy.position,ignore_npc=daisy))
        r=pygame.Rect(rug['position'],rug['frame_size'])
        origin=daisy.position-pygame.Vector2(daisy.draw_anchor)
        self.assertTrue(r.contains(daisy.sprite(0).get_bounding_rect().move(origin)))
        self.game.player.position.update(214,270)
        target=pygame.Surface(main.VIEW_SIZE)
        camera=(-24,16);self.room.draw(target,camera,self.game.player,0)
        # This white native forepaw must be drawn above the woven rug.
        native=(8,34);pixel=daisy.sprite(0).get_at(native)
        self.assertEqual(pixel.a,255)
        world=origin+native
        self.assertEqual(target.get_at((round(world.x)-camera[0],round(world.y)-camera[1])),pixel)

    def test_new_pixel_assets_retain_palette_face_and_reconstruct_from_source_parts(self):
        dogdir=main.ROOT/'assets/characters/daisy/lying_left';pose=read(dogdir/'pose.json')
        dog=Image.open(dogdir/pose['image']).convert('RGBA')
        idle=Image.open(main.ROOT/'assets/characters/daisy/idle_left.png').convert('RGBA')
        palette=read(main.ROOT/'assets/characters/daisy/palette.json')
        allowed={tuple(bytes.fromhex(c[1:]))+(255,) for ramp in palette['materials'].values() for c in ramp}
        allowed.update(tuple(bytes.fromhex(c[1:]))+(255,) for c in palette['eyes'].values())
        self.assertEqual(dog.size,(40,36));self.assertEqual(dog.getbbox()[3],35)
        self.assertLess(dog.getbbox()[3]-dog.getbbox()[1],23)
        self.assertEqual(set(dog.getchannel('A').tobytes()),{0,255})
        self.assertTrue(all(not p[3] or p in allowed for p in getattr(dog,'get_flattened_data',dog.getdata)()))
        for y in range(12,21):
            for x in range(1,9):
                p=idle.getpixel((x,y))
                if p[3]:self.assertEqual(dog.getpixel((x+4,y+6)),p)
        self.assertGreater(list(getattr(dog,'get_flattened_data',dog.getdata)()).count((37,39,43,255)),5)
        rugdir=main.ROOT/'assets/terrain/eldenmere/liam_home';rug=read(rugdir/'rug.json')
        for meta,directory in ((pose,dogdir),(rug,rugdir)):
            actual=Image.open(directory/meta['image']).convert('RGBA')
            merged=Image.new('RGBA',actual.size)
            for path in meta['layers_from_repo_root']:merged.alpha_composite(Image.open(main.ROOT/path).convert('RGBA'))
            self.assertEqual(merged.tobytes(),actual.tobytes())
            self.assertEqual(set(actual.getchannel('A').tobytes()),{0,255})

    def test_exit_and_reentry_reuse_the_same_stationary_household(self):
        identities=[id(n) for n in self.room.npcs]
        exit_door=self.room.doors[0]
        self.assertTrue(self.game.enter(exit_door))
        self.assertIs(self.game.world,self.game.town)
        self.game.transfer_cooldown=0
        front=next(d for d in self.game.town.doors if d.data['id']=='liam_house')
        front.force_open()
        self.assertTrue(self.game.enter(front))
        self.assertIs(self.game.world,self.room)
        self.assertEqual(identities,[id(n) for n in self.room.npcs])
        self.assertTrue(self.room.can_stand(self.game.player.position))


if __name__=='__main__':unittest.main()
