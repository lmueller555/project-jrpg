"""Discovery cues use logical feet distance, real availability and normal depth."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import pygame
from object_cues import ObjectCues
from rendering import WorldCanvas,artwork

RECORD={'id':'breakfast','entity':'plates','available_when':'meal',
        'interaction_boundary':[20,20,10,10],'glint_anchor':[2,2]}


class ObjectCueTests(unittest.TestCase):
    def setUp(self):
        self.cues=ObjectCues([RECORD])
        self.world=SimpleNamespace(size=(80,80),blocked=pygame.Mask((80,80)))
        self.player=SimpleNamespace(position=pygame.Vector2(25,40))
        self.entity={'id':'plates'}

    def tick(self,seconds=.12,conditions=('meal',),**kwargs):
        self.cues.update(seconds,self.world,self.player,conditions,**kwargs)

    def test_ten_pixel_activation_and_twelve_pixel_exit_use_feet_boundary(self):
        self.tick();self.assertTrue(self.cues.states['plates']['near'])
        self.player.position.y=42;self.tick();self.assertTrue(self.cues.states['plates']['near'])
        self.player.position.y=42.01;self.tick();self.assertFalse(self.cues.states['plates']['near'])
        self.player.position.y=41;self.tick();self.assertFalse(self.cues.states['plates']['near'])
        self.player.position.y=40;self.tick();self.assertTrue(self.cues.states['plates']['near'])

    def test_diagonal_distance_is_euclidean_not_square_radius(self):
        self.player.position.update(38,38);self.tick()
        self.assertFalse(self.cues.states['plates']['near'])
        self.player.position.update(36,38);self.tick()
        self.assertTrue(self.cues.states['plates']['near'])

    def test_wall_blocks_nearby_outline(self):
        for x in range(80):self.world.blocked.set_at((x,35))
        self.tick();self.assertFalse(self.cues.states['plates']['near'])

    def test_fade_is_short_then_steady_without_pulsing(self):
        self.tick(.06);self.assertAlmostEqual(self.cues.states['plates']['alpha'],.5)
        self.tick(.06);self.assertEqual(self.cues.states['plates']['alpha'],1)
        self.tick(5);self.assertEqual(self.cues.states['plates']['alpha'],1)

    def test_completed_condition_removes_glint_and_outline_immediately(self):
        self.tick();self.tick(0,conditions=())
        self.assertEqual(self.cues.states,{})

    def test_pause_freezes_clock_without_catchup_and_reset_forgets_nearness(self):
        self.tick();clock=self.cues.clock
        self.tick(100,enabled=False);self.assertEqual(self.cues.clock,clock)
        self.tick(.01);self.assertAlmostEqual(self.cues.clock,clock+.01)
        self.cues.reset();self.assertFalse(self.cues.enabled);self.assertEqual(self.cues.states,{})

    def test_glints_have_staggered_three_to_five_second_periods(self):
        timings=[self.cues.timing(key) for key in ('breakfast','ledger','herbs')]
        self.assertEqual(len(set(timings)),3)
        for period,offset in timings:
            self.assertTrue(3<=period<=5);self.assertGreater(period-offset,.28)

    def test_outline_is_one_native_pixel_outside_existing_black_contour(self):
        native=pygame.Surface((8,8),pygame.SRCALPHA);native.fill('black')
        native.fill('brown',(1,1,6,6));sprite=artwork(native,2)
        canvas=WorldCanvas((20,20));canvas.fill('navy')
        self.tick();self.cues.draw_outline(canvas,self.entity,sprite,(5,5));canvas.blit(sprite,(5,5))
        self.assertEqual(canvas.native.get_at((9,12))[:3],(244,211,92))
        self.assertEqual(canvas.native.get_at((8,12))[:3],pygame.Color('navy')[:3])
        self.assertEqual(canvas.native.get_at((10,12))[:3],(0,0,0))
        self.assertEqual(canvas.native.get_at((11,12))[:3],pygame.Color('brown')[:3])
        # Later actors/foregrounds cover the cue in the same composition.
        cover=pygame.Surface((4,4));cover.fill('green');canvas.blit(cover,(4,5))
        self.assertEqual(canvas.native.get_at((9,12))[:3],pygame.Color('green')[:3])

    def test_reduced_motion_has_static_marker_and_render_does_not_advance_clock(self):
        self.tick(reduced_motion=True);clock=self.cues.clock
        sprite=pygame.Surface((4,4));sprite.fill('black')
        a=WorldCanvas((20,20));b=WorldCanvas((20,20))
        self.cues.draw_glint(a,self.entity,sprite,(4,4));self.cues.clock+=2
        self.cues.draw_glint(b,self.entity,sprite,(4,4))
        self.assertEqual(pygame.image.tobytes(a.native,'RGB'),pygame.image.tobytes(b.native,'RGB'))
        self.assertEqual(self.cues.clock,clock+2)


class DiningCueIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from main import Game
        cls.temp=tempfile.TemporaryDirectory();p=Path(cls.temp.name)
        cls.game=Game(fullscreen=False,start_on_title=True,save_path=p/'save.json',settings_path=p/'settings.json')

    @classmethod
    def tearDownClass(cls):
        cls.game.music.stop();pygame.quit();cls.temp.cleanup()

    def setUp(self):
        g=self.game;g.on_title=False;g.pause.is_open=False
        g.world=g._scene_by_id('sanctuary_dining');g.world.object_cues.reset()
        g.opening.stage='explore';g.player.position.update(168,220)
        g.social.cancel_script();g._music_focused=True

    def test_actual_breakfast_state_and_scene_exit_control_cues(self):
        g=self.game;g._update_object_cues(.12)
        self.assertTrue(g.world.object_cues.states['breakfast']['near'])
        # Proximity marks the setting; joining still uses the existing seat
        # approach, rather than silently extending the gameplay trigger.
        g.player.position.update(108,200)
        self.assertEqual(g.opening.interaction_hint(),'E: join breakfast')
        dining=g.world;g.world=g._scene_by_id('sanctuary_hall');g._update_object_cues(.12)
        self.assertEqual(dining.object_cues.states,{})
        g.world=dining;g.opening.stage='done';g._update_object_cues(.12)
        self.assertEqual(dining.object_cues.states,{})

    def test_room_only_routine_props_use_native_bank_without_changing_hall(self):
        g=self.game
        serene=next(a for a in g.persistent_npcs if a.data['id']=='mother_serene')
        for prop in serene.surface_props:
            if prop['scene']=='sanctuary_dining':self.assertIsInstance(prop['surface'],WorldCanvas)
            elif prop['scene']=='sanctuary_hall':self.assertNotIsInstance(prop['surface'],WorldCanvas)

    def test_distant_eligible_object_still_glints_and_decorations_do_not(self):
        g=self.game;g.player.position.update(228,294);g._update_object_cues(.1)
        self.assertEqual(set(g.world.object_cues.states),{'breakfast'})
        self.assertFalse(g.world.object_cues.states['breakfast']['near'])

    def test_menus_focus_and_real_update_preserve_clock(self):
        g=self.game;g._update_object_cues(.12);clock=g.world.object_cues.clock
        g._music_focused=False;g.update(5,(0,0),False)
        self.assertEqual(g.world.object_cues.clock,clock)
        self.assertFalse(g.world.object_cues.enabled)
        g._music_focused=True;g.map_open=True;g.update(5,(0,0),False)
        self.assertEqual(g.world.object_cues.clock,clock)
        g.map_open=False
