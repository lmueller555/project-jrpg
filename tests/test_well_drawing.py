"""Centered near-side handoffs, mechanism timing and persistent state."""
import math
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import unittest
import pygame
import main


class WellDrawing(unittest.TestCase):
    def setUp(self):
        self.game=main.Game();self.world=self.game.town
        self.actor=self.world.npcs[1];self.well=self.world.well
        self.game.player.position.update(480,924)
        self.game.update(self.actor.rest_remaining_ms/1000+1/60,(0,0),False)

    def tearDown(self):pygame.quit()

    def until(self,state,limit=50):
        for _ in range(limit*60):
            if self.actor.state==state:return
            self.game.update(1/60,(0,0),False)
        self.fail(f'Waiting for {state}: {self.actor.state}')

    def held_grip(self):
        name,frame,pose,key,xy=self.actor.bucket_placement()
        bucket=self.actor.animation['buckets'][key]
        return (self.actor.position-pygame.Vector2(self.actor.draw_anchor)+xy+
                pygame.Vector2(bucket['grip']))

    def test_near_side_registration_is_centered_with_one_six_pixel_depth_snap(self):
        data=self.well.data;origin=pygame.Vector2(data['position'])
        self.assertEqual(data['shaft_center_x'],40)
        self.assertEqual(data['rope_origin'][0],40)
        self.assertEqual(data['loading_grip'][0],40)
        self.assertEqual(data['shaft_grip'][0],40)
        self.assertEqual(data['lowered_bucket_grip'][0],40)
        self.assertEqual(origin.x+40,526)
        self.assertEqual(data['loading_position'],[526,892])
        self.assertEqual(abs(data['loading_grip'][1]-data['shaft_grip'][1]),6)

        self.until('well_settle')
        self.assertEqual(tuple(self.well.bucket_grip),tuple(data['loading_grip']))
        self.game.update(.4,(0,0),False)
        self.assertEqual(self.actor.state,'well_settle')
        self.assertEqual(tuple(self.well.bucket_grip),tuple(data['shaft_grip']))
        self.until('well_catch')
        self.assertEqual(tuple(self.well.bucket_grip),tuple(data['shaft_grip']))
        self.game.update(.5,(0,0),False)
        self.assertEqual(self.actor.state,'well_catch')
        self.assertEqual(tuple(self.well.bucket_grip),tuple(data['loading_grip']))

    def test_near_side_poses_keep_normal_arm_lengths_and_fixed_body_proportions(self):
        recipe=main.read_json(main.ROOT/'assets/source/characters/npcs/female_02/gardener/recipe.json')
        names=[n for n in recipe['work_poses'] if n.startswith(
            ('well_attach_back_','well_release_back_','well_catch_back_',
             'well_unhook_back','well_take_back_'))]
        self.assertEqual(len(names),27)
        for name in names:
            pose=recipe['work_poses'][name]
            self.assertEqual(pose['direction'],'back')
            self.assertLessEqual(max(abs(v) for v in pose['lean']),2)
            for limb in pose['arms']:
                for a,b in zip(limb,limb[1:]):
                    self.assertLessEqual(math.dist(a,b),7,name)

    def test_one_pail_changes_owner_only_at_registered_matching_handoffs(self):
        origin=pygame.Vector2(self.well.data['position'])
        loading=origin+self.well.data['loading_grip']
        self.until('well_hook')
        self.assertFalse(self.well.bucket_on_rope)
        self.assertEqual(self.held_grip(),loading)
        self.until('well_settle')
        self.assertTrue(self.well.bucket_on_rope)
        self.assertEqual(origin+self.well.bucket_grip,loading)
        self.until('well_catch');self.game.update(.5,(0,0),False)
        name,_=self.actor.pose()
        pose=main.read_json(main.ROOT/'assets/source/characters/npcs/female_02/gardener/recipe.json')['work_poses'][name]
        body_origin=self.actor.position-pygame.Vector2(12,30)
        hands=[body_origin+limb[-1] for limb in pose['arms']]
        self.assertTrue(all(hand.distance_to(loading)<=3 for hand in hands))
        self.until('well_unhook')
        self.assertFalse(self.well.bucket_on_rope)
        self.assertEqual(self.held_grip(),loading)
        self.until('well_take');previous=self.held_grip()
        while self.actor.state=='well_take':
            current=self.held_grip()
            self.assertLessEqual(current.distance_to(previous),3)
            previous=current;self.game.update(1/60,(0,0),False)

    def test_suspended_pail_stays_centered_and_moves_only_vertically(self):
        self.until('well_lower');last=self.well.bucket_grip.y
        while self.actor.state=='well_lower':
            self.assertEqual(self.well.bucket_grip.x,40)
            self.assertGreaterEqual(self.well.bucket_grip.y,last)
            self.assertTrue(self.well.bucket_on_rope)
            last=self.well.bucket_grip.y;self.game.update(.1,(0,0),False)
        self.until('well_raise');last=self.well.bucket_grip.y
        while self.actor.state=='well_raise':
            self.assertEqual(self.well.bucket_grip.x,40)
            self.assertLessEqual(self.well.bucket_grip.y,last)
            self.assertTrue(self.well.bucket_on_rope)
            last=self.well.bucket_grip.y;self.game.update(.1,(0,0),False)

    def test_crank_hand_alignment_and_loaded_reverse_rotation(self):
        self.until('well_lower');seen=[]
        for _ in range(8):
            name,_=self.actor.pose();grip=pygame.Vector2(self.actor.animation['poses'][name]['grip'])
            hand=self.actor.position-pygame.Vector2(12,30)+grip
            expected=pygame.Vector2(self.well.data['position'])+self.well.data['crank_handles'][self.well.crank_index]
            self.assertEqual(hand,expected);seen.append(self.well.crank_index)
            self.game.update(.1,(0,0),False)
        self.assertEqual(seen,list(range(8)))
        self.until('well_raise');start=self.well.bucket_grip.y
        self.game.update(.15,(0,0),False)
        self.assertEqual(self.well.crank_index,7)
        self.assertLess(self.well.bucket_grip.y,start)
        self.assertTrue(self.actor.pose()[0].startswith('well_heavy_left_'))

    def test_rim_hides_shaft_pail_and_roof_never_changes(self):
        source=self.world.image('assets/source/terrain/eldenmere/well/parts/native_structure.png')
        fixed=self.well.fixed
        for y in range(36):
            for x in range(84):self.assertEqual(fixed.get_at((x,y)),source.get_at((x,y)))
        self.until('well_fill');first=self.well.sprite(0);index=self.well.crank_index
        self.game.update(1,(0,0),False);second=self.well.sprite(0)
        self.assertEqual(self.well.crank_index,index)
        self.assertGreater(self.actor.water_units,0)
        for y in range(72,96):
            for x in range(84):
                self.assertEqual(first.get_at((x,y)),self.well.rim.get_at((x,y)))
                self.assertEqual(first.get_at((x,y)),second.get_at((x,y)))
        for y in range(96,112):
            for x in range(84):self.assertEqual(first.get_at((x,y)).a,0)

    def test_scene_visit_preserves_active_draw_and_releases_reservation(self):
        self.until('well_lower');self.game.update(1,(0,0),False)
        before=self.well.bucket_grip.y;time=self.actor.state_ms
        door=next(d for d in self.world.doors if d.data['id']=='home_a')
        self.game.enter(door);self.game.update(.5,(0,0),False)
        self.assertEqual(self.actor.state,'well_lower')
        self.assertGreater(self.actor.state_ms,time)
        self.assertGreater(self.well.bucket_grip.y,before)
        self.game.enter(self.game.world.doors[0])
        self.assertIs(self.world.well,self.well)
        self.assertIs(self.well.owner,self.actor)
        self.until('return_to_sanctuary')
        self.assertIsNone(self.well.owner)
        self.assertEqual(self.actor.water_units,6)

    def test_blocked_loading_and_crank_positions_wait_then_resume(self):
        game=main.Game();actor=game.town.npcs[1];well=game.town.well
        game.player.position.update(well.data['loading_position'])
        game.update(actor.rest_remaining_ms/1000+1/60,(0,0),False)
        for _ in range(35*60):
            game.update(1/60,(0,0),False)
            if actor.waiting:break
        self.assertEqual(actor.state,'to_well');self.assertTrue(actor.waiting)
        self.assertEqual(actor.water_units,0);self.assertIsNone(well.owner)
        game.player.position.update(480,924)
        for _ in range(12*60):
            game.update(1/60,(0,0),False)
            if actor.state=='well_to_crank':break
        game.player.position.update(well.data['operator_position'])
        for _ in range(180):game.update(1/60,(0,0),False)
        self.assertEqual(actor.state,'well_to_crank');self.assertTrue(actor.waiting)
        self.assertTrue(well.bucket_on_rope)


if __name__=='__main__':unittest.main()
