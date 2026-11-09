"""The public hall has real navigation, correct furniture depth and a safe exit."""
import os
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from PIL import Image

from main import Player, World
from npc_routines import find_path
from tools.build_sanctuary_reserve_hall import build, png

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT/'assets/maps/elden_vale_sanctuary_hall/map.json'


class SanctuaryReserveHallTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode((480,320))
        self.world = World(MAP)

    def tearDown(self):pygame.quit()

    def test_pixel_asset_recipe_reproduces_runtime_products(self):
        build(check=True)
        self.assertEqual(self.world.data['authoring'],'native_pixel_asset_modules')
        self.assertEqual(self.world.data['tile_size'],24)
        self.assertEqual(self.world.probe_size,(24,12))
        sources = self.world.data['source_assets']
        self.assertGreaterEqual(len(sources),12)
        self.assertEqual(len({record['path'] for record in sources}),len(sources))
        for source in sources:
            with self.subTest(source=source['path']):
                self.assertTrue(source['path'].startswith('assets/terrain/eldenmere/'))
                self.assertEqual(hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest(),
                                 source['sha256'])
        recipe = (ROOT/self.world.data['source_recipe']).read_text()
        for obsolete in ('generated_hall.png','source_polygon','source_openings'):
            self.assertNotIn(obsolete,recipe)
        self.assertFalse(list((ROOT/'assets/terrain/elden_vale_sanctuary_hall/depth').glob('*.png')))

    def test_complete_character_footprint_can_walk_to_every_inspection_and_exit(self):
        player = Player(self.world)
        targets = [*self.world.data['destinations'].values(), self.world.data['spawn'], [288,350]]
        for target in targets:
            route = find_path(self.world,player.position,target,self.world.probe_size,None)
            self.assertIsNotNone(route,target)
            for point in route:
                for _ in range(3000):
                    delta = pygame.Vector2(point)-player.position
                    if delta.length() < .1:break
                    old = player.position.copy()
                    player.update(delta,min(.05,delta.length()/72),self.world)
                    self.assertNotEqual(player.position,old,(point,old))
                    self.assertTrue(self.world.can_stand(player.position))
                else:self.fail(f'Walk stalled at {point}')
            self.assertLess(player.position.distance_to(target),.1)
        door = self.world.doors[0]
        self.assertTrue(door.can_enter(player.position,(0,1)))
        self.assertFalse(door.can_enter(player.position,(0,-1)))
        player.update((0,1),.3,self.world)
        self.assertLessEqual(abs(player.position.y-350),1)
        self.assertTrue(door.can_enter(player.position,(0,1)))

    def test_crystal_windows_and_wall_carvings_stay_above_the_existing_walkable_floor(self):
        data=self.world.data
        details=data['fantasy_details']
        self.assertEqual(details['authoring'],'native_pixel_geometry')
        folder=ROOT/'assets/terrain/elden_vale_sanctuary_hall/fantasy'
        ground=Image.open(ROOT/data['ground_frames'][0]).convert('RGB')
        window=Image.open(folder/'crystal_window.png').convert('RGBA')
        recipe=json.loads((ROOT/data['source_recipe']).read_text())
        for x,y in recipe['windows']:
            with self.subTest(window=(x,y)):
                actual=ground.crop((x,y,x+window.width,y+window.height))
                for yy in range(window.height):
                    for xx in range(window.width):
                        pixel=window.getpixel((xx,yy))
                        if pixel[3]:self.assertEqual(actual.getpixel((xx,yy)),pixel[:3])
        for record in details['wall_details']:
            with self.subTest(module=record['module'],position=record['position']):
                image=Image.open(folder/(record['module']+'.png')).convert('RGBA')
                self.assertLessEqual(set(image.getchannel('A').get_flattened_data()),{0,255})
                self.assertGreaterEqual(record['position'][1],48)
                self.assertLessEqual(record['position'][1]+image.height,144)
        # The new doorway cuts only its narrow north-wall threshold. Closing
        # that opening reconstructs the earlier hall's exact collision mask.
        collision = Image.open(ROOT/data['collision']).convert('L')
        clearance = pygame.Rect(data['relief_clearance']).clip(pygame.Rect(recipe['walls']['north']))
        collision.paste(255, (clearance.x, clearance.y, clearance.right, clearance.bottom))
        self.assertEqual(hashlib.sha256(png(collision)).hexdigest(),
                         '4574117ff4a450028225d349d11048836eb8378ffeae74d4302ffdeda1c7d956')

    def test_full_foot_flood_connects_all_clear_floor_around_the_furniture(self):
        from test_reserve_free_roam import full_foot_flood
        clear,reached = full_foot_flood(self.world)
        self.assertGreater(len(clear),2000)
        self.assertEqual(clear,reached)

    def test_solid_furniture_and_walls_cannot_be_walked_through(self):
        for point in ((128,208),(128,278),(476,240),(288,151),(486,152),
                      (20,200),(550,200),(288,100),(200,340),(288,365)):
            self.assertFalse(self.world.can_stand(point),point)
        self.assertTrue(self.world.can_stand((288,328)))
        self.assertTrue(self.world.can_stand((288,350)))

    def test_character_is_behind_bench_to_the_north_and_in_front_to_the_south(self):
        color = (251,0,245)
        sprite = pygame.Surface((24,36));sprite.fill(color)
        player = SimpleNamespace(position=pygame.Vector2(128,194),sprite=lambda:sprite)
        canvas = pygame.Surface((480,320))
        self.assertTrue(self.world.can_stand(player.position))
        self.world.draw(canvas,(0,0),player,0)
        self.assertNotEqual(canvas.get_at((128,188))[:3],color)
        player.position.update(128,232)
        self.assertTrue(self.world.can_stand(player.position))
        self.world.draw(canvas,(0,0),player,0)
        self.assertEqual(canvas.get_at((128,210))[:3],color)

    def test_projecting_plants_and_cabinet_hide_the_actor_only_from_behind(self):
        color = (251,0,245)
        sprite = pygame.Surface((24,36));sprite.fill(color)
        # These points are chosen against visible furniture, independently of
        # exported sorting metadata. Compare the real scenery-only rendering
        # because native props are deliberately absent from the ground layer.
        pairs = (
            ('west plant', (45,296), (43,293), (45,318), (43,293)),
            ('east plant', (527,296), (525,293), (527,318), (525,293)),
            ('records cabinet edge', (439,152), (449,148), (460,172), (449,148)),
        )
        for name,back,back_pixel,front,front_pixel in pairs:
            for position,point,visible in ((back,back_pixel,False),(front,front_pixel,True)):
                with self.subTest(prop=name, visible=visible):
                    self.assertTrue(self.world.can_stand(position))
                    player = SimpleNamespace(position=pygame.Vector2(position),sprite=lambda:sprite)
                    camera = (96,64) if position[0] >= 480 else (0,64)
                    before = pygame.Surface((480,320));canvas = pygame.Surface((480,320))
                    self.world.draw(before,camera,SimpleNamespace(position=player.position,
                                                                 story_visible=False),0)
                    self.world.draw(canvas,camera,player,0)
                    pixel = canvas.get_at((point[0]-camera[0],point[1]-camera[1]))[:3]
                    if visible:self.assertEqual(pixel,color)
                    else:
                        self.assertNotEqual(pixel,color)
                        self.assertEqual(pixel,before.get_at((point[0]-camera[0],point[1]-camera[1]))[:3])

    def test_real_gaps_between_leaves_and_flower_spikes_do_not_erase_the_actor(self):
        color = (251,0,245)
        sprite = pygame.Surface((24,36));sprite.fill(color)
        for position,point,camera in (((45,296),(45,292),(0,64)),
                                      ((527,296),(527,292),(96,64))):
            with self.subTest(gap=point):
                self.assertTrue(self.world.can_stand(position))
                player = SimpleNamespace(position=pygame.Vector2(position),sprite=lambda:sprite)
                canvas = pygame.Surface((480,320))
                self.world.draw(canvas,camera,player,0)
                self.assertEqual(canvas.get_at((point[0]-camera[0],point[1]-camera[1]))[:3],color)
                # The transparent leaf gap is enclosed by opaque neighboring
                # leaves, so an entirely missing prop cannot satisfy the test.
                for dx in (-1,1):
                    self.assertNotEqual(canvas.get_at((point[0]+dx-camera[0],point[1]-camera[1]))[:3],color)


if __name__ == '__main__':unittest.main()
