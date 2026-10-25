"""Tomas's delivery ownership, conversations and persistent sanctuary loop."""
import hashlib
import json
import os
from pathlib import Path
import unittest

os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import pygame
from PIL import Image
import main
from npc_routines import find_path

ROOT=Path(__file__).resolve().parents[1]


class TomasRoutines(unittest.TestCase):
    def setUp(self):
        self.game=main.Game(fullscreen=False,start_on_title=False)
        self.actor=next(a for a in self.game.persistent_npcs if a.data['id']=='tomas')
        self.game.world=self.game._scene_by_id('sanctuary_bedroom')
        self.game.player.position.update(144,270)

    def tearDown(self):pygame.quit()

    def place(self,step,position=(160,262),scene='sanctuary_dining'):
        a=self.actor;world=self.game._scene_by_id(scene)
        for w in self.game.scenes.values():
            if a in w.npcs:w.npcs.remove(a)
        a.select_step(step,position,scene)
        world.npcs.append(a);self.game._routine_worlds[a]=world
        return world

    def test_route_stations_and_door_landings_are_reachable(self):
        a=self.actor;scene=a.scene_id;point=tuple(a.position)
        for step in a.steps:
            world=self.game._scene_by_id(scene)
            if step['type']=='move':
                for goal in step['waypoints']:
                    self.assertIsNotNone(find_path(world,point,goal,a.probe_size,a),(step['id'],point,goal))
                    point=tuple(goal)
            elif step['type']=='transfer':
                scene=step['scene'];point=tuple(step['position'])
                self.assertTrue(self.game._scene_by_id(scene).can_stand(point,a.probe_size,a))
        for review in a.behavior['review'].values():
            world=self.game._scene_by_id(review['scene'])
            probe=world.probe_rect(review['station'],a.probe_size)
            self.assertTrue(world.can_stand(review['station'],a.probe_size,a))
            for door in world.doors:
                self.assertFalse(probe.colliderect(world.probe_rect(door.data['anchor'])),review)

    def test_loose_bundle_has_exactly_one_owner_for_every_frame_and_step(self):
        a=self.actor
        props=[p for p in a.surface_props if p['id'] in ('table_bundle','stored_bundle')]
        for step in a.steps:
            a.select_step(step['id']);elapsed=0
            records=a.action_records[a.action_id] if a.action_id else [{'duration_ms':1}]
            for record in records:
                a.state_ms=elapsed+record['duration_ms']/2
                surface=sum(a.surface_prop_visible(p) for p in props)
                carrying=bool(step.get('walk_set')) or (a.action_id in
                    ('prepare','store_bundle','fetch_bundle','return_bundle') and record.get('prop_owner')=='actor')
                self.assertEqual(surface+int(carrying),1,(step['id'],record.get('phase')))
                elapsed+=record['duration_ms']

    def test_room_and_actor_prop_handoffs_register_on_same_pixels(self):
        a=self.actor
        for step,position,prop_id in [('prepare',(160,262),'table_bundle'),
                                     ('store_bundle',(200,256),'stored_bundle'),
                                     ('fetch_bundle',(200,256),'stored_bundle'),
                                     ('return_bundle',(160,262),'table_bundle')]:
            source=json.loads((ROOT/'assets/source/characters/tomas/routines/poses.json').read_text())
            prop=next(p for p in a.surface_props if p['id']==prop_id)
            # Each handoff contains an actor-owned pose at the exact room
            # anchor (before or after the lift), rather than down on the floor.
            anchors=[r['prop_anchor'] for r in source['actions'][step] if r['prop_anchor']]
            expected=[prop['position'][0]-(position[0]-12),prop['position'][1]-(position[1]-30)]
            self.assertIn(expected,[list(p) for p in anchors],step)

    def test_conversation_waits_until_carried_bundle_is_released_then_resumes(self):
        a=self.actor;self.game.world=self.place('carry_to_storage')
        # Stay near the short delivery route in the same room. Live dialogue
        # correctly ends when either participant is in another room or leaves
        # the release radius, including while a handoff is pending.
        self.game.player.position.update(180,280)
        self.assertTrue(self.game.world.can_stand(self.game.player.position))
        self.game.social.start(a)
        self.assertTrue(self.game.social.pending)
        for _ in range(600):
            self.game.update(1/60,(0,0),False)
            if self.game.social.active:break
        self.assertTrue(self.game.social.active)
        self.assertEqual(a.state,'store_bundle')
        self.assertEqual(a.current_action_record['prop_owner'],'surface')
        paused=a.state_ms;position=tuple(a.position)
        self.game.update(1,(0,0),False)
        self.assertEqual((a.state_ms,tuple(a.position)),(paused,position))
        while self.game.social.active:self.game.social.advance()
        self.game.update(.1,(0,0),False)
        self.assertGreater(a.state_ms,paused)
        self.assertIn('tomas_greeted',self.game.social.flags)
        self.game.social.start(a)
        self.assertEqual(self.game.social.conversation['id'],'tomas_repeat')

    def test_full_schedule_completes_with_other_npcs_and_preserves_identity(self):
        a=self.actor;visited=set();seen=set()
        for _ in range(1600):
            visited.add(a.scene_id);seen.add(a.state)
            self.game.update(.1,(0,0),False)
            if a.completed_cycles:break
        self.assertEqual(a.completed_cycles,1,(a.state,tuple(a.position)))
        self.assertEqual(visited,{'sanctuary_dining','sanctuary_hall','eldenmere.playable'})
        self.assertIn('courtyard_break',seen);self.assertIn('fetch_bundle',seen)
        memberships=[w for w in self.game.scenes.values() if a in w.npcs]
        self.assertEqual(memberships,[self.game._scene_by_id('sanctuary_dining')])
        self.assertEqual(a.state,'prepare')
        self.assertEqual(tuple(a.position),(160,262))

    def test_carry_waiting_pose_retains_bundle_and_walk_timing(self):
        a=self.actor;world=self.place('carry_to_storage')
        a.facing='right';a.moving=False
        self.assertIs(a.sprite(0),a.walk_sets['bundle']['right'][0][0])
        self.assertEqual([ms for _,ms in a.walk_sets['bundle']['right']],[140]*4)
        blocked=world.probe_rect((162,262),(12,8))
        original=tuple(a.position);a.update(.1,world,blocked)
        self.assertEqual(tuple(a.position),original)
        self.assertFalse(a.conversation_ready)

    def test_player_blocking_delivery_can_talk_without_losing_bundle_or_getting_stuck(self):
        a=self.actor;world=self.place('carry_to_storage',(178,262))
        self.game.world=world;self.game.player.position.update(200,262)
        self.assertTrue(world.can_stand(self.game.player.position))
        self.game.social.start(a)
        for _ in range(60):
            self.game.update(1/60,(0,0),False)
            if self.game.social.active:break
        self.assertTrue(self.game.social.active)
        self.assertEqual(a.state,'carry_to_storage')
        self.assertIs(a.sprite(0),a.walk_sets['bundle'][a.conversation_facing][0][0])
        while self.game.social.active:self.game.social.advance()
        self.game.player.position.update(240,294)
        for _ in range(300):self.game.update(1/60,(0,0),False)
        self.assertNotEqual(a.state,'carry_to_storage')

    def test_work_assets_are_hard_pixels_and_crank_base_stays_fixed(self):
        folder=ROOT/'assets/characters/tomas/routines'
        for path in folder.glob('*/frame_*.png'):
            with Image.open(path) as im:
                self.assertEqual(im.size,(64,48));self.assertEqual(set(im.getchannel('A').tobytes()),{0,255})
        frames=self.actor.action_records['tinker']
        hashes={hashlib.sha256((folder/r['file']).read_bytes()).hexdigest() for r in frames if r['phase']=='turn_crank'}
        self.assertGreaterEqual(len(hashes),6)
        # No action changes Tomas's approved visible height or stretches his
        # body; only sleeve joints, small props and a one-pixel lean are new.
        source=json.loads((ROOT/'assets/source/characters/tomas/routines/poses.json').read_text())
        for action,specs in source['actions'].items():
            for record in specs:
                for shoulder,elbow,hand in record['arms']:
                    self.assertLessEqual(abs(shoulder[0]-hand[0]),16)
                    if action=='tinker':
                        self.assertLessEqual(abs(shoulder[0]-hand[0]),6,
                                             'Tomas should reach the near-side crank with a bent arm')

    def test_random_break_is_sampled_once_and_stays_in_range(self):
        a=self.actor;world=self.place('courtyard_break',(418,406),'eldenmere.playable')
        duration=a._duration();self.assertTrue(12000<=duration<=20000)
        a.update(.5,world)
        self.assertEqual(a._duration(),duration)
        self.assertAlmostEqual(a.state_ms,500)

    def test_npc_opens_door_and_waits_for_its_animation_before_transfer(self):
        a=self.actor;world=self.place('return_to_hall',(386,306),'eldenmere.playable')
        door=next(d for d in world.doors if d.data['id']=='sanctuary')
        self.assertEqual(door.state,'closed')
        self.game.update(.1,(0,0),False)
        self.assertEqual(a.scene_id,'eldenmere.playable')
        self.assertEqual(door.state,'opening')
        self.assertTrue(a.waiting)
        for _ in range(5):self.game.update(.1,(0,0),False)
        self.assertEqual(a.scene_id,'sanctuary_hall')
        # One doorway timer update per frame, even with multiple residents.
        door.progress=0;door.target_open=False
        door.update(None,.1,[(386,306),(386,308)])
        self.assertEqual(door.progress,1)


if __name__=='__main__':unittest.main()
