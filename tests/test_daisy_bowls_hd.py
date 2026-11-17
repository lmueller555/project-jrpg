"""Live room bowl levels, native registration, overlays and session boundaries."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from copy import deepcopy
from hashlib import sha256
import json
import unittest
import pygame
from PIL import Image,ImageChops
import main
from tools.build_daisy_bowls_hd import products,integrate,PACK,ROOM,STATES


class DaisyBowlHDExports(unittest.TestCase):
    def test_scoped_export_is_reproducible_and_manifest_hashes_match(self):
        out,meta=products()
        for path,raw in out.items():self.assertEqual((main.ROOT/path).read_bytes(),raw,path)
        manifest=json.loads((main.ROOT/'assets/maps/eldenmere/town_hd/manifest.json').read_text())
        records={r['file']:r for r in manifest['exports']}
        for path,raw in out.items():
            if path in records:self.assertEqual(records[path]['sha256'],sha256(raw).hexdigest())
        self.assertEqual(meta['logical_size'],[24,24]);self.assertEqual(meta['artwork_pixels_per_world_pixel'],2)

    def test_town_composer_uses_the_same_registered_exports_and_binding(self):
        from tools.build_eldenmere_hd import Export
        data=json.loads((main.ROOT/ROOM).read_text());export=Export()
        for entity in data['entities']:
            if entity.get('bowl_kind'):
                before=deepcopy(entity);integrate(entity,data,export)
                self.assertEqual(entity,before)
        out,_=products()
        self.assertEqual(export.out,out)

    def test_all_levels_preserve_body_alpha_and_their_exact_front_lip(self):
        _,meta=products();fullmask=Image.open(main.ROOT/PACK/'content_mask.png').convert('L')
        halfmask=Image.open(main.ROOT/PACK/'half_content_mask.png').convert('L')
        self.assertIsNone(ImageChops.subtract(halfmask,fullmask).getbbox())
        for kind,bowl in meta['bowls'].items():
            empty=Image.open(main.ROOT/bowl['states']['empty']['image']).convert('RGBA')
            lip=Image.open(main.ROOT/PACK/bowl['front_overlay']).convert('RGBA')
            content=[]
            for state,r in bowl['states'].items():
                image=Image.open(main.ROOT/r['image']).convert('RGBA');content.append(r['content_pixels'])
                self.assertEqual(image.getchannel('A').tobytes(),empty.getchannel('A').tobytes())
                for y in range(48):
                    for x in range(48):
                        if not fullmask.getpixel((x,y)):self.assertEqual(image.getpixel((x,y)),empty.getpixel((x,y)))
                        if lip.getpixel((x,y))[3]:self.assertEqual(lip.getpixel((x,y)),image.getpixel((x,y)))
            self.assertGreater(content[0],content[1]);self.assertGreater(content[1],0);self.assertEqual(content[2],0)
        # Half-full is a lower horizontal surface, never a dark vertical slice.
        self.assertGreater(halfmask.getbbox()[1],fullmask.getbbox()[1])


class DaisyBowlHDLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game=main.Game(fullscreen=False,start_on_title=False)
        cls.world=cls.game._scene_by_id('liam_house');cls.game.world=cls.world
        cls.game.player.position.update(230,300)
        cls.actor=next(n for n in cls.world.npcs if n.data['id']=='daisy')

    @classmethod
    def tearDownClass(cls):
        cls.game.music.stop();pygame.quit()
        del cls.game,cls.world,cls.actor

    def setUp(self):
        a=self.actor;a._release();a.position.update(a.behavior['home']);a.activity=None
        a.play_owned=False;a.play_pose=None;a._transition('rest',999999)
        for kind,bowl in a.bowls.items():self.world.set_entity_state(bowl['id'],'full')
        self.world.reduced_motion=False

    def until(self,predicate):
        for _ in range(3000):
            self.actor.update(1/60,self.world)
            if predicate():return
        self.fail((self.actor.state,tuple(self.actor.position)))

    def draw(self):
        self.world.draw(self.game.canvas,(-24,16),self.game.player,0)
        return self.game.canvas.native.copy()

    def test_initial_surface_is_the_registered_full_state_and_repeated_set_is_stable(self):
        for bowl in self.actor.bowls.values():
            initial=pygame.image.tobytes(bowl['surfaces'][0].native,'RGBA')
            self.assertEqual(bowl['frames'],[bowl['state_images']['full']])
            self.world.set_entity_state(bowl['id'],'full')
            self.assertEqual(pygame.image.tobytes(bowl['surfaces'][0].native,'RGBA'),initial)

    def test_actual_room_contents_deplete_twice_with_unchanged_support_and_refill(self):
        a=self.actor
        for kind in ('food','water'):
            bowl=a.bowls[kind];geometry={k:bowl[k] for k in ('position','floor_rect','sort_y','rect')}
            seen=[]
            for state in STATES:
                if state!='full':
                    a.begin_activity(kind,self.world);self.until(lambda:a.state=='rest')
                self.assertEqual(bowl['state'],state)
                self.assertTrue(all(bowl[k]==v for k,v in geometry.items()))
                image=self.draw();x,y=bowl['position'];crop=image.subsurface(((x+24)*2,(y-16)*2,48,48))
                seen.append(pygame.image.tobytes(crop,'RGBA'))
                self.world.reduced_motion=True
                self.assertEqual(pygame.image.tobytes(self.draw(),'RGBA'),pygame.image.tobytes(image,'RGBA'))
                self.world.reduced_motion=False
            self.assertEqual(len(set(seen)),3)
            self.assertTrue(self.world.set_entity_state(bowl['id'],'full','caregiver'))
            self.assertEqual(bowl['state'],'full')

    def test_every_contact_and_lip_uses_the_live_density_bank(self):
        a=self.actor
        for kind,action in (('food','eat'),('water','drink')):
            bowl=a.bowls[kind];path=main.ROOT/PACK
            masks=[Image.open(path/name).convert('L') for name in ('content_mask.png','half_content_mask.png')]
            for frame in a.animation['actions'][action]['frames']:
                if not frame['contact']:continue
                mouth=pygame.Vector2(a.behavior['bowls'][kind]['station'])-a.draw_anchor+frame['mouth_local']-bowl['position']
                for mask in masks:self.assertTrue(mask.getpixel((round(mouth.x*2),round(mouth.y*2))),(kind,frame))
            a.begin_activity(kind,self.world);self.until(lambda:a.state==action)
            image=self.draw();lip=a.lips[kind].native;x,y=bowl['position']
            for yy in range(48):
                for xx in range(48):
                    color=lip.get_at((xx,yy))
                    if color.a:self.assertEqual(image.get_at(((x+24)*2+xx,(y-16)*2+yy)),color)
            self.until(lambda:a.state=='rest')

    def test_ripples_are_clipped_to_current_water_and_suppressed_in_reduced_motion(self):
        a=self.actor;a.begin_activity('water',self.world);self.until(lambda:a.state=='drink')
        for state in ('full','half_full','empty'):
            self.world.set_entity_state(a.bowls['water']['id'],state,'daisy')
            for ms in (0,150,300,450):
                a.state_ms=ms;target=main.WorldCanvas(main.VIEW_SIZE,pygame.SRCALPHA)
                a.draw_background(target,(-24,16))
                mask=a.water_masks.get(state);bowl=a.bowls['water']
                for yy in range(24):
                    for xx in range(24):
                        color=target.get_at((bowl['position'][0]+24+xx,bowl['position'][1]-16+yy))
                        if color.a:self.assertIsNotNone(mask);self.assertTrue(mask.get_at((xx,yy)).r)
                for yy in range(48):
                    for xx in range(48):
                        color=target.native.get_at(((bowl['position'][0]+24)*2+xx,(bowl['position'][1]-16)*2+yy))
                        if color.a:self.assertIsNotNone(mask);self.assertTrue(mask.native.get_at((xx,yy)).r)
            self.world.reduced_motion=True;target=main.WorldCanvas(main.VIEW_SIZE,pygame.SRCALPHA)
            a.draw_background(target,(-24,16));self.assertEqual(pygame.mask.from_surface(target.native).count(),0)
            self.world.reduced_motion=False

    def test_pause_and_focus_loss_freeze_consumption_without_catchup(self):
        g=self.game;a=self.actor;a.begin_activity('food',self.world)
        self.until(lambda:a.state=='eat')
        def state():return (a.state_ms,a.consumed,a.bowls['food']['state'],tuple(a.position))
        before=state();g.pause.open();g.update(30,(0,0),False)
        self.assertEqual(state(),before);g.pause.close()
        g._music_focused=False;g.update(30,(0,0),False)
        self.assertEqual(state(),before);g._music_focused=True
        g.update(1/60,(0,0),False)
        self.assertAlmostEqual(a.state_ms,before[0]+1000/60)
        self.assertEqual(a.bowls['food']['state'],'full')

    def test_new_scene_session_starts_full_without_changing_cached_session_levels(self):
        self.world.set_entity_state('daisy_food_bowl','empty')
        self.assertIs(self.game._scene_by_id('liam_house'),self.world)
        self.assertEqual(self.actor.bowls['food']['state'],'empty')
        # Historical session-only ambient contract: a fresh room/Continue starts full.
        fresh=main.World(self.world.path,self.world._images)
        self.assertTrue(all(e['state']=='full' for e in fresh.entities if e.get('bowl_kind')))
        self.assertEqual(self.actor.bowls['food']['state'],'empty')

if __name__=='__main__':unittest.main()
