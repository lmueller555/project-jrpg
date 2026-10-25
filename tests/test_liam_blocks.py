"""Five-block conservation, single probability rolls, shared ownership and contact art."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import hashlib
import json
import random
import unittest

import pygame
from PIL import Image
import main


class CountingRandom:
    def __init__(self,value):self.value=value;self.calls=0;self.other=random.Random(7)
    def random(self):self.calls+=1;return self.value
    def __getattr__(self,name):return getattr(self.other,name)


class LiamBlocksTests(unittest.TestCase):
    def setUp(self):
        self.game=main.Game(fullscreen=False,start_on_title=False)
        self.r=self.game.block_routines[0];self.shared=self.r.shared
        self.shared.cooldown_ms=999999;self.r.cooldown_ms=999999
        self.game.player.position.update(430,600)
        self.r.daisy.duration_ms=999999
        self.r.daisy.cooldowns={'food':999999,'water':999999}

    def tearDown(self):pygame.quit()

    def tick(self):
        before={a:(self.shared.worlds[a],a.position.copy()) for a in (self.r.liam,self.r.daisy)}
        block_before={b['id']:(b['state'],b['center'].copy()) for b in self.r.blocks}
        self.game.update(1/60,(0,0),False)
        self.assertEqual(len(self.r.blocks),5)
        self.assertEqual(len({b['id'] for b in self.r.blocks}),5)
        self.assertTrue(all(b['state'] in ('box','held','placed','scattered','forgotten') for b in self.r.blocks))
        self.assertLessEqual(sum(b['state']=='held' for b in self.r.blocks),1)
        for block in self.r.blocks:
            previous,old_center=block_before[block['id']];current=block['state']
            if (previous,current) in (('box','held'),('held','box'),('held','placed')) or (previous in ('placed','scattered','forgotten') and current=='held'):
                index,frame=self.r._frame()
                spec=self.r.meta['actions'][self.r.liam.action]
                self.assertEqual(index,spec['handoff_contact_frame'])
                hand=self.r.liam.position-pygame.Vector2(self.r.liam.draw_anchor)+frame['hand_local']
                target=(self.r.pack['box_contact'] if previous=='box' or current=='box' else
                        block['center'] if current=='placed' else old_center)
                self.assertLess(hand.distance_to(target),1,(previous,current,tuple(hand),tuple(target)))
        for actor,(oldworld,oldpos) in before.items():
            world=self.shared.worlds[actor]
            self.assertEqual(sum(n is actor for scene in self.game.scenes.values() for n in scene.npcs),1)
            self.assertTrue(world.can_stand(actor.position,actor.probe_size,actor),
                            (self.r.state,actor.data['id'],tuple(actor.position)))
            if world is oldworld:self.assertLessEqual(actor.position.distance_to(oldpos),64/60+1e-6)

    def until(self,predicate,limit=150):
        for i in range(limit*60):
            self.tick()
            if predicate():return i/60
        self.fail((self.r.state,[(b['id'],b['state']) for b in self.r.blocks],tuple(self.r.liam.position),tuple(self.r.daisy.position)))

    def nearby_daisy(self):
        d=self.r.daisy;d.position.update(126,180)
        self.assertTrue(self.r.home.can_stand(d.position,d.probe_size,d))
        d.state='pause';d.state_ms=0;d.duration_ms=999999;d.activity=None;d.moving=False
        d.active_bowl=None

    def test_builds_all_five_then_returns_all_and_releases_liam(self):
        r=self.r;self.assertTrue(r.begin(accident=False,forget=False))
        self.until(lambda:sum(b['state']=='placed' for b in r.blocks)==5)
        self.assertIs(self.shared.liam_owner,r)
        self.assertFalse(self.shared._available())
        self.until(lambda:r.completed_cycles==1)
        self.assertEqual(r.state,'cooldown');self.assertEqual([b['state'] for b in r.blocks],['box']*5)
        self.assertIsNone(r.forgotten_id);self.assertIsNone(self.shared.liam_owner)
        self.assertFalse(r.daisy.play_owned)

    def test_forgets_exactly_one_persists_on_reentry_and_recovers_before_next_build(self):
        r=self.r;ids=[b['id'] for b in r.blocks]
        self.assertTrue(r.begin(accident=False,forget=True))
        self.until(lambda:r.completed_cycles==1)
        forgotten=[b for b in r.blocks if b['state']=='forgotten']
        self.assertEqual(len(forgotten),1);self.assertEqual(sum(b['state']=='box' for b in r.blocks),4)
        self.assertEqual(r.forgotten_id,forgotten[0]['id'])
        front=next(d for d in self.game.town.doors if d.data['id']=='liam_house')
        self.assertTrue(self.game.enter(front))
        self.assertIs(self.game.block_routines[0],r)
        self.assertEqual([b['id'] for b in r.blocks],ids)
        self.assertEqual(sum(b['state']=='forgotten' for b in r.blocks),1)
        self.game.world=self.game.town;self.game.player.position.update(430,600)
        self.assertTrue(r.begin(accident=False,forget=False))
        self.until(lambda:all(b['state']=='box' for b in r.blocks))
        self.assertIsNone(r.forgotten_id)
        self.until(lambda:sum(b['state']=='placed' for b in r.blocks)==5)
        self.until(lambda:r.completed_cycles==2)
        self.assertEqual([b['id'] for b in r.blocks],ids)
        self.assertTrue(all(b['state']=='box' for b in r.blocks))

    def test_daisy_accident_requires_completed_build_contact_and_returns_her_to_rug(self):
        r=self.r;self.nearby_daisy();self.assertTrue(r.begin(accident=True,forget=False))
        self.until(lambda:sum(b['state']=='placed' for b in r.blocks)==5)
        self.assertFalse(any(b['state']=='scattered' for b in r.blocks))
        self.until(lambda:any(b['state']=='scattered' for b in r.blocks))
        self.assertTrue(r.accident_rolled);self.assertTrue(r.accident_selected)
        self.assertEqual(sum(b['state']=='scattered' for b in r.blocks),5)
        self.assertLess(r.daisy.position.distance_to((110,200)),36)
        self.until(lambda:r.completed_cycles==1)
        self.assertEqual(r.daisy.state,'rest')
        self.assertAlmostEqual(r.daisy.position.distance_to((108,282)),0)
        self.assertGreaterEqual(r.daisy.duration_ms,45000);self.assertLessEqual(r.daisy.duration_ms,90000)
        self.assertFalse(r.daisy.play_owned)
        self.assertTrue(all(b['state']=='box' for b in r.blocks))

    def test_probability_roll_is_once_on_first_eligible_nearby_visit(self):
        r=self.r;r._rng=CountingRandom(.1)
        self.assertEqual(r.config['accident_probability'],.1)
        self.assertEqual(r.config['forget_probability'],.5)
        self.assertTrue(r.begin(forget=False))
        self.until(lambda:sum(b['state']=='placed' for b in r.blocks)==5)
        self.assertFalse(r.accident_rolled);self.assertEqual(r._rng.calls,0)
        self.nearby_daisy();self.until(lambda:r.accident_rolled,limit=2)
        self.assertFalse(r.accident_selected)
        self.until(lambda:r.completed_cycles==1)
        self.assertEqual(r._rng.calls,1)

    def test_selected_accident_does_not_freeze_daisy_on_a_future_build_station(self):
        r=self.r;self.assertTrue(r.begin(accident=True,forget=False))
        self.until(lambda:sum(b['state']=='placed' for b in r.blocks)==3)
        d=r.daisy
        # A genuine wandering pause can occupy the fourth placement approach.
        # Initialize its normal wander bookkeeping before selecting this pause.
        d.begin_activity('wander',r.home);d._start_activity(r.home,None)
        d.position.update(116,208);d._transition('pause',250)
        self.assertTrue(r.home.can_stand(d.position,d.probe_size,d))
        self.assertFalse(r.home.can_stand((106,206),r.liam.probe_size,r.liam))
        self.until(lambda:r.accident_rolled,limit=1)
        self.assertTrue(r.accident_selected)
        self.assertFalse(d.play_owned)
        self.assertFalse(r.dog_owned)
        self.until(lambda:sum(b['state']=='placed' for b in r.blocks)==5)
        self.until(lambda:r.completed_cycles==1)
        self.assertTrue(all(b['state']=='box' for b in r.blocks))
        self.assertTrue(any(event.get('knockdown') for event in r.events))
        self.assertEqual(d.state,'rest')
        self.assertFalse(d.play_owned)

    def test_existing_chase_owns_liam_and_blocked_box_approach_waits(self):
        r=self.r
        self.assertTrue(self.shared.begin(drink=False))
        self.until(lambda:self.shared.active,limit=2)
        self.assertFalse(r.begin(accident=False,forget=False))
        self.until(lambda:self.shared.state=='nap')
        self.shared.rest_duration=1;self.until(lambda:self.shared.state=='cooldown',limit=5)
        self.shared.cooldown_ms=999999
        self.game.world=r.home;self.game.player.position.update(80,200)
        self.assertTrue(r.begin(accident=False,forget=False))
        for _ in range(180):
            self.tick()
            self.assertFalse(r.liam.blocker.colliderect(r.home.probe_rect(self.game.player.position)))
        self.assertTrue(all(b['state']=='box' for b in r.blocks))
        self.game.player.position.update(220,300)
        self.until(lambda:r.completed_cycles==1)

    def test_authored_four_pose_layers_hand_contacts_and_approved_art_hashes(self):
        root=main.ROOT
        meta=json.loads((root/'assets/characters/liam_family/block_play/animations.json').read_text())
        self.assertEqual(meta['canvas_size'],[96,96]);self.assertEqual(meta['draw_anchor'],[64,66])
        for action,spec in meta['actions'].items():
            self.assertEqual(len(spec['frames']),4);unique=set()
            for frame in spec['frames']:
                im=Image.open(root/frame['file']).convert('RGBA');unique.add(im.tobytes())
                rebuilt=Image.new('RGBA',im.size)
                for path in frame['layers_from_repo_root']:rebuilt.alpha_composite(Image.open(root/path).convert('RGBA'))
                self.assertEqual(rebuilt.tobytes(),im.tobytes());self.assertEqual(im.size,tuple(spec['canvas_size']))
                self.assertEqual(set(im.getchannel('A').tobytes()),{0,255})
                landmark=frame['hand_local'] if spec['character']=='liam' else frame['nose_local']
                self.assertTrue(0<=landmark[0]<im.width and 0<=landmark[1]<im.height)
            self.assertEqual(len(unique),4,action)
            if action in ('take_left','return_left','place_right','collect_right'):
                self.assertEqual(spec['handoff_contact_frame'],2)
                self.assertEqual(spec['frames'][2]['hand_local'],[54,57] if action.endswith('left') else [74,57])
        for path,sha in meta['approved_png_sha256'].items():self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(),sha)
        pack=json.loads((root/'assets/terrain/eldenmere/liam_home/blocks/blocks.json').read_text())
        self.assertEqual(len(pack['blocks']),5)
        self.assertEqual(set(pack['box_states']),{str(i) for i in range(6)})
        variants=[Image.open(root/pack['box_states'][str(i)]['image']).convert('RGBA') for i in range(6)]
        self.assertEqual(len({im.size for im in variants}),1)


if __name__=='__main__':unittest.main()
