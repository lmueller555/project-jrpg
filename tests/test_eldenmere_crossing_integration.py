"""Production Game crossing coverage, full-foot movement and rail layering.

These are live-map checks, not synthetic-water source previews. The two bridge
edge lanes use the extreme centers admitted by the unchanged 24x12 player probe.
The mill's wider apron lanes explicitly fan into its existing narrow doorway
throat; x978 straight through y354 was already blocked before this PR.
"""
from __future__ import annotations
import copy
import gc
import os
from pathlib import Path
import tempfile
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from PIL import Image, ImageChops
from main import Game
from tools.eldenmere_crossing_art import crossing_assemblies
from tools.capture_eldenmere_architecture_audit import CROSSING_REVIEW_ROUTES

ROOT=Path(__file__).resolve().parents[1]


class CrossingProductionGame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='crossing-integration-')
        cls.folder=Path(cls.temporary.name)
        cls.g=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
                   save_path=cls.folder/'journey.json',settings_path=cls.folder/'settings.json')
        cls.g.on_title=False;cls.g.opening.restore({'version':1,'stage':'disabled'})
        cls.g.audio.set_music(0);cls.g.audio.set_effects(0)
        cls.assemblies=crossing_assemblies()

    @classmethod
    def tearDownClass(cls):
        cls.g.music.stop();pygame.quit();cls.temporary.cleanup();del cls.g;gc.collect()

    def station(self,position,reduced=False):
        g=self.g;g.world=g.town;g.player.position.update(position)
        g.player.facing='front';g.player.moving=g.player.running=False;g.player.walk_ms=0
        g.opening_fade=g.transfer_cooldown=0;g.elapsed_ms=0
        g.party_travel.reset();g.audio.set_reduced_motion(reduced)
        g.town.reset_grass(reduced_motion=reduced);g.camera.reset()
        return g

    def follow(self,game,points,running=False):
        trace=[]
        for target in points:
            target=pygame.Vector2(target)
            for _ in range(900):
                delta=target-game.player.position
                if delta.length()<.5:break
                old=game.player.position.copy()
                game.update(min(1/60,delta.length()/(108 if running else 72)),delta,running)
                self.assertIs(game.world,game.town)
                self.assertNotEqual(game.player.position,old,('Stalled',tuple(old),tuple(target)))
                self.assertTrue(game.world.can_stand(game.player.position))
                self.assertTrue(all(game.world.can_stand(actor.position) for actor in game.party_travel.actors()))
                trace.append(tuple(game.player.position))
            else:self.fail(('Movement budget',tuple(target)))
        return trace

    def native(self):
        self.g.draw()
        return Image.frombytes('RGBA',(960,640),pygame.image.tobytes(self.g.canvas.native,'RGBA'))

    def test_live_native_ground_has_exact_opaque_deck_after_every_water_phase_and_reduced_motion(self):
        g=self.g
        for name,a in self.assemblies.items():
            lx,ly,w,h=a.metadata['walk_surface'];x,y=a.position
            expected=a.ground.crop((lx*2,ly*2,(lx+w)*2,(ly+h)*2)).convert('RGB')
            self.assertEqual(a.deck.getchannel('A').crop((lx*2,ly*2,(lx+w)*2,(ly+h)*2)).getextrema(),(255,255))
            for reduced in (False,True):
                g.town.reset_grass(reduced_motion=reduced)
                for phase in range(6):
                    with self.subTest(crossing=name,reduced=reduced,phase=phase):
                        actual=g.town.ground_region((x+lx,y+ly,w,h),phase*200).native
                        rgb=pygame.image.tobytes(actual,'RGB')
                        self.assertEqual(rgb,expected.tobytes(),(name,reduced,phase))

    def test_live_water_still_moves_beside_decks_and_holds_in_reduced_motion(self):
        g=self.g
        for name,a in self.assemblies.items():
            normal=[];held=[]
            for reduced,result in ((False,normal),(True,held)):
                g.town.reset_grass(reduced_motion=reduced)
                for phase in range(6):
                    result.append(tuple(pygame.image.tobytes(g.town.ground_region((x-6,y-6,12,12),phase*200).native,'RGB')
                                        for x,y in a.metadata['water_beside_samples_world']))
            self.assertGreater(len(set(normal)),1,(name,'water should remain animated beside structure'))
            self.assertEqual(len(set(held)),1,(name,'held water should remain held'))
            self.assertEqual(held[0],normal[0])

    def test_actual_selected_near_rails_keep_native_pixels_and_occupied_span_lengths(self):
        widths={}
        for name,a in self.assemblies.items():
            selected=[im for im,position in self.g.town.foreground if tuple(position)==a.position]
            self.assertEqual(len(selected),1,(name,a.position))
            self.assertTrue(hasattr(selected[0],'native'),name)
            self.assertEqual(pygame.image.tobytes(selected[0].native,'RGBA'),a.near_rail.tobytes(),name)
            box=selected[0].native.get_bounding_rect()
            if name!='mill_landing':
                widths[name]=box.width
                self.assertGreaterEqual(box.width,a.logical_size[0]*2*.97)
        self.assertEqual(widths['main_bridge']-widths['upper_bridge'],48)

    def test_full_24_by_12_probe_traverses_extreme_bridge_lanes_and_mill_apron_fan_in(self):
        self.assertEqual(self.g.town.probe_size,(24,12),'Do not shrink player to satisfy artwork')
        for name,lanes in CROSSING_REVIEW_ROUTES.items():
            for lane,declared_route in lanes.items():
                for running in (False,True):
                    for reverse in (False,True):
                        with self.subTest(crossing=name,lane=lane,running=running,reverse=reverse):
                            route=list(reversed(declared_route)) if reverse else declared_route
                            g=self.station(route[0]);self.assertTrue(g.town.can_stand(g.player.position))
                            self.assertGreater(len(self.follow(g,route[1:],running)),10)
                            self.assertLess(g.player.position.distance_to(route[-1]),.5)
        self.assertFalse(self.g.town.can_stand((978,354)),
                         'Existing east doorway blocker should not silently change in an art-only crossing PR')

    def test_far_rail_stays_behind_actor_and_near_rail_occludes_only_lower_body_in_game_draw(self):
        for name,x,far_y,near_y in [('upper_bridge',850,462,498),('main_bridge',850,1014,1050)]:
            for edge,y in [('far',far_y),('near',near_y)]:
                with self.subTest(crossing=name,edge=edge):
                    g=self.station((x,y));self.assertTrue(g.town.can_stand(g.player.position))
                    actual=self.native()
                    # Matched control used only for a layer assertion, never
                    # offered as a gameplay screenshot or replacement artwork.
                    g.player.story_visible=False
                    try:background=self.native()
                    finally:del g.player.story_visible
                    expected=background.copy();sprite=g.player.sprite()
                    source=Image.frombytes('RGBA',sprite.native.get_size(),pygame.image.tobytes(sprite.native,'RGBA'))
                    cx,cy=g.camera.position();ax,ay=g.player.draw_anchor
                    origin=(round((round(x)-ax-cx)*2),round((round(y)-ay-cy)*2))
                    expected.alpha_composite(source,origin)
                    difference=ImageChops.difference(actual.convert('RGB'),expected.convert('RGB')).convert('L')
                    if edge=='far':
                        self.assertIsNone(difference.getbbox(),name)
                    else:
                        box=difference.getbbox();self.assertIsNotNone(box,name)
                        actor_box=source.getchannel('A').getbbox()
                        self.assertGreaterEqual(box[1],origin[1]+actor_box[1]+(actor_box[3]-actor_box[1])//2,
                                                (name,'rail hides head/upper body',box))
                        self.assertLessEqual(box[3],origin[1]+source.height)
                        self.assertLess(box[3]-box[1],source.height//2)

    def test_seeded_companion_crosses_with_full_probe_then_continue_preserves_state_at_every_crossing(self):
        g=self.g
        if 'rhea' not in g.party.members:self.assertTrue(g.party.recruit('rhea'))
        for name,lanes in CROSSING_REVIEW_ROUTES.items():
            with self.subTest(crossing=name):
                route=lanes['center'];g=self.station(route[0])
                self.follow(g,route[1:],running=True)
                self.assertIn('rhea',[a.identifier for a in g.party_travel.actors()])
                g.update(.2,(0,0),False)
                expected=copy.deepcopy(g.journey_snapshot());self.assertTrue(g.save_progress(),g.save_error)
                other=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
                           save_path=self.folder/'journey.json',settings_path=self.folder/'settings.json')
                try:
                    self.assertTrue(other.begin_journey(True),other.save_error)
                    actual=other.journey_snapshot()
                    for key in ('quests','party','inventory','player','overworld'):
                        self.assertEqual(actual[key],expected[key],(name,key))
                    self.assertTrue(other.world.can_stand(other.player.position))
                    other.update(.7,(0,0),False);self.assertIs(other.world,other.town)
                    self.follow(other,list(reversed(route[:-1])),running=False)
                    self.assertIn('rhea',[a.identifier for a in other.party_travel.actors()])
                finally:other.music.stop();other=None;gc.collect()


if __name__=='__main__':unittest.main()
