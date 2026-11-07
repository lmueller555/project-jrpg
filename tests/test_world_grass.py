"""The normal exploration world owns vegetation contact, depth and its clock."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from grass_demo import GrassDemoWorld
from interactive_grass import InteractiveGrass
from main import Game, Player, ROOT, World, read_json


DEMO_MAP = ROOT/'assets/maps/grass_demo/map.json'
GRASS_MANIFEST = ROOT/'assets/terrain/grass_demo/assets.json'


def attach_grass(world, position):
    """Place one real approved clump without depending on final map density."""
    world.entities = [record for record in world.entities if 'grass_instance' not in record]
    world.grass = InteractiveGrass(read_json(GRASS_MANIFEST), [
        {'id': 'contact', 'position': list(position), 'variant': 'fan'}], world.image)
    world.entities.extend(world.grass.entity_records)
    return world.grass


def person(position, **kwargs):
    return SimpleNamespace(position=pygame.Vector2(position), facing='front', **kwargs)


class WorldGrassTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.display.set_mode((480, 320))
        self.addCleanup(pygame.quit)

    def test_normal_world_loads_map_grass_once_and_keeps_vegetation_nonblocking(self):
        world = World(DEMO_MAP)
        self.assertEqual(len(world.grass.clumps), len(world.data['grass']['instances']))
        records = [record for record in world.entities if 'grass_instance' in record]
        self.assertEqual(len(records), 2*len(world.grass.clumps))
        self.assertEqual(len({record['id'] for record in records}), len(records))
        demo = GrassDemoWorld(DEMO_MAP)
        self.assertEqual(len(demo.entities), len(world.entities))
        root = world.grass.clumps[0].position
        self.assertTrue(world.can_stand(root))
        player = Player(world)
        player.position.update(root)
        world.update_grass(.2, player)
        self.assertTrue(world.can_stand(root))
        self.assertGreater(world.grass.clumps[0].strength, 0)

    def test_visible_scene_npc_and_party_contact_excludes_hidden_authored_duplicate(self):
        world = World(DEMO_MAP)
        grass = attach_grass(world, (240, 312))
        npc = person((240, 312))
        hidden = person((240, 312), story_visible=False)
        authored_duplicate = person((240, 312), party_travelling=True)
        companion = person((246, 312))
        world.npcs = [npc, hidden, authored_duplicate]
        world.update_grass(.2, None, (companion,))
        self.assertEqual(grass.clumps[0].occupants, {id(npc), id(companion)})
        world.npcs = []
        world.update_grass(1., None, ())
        self.assertEqual(grass.clumps[0].strength, 0)
        self.assertEqual(grass.clumps[0].occupants, set())

    def test_story_staging_uses_the_rendered_foot_position(self):
        world = World(DEMO_MAP)
        grass = attach_grass(world, (240, 312))
        actor = person((400, 312), story_position=pygame.Vector2(240, 312))
        world.update_grass(.2, actor)
        self.assertEqual(grass.clumps[0].occupants, {id(actor)})
        self.assertEqual(tuple(actor.position), (400, 312))

    def test_map_without_grass_has_no_extra_entities_and_keeps_draw_behavior(self):
        world = World(ROOT/'assets/maps/eldenmere/building_interiors/rooms/sanctuary_bedroom/map.json')
        self.assertIsNone(world.grass)
        count = len(world.entities)
        player = Player(world)
        world.update_grass(.2, player, reduced_motion=True)
        world.draw(pygame.Surface((480, 320)), (0, 0), player, 200, False)
        self.assertTrue(world.reduced_motion)
        self.assertEqual(len(world.entities), count)


class GameGrassTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(pygame.quit)
        path = Path(self.directory.name)
        self.game = Game(fullscreen=False, start_on_title=False,
                         save_path=path/'journey.json', settings_path=path/'settings.json')
        self.game.audio.set_music(0)
        self.game.audio.set_effects(0)
        self.game.opening.restore({'version': 1, 'stage': 'disabled'})
        self.game.opening_fade = self.game.transfer_cooldown = 0
        self.game.world = self.game.town
        self.game.player.position.update(self.game.town.data['spawn'])
        self.grass = attach_grass(self.game.world, self.game.player.position)

    def test_game_samples_after_player_and_party_motion_and_freezes_in_modal_menus(self):
        game = self.game
        positions = []
        original = game.world.update_grass
        def observed(seconds, player=None, party_actors=(), **kwargs):
            positions.append((tuple(player.position), tuple(party_actors)))
            return original(seconds, player, party_actors, **kwargs)
        with patch.object(game.world, 'update_grass', side_effect=observed), \
                patch.object(game.party_travel, 'update', wraps=game.party_travel.update) as party_update:
            start = game.player.position.copy()
            game.update(.1, (1, 0), True)
            self.assertGreater(game.player.position.x, start.x)
            self.assertEqual(positions[-1][0], tuple(game.player.position))
            party_update.assert_called_once_with(.1)
        self.assertEqual(self.grass.clumps[0].occupants, {id(game.player)})
        for name in ('pause', 'inventory_ui', 'party_ui', 'world_map_viewer'):
            with self.subTest(menu=name):
                menu = getattr(game, name)
                before = self.grass.snapshot()
                menu.is_open = True
                game.update(.5, (1, 0), True)
                self.assertEqual(self.grass.snapshot(), before)
                menu.is_open = False
        game.audio.set_reduced_motion(True)
        clock = self.grass.elapsed_ms
        game.update(.2, (0, 0), False)
        self.assertEqual(self.grass.elapsed_ms, clock)
        self.assertTrue(self.grass.reduced_motion)
        self.assertEqual(self.grass.clumps[0].strength, 1)

    def test_scene_change_releases_old_contact_and_reentry_never_sweeps_a_teleport(self):
        game = self.game
        game._update_grass(.2)
        self.assertEqual(self.grass.clumps[0].occupants, {id(game.player)})
        origin = game.world
        destination = next(scene for scene in game.scenes.values() if scene is not origin)
        game.world = destination
        game.player.position.update(destination.data['spawn'])
        game._update_grass(1.)
        self.assertEqual(self.grass.clumps[0].occupants, set())
        self.assertEqual(self.grass.clumps[0].strength, 0)
        self.assertNotIn(id(game.player), self.grass._previous_positions)
        count = self.grass.clumps[0].activations
        game.world = origin
        game.player.position.update(pygame.Vector2(origin.data['spawn'])+(90, 0))
        game._update_grass(.2)
        self.assertEqual(self.grass.clumps[0].activations, count)

    def test_continue_in_same_map_clears_old_feet_without_replacing_cached_scenery(self):
        game = self.game
        world = game.world
        saved = game.player.position.copy()
        previous = next(saved+pygame.Vector2(dx, dy)*90
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if world.can_stand(saved+pygame.Vector2(dx, dy)*90))
        grass = attach_grass(world, saved.lerp(previous, .5))
        records = tuple(grass.entity_records)
        cached_images = dict(world._images)
        self.assertTrue(game.save_progress())
        game.player.position.update(previous)
        game._update_grass(.2)
        self.assertIn(id(game.player), grass._previous_positions)
        game.audio.set_reduced_motion(True)
        self.assertTrue(game.begin_journey(True))
        self.assertIs(game.world, world)
        self.assertEqual(game.player.position, saved)
        self.assertIs(world.grass, grass)
        self.assertEqual(grass._previous_positions, {})
        self.assertEqual(grass.elapsed_ms, 0)
        self.assertTrue(grass.reduced_motion)
        self.assertEqual(grass.clumps[0].occupants, set())
        for old, current in zip(records, grass.entity_records):self.assertIs(current, old)
        for key, image in cached_images.items():self.assertIs(world._images[key], image)
        game._update_grass(.2)
        self.assertEqual(grass.clumps[0].activations, 0,
                         'Reloading must not sweep the previous journey through this midpoint')

    def test_new_journey_clears_contact_in_all_reused_scene_worlds(self):
        game = self.game
        game._update_grass(.2)
        self.assertGreater(self.grass.clumps[0].strength, 0)
        self.assertTrue(game.begin_journey(False, show_cinematic=False))
        self.assertEqual(self.grass._previous_positions, {})
        self.assertEqual(self.grass.clumps[0].strength, 0)
        self.assertEqual(self.grass.clumps[0].activations, 0)
        self.assertEqual(self.grass.clumps[0].occupants, set())


if __name__ == '__main__':unittest.main()
