"""Clear scenery must accept real feet, including ground outside the old roads.

The coordinates below were read from the retained ground painting and reviewed
cloister floor patch, independently of the navigation recipe. They include lawn, path shoulders and
the floor under the cloister rather than only landmark approach points.
"""
from collections import deque
import json
import os
from pathlib import Path
import random
import tempfile
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from main import Game, Player, World, camera_for

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT/'assets/maps/elden_vale_sanctuary/map.json'

# Independent observations of visible ground and the reviewed opening floors.
VISIBLE_GROUND = {
    'north-west shoulder': (430, 81),
    'grass behind the hall': (510, 120),
    'north-east grass': (808, 96),
    'north-east shoulder': (958, 104),
    'shaded grove lawn': (220, 385),
    'grove inner lawn': (355, 385),
    'grove south lawn': (300, 571),
    'south-west flowers and grass': (309, 603),
    'south court shoulder': (598, 575),
    'survey inner lawn': (917, 610),
    'survey east lawn': (1050, 590),
    'cloister west bay': (666, 302),
    'cloister middle-west bay': (717, 302),
    'cloister middle-east bay': (771, 302),
    'cloister west rear floor': (666, 291),
    'cloister middle-west rear floor': (717, 291),
    'cloister middle-east rear floor': (771, 291),
}

# Cross an old road edge directly; an A* detour would hide the original fault.
FREE_CROSSINGS = {
    'north shoulder': ((430, 96), (430, 73)),
    'shaded grove': ((250, 370), (220, 370)),
    'south grove lawn': ((336, 571), (300, 571)),
    'south-west grass': ((339, 603), (309, 603)),
    'survey lawn': ((917, 634), (917, 610)),
    'cloister west opening': ((666, 326), (666, 291)),
    'cloister middle-west opening': ((717, 320), (717, 291)),
    'cloister middle-east opening': ((771, 315), (771, 291)),
}


def walk_player(player, world, target):
    """Steer the production 24×12 player straight to a point, without routing."""
    target = pygame.Vector2(target)
    for _ in range(2000):
        delta = target-player.position
        if delta.length() < .02:
            return
        before = player.position.copy()
        player.update(delta, min(.035, delta.length()/72), world)
        if player.position == before:
            raise AssertionError(('Invisible obstacle during straight movement',
                                  tuple(before), tuple(target)))
        if not world.can_stand(player.position):
            raise AssertionError(('Full player feet overlap a blocker', tuple(player.position)))
    raise AssertionError(('Straight movement exceeded budget', tuple(target)))


def full_foot_flood(world, step=6):
    """Sample the complete map, checking every pixel of each cardinal edge."""
    clear = {(x, y) for y in range(step, world.size[1], step)
             for x in range(step, world.size[0], step) if world.can_stand((x, y))}
    start = tuple(round(value/step)*step for value in world.data['spawn'])
    if start not in clear:
        raise AssertionError(('Flood spawn blocked', start))
    seen = {start};pending = deque([start])
    while pending:
        x, y = pending.popleft()
        for dx, dy in ((step, 0), (-step, 0), (0, step), (0, -step)):
            other = x+dx, y+dy
            if other in seen or other not in clear:
                continue
            if not all(world.can_stand((x+dx*i/step, y+dy*i/step))
                       for i in range(1, step+1)):
                continue
            seen.add(other);pending.append(other)
    return clear, seen


class ReserveFreeRoamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();pygame.display.set_mode((480, 320))
        cls.world = World(MAP)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_independent_visible_lawns_accept_the_complete_player(self):
        self.assertEqual(self.world.probe_size, (24, 12))
        for label, point in VISIBLE_GROUND.items():
            with self.subTest(ground=label):
                self.assertTrue(self.world.can_stand(point), (label, point))

    def test_player_crosses_former_corridor_edges_in_both_directions(self):
        player = Player(self.world)
        for label, (start, end) in FREE_CROSSINGS.items():
            with self.subTest(ground=label):
                self.assertTrue(self.world.can_stand(start), (label, start))
                player.position.update(start)
                walk_player(player, self.world, end)
                walk_player(player, self.world, start)

    def test_manual_steering_explores_ground_around_the_grass_samples(self):
        player = Player(self.world);rng = random.Random(24012)
        # Short freely steered walks around clear grass exercise arbitrary
        # directions and fractional feet, rather than a navigation mesh route.
        for label in ('north-west shoulder', 'shaded grove lawn',
                      'south-west flowers and grass', 'survey inner lawn'):
            origin = pygame.Vector2(VISIBLE_GROUND[label])
            player.position.update(origin)
            for _ in range(24):
                target = origin+pygame.Vector2(rng.uniform(-4, 4), rng.uniform(-4, 4))
                walk_player(player, self.world, target)
            walk_player(player, self.world, origin)

    def test_broad_full_foot_flood_reaches_visual_ground_and_public_approaches(self):
        clear, reached = full_foot_flood(self.world)
        self.assertGreater(len(reached), 8000, 'Only a narrow road network is open')
        for label, point in {**VISIBLE_GROUND, **self.world.data['public_approaches']}.items():
            nearest = min(clear, key=lambda p:(p[0]-point[0])**2+(p[1]-point[1])**2)
            self.assertLessEqual(pygame.Vector2(nearest).distance_to(point), 5, label)
            self.assertIn(nearest, reached, (label, point, nearest))

    def test_visible_physical_bases_stop_running_crossings(self):
        player = Player(self.world)
        for name, start, direction, axis, boundary in (
                ('hall wall', (470, 362), (0, -1), 1, 337),
                ('basin', (750, 383), (0, -1), 1, 345),
                ('western oak roots', (59, 382), (1, 0), 0, 100),
                ('cliff face', (698, 481), (0, -1), 1, 437),
                ('southern stone wall', (670, 635), (0, 1), 1, 695),
                ('cloister back wall', (666, 302), (0, -1), 1, 284),
                ('cloister column', (666, 302), (1, 0), 0, 685),
                ('eastern cloister worktable', (824, 330), (0, -1), 1, 315),
                ('visible cave rail', (1008, 406), (0, -1), 1, 377)):
            with self.subTest(solid=name):
                self.assertTrue(self.world.can_stand(start), (name, start))
                player.position.update(start)
                player.update(direction, 2, self.world, running=True)
                self.assertTrue(self.world.can_stand(player.position), name)
                if direction[axis] < 0:
                    self.assertGreater(player.position[axis], boundary, (name, player.position))
                else:
                    self.assertLess(player.position[axis], boundary, (name, player.position))
        for point in ((822,303), (808,309), (843,315), (875,309)):
            self.assertFalse(self.world.can_stand(point), ('Solid garden workstation', point))
        for x in (666,717,771):
            self.assertFalse(self.world.can_stand((x,286)), ('Visible rear wall base', x))

    def test_open_bay_feet_rest_on_revised_floor_instead_of_original_masonry(self):
        # The retained painting has masonry across the upper half of each of
        # these 24×12 feet. A reviewed floor patch must replace those pixels in
        # the actual renderer before those standing spots are treated as open.
        invisible = SimpleNamespace(position=pygame.Vector2(), story_visible=False)
        original = pygame.image.load(str(ROOT/'assets/terrain/elden_vale_sanctuary/ground.png')).convert()
        for feet in ((666,302), (717,302), (771,302)):
            with self.subTest(feet=feet):
                camera = camera_for(feet, self.world.size)
                canvas = pygame.Surface((480, 320))
                self.world.draw(canvas, camera, invisible, 0)
                rect = self.world.probe_rect(feet)
                former_wall = [(x,y) for y in range(rect.top, rect.centery)
                               for x in range(rect.left, rect.right)]
                changed = sum(canvas.get_at((x-camera[0],y-camera[1]))
                              != original.get_at((x,y)) for x,y in former_wall)
                self.assertGreater(changed/len(former_wall), .9,
                                   ('Player feet still overlap the original painted masonry', feet))

    def test_new_cloister_floor_and_ground_behind_the_roof_preserve_depth(self):
        player = Player(self.world);player.facing = 'front'
        for feet, point, hidden in (((717, 302), (717, 282), False),
                                    ((717, 269), (717, 249), True),
                                    ((510, 180), (510, 160), True)):
            with self.subTest(feet=feet):
                player.position.update(feet)
                self.assertTrue(self.world.can_stand(feet))
                camera = camera_for(feet, self.world.size)
                before = pygame.Surface((480, 320));after = pygame.Surface((480, 320))
                self.world.draw(before, camera, SimpleNamespace(position=player.position,
                                                               story_visible=False), 0)
                self.world.draw(after, camera, player, 0)
                actor = player.sprite().get_at((point[0]-feet[0]+12, point[1]-feet[1]+30))
                self.assertEqual(actor.a, 255)
                screen = point[0]-camera[0], point[1]-camera[1]
                scenery = before.get_at(screen)
                self.assertNotEqual(scenery, actor)
                self.assertEqual(after.get_at(screen), scenery if hidden else actor)

    def test_legacy_save_at_formerly_blocked_grass_continues_and_can_move(self):
        # Only the historical location is synthesized. The ordinary new-game
        # progression and equipment are retained byte-for-byte in the save.
        with tempfile.TemporaryDirectory(prefix='reserve-old-location-') as temporary:
            save = Path(temporary)/'journey.json';settings = Path(temporary)/'settings.json'
            game = Game(window_size=(480, 320), fullscreen=False, start_on_title=False,
                        save_path=save, settings_path=settings)
            self.assertTrue(game.save_progress())
            payload = json.loads(save.read_text())
            payload['player'].update(scene='elden_vale_sanctuary', position=[309, 603])
            save.write_text(json.dumps(payload)+'\n')
            restored = Game(window_size=(480, 320), fullscreen=False, start_on_title=True,
                            save_path=save, settings_path=settings)
            self.assertTrue(restored.begin_journey(True))
            self.assertEqual(restored.world.data['id'], 'elden_vale_sanctuary')
            self.assertEqual(tuple(restored.player.position), (309, 603))
            restored.update(.6, (0, 0), False)
            before = restored.player.position.copy()
            restored.update(.15, (1, 0), False)
            self.assertGreater(restored.player.position.x, before.x+9)
            self.assertTrue(restored.world.can_stand(restored.player.position))
            game.music.stop();restored.music.stop()


if __name__ == '__main__':
    unittest.main()
