"""Actual shared mechanism/actor timing, occlusion, water and scene persistence."""
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

    def test_hand_follows_full_crank_rotation_and_reversed_loaded_ascent(self):
        self.until('well_lower');seen=[]
        for _ in range(8):
            name,frame=self.actor.pose()
            grip=pygame.Vector2(self.actor.animation['poses'][name]['grip'])
            hand=self.actor.position-pygame.Vector2(self.actor.draw_anchor)+pygame.Vector2(self.actor.animation['body_offset'])+grip
            expected=pygame.Vector2(self.well.data['position'])+self.well.data['crank_handles'][self.well.crank_index]
            self.assertEqual(hand,expected)
            seen.append(self.well.crank_index)
            self.game.update(.1,(0,0),False)
        self.assertEqual(seen,list(range(8)))
        self.until('well_raise');start=self.well.bucket_grip.y
        self.game.update(.15,(0,0),False)
        self.assertEqual(self.well.crank_index,7)
        self.assertLess(self.well.bucket_grip.y,start)
        self.assertTrue(self.actor.pose()[0].startswith('well_heavy_left_'))

    def test_shaft_front_rim_hides_bucket_and_crank_stops_during_fill(self):
        self.until('well_fill')
        first=self.well.sprite(0);index=self.well.crank_index
        self.game.update(1,(0,0),False)
        self.assertEqual(self.well.crank_index,index)
        self.assertGreater(self.actor.water_units,0)
        second=self.well.sprite(0)
        for y in range(72,96):
            for x in range(84):
                self.assertEqual(first.get_at((x,y)),self.well.rim.get_at((x,y)))
                self.assertEqual(first.get_at((x,y)),second.get_at((x,y)))

    def test_scene_visit_preserves_active_well_and_continues_same_draw(self):
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

    def test_reservation_and_empty_hook_after_departure(self):
        self.until('well_grip')
        self.assertFalse(self.well.reserve(object()))
        self.assertIs(self.well.owner,self.actor)
        self.assertTrue(self.well.bucket_on_rope)
        self.assertTrue(self.world.can_stand((564,900)))
        self.assertTrue(self.world.can_stand((528,900)))
        self.until('return_to_sanctuary')
        self.assertIsNone(self.well.owner)
        self.assertFalse(self.well.bucket_on_rope)
        self.assertEqual(tuple(self.well.bucket_grip),tuple(self.well.data['hook_grip']))

    def held_grip(self):
        name,frame,pose,key,xy=self.actor.bucket_placement()
        return self.actor.position-pygame.Vector2(self.actor.draw_anchor)+xy+pygame.Vector2(self.actor.animation['buckets'][key]['grip'])

    def test_one_pail_handoffs_match_exactly_and_moves_only_with_hands(self):
        self.until('well_attach')
        for _ in range(108):
            self.assertFalse(self.well.bucket_on_rope)
            name,frame=self.actor.pose()
            expected=self.actor.position+pygame.Vector2(self.actor.animation['poses'][name]['grip'])-pygame.Vector2(12,30)
            self.assertEqual(self.held_grip(),expected)
            self.game.update(1/60,(0,0),False)
        self.assertEqual(self.actor.state,'well_secure')
        self.assertTrue(self.well.bucket_on_rope)
        self.assertEqual(self.held_grip(),pygame.Vector2(self.well.data['position'])+self.well.bucket_grip)
        self.until('well_unhook')
        self.assertFalse(self.well.bucket_on_rope)
        self.assertEqual(self.held_grip(),pygame.Vector2(self.well.data['position'])+self.well.bucket_grip)
        self.assertEqual(self.actor.water_units,6)
        self.until('well_take')
        previous=self.held_grip()
        for _ in range(84):
            if self.actor.state!='well_take':break
            current=self.held_grip()
            self.assertLessEqual(current.distance_to(previous),3)
            self.assertFalse(self.well.bucket_on_rope)
            previous=current;self.game.update(1/60,(0,0),False)

    def test_suspended_bucket_stays_in_one_vertical_column(self):
        self.until('well_lower')
        while self.actor.state in ('well_lower','well_fill','well_raise'):
            self.assertEqual(self.well.bucket_grip.x,self.well.data['hook_grip'][0])
            self.assertTrue(self.well.bucket_on_rope)
            self.game.update(.1,(0,0),False)

    def test_occupied_crank_pauses_before_lowering_then_resumes(self):
        self.until('well_to_crank')
        self.game.player.position.update(self.well.data['operator_position'])
        for _ in range(180):self.game.update(1/60,(0,0),False)
        self.assertEqual(self.actor.state,'well_to_crank')
        self.assertTrue(self.actor.waiting)
        self.assertEqual(self.actor.water_units,0)
        self.assertEqual(tuple(self.well.bucket_grip),tuple(self.well.data['hook_grip']))
        self.game.player.position.update(480,924)
        self.until('well_lower',limit=5)


if __name__=='__main__':unittest.main()
