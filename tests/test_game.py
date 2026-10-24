"""Headless checks of the real town, player controls, navigation and rendering."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'

from collections import defaultdict, deque
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pygame
import main


class PlayableEldenmere(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game=main.Game(fullscreen=False)
        cls.world=cls.game.world

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def setUp(self):
        self.game.player=main.Player(self.world)
        self.game.map_open=False
        self.game.elapsed_ms=0
        pygame.event.clear()

    def test_approved_town_contract_and_current_npcs(self):
        self.assertEqual(self.world.size,(1536,1344))
        self.assertEqual(self.world.data['size_tiles'],[64,56])
        self.assertEqual(self.world.probe_size,(24,12))
        self.assertEqual([r['id'] for r in self.world.data['npcs']],['mira_worker','sanctuary_gardener'])
        self.assertEqual(self.world.data['quests'],[])
        ids={r['id'] for r in self.world.entities}
        self.assertTrue({'sanctuary','mira','mill','halden','elira','venn','home_a','home_b','home_c'}<=ids)
        self.assertEqual(len(self.world.foreground),2)
        self.assertTrue(self.world.can_stand(self.game.player.position))
        original=main.read_json(main.ROOT/'assets/maps/eldenmere/terrain_foundation/scene.json')
        expected={b['id']:b['position'] for b in original['buildings']}
        expected['sanctuary']=main.read_json(main.ROOT/'assets/source/terrain/eldenmere/sanctuary_charm/recipe.json')['building_position']
        expected['mira']=main.read_json(main.ROOT/'assets/terrain/eldenmere/workshop/workshop.json')['position']
        for entity in self.world.entities:
            if entity['id'] in expected:self.assertEqual(entity['position'],expected[entity['id']])
        approved=pygame.image.load(str(main.ROOT/'assets/terrain/eldenmere/workshop/navigation/blocking.png')).convert()
        well=main.read_json(main.ROOT/'assets/terrain/eldenmere/well/well.json')
        pygame.draw.rect(approved,'white',well['ground_rect'])
        compiled=self.world.image(self.world.data['collision'],False)
        self.assertEqual(pygame.image.tobytes(approved,'RGB'),pygame.image.tobytes(compiled,'RGB'))

    def test_every_approved_route_destination_is_reachable(self):
        # Restrict this search to the original intended routes, though the
        # game also permits walking on unblocked grass outside these routes.
        allowed=pygame.image.load(str(main.ROOT/self.world.data['navigation_allowed']))
        start=tuple(self.world.data['spawn']);queue=deque([start]);visited={start}
        destinations={tuple(p) for p in self.world.data['destinations'].values()}
        remaining=set(destinations)
        width,height=self.world.size
        while queue and remaining:
            point=queue.popleft();remaining.discard(point)
            x,y=point
            for next_point in ((x-2,y),(x+2,y),(x,y-2),(x,y+2)):
                nx,ny=next_point
                if next_point in visited or not (0<=nx<width and 0<=ny<height):continue
                visited.add(next_point)
                if allowed.get_at(next_point).r and self.world.can_stand(next_point):queue.append(next_point)
        self.assertFalse(remaining,f'Unreachable approved destinations: {remaining}')

    def test_water_buildings_and_walls_block_without_tunnelling(self):
        player=self.game.player
        self.assertFalse(self.world.can_stand((852,600))) # midstream
        self.assertFalse(self.world.can_stand((384,240))) # sanctuary ground
        player.position.update(792,600)
        self.assertTrue(self.world.can_stand(player.position))
        player.update((1,0),3,self.world,True)
        self.assertLess(player.position.x,816)
        self.assertTrue(self.world.can_stand(player.position))
        player.position.update(384,312)
        player.update((0,-1),3,self.world,True)
        self.assertGreaterEqual(player.position.y,294)
        self.assertTrue(self.world.can_stand(player.position))
        player.position.update(340,330)
        self.assertTrue(self.world.can_stand(player.position))
        player.update((0,1),1,self.world)
        self.assertLess(player.position.y,384)

    def test_bridges_and_stairs_are_actually_walkable(self):
        player=self.game.player
        for start in [(768,480),(768,1032)]:
            player.position.update(start)
            self.assertTrue(self.world.can_stand(start))
            player.update((1,0),2,self.world)
            self.assertAlmostEqual(player.position.x,912,places=5)
        for start in [(384,330),(1176,828)]:
            player.position.update(start)
            self.assertTrue(self.world.can_stand(start))
            player.update((0,1),1.2,self.world)
            self.assertAlmostEqual(player.position.y,start[1]+86.4,places=5)

    def test_wasd_arrow_controls_speed_run_and_diagonal_normalization(self):
        # Keep the input/speed fixture in open ground south of the new well.
        control_start=(456,936)
        for key,axis,sign in [(pygame.K_d,0,1),(pygame.K_RIGHT,0,1),(pygame.K_a,0,-1),(pygame.K_LEFT,0,-1),
                              (pygame.K_w,1,-1),(pygame.K_UP,1,-1),(pygame.K_s,1,1),(pygame.K_DOWN,1,1)]:
            self.game.player.position.update(control_start)
            keys=defaultdict(bool,{key:True})
            with patch('main.pygame.key.get_pressed',return_value=keys):self.game.update(.1)
            self.assertAlmostEqual(self.game.player.position[axis]-control_start[axis],sign*7.2,places=5)
        player=self.game.player
        start=pygame.Vector2(control_start)
        player.position.update(start);player.update((1,1),.2,self.world)
        self.assertAlmostEqual(player.position.distance_to(start),14.4,places=5)
        player.position.update(start);player.update((1,0),.2,self.world,True)
        self.assertAlmostEqual(player.position.distance_to(start),21.6,places=5)

    def test_walks_animate_only_on_movement_and_keep_facing_when_stopped(self):
        player=self.game.player;player.position.update(516,900)
        player.update((1,0),.05,self.world)
        self.assertEqual(player.facing,'right');self.assertTrue(player.moving)
        first=player.sprite()
        player.update((1,0),.14,self.world)
        self.assertIsNot(player.sprite(),first)
        player.update((0,0),.1,self.world)
        self.assertFalse(player.moving);self.assertEqual(player.facing,'right')
        self.assertIs(player.sprite(),player.idles['right'])
        player.position.update(384,294);player.update((0,-1),.1,self.world)
        self.assertFalse(player.moving)

    def test_camera_edges_and_world_bounds(self):
        self.assertEqual(main.camera_for((0,0),self.world.size),(0,0))
        self.assertEqual(main.camera_for(self.world.size,self.world.size),(1056,1024))
        self.assertEqual(main.camera_for((20,20),(100,100)),(-190,-110))
        for p in [(0,0),(-1,400),(1536,500),(400,1344)]:self.assertFalse(self.world.can_stand(p))

    def test_roofs_occlude_from_behind_and_player_draws_in_front(self):
        building=next(r for r in self.world.entities if r['id']=='halden')
        player=self.game.player
        marker=pygame.Surface((24,36),pygame.SRCALPHA);marker.fill('#ff00ff')
        target=pygame.Surface(main.VIEW_SIZE)
        with patch.object(self.world,'entities',[building]),patch.object(self.world,'foreground',[]),patch.object(player,'sprite',return_value=marker):
            player.position.update(1008,544)
            self.assertTrue(self.world.can_stand(player.position))
            self.world.draw(target,(800,420),player,0)
            expected=building['surfaces'][0].get_at((60,60))
            self.assertEqual(expected.a,255)
            self.assertEqual(target.get_at((208,120))[:3],expected[:3])
            player.position.update(1008,650)
            self.world.draw(target,(800,420),player,0)
            self.assertEqual(target.get_at((208,202))[:3],(255,0,255))

    def test_animated_environment_map_toggle_and_quit(self):
        self.assertNotEqual(pygame.image.tobytes(self.world.ground[0],'RGB'),pygame.image.tobytes(self.world.ground[1],'RGB'))
        for identifier in ['mill','mira','sanctuary']:
            self.assertGreater(len(next(r for r in self.world.entities if r['id']==identifier)['surfaces']),1)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_m))
        self.assertTrue(self.game.handle_events());self.assertTrue(self.game.map_open)
        start=self.game.player.position.copy();self.game.update(.1,(1,0),False)
        self.assertEqual(self.game.player.position,start)
        self.game.draw()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
        self.assertTrue(self.game.handle_events());self.assertFalse(self.game.map_open)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(self.game.handle_events())

    def test_entrypoint_launches_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            screenshot=Path(directory)/'game.png'
            result=subprocess.run([sys.executable,str(main.ROOT/'main.py'),'--headless','--frames','3','--screenshot',str(screenshot)],
                                  cwd=directory,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(pygame.image.load(str(screenshot)).get_size(),main.WINDOW_SIZE)

    def test_resize_keeps_crisp_integer_scaling_and_letterboxing(self):
        pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE,w=1024,h=768,size=(1024,768)))
        self.assertTrue(self.game.handle_events());self.game.draw()
        self.assertEqual(self.game.window.get_size(),(1024,768))
        self.assertEqual(self.game.window.get_at((0,0))[:3],(16,27,25))
        # A native HUD pixel becomes an exact 2×2 block, with a (32,64) inset.
        expected=self.game.canvas.get_at((10,10))
        for dx in (0,1):
            for dy in (0,1):self.assertEqual(self.game.window.get_at((52+dx,84+dy)),expected)


class FullscreenLaunch(unittest.TestCase):
    def tearDown(self):pygame.quit()

    def test_default_uses_desktop_fullscreen_and_f11_restores_window_size(self):
        pygame.display.init()
        surface=pygame.display.set_mode(main.WINDOW_SIZE,pygame.RESIZABLE)
        # SDL's dummy backend cannot resize a display first opened fullscreen.
        # Check the exact mode requests, using a real windowed drawing surface.
        with patch('main.pygame.display.set_mode',return_value=surface) as mode:
            game=main.Game()
            self.assertTrue(game.fullscreen)
            mode.assert_called_once_with((0,0),pygame.FULLSCREEN)
            self.assertEqual(game.canvas.get_size(),main.VIEW_SIZE)
            for expected in (False,True,False):
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F11))
                self.assertTrue(game.handle_events())
                self.assertEqual(game.fullscreen,expected)
                mode.assert_called_with((0,0) if expected else main.WINDOW_SIZE,
                                        pygame.FULLSCREEN if expected else pygame.RESIZABLE)
                game.draw()

    def test_windowed_override_and_fullscreen_round_trip_preserve_resize(self):
        game=main.Game(window_size=(1024,768),fullscreen=False)
        self.assertFalse(game.fullscreen)
        self.assertEqual(game.window.get_size(),(1024,768))
        for expected in (True,False):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F11))
            game.handle_events()
            self.assertEqual(game.fullscreen,expected)
        self.assertEqual(game.window.get_size(),(1024,768))

    def test_entrypoint_defaults_fullscreen_but_headless_and_override_are_windowed(self):
        for argv,expected in (([],True),(['--windowed'],False),(['--headless'],False)):
            with self.subTest(argv=argv),patch('main.Game') as constructor:
                constructor.return_value.handle_events.return_value=False
                self.assertEqual(main.main(argv),0)
                constructor.assert_called_once_with(fullscreen=expected)


if __name__=='__main__':unittest.main()
