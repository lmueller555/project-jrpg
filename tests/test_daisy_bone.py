"""One persistent bone, safe activity handoffs, real pathing and mouth occlusion."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import hashlib
import json
import random
import unittest

import pygame
from PIL import Image
import main


class DaisyBoneTests(unittest.TestCase):
    def setUp(self):
        self.game=main.Game(fullscreen=False,start_on_title=False)
        self.r=self.game.bone_routines[0];self.daisy=self.r.daisy
        self.r._rng=random.Random(7);self.r.cooldown_ms=999999
        self.r.shared.cooldown_ms=999999
        for routine in self.game.block_routines:routine.cooldown_ms=999999
        self.daisy.duration_ms=999999
        self.daisy.cooldowns={'food':999999,'water':999999}
        self.game.player.position.update(430,600)
        self.identity=id(self.r.bone)
        self.seen_bone_states=set()

    def tearDown(self):pygame.quit()

    def tick(self):
        before=self.daisy.position.copy();oldworld=self.r.shared.worlds[self.daisy]
        old_bone_state=self.r.bone['state'];old_bone_position=pygame.Vector2(self.r.bone['position'])
        self.game.update(1/60,(0,0),False)
        self.assertEqual(id(self.r.bone),self.identity)
        self.assertEqual(self.r.bone['id'],'daisy_bone')
        self.assertIn(self.r.bone['state'],('ground','mouth','paws'))
        self.seen_bone_states.add(self.r.bone['state'])
        props=[prop for owner,prop in self.r.home.routine_props if owner is self.r and prop['id']=='daisy_bone']
        self.assertEqual(len(props),1)
        self.assertEqual(self.r.surface_prop_visible(props[0]),self.r.bone['state']=='ground')
        if self.r.bone['state']!=old_bone_state:
            spec=self.r.meta['actions'][self.r.current_action]
            self.assertEqual(self.r.frame_index,spec['contact_frame'])
            mouth=self.daisy.position-pygame.Vector2(self.daisy.draw_anchor)+self.r.current_frame_record['bone_local']
            target=old_bone_position if old_bone_state=='ground' else self.r.bone['position']
            self.assertLess(mouth.distance_to(target),1,(old_bone_state,self.r.bone['state'],tuple(mouth),tuple(target)))
        self.assertEqual(sum(n is self.daisy for w in self.game.scenes.values() for n in w.npcs),1)
        world=self.r.shared.worlds[self.daisy]
        self.assertTrue(world.can_stand(self.daisy.position,self.daisy.probe_size,self.daisy),
                        (self.r.state,tuple(self.daisy.position),self.daisy.state))
        if world is oldworld:self.assertLessEqual(self.daisy.position.distance_to(before),64/60+1e-6)
        if self.r.bone['state']!='ground':self.assertFalse(self.r.shared.active)

    def until(self,predicate,limit=100):
        for i in range(limit*60):
            self.tick()
            if predicate():return i/60
        self.fail((self.r.state,self.r.bone,tuple(self.daisy.position)))

    def test_rug_play_uses_same_bone_through_mouth_paws_and_ground(self):
        r=self.r
        self.assertEqual(r.config['cooldown_ms'],[120000,240000])
        self.assertEqual(r.config['chew_ms'],[15000,25000])
        self.assertEqual(r.bone['state'],'ground')
        self.assertTrue(r.begin('rug',playful=True))
        self.until(lambda:r.completed_cycles==1)
        self.assertEqual(self.seen_bone_states,{'ground','mouth','paws'})
        self.assertEqual(r.state,'cooldown');self.assertEqual(r.bone['state'],'ground')
        self.assertFalse(self.daisy.play_owned)
        self.assertAlmostEqual(self.daisy.position.distance_to(self.daisy.behavior['home']),0)
        self.assertGreaterEqual(r.cooldown_ms,120000);self.assertLessEqual(r.cooldown_ms,240000)

    def test_relocation_persists_on_reentry_and_next_session_finds_that_bone(self):
        r=self.r;start=pygame.Vector2(r.bone['position'])
        point=next(p for p in r.config['drop_points'] if pygame.Vector2(p).distance_to(start)>20)
        self.assertTrue(r.begin('relocate',drop_point=point))
        self.until(lambda:r.completed_cycles==1)
        dropped=pygame.Vector2(r.bone['position'])
        self.assertLess(dropped.distance_to(point),1)
        self.assertGreater(dropped.distance_to(start),20)
        self.assertEqual(r.bone['state'],'ground')
        front=next(d for d in self.game.town.doors if d.data['id']=='liam_house')
        self.assertTrue(self.game.enter(front));self.assertIs(self.game.bone_routines[0],r)
        self.assertEqual(id(r.bone),self.identity)
        self.assertLess(pygame.Vector2(r.bone['position']).distance_to(dropped),1)
        self.game.transfer_cooldown=0
        self.assertTrue(self.game.enter(r.home.doors[0]))
        self.assertEqual(id(r.bone),self.identity)
        self.assertTrue(r.begin('rug',playful=False))
        self.until(lambda:r.bone['state']=='mouth')
        self.assertLess(self.daisy.position.distance_to(dropped),32)
        self.until(lambda:r.completed_cycles==2)
        self.assertEqual(r.bone['state'],'ground')
        self.assertLess(pygame.Vector2(r.bone['position']).distance_to(self.daisy.behavior['home']),36)

    def test_automatic_relocation_chooses_a_different_place_and_can_be_retrieved(self):
        r=self.r;initial=pygame.Vector2(r.bone['position'])
        # Keep nearest-first candidate order: this used to choose the original
        # floor position, picking up the bone only to put it straight back.
        r._rng.shuffle=lambda candidates:None
        self.assertTrue(r.begin('relocate',playful=False))
        self.until(lambda:r.completed_cycles==1)
        dropped=pygame.Vector2(r.bone['position'])
        self.assertGreaterEqual(dropped.distance_to(initial),24-1e-6)
        self.assertEqual(r.bone['state'],'ground')
        self.assertTrue(r.begin('rug',playful=False))
        self.until(lambda:r.bone['state']=='mouth')
        self.assertLess(self.daisy.position.distance_to(dropped),32)
        self.until(lambda:r.completed_cycles==2)
        self.assertEqual(r.bone['state'],'ground')

    def test_blocked_approach_waits_without_teleporting_or_losing_the_ground_bone(self):
        r=self.r;bone=pygame.Vector2(r.bone['position']);self.game.world=r.home
        # The player covers the bone and its short pickup approach.
        self.game.player.position.update(bone+pygame.Vector2(10,1))
        self.assertTrue(r.begin('rug',playful=False))
        for _ in range(180):
            self.tick()
            self.assertEqual(r.bone['state'],'ground')
            self.assertFalse(self.daisy.blocker.colliderect(r.home.probe_rect(self.game.player.position)))
            self.assertLess(pygame.Vector2(r.bone['position']).distance_to(bone),1)
        self.game.player.position.update(230,300)
        self.until(lambda:r.completed_cycles==1)
        self.assertEqual(r.bone['state'],'ground')

    def test_liam_invitation_requires_safe_drop_before_taking_daisy(self):
        r=self.r;self.assertTrue(r.begin('rug',playful=True))
        self.until(lambda:r.bone['state']=='mouth')
        self.assertTrue(r.shared.begin(drink=False))
        self.until(lambda:r.shared.active,limit=30)
        self.assertFalse(r.active);self.assertEqual(r.bone['state'],'ground')
        self.assertTrue(r.home.can_stand(r.bone['position'],(8,4),ignore_npc=self.daisy))
        self.assertTrue(self.daisy.play_owned)
        self.assertIsNone(self.daisy.active_bowl)

    def test_existing_meal_is_not_interrupted_and_release_request_finishes_contact(self):
        r=self.r;self.daisy.begin_activity('food',r.home)
        self.until(lambda:self.daisy.state=='eat',limit=15)
        start=pygame.Vector2(r.bone['position'])
        self.assertFalse(r.begin('rug',playful=False))
        self.assertEqual(r.bone['state'],'ground')
        self.assertLess(pygame.Vector2(r.bone['position']).distance_to(start),1)
        self.until(lambda:self.daisy.state=='rest',limit=30)
        self.assertEqual(self.daisy.bowls['food']['state'],'half_full')
        self.assertTrue(r.begin('rug',playful=True))
        self.until(lambda:r.bone['state']=='mouth')
        r.request_release();r.request_release()
        self.until(lambda:not r.active,limit=20)
        self.assertEqual(r.bone['state'],'ground');self.assertFalse(self.daisy.play_owned)

    def test_food_due_during_final_nudge_rises_and_reserves_bowl_without_a_new_rest(self):
        r=self.r;d=self.daisy
        self.assertTrue(r.begin('rug',playful=True))
        self.until(lambda:r.state=='nudge')
        self.assertEqual(r.bone['state'],'ground')
        d.cooldowns['food']=-1
        seen={r.state}
        for _ in range(6*60):
            self.tick();seen.add(r.state)
            if d.active_bowl=='food':break
        else:self.fail((r.state,d.state,d.duration_ms,d.active_bowl))
        self.assertIn('rise',seen)
        self.assertFalse(r.active);self.assertFalse(d.play_owned)
        self.assertEqual(r.bone['state'],'ground')
        self.assertEqual(d.bowls['food'].get('reserved_by'),d.data['id'])
        self.assertNotEqual(d.state,'rest')

    def test_invalid_drop_locations_never_receive_the_bone(self):
        r=self.r
        for invalid in ((0,1),(60,239),(164,277),(252,305)):
            with self.subTest(point=invalid):
                completed=r.completed_cycles
                try:accepted=r.begin('relocate',drop_point=invalid)
                except ValueError:continue
                if not accepted:
                    self.assertFalse(r.active);continue
                self.until(lambda:r.completed_cycles>completed)
                self.assertGreater(pygame.Vector2(r.bone['position']).distance_to(invalid),4)
                self.assertEqual(r.bone['state'],'ground')
        building=self.game.block_routines[0]
        building.state='admire'
        self.assertFalse(r.valid_drop((110,201)))
        building.state='cooldown'
        building.blocks[1]['state']='forgotten'
        self.assertFalse(r.valid_drop((116,201)))

    def test_four_frame_sources_carry_registration_and_back_occlusion(self):
        root=main.ROOT;folder=root/'assets/characters/daisy/bone_play'
        meta=json.loads((folder/'animations.json').read_text())
        for name,spec in meta['actions'].items():
            with self.subTest(action=name):
                self.assertEqual(len(spec['frames']),4);unique=set()
                for record in spec['frames']:
                    body=Image.open(root/record['file']).convert('RGBA')
                    overlay=Image.open(root/record['bone_file']).convert('RGBA')
                    self.assertEqual(body.size,(64,48));self.assertEqual(overlay.size,(64,48))
                    self.assertLessEqual(set(body.getchannel('A').tobytes()),{0,255})
                    self.assertLessEqual(set(overlay.getchannel('A').tobytes()),{0,255})
                    unique.add(body.tobytes()+overlay.tobytes())
                    for im,key in ((body,'layers_from_repo_root'),(overlay,'bone_layers_from_repo_root')):
                        rebuilt=Image.new('RGBA',im.size)
                        for path in record[key]:rebuilt.alpha_composite(Image.open(root/path).convert('RGBA'))
                        self.assertEqual(rebuilt.tobytes(),im.tobytes())
                    self.assertTrue(0<=record['bone_local'][0]<64 and 0<=record['bone_local'][1]<48)
                self.assertEqual(len(unique),4)
        for direction in ('front','left','right','back'):
            spec=meta['actions'][f'carry_walk_{direction}']
            native_folder=root/f'assets/characters/daisy/walk_{direction}'
            native=json.loads((native_folder/'animation.json').read_text())
            for record,original in zip(spec['frames'],native['frames']):
                padded=Image.new('RGBA',(64,48));padded.alpha_composite(Image.open(native_folder/original['file']).convert('RGBA'),(16,12))
                self.assertEqual(Image.open(root/record['file']).convert('RGBA').tobytes(),padded.tobytes())
                if direction=='back':
                    self.assertFalse(record['bone_visible'])
                    self.assertIsNone(Image.open(root/record['bone_file']).convert('RGBA').getbbox())
        for path,sha in meta['approved_png_sha256'].items():
            self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(),sha)
        pack=json.loads((root/'assets/terrain/eldenmere/liam_home/bone/bone.json').read_text())
        self.assertGreaterEqual(len(pack['variants']),3)
        for spec in pack['variants'].values():
            self.assertTrue((root/spec['image']).is_file())


if __name__=='__main__':unittest.main()
