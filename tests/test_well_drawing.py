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
        self.game=main.Game(fullscreen=False);self.world=self.game.town
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

    def test_handoffs_snap_between_concealed_hands_and_visible_top_winch(self):
        data=self.well.data;origin=pygame.Vector2(data['position'])
        self.assertEqual(data['shaft_center_x'],40)
        self.assertEqual(data['rope_origin'][0],40)
        self.assertEqual(data['hook_tip'][0],40)
        self.assertEqual(data['loading_grip'][0],40)
        self.assertEqual(data['parked_bucket_grip'][0],40)
        self.assertEqual(data['lowered_bucket_grip'][0],40)
        self.assertEqual(origin.x+40,526)
        self.assertEqual(data['loading_position'],[526,892])
        self.assertEqual(data['hook_tip'][1]-data['hook_mount'][1],3)
        self.assertEqual(data['parked_bucket_grip'][1]-data['hook_tip'][1],2)
        self.assertEqual(abs(data['loading_grip'][1]-data['parked_bucket_grip'][1]),31)
        self.assertEqual(data['snap_pixels'],31)
        self.assertEqual(data['settle_bounce_pixels'],1)

        self.until('well_settle')
        self.assertEqual(tuple(self.well.bucket_grip),tuple(data['parked_bucket_grip']))
        self.until('well_catch')
        self.assertEqual(tuple(self.well.bucket_grip),tuple(data['parked_bucket_grip']))
        self.game.update(.5,(0,0),False)
        self.assertEqual(self.actor.state,'well_catch')
        self.assertEqual(tuple(self.well.bucket_grip),tuple(data['loading_grip']))

    def test_idle_hook_is_retracted_beneath_windlass_with_no_long_rope(self):
        data=self.well.data
        baseline=self.well.fixed.copy();baseline.blit(self.well.rim,(0,0))
        idle=self.well.sprite(0)
        mount=data['hook_mount'][1];tip=data['hook_tip'][1]
        self.assertEqual(tip-mount,3)
        changed=[]
        for y in range(mount,tip+1):
            for x in range(data['hook_tip'][0]-1,data['hook_tip'][0]+4):
                if idle.get_at((x,y))!=baseline.get_at((x,y)):changed.append((x,y))
        self.assertTrue(changed)
        for y in range(tip+1,72):
            for x in range(data['hook_tip'][0]-3,data['hook_tip'][0]+4):
                self.assertEqual(idle.get_at((x,y)),baseline.get_at((x,y)),(x,y))

    def test_rope_connector_exists_only_while_well_owns_attached_pail(self):
        baseline=self.well.fixed.copy();baseline.blit(self.well.rim,(0,0))
        def set_state(state,progress=0):
            if state=='idle':
                self.well.owner=None;return
            self.well.owner=self.actor
            self.actor.step_index=next(i for i,s in enumerate(self.actor.steps) if s['id']==state)
            self.actor.state_ms=self.well.data['phases_ms'].get(state,1)*progress
        for state in ('idle','well_attach','well_hook','well_unhook','well_take'):
            set_state(state,.5)
            self.assertFalse(self.well.rope_deployed,state)
            self.assertEqual(self.well.sprite(0).get_at((40,60)),baseline.get_at((40,60)),state)
        for state in ('well_settle','well_to_crank','well_grip','well_lower','well_fill',
                      'well_raise','well_lock','well_to_loading'):
            set_state(state,.5)
            self.assertTrue(self.well.rope_deployed,state)
            self.assertNotEqual(self.well.sprite(0).get_at((40,60)),baseline.get_at((40,60)),state)
        set_state('well_catch',.25)
        self.assertTrue(self.well.rope_deployed)
        self.assertNotEqual(self.well.sprite(0).get_at((40,60)),baseline.get_at((40,60)))
        set_state('well_catch',.75)
        self.assertFalse(self.well.rope_deployed)
        self.assertEqual(self.well.sprite(0).get_at((40,60)),baseline.get_at((40,60)))

    def test_top_pail_settles_one_pixel_then_rope_follows_its_descent_and_ascent(self):
        self.well.owner=self.actor
        def grips(state,progresses):
            self.actor.step_index=next(i for i,s in enumerate(self.actor.steps) if s['id']==state)
            duration=self.well.data['phases_ms'][state]
            values=[]
            for progress in progresses:
                self.actor.state_ms=duration*progress
                values.append(tuple(self.well.bucket_grip))
                self.assertEqual(self.well.rope_end,self.well.bucket_grip)
            return values
        parked=tuple(self.well.data['parked_bucket_grip']);bounce=(parked[0],parked[1]+1)
        self.assertEqual(grips('well_settle',(0,.3,.6)),[parked,bounce,parked])
        lowered=grips('well_lower',(0,.25,.5,.75,1))
        self.assertEqual(lowered[0],parked)
        self.assertEqual(lowered[-1],tuple(self.well.data['lowered_bucket_grip']))
        self.assertTrue(all(a[1]<b[1] for a,b in zip(lowered,lowered[1:])))
        raised=grips('well_raise',(0,.25,.5,.75,1))
        self.assertEqual(raised,list(reversed(lowered)))

    def test_parked_pail_is_fully_visible_then_rim_masks_its_descent(self):
        self.well.owner=self.actor
        baseline=self.well.fixed.copy();baseline.blit(self.well.rim,(0,0))
        index=next(i for i,s in enumerate(self.actor.steps) if s['id']=='well_lower')
        self.actor.step_index=index
        def visible_pail_pixels(progress):
            self.actor.state_ms=self.well.data['phases_ms']['well_lower']*progress
            image=self.well.sprite(0);count=0
            for y in range(50,72):
                for x in (*range(34,39),*range(42,47)):
                    if image.get_at((x,y))!=baseline.get_at((x,y)):count+=1
            return count
        top=visible_pail_pixels(0);middle=visible_pail_pixels(.5);bottom=visible_pail_pixels(1)
        self.assertGreater(top,middle)
        self.assertGreater(middle,bottom)
        self.assertEqual(bottom,0)
        parked=self.well.data['parked_bucket_grip'];bucket=self.well.bucket_data['bucket_0_0']
        source=self.well.pails['bucket_0_0'];bbox=source.get_bounding_rect()
        top_y=parked[1]-bucket['grip'][1]+bbox.top
        bottom_y=parked[1]-bucket['grip'][1]+bbox.bottom
        self.assertEqual((top_y,bottom_y),(50,64))
        self.assertLessEqual(bottom_y+self.well.data['settle_bounce_pixels'],72)

    def test_actor_held_pail_is_behind_torso_and_articulated_arms(self):
        self.well.owner=self.actor
        checks=(('well_attach',.99,0),('well_hook',.5,0),
                ('well_unhook',.5,6),('well_take',.15,6),('well_take',.85,6))
        for state,progress,water in checks:
            self.actor.step_index=next(i for i,s in enumerate(self.actor.steps) if s['id']==state)
            self.actor.state_ms=self.well.data['phases_ms'][state]*progress
            self.actor.water_units=water
            name,frame,pose,key,xy=self.actor.bucket_placement()
            self.assertEqual(pose['order'],'before',name)
            rendered=self.actor.sprite(0);body=self.actor.bodies[name];bucket=self.actor.buckets[key]
            arms=self.world.image(f'assets/source/characters/npcs/female_02/gardener/parts/{name}_arms.png')
            overlap=arm_overlap=0;x0,y0=round(xy.x),round(xy.y)
            for by in range(bucket.get_height()):
                for bx in range(bucket.get_width()):
                    x,y=x0+bx,y0+by
                    if not (0<=x<rendered.get_width() and 0<=y<rendered.get_height()):continue
                    if not bucket.get_at((bx,by)).a or not body.get_at((x,y)).a:continue
                    overlap+=1
                    self.assertEqual(rendered.get_at((x,y)),body.get_at((x,y)),(name,x,y))
                    if arms.get_at((x,y)).a:arm_overlap+=1
            self.assertGreater(overlap,0,name)
            self.assertGreater(arm_overlap,0,name)

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
        self.assertEqual(origin+self.well.bucket_grip,origin+self.well.data['parked_bucket_grip'])
        self.assertEqual(loading.distance_to(origin+self.well.bucket_grip),31)
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
        game=main.Game(fullscreen=False);actor=game.town.npcs[1];well=game.town.well
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
