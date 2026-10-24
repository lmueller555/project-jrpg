"""Real routine completion, water accounting, collision and interruption checks."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

import unittest
from unittest.mock import Mock, patch
import random
import pygame
import main


class SanctuaryGardener(unittest.TestCase):
    def setUp(self):
        self.game=main.Game(fullscreen=False);self.world=self.game.town
        self.actor=next(a for a in self.world.npcs if a.data['id']=='sanctuary_gardener')
        self.actor=main.Gardener(self.actor.data,self.world,random.Random(1234))
        self.world.npcs[1]=self.actor
        self.game.player.position.update(520,520)

    def tearDown(self):pygame.quit()

    def until(self,predicate,limit=120,dt=1/30):
        if self.actor.state=='rest' and self.actor.completed_cycles==0:
            self.start_trip()
        for _ in range(round(limit/dt)):
            if predicate():return
            self.game.update(dt,(0,0),False)
        self.fail(f'Timed out in {self.actor.state} at {tuple(self.actor.position)}')

    def start_trip(self):
        self.game.update(self.actor.rest_remaining_ms/1000+1/60,(0,0),False)

    def test_complete_cycle_uses_dry_routes_stairs_and_all_six_targets(self):
        a=self.actor;stairs=set();states=set();footmask=pygame.Mask(a.probe_size,fill=True)
        self.start_trip();started=self.game.elapsed_ms
        for _ in range(3000):
            self.game.update(1/30,(0,0),False);states.add(a.state)
            self.assertIsNone(self.world.blocked.overlap(footmask,a.blocker.topleft))
            self.assertFalse(a.blocker.colliderect(self.world.npcs[0].blocker))
            self.assertFalse(a.blocker.colliderect(self.world.probe_rect(self.game.player.position)))
            # Moving work must never occupy a building's arrival point.
            for door in self.world.doors:
                point=pygame.Vector2(door.data['anchor'])+(0,12)
                self.assertTrue(self.world.can_stand(point),door.data['id'])
            if 350<a.position.y<400 and 360<a.position.x<408:
                stairs.add('loaded' if a.water_units else 'empty')
            if a.completed_cycles:break
        self.assertEqual(a.completed_cycles,1)
        self.assertEqual(stairs,{'empty','loaded'})
        self.assertEqual(a.watered_beds,[b['id'] for b in a.behavior['beds']])
        self.assertEqual(a.water_units,0)
        self.assertEqual(a.position,pygame.Vector2(a.behavior['rest_position']))
        watered=[e for e in a.events if e['type']=='watered']
        self.assertEqual([e['units'] for e in watered],[5,4,3,2,1,0])
        self.assertTrue({'well_lower','well_fill','well_raise','well_attach','well_unhook','pickup','setdown'}<=states)
        self.assertGreater(self.game.elapsed_ms-started,60000)
        self.assertLess(self.game.elapsed_ms-started,100000)

    def test_waits_when_collection_point_is_occupied_and_resumes(self):
        self.game.player.position.update(526,898)
        self.assertTrue(self.world.can_stand(self.game.player.position))
        self.until(lambda:self.actor.state=='to_well' and self.actor.waiting,limit=30)
        position=self.actor.position.copy()
        self.game.update(3,(0,0),False)
        self.assertEqual(self.actor.state,'to_well')
        self.assertEqual(self.actor.water_units,0)
        self.assertEqual(self.actor.position,position)
        self.assertFalse(self.actor.blocker.colliderect(self.world.probe_rect(self.game.player.position)))
        self.game.player.position.update(520,520)
        self.until(lambda:self.actor.state=='return_to_sanctuary',limit=40)
        self.assertEqual(self.actor.water_units,6)

    def test_brief_player_obstruction_pauses_movement_then_continues(self):
        self.until(lambda:self.actor.state=='to_well' and self.actor.waypoint_index==2 and self.actor.position.y>=348)
        self.game.player.position.update(384,370)
        self.until(lambda:self.actor.waiting,limit=2,dt=1/60)
        position=self.actor.position.copy();units=self.actor.water_units
        self.game.update(.35,(0,0),False)
        self.assertEqual(self.actor.position,position)
        self.assertEqual(self.actor.water_units,units)
        self.assertEqual(self.actor.state,'to_well')
        self.assertFalse(self.actor.blocker.colliderect(self.world.probe_rect(self.game.player.position)))
        self.game.player.position.update(520,520)
        self.game.update(.5,(0,0),False)
        self.assertGreater(self.actor.position.distance_to(position),1)

    def test_one_pail_fills_in_shaft_and_pours_descend_to_roots(self):
        a=self.actor;well=self.world.well
        self.until(lambda:a.state=='well_lower')
        self.assertEqual(a.water_units,0)
        self.until(lambda:a.state=='well_fill',limit=5)
        self.assertEqual(a.water_units,0)
        self.game.update(1,(0,0),False)
        self.assertGreater(a.water_units,0)
        self.assertEqual(a.water_units,well.draw_level)
        self.until(lambda:a.state=='well_raise',limit=3)
        self.assertEqual(a.water_units,6)
        self.until(lambda:a.state=='well_unhook',limit=15)
        self.assertEqual(a.water_units,6)
        self.assertFalse(well.bucket_on_rope)
        self.assertEqual(a.position,pygame.Vector2(well.data['loading_position']))
        self.assertIsNone(self.world.blocked.overlap(self.world._probes[a.probe_size],a.blocker.topleft))
        for bed in a.behavior['beds']:
            self.until(lambda:a.state=='water_'+bed['id'] and a.pose()[1].get('effect')=='pour')
            _,frame,_,key,xy=a.bucket_placement()
            spout=a.position-pygame.Vector2(a.draw_anchor)+xy+a.animation['buckets'][key]['spout']
            self.assertLess(spout.y,bed['root'][1])
            patch=pygame.Rect(bed['patch_position'],bed.get('patch_size',(24,24)))
            self.assertTrue(patch.collidepoint(bed['root']))
            self.assertNotEqual(frame['angle'],0)
            if 'window_trough' in bed['id']:
                self.assertTrue(a.pose()[0].startswith('raise_trough_'))
                self.assertLess(a.animation['poses'][a.pose()[0]]['grip'][1],10)

    def test_sustained_obstruction_gets_a_safe_detour_on_the_open_lane(self):
        a=self.actor
        self.until(lambda:a.state=='to_well' and a.waypoint_index==5 and a.position.x>=490)
        self.game.player.position.update(528,816)
        deviated=False
        for _ in range(180):
            self.game.update(1/30,(0,0),False)
            self.assertFalse(a.blocker.colliderect(self.world.probe_rect(self.game.player.position)))
            deviated=deviated or abs(a.position.y-816)>1
            if a.position.x>548:break
        self.assertTrue(deviated)
        self.assertGreater(a.position.x,548)
        self.assertEqual(a.water_units,0)

    def test_room_visit_preserves_actor_bucket_and_progress(self):
        a=self.actor
        self.until(lambda:a.state=='return_to_sanctuary')
        before=a.position.copy()
        door=next(d for d in self.world.doors if d.data['id']=='home_a')
        self.game.enter(door)
        self.assertEqual(self.game.world.npcs,[])
        self.game.update(3,(0,0),False)
        self.assertEqual(a.water_units,6)
        self.assertNotEqual(a.position,before)
        self.game.enter(self.game.world.doors[0])
        self.assertIs(self.game.world,self.world)
        self.assertIs(self.game.world.npcs[1],a)
        self.assertEqual(len(self.game.world.npcs),2)
        self.assertEqual(a.water_units,6)

    def test_fixed_simulation_matches_different_frame_rates(self):
        a=self.actor
        self.start_trip()
        # Advance at 10 FPS, then reproduce with independent 60 FPS updates.
        for _ in range(600):self.game.update(.1,(0,0),False)
        expected=(a.state,tuple(a.position),a.water_units,a.state_ms)
        other=main.Game(fullscreen=False);other.player.position.update(520,520)
        other.town.npcs[1]=main.Gardener(a.data,other.town,random.Random(1234))
        other.update(other.town.npcs[1].rest_duration_ms/1000+1/60,(0,0),False)
        for _ in range(3600):other.update(1/60,(0,0),False)
        b=other.town.npcs[1]
        self.assertEqual((b.state,tuple(b.position),b.water_units,b.state_ms),expected)

    def test_player_collision_and_own_probe_exclusion(self):
        a=self.actor;player=self.game.player
        self.assertFalse(self.world.can_stand(a.position))
        self.assertTrue(self.world.can_stand(a.position,a.probe_size,a))
        player.position.update(344,346)
        self.assertTrue(self.world.can_stand(player.position))
        player.update((-1,0),1,self.world)
        self.assertGreaterEqual(player.position.x,340)
        self.assertTrue(self.world.can_stand(player.position))

    def test_static_action_feet_and_player_depth_order(self):
        a=self.actor
        recipe=main.read_json(main.ROOT/'assets/source/characters/npcs/female_02/gardener/recipe.json')
        for name,spec in a.animation['poses'].items():
            if name.startswith('carry_'):continue
            direction='left' if name.endswith('left') else 'right' if name in ('rest',) or name.startswith(('pickup','fill')) or name.endswith('right') else 'front' if name.endswith('front') else 'back'
            if name in recipe['work_poses']:direction=recipe['work_poses'][name]['direction']
            original=self.world.image(f'assets/characters/npcs/female_02/idle_{direction}.png')
            feet=original.subsurface((0,30,24,6));bounds=feet.get_bounding_rect()
            expected=pygame.image.tobytes(feet.subsurface(bounds),'RGBA')
            bounds.move_ip(12,36)
            actual=pygame.image.tobytes(a.bodies[name].subsurface(bounds),'RGBA')
            self.assertEqual(actual,expected,name)
        marker=pygame.Surface((24,36),pygame.SRCALPHA);marker.fill('#ff00ff')
        target=pygame.Surface(main.VIEW_SIZE);player=self.game.player
        with patch.object(player,'sprite',return_value=marker):
            player.position.update(322,342)
            self.world.draw(target,(200,240),player,0)
            self.assertNotEqual(target.get_at((122,98))[:3],(255,0,255))
            player.position.update(322,358)
            self.world.draw(target,(200,240),player,0)
            self.assertEqual(target.get_at((122,98))[:3],(255,0,255))

    def test_carrying_retains_approved_stride_and_bucket_levels_are_visible(self):
        a=self.actor
        for direction in ('front','left','right','back'):
            for index in range(1,5):
                source=self.world.image(f'assets/characters/npcs/female_02/walk_{direction}/frame_{index:02}.png')
                expected=pygame.image.tobytes(source.subsurface((0,30,24,6)),'RGBA')
                for mode in ('empty','full'):
                    body=a.bodies[f'carry_{mode}.{direction}_{index:02}']
                    self.assertEqual(pygame.image.tobytes(body.subsurface((12,36,24,6)),'RGBA'),expected)
        water_colors={(89,142,159),(185,217,210)}
        counts=[]
        for level in range(a.water_capacity+1):
            bucket=a.buckets[f'bucket_0_{level}']
            counts.append(sum(bucket.get_at((x,y))[:3] in water_colors for x in range(32) for y in range(32)))
        self.assertEqual(counts[0],0)
        self.assertTrue(all(a<b for a,b in zip(counts,counts[1:])),counts)

    def test_random_rest_is_sampled_once_and_lasts_three_to_five_minutes(self):
        rng=Mock();rng.randint.side_effect=[180000,300000,240000]
        a=main.Gardener(self.actor.data,self.world,rng);self.actor=a;self.world.npcs[1]=a
        self.assertEqual(a.rest_duration_ms,180000)
        rng.randint.assert_called_once_with(180000,300000)
        self.game.update(179,(0,0),False)
        self.assertEqual(a.state,'rest');self.assertAlmostEqual(a.rest_remaining_ms,1000,places=5)
        self.assertEqual(rng.randint.call_count,1)
        self.game.update(1,(0,0),False)
        self.assertEqual(a.state,'pickup')
        self.until(lambda:a.completed_cycles==1,limit=120)
        self.assertEqual(a.state,'rest');self.assertEqual(a.rest_duration_ms,300000)
        self.assertEqual(rng.randint.call_count,2)
        self.game.update(299,(0,0),False)
        self.assertEqual(a.state,'rest');self.assertEqual(a.water_units,0)
        self.game.update(1,(0,0),False)
        self.assertEqual(a.state,'pickup');self.assertEqual(rng.randint.call_count,2)
        self.until(lambda:a.completed_cycles==2,limit=120)
        self.assertEqual(a.rest_duration_ms,240000);self.assertEqual(rng.randint.call_count,3)

    def test_rest_countdown_survives_room_visits_and_rendering(self):
        a=self.actor;duration=a.rest_duration_ms
        self.assertTrue(180000<=duration<=300000)
        self.game.update(20,(0,0),False)
        before=a.rest_remaining_ms
        door=next(d for d in self.world.doors if d.data['id']=='home_a')
        self.game.enter(door);self.game.update(12,(0,0),False)
        self.game.enter(self.game.world.doors[0])
        self.assertEqual(a.rest_duration_ms,duration)
        self.assertAlmostEqual(a.rest_remaining_ms,before-12000,places=4)
        for _ in range(10):a.sprite(self.game.elapsed_ms)
        self.assertEqual(a.rest_duration_ms,duration)


if __name__=='__main__':unittest.main()
