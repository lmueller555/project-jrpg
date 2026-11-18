"""Real pathing, feeding, persistence and authored mouth/bowl registration."""
import os
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
from collections import deque
import hashlib
import json
from pathlib import Path
import random
import unittest

import pygame
from PIL import Image
import main
from npc_routines import find_path

ROOT=main.ROOT


def read(path):return json.loads(path.read_text())


class DaisyRoutineTests(unittest.TestCase):
    def setUp(self):
        self.game=main.Game(fullscreen=False,start_on_title=False)
        self.world=self.game._scene_by_id('liam_house')
        self.actor=next(n for n in self.world.npcs if n.data['id']=='daisy')
        self.actor._rng=random.Random(4)

    def tearDown(self):pygame.quit()

    def until(self,predicate,limit=60,player=None):
        for i in range(int(limit*60)):
            before=self.actor.position.copy()
            self.actor.update(1/60,self.world,player)
            self.assertLessEqual(self.actor.position.distance_to(before),self.actor.speed/60+1e-6)
            self.assertTrue(self.world.can_stand(self.actor.position,self.actor.probe_size,self.actor))
            if predicate():return i/60
        self.fail((self.actor.state,tuple(self.actor.position),list(self.actor.events)[-5:]))

    def visit(self,kind):
        self.actor.begin_activity(kind,self.world)
        return self.until(lambda:self.actor.state=='rest',limit=45)

    def test_initial_rest_and_production_timing_and_paths(self):
        a=self.actor;b=a.behavior
        self.assertEqual(a.state,'rest');self.assertEqual(tuple(a.position),(108,282))
        self.assertEqual(b['speed'],36)
        for key,bounds in [('rest_ms',[45000,90000]),('wander_ms',[20000,40000]),('pause_ms',[2000,5000]),
                           ('food_cooldown_ms',[120000,240000]),('water_cooldown_ms',[90000,180000])]:
            self.assertEqual(b[key],bounds)
        for point in b['wander_points']+[v['station'] for v in b['bowls'].values()]+[v['clear'] for v in b['bowls'].values()]:
            self.assertIsNotNone(find_path(self.world,a.position,point,a.probe_size,a),point)
        self.assertTrue(all(n.data['kind']=='stationary' for n in self.world.npcs if n.data['id'] not in ('liam','daisy')))
        self.assertNotIn('daisy',self.game.social.profiles)

    def test_wander_stands_walks_pauses_and_settles_without_leaving_room(self):
        a=self.actor;identity=id(a);a.begin_activity('wander',self.world)
        seen=set();positions=set()
        for _ in range(60*90):
            a.update(1/60,self.world)
            seen.add(a.state);positions.add((round(a.position.x),round(a.position.y)))
            self.assertTrue(self.world.can_stand(a.position,a.probe_size,a))
            if a.state=='rest':break
        self.assertTrue({'stand_up','walk','pause','settle_down','rest'}<=seen)
        self.assertGreater(len(positions),50)
        self.assertEqual(a.completed_wanders,1)
        self.assertGreaterEqual(a.wander_elapsed,20000)
        self.assertEqual(tuple(a.position),tuple(a.behavior['home']))
        self.assertEqual(id(a),identity);self.assertIn(a,self.world.npcs)
        self.assertNotIn(a,self.game.town.npcs)

    def test_expired_cooldowns_automatically_select_a_bowl_after_rest(self):
        a=self.actor;a.duration_ms=100;a.cooldowns={'food':999999,'water':-100}
        a.update(.2,self.world)
        self.assertEqual(a.state,'stand_up');self.assertEqual(a.activity,'water')
        self.until(lambda:a.state=='rest')
        self.assertEqual(a.bowls['water']['state'],'half_full')
        self.assertEqual(a.bowls['food']['state'],'full')
        self.assertGreater(a.cooldowns['water'],80000)
        self.assertGreaterEqual(a.duration_ms,45000);self.assertLessEqual(a.duration_ms,90000)

    def test_time_chunking_keeps_movement_and_consumption_consistent(self):
        other=main.World(self.world.path,self.game.town._images)
        b=next(n for n in other.npcs if n.data['id']=='daisy')
        for a,w in ((self.actor,self.world),(b,other)):
            a._rng=random.Random(7);a.begin_activity('food',w)
        for _ in range(180):self.actor.update(.1,self.world)
        for _ in range(1080):b.update(1/60,other)
        self.assertEqual(self.actor.state,b.state)
        self.assertEqual(tuple(self.actor.position),tuple(b.position))
        self.assertEqual(self.actor.bowls['food']['state'],b.bowls['food']['state'])
        self.assertEqual(self.actor.completed_visits,b.completed_visits)

    def test_each_food_or_water_visit_consumes_exactly_one_level(self):
        a=self.actor
        for kind in ('food','water'):
            for expected in ('half_full','empty'):
                self.visit(kind)
                self.assertEqual(a.bowls[kind]['state'],expected)
                self.assertNotIn('reserved_by',a.bowls[kind])
            self.assertEqual(a.completed_visits[kind],2)
        changes=[e for e in a.events if e['type']=='consumed']
        self.assertEqual(len(changes),4)
        self.assertEqual([e['to'] for e in changes],['half_full','empty']*2)

    def test_empty_bowls_are_inspected_without_chewing_lapping_or_consumption(self):
        a=self.actor
        for kind in ('food','water'):
            self.assertTrue(self.world.set_entity_state(a.bowls[kind]['id'],'empty'))
            a.events.clear();self.visit(kind)
            states=[e.get('to') for e in a.events if e['type']=='state']
            self.assertIn('inspect',states)
            self.assertNotIn('eat',states);self.assertNotIn('drink',states)
            self.assertFalse(any(e['type']=='consumed' for e in a.events))
            self.assertEqual(a.bowls[kind]['state'],'empty')

    def test_reservation_blocks_refill_until_daisy_steps_away(self):
        a=self.actor;a.begin_activity('food',self.world)
        self.until(lambda:a.state=='eat')
        bowl=a.bowls['food']
        self.assertEqual(bowl['reserved_by'],'daisy')
        self.assertFalse(self.world.set_entity_state(bowl['id'],'empty','liam'))
        self.assertEqual(bowl['state'],'full')
        self.until(lambda:a.state=='rest')
        self.assertTrue(self.world.set_entity_state(bowl['id'],'full','liam'))
        self.assertEqual(bowl['state'],'full')
        with self.assertRaises(ValueError):self.world.set_entity_state(bowl['id'],'unknown')

    def test_player_blocking_station_causes_waiting_without_teleport_or_consumption(self):
        a=self.actor;station=a.behavior['bowls']['food']['station']
        blocker=self.world.probe_rect(station)
        a.begin_activity('food',self.world)
        before=a.position.copy()
        for _ in range(180):a.update(1/60,self.world,blocker)
        self.assertEqual(a.bowls['food']['state'],'full')
        self.assertEqual(a.position,before)
        self.assertTrue(a.waiting)
        self.until(lambda:a.state=='rest')
        self.assertEqual(a.bowls['food']['state'],'half_full')

    def test_offscreen_update_and_exit_reentry_preserve_actor_and_bowl_state(self):
        a=self.actor;identity=id(a)
        self.assertIsNot(self.game.world,self.world)
        a.begin_activity('water',self.world)
        for _ in range(180):self.game.update(.1,(0,0),False)
        self.assertEqual(a.bowls['water']['state'],'half_full')
        self.assertIs(self.game._scene_by_id('liam_house'),self.world)
        front=next(d for d in self.game.town.doors if d.data['id']=='liam_house')
        self.assertTrue(self.game.enter(front))
        self.assertEqual(id(next(n for n in self.game.world.npcs if n.data['id']=='daisy')),identity)
        self.game.transfer_cooldown=0;self.assertTrue(self.game.enter(self.world.doors[0]))
        self.game.transfer_cooldown=0;self.assertTrue(self.game.enter(front))
        self.assertEqual(a.bowls['water']['state'],'half_full')
        self.assertEqual(sum(n is a for w in self.game.scenes.values() for n in w.npcs),1)

    def test_authored_four_frame_actions_and_sources_preserve_approved_art(self):
        a=self.actor;meta=a.animation;palette=read(ROOT/'assets/characters/daisy/palette.json')
        colors={tuple(bytes.fromhex(c[1:]))+(255,) for ramp in palette['materials'].values() for c in ramp}
        colors.update(tuple(bytes.fromhex(c[1:]))+(255,) for c in palette['eyes'].values())
        colors.add(tuple(bytes.fromhex(meta['tongue_color'][1:]))+(255,))
        for action,spec in meta['actions'].items():
            self.assertEqual(len(spec['frames']),4)
            self.assertEqual(spec['duration_ms'],sum(f['duration_ms'] for f in spec['frames']))
            unique=set()
            for record in spec['frames']:
                image=Image.open(ROOT/record['file']).convert('RGBA');unique.add(image.tobytes())
                self.assertEqual(image.size,(64,48));self.assertEqual(set(image.getchannel('A').tobytes()),{0,255})
                self.assertLessEqual(image.getbbox()[3],47)
                self.assertTrue(all(not p[3] or p in colors for p in getattr(image,'get_flattened_data',image.getdata)()))
                rebuilt=Image.new('RGBA',image.size)
                for path in record['layers_from_repo_root']:rebuilt.alpha_composite(Image.open(ROOT/path).convert('RGBA'))
                self.assertEqual(rebuilt.tobytes(),image.tobytes())
            self.assertEqual(len(unique),4,action)
        for path,sha in meta['approved_png_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),sha)

    def test_contact_landmarks_meet_full_and_half_contents_and_front_rim_occludes(self):
        a=self.actor;pack=read(ROOT/'assets/terrain/eldenmere/liam_home/bowls/bowls.json')
        masks=[Image.open(ROOT/'assets/terrain/eldenmere/liam_home/bowls'/pack[key]).convert('L') for key in ('content_mask','half_content_mask')]
        for kind,action in (('food','eat'),('water','drink')):
            station=pygame.Vector2(a.behavior['bowls'][kind]['station']);bowl=a.bowls[kind]
            for record in a.animation['actions'][action]['frames']:
                if not record['contact']:continue
                mouth=station-pygame.Vector2(a.draw_anchor)+record['mouth_local']
                relative=mouth-pygame.Vector2(bowl['position'])
                for mask in masks:self.assertTrue(mask.getpixel((round(relative.x),round(relative.y))),(kind,record))
            a.begin_activity(kind,self.world);self.until(lambda:a.state==action)
            self.game.player.position.update(230,300)
            target=pygame.Surface(main.VIEW_SIZE);camera=(-24,16)
            self.world.draw(target,camera,self.game.player,0)
            # Every foreground lip pixel is the exact same wood after the head
            # is drawn. Contents pixels remain available for mouth/tongue contact.
            for y in range(24):
                for x in range(24):
                    color=a.lip.get_at((x,y))
                    if color.a:
                        point=(bowl['position'][0]+x-camera[0],bowl['position'][1]+y-camera[1])
                        self.assertEqual(target.get_at(point),color)
            self.until(lambda:a.state=='rest')


if __name__=='__main__':unittest.main()
