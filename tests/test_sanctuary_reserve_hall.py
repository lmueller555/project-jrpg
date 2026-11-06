"""The public hall has real navigation, correct furniture depth and a safe exit."""
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from main import Player, World
from npc_routines import find_path
from tools.build_sanctuary_reserve_hall import build

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT/'assets/maps/elden_vale_sanctuary_hall/map.json'


class SanctuaryReserveHallTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode((480,320))
        self.world = World(MAP)

    def tearDown(self):pygame.quit()

    def test_retained_source_reproduces_runtime_products(self):
        build(check=True)

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
        # These points were selected against the original scene pixels, not
        # derived from the exported masks or their sorting metadata.
        pairs = (
            ('west plant', (62,288), (59,279), (74,319), (65,296)),
            ('east plant', (506,285), (512,283), (500,319), (509,296)),
            ('records cabinet', (436,152), (447,130), (436,170), (447,145)),
        )
        for name,back,back_pixel,front,front_pixel in pairs:
            for position,point,visible in ((back,back_pixel,False),(front,front_pixel,True)):
                with self.subTest(prop=name, visible=visible):
                    self.assertTrue(self.world.can_stand(position))
                    player = SimpleNamespace(position=pygame.Vector2(position),sprite=lambda:sprite)
                    camera = (96,64) if position[0] >= 480 else (0,64)
                    canvas = pygame.Surface((480,320))
                    self.world.draw(canvas,camera,player,0)
                    pixel = canvas.get_at((point[0]-camera[0],point[1]-camera[1]))[:3]
                    if visible:self.assertEqual(pixel,color)
                    else:
                        self.assertNotEqual(pixel,color)
                        self.assertEqual(pixel,self.world.ground[0].get_at(point)[:3])

    def test_real_gaps_between_leaves_and_flower_spikes_do_not_erase_the_actor(self):
        color = (251,0,245)
        sprite = pygame.Surface((24,36));sprite.fill(color)
        for position,point,camera in (((62,288),(59,275),(0,64)),
                                      ((519,285),(520,272),(96,64))):
            with self.subTest(gap=point):
                self.assertTrue(self.world.can_stand(position))
                player = SimpleNamespace(position=pygame.Vector2(position),sprite=lambda:sprite)
                canvas = pygame.Surface((480,320))
                self.world.draw(canvas,camera,player,0)
                self.assertEqual(canvas.get_at((point[0]-camera[0],point[1]-camera[1]))[:3],color)


if __name__ == '__main__':unittest.main()
