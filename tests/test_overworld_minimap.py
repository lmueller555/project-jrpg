"""Local cartography, exploration-only HUD, and removed Menu input behavior."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from main import Game
from overworld_minimap import OverworldMinimap
from ui_style import Painter, UIStyle


class ChartFixture:
    def __init__(self):
        self.terrain_calls = []
        self.route_flags = []
        self.icons = []

    def draw_terrain(self, target, rect, center, scale):
        self.terrain_calls.append((pygame.Rect(rect), tuple(center), scale))
        pygame.draw.rect(target, '#587b55', rect)

    def draw_routes(self, target, rect, center, scale, flags=()):
        self.route_flags.append(set(flags))

    def icon(self, key, size):
        self.icons.append(key)
        return None


class OverworldMinimapTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init();pygame.font.init()
        pygame.display.set_mode((960, 640))
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def tearDown(self):
        pygame.quit()

    def fixture(self):
        data = {'id': 'fixture', 'tile_size': 24, 'bounds_tiles': [-128, -128, 256, 256],
                'town': {'id': 'eldenmere', 'tile_position': [-10, -22]},
                'bridge': {'id': 'west_bridge', 'tile_position': [-20, -20],
                           'repair_flag': 'REPAIRED'},
                'gates': [{'id': 'north_gate', 'tile_position': [-10, -30],
                           'clearance_flag': 'RELEASED', 'destination_ready': False}],
                'landmarks': [{'id': 'known', 'kind': 'overlook', 'tile_position': [-8, -20]},
                              {'id': 'unknown', 'kind': 'millrace', 'tile_position': [-12, -20]}]}
        game = SimpleNamespace(world=SimpleNamespace(is_overworld=True, region=data),
            player=SimpleNamespace(position=pygame.Vector2(-240, -480), facing='front'),
            audio=SimpleNamespace(text_scale=1, effects_volume=0),
            map_open=False, on_title=False, _mouse_held=False, household_action=None,
            social=SimpleNamespace(locked=False, active=False, flags=set(), clear_pointer=Mock()),
            overworld_travel=SimpleNamespace(discovered={'eldenmere', 'known'}),
            quest_ui=SimpleNamespace(current_notice=None, journal_open=False))
        game.ui = UIStyle(game)
        return game, OverworldMinimap(game)

    def game(self, size=(960, 640)):
        directory = Path(self.directory.name)
        game = Game(window_size=size, fullscreen=False, start_on_title=False,
                    save_path=directory/'journey.json', settings_path=directory/'settings.json')
        game.audio.set_music(0);game.audio.set_effects(0)
        game.opening_fade = game.transfer_cooldown = 0
        game.quest_ui.current_notice = None
        pygame.event.clear()
        return game

    def depart(self, game):
        game.world = game.overworld_world
        game.player.position.update(game.world.town_exit)
        game.location_seconds = 0
        game.camera.reset()

    @staticmethod
    def screen_point(game, point):
        width, height = game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return (round((width-480*scale)//2+point[0]*scale),
                round((height-320*scale)//2+point[1]*scale))

    @staticmethod
    def event(game, kind, **fields):
        pygame.event.post(pygame.event.Event(kind, **fields))
        return game.handle_events()

    def test_visibility_is_limited_to_unobstructed_regional_exploration(self):
        game, minimap = self.fixture()
        self.assertTrue(minimap.visible)
        game.world.is_overworld = False
        self.assertFalse(minimap.visible)
        game.world.is_overworld = True
        for field in ('on_title', 'map_open', 'household_action'):
            with self.subTest(field=field):
                setattr(game, field, True)
                self.assertFalse(minimap.visible)
                setattr(game, field, False)
        for owner, flag in (('pause', 'is_open'), ('inventory_ui', 'is_open'),
                ('status_ui', 'is_open'), ('lattice_ui', 'is_open'),
                ('world_map_viewer', 'is_open'), ('opening_cinematic', 'active'),
                ('combat', 'active'), ('opening', 'locks_player'),
                ('opening', 'controls_player'), ('opening', 'in_action'),
                ('mill_quest', 'encounter_cutscene_active')):
            with self.subTest(owner=owner, flag=flag):
                setattr(game, owner, SimpleNamespace(**{flag: True}))
                self.assertFalse(minimap.visible)
                setattr(game, owner, SimpleNamespace(**{flag: False}))
        for flag in ('locked', 'active'):
            setattr(game.social, flag, True)
            self.assertFalse(minimap.visible)
            setattr(game.social, flag, False)
        game.quest_ui.journal_open = True
        self.assertFalse(minimap.visible)
        game.quest_ui.journal_open = False
        game.quest_ui.current_notice = {'kind': 'objective'}
        self.assertFalse(minimap.visible)

    def test_negative_coordinates_follow_player_with_same_display_transform(self):
        game, minimap = self.fixture();chart = ChartFixture()
        target = pygame.Surface((960, 640))
        with patch.object(minimap, 'cartography', return_value=chart):
            minimap.draw(target)
            self.assertEqual(minimap.world_to_map(game.player.position), minimap.content_rect.center)
            east = minimap.world_to_map(game.player.position+(24, 0))
            north = minimap.world_to_map(game.player.position+(0, -24))
            self.assertAlmostEqual(east.x-minimap.content_rect.centerx, minimap.content_rect.width/80)
            self.assertLess(north.y, minimap.content_rect.centery)
            game.player.position += (-72, 48)
            minimap.draw(target)
        self.assertEqual(chart.terrain_calls[0][1], (-10, -20))
        self.assertEqual(chart.terrain_calls[1][1], (-13, -18))
        self.assertEqual(chart.terrain_calls[0][0], pygame.Rect(734, 466, 196, 144))
        self.assertAlmostEqual(chart.terrain_calls[0][2], minimap.scale*2)
        self.assertEqual(minimap.world_to_map(game.player.position), minimap.content_rect.center)

    def test_live_passage_states_and_discovered_places_are_drawn_without_progress_changes(self):
        game, minimap = self.fixture();chart = ChartFixture()
        target = pygame.Surface((960, 640));initial = set(game.social.flags)
        with patch.object(minimap, 'cartography', return_value=chart):
            minimap.draw(target)
            self.assertIn('bridge_broken', chart.icons)
            self.assertIn('gate_closed', chart.icons)
            self.assertIn('known', minimap.marker_rects)
            self.assertNotIn('unknown', minimap.marker_rects)
            self.assertEqual(game.social.flags, initial)
            game.social.flags.update(('REPAIRED', 'RELEASED'))
            chart.icons.clear();minimap.draw(target)
            self.assertIn('bridge_repaired', chart.icons)
            self.assertIn('gate_closed', chart.icons)
            self.assertEqual(chart.route_flags[-1], {'REPAIRED', 'RELEASED'})
            game.world.region['gates'][0]['destination_ready'] = True
            chart.icons.clear();minimap.draw(target)
            self.assertIn('gate_open', chart.icons)

        # Exercise the real route renderer as well as the icon selection. The
        # bridge line is away from the centered player, and icons are omitted
        # from this sub-view so a changed symbol cannot conceal a stale road.
        from regional_cartography import RegionalCartography
        game.world.region['bridge'].update(tile_position=[-30, -20],
                                          damage_rect_tiles=[-34, -21, 8, 2])
        game.world.region['roads'] = [{'id': 'west_road', 'kind': 'stone', 'width': 3,
                                      'points': [[-38, -20], [-22, -20]]}]
        actual = RegionalCartography(game.world,
            manifest_path=Path(self.directory.name)/'absent-chart.json')
        sample = game.ui.painter(target).point(minimap.tile_to_map((-30, -20)))
        with patch.object(minimap, 'cartography', return_value=actual), \
                patch.object(minimap, '_places', return_value=[]):
            game.social.flags.clear();minimap.draw(target)
            broken_pixel = target.get_at(sample)
            game.social.flags.add('REPAIRED');minimap.draw(target)
            self.assertNotEqual(target.get_at(sample), broken_pixel,
                                'Repair must restore the road pixels beneath the live bridge marker')

    def test_directional_player_remains_distinct_on_landmark_and_drawing_restores_clip(self):
        game, minimap = self.fixture();chart = ChartFixture()
        game.world.region['town']['tile_position'] = [-10, -20]
        target = pygame.Surface((960, 640))
        clip = pygame.Rect(600, 400, 350, 220);target.set_clip(clip)
        centers = {}
        with patch.object(minimap, 'cartography', return_value=chart):
            for facing in ('front', 'back', 'left', 'right'):
                game.player.facing = facing;target.fill('#0b1310');minimap.draw(target)
                self.assertEqual(target.get_clip(), clip)
                mask = pygame.mask.from_threshold(target, pygame.Color('#fff3ce'), (1, 1, 1, 255))
                bounds = mask.get_bounding_rects()
                self.assertTrue(bounds, 'Player must remain visible atop a town symbol')
                combined = bounds[0].unionall(bounds[1:]);centers[facing] = combined.center
        center = (minimap.content_rect.centerx*2, minimap.content_rect.centery*2)
        self.assertGreater(centers['front'][1], center[1])
        self.assertLess(centers['back'][1], center[1])
        self.assertLess(centers['left'][0], center[0])
        self.assertGreater(centers['right'][0], center[0])

    def test_old_corner_button_is_gone_in_town_and_interior_and_escape_still_pauses(self):
        game = self.game()
        self.assertFalse(hasattr(game, '_hud_menu_rect'))
        self.assertFalse(hasattr(game, 'menu_rect'))
        interior = game._scene_by_id(next(iter(game.town.data['interior_scenes'])))
        for world in (game.town, interior):
            with self.subTest(scene=world.data['id']):
                game.world = world
                self.assertFalse(game.minimap.visible)
                point = self.screen_point(game, (430, 285))
                self.assertTrue(self.event(game, pygame.MOUSEBUTTONDOWN, button=1, pos=point))
                self.assertTrue(self.event(game, pygame.MOUSEBUTTONUP, button=1, pos=point))
                self.assertFalse(game.pause.is_open)
                self.assertTrue(self.event(game, pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
                self.assertTrue(game.pause.is_open)
                self.assertTrue(self.event(game, pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
                self.assertFalse(game.pause.is_open)

    def test_letterboxed_click_opens_atlas_without_leaking_queued_input_or_reopening_after_close(self):
        game = self.game((1100, 750));self.depart(game)
        self.assertTrue(game.minimap.visible)
        self.assertTrue(self.event(game, pygame.MOUSEBUTTONDOWN, button=1, pos=(8, 8)))
        self.assertFalse(game.map_open)
        self.assertTrue(self.event(game, pygame.MOUSEBUTTONUP, button=1, pos=(8, 8)))
        point = self.screen_point(game, game.minimap.rect.center)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEBUTTONDOWN):
            pygame.event.post(pygame.event.Event(kind, button=1, pos=point))
        self.assertTrue(game.handle_events())
        self.assertTrue(game.map_open)
        self.assertFalse(game.pause.is_open)
        self.assertFalse(game._mouse_held)
        self.assertFalse(game.minimap.visible)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, repeat=False))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        self.assertTrue(game.handle_events())
        self.assertFalse(game.map_open, 'Queued corner click must not reopen the atlas')
        self.assertFalse(game.pause.is_open)
        self.assertTrue(game.minimap.visible)

    def test_full_atlas_and_minimap_share_the_same_art_service(self):
        from regional_cartography import get_cartography
        game = self.game();self.depart(game)
        chart = game.minimap.cartography()
        self.assertIs(chart, get_cartography(game))
        game.map_open = True;game.map_ui.reset()
        self.assertIs(chart, get_cartography(game))
        game.map_open = False
        game.player.position += (48, -24)
        self.assertIs(chart, game.minimap.cartography())

    def test_hint_and_save_notice_reserve_the_real_minimap_bounds_at_large_text(self):
        game = self.game();self.depart(game)
        game.audio.text_scale = 1.5
        game.save_error = 'A write failed'
        game.overworld_travel.interaction_hint = lambda: 'E: Speak with the road guard about the northern checkpoint'
        rectangles = []
        original = Painter.panel
        def record(painter, rect, *args, **kwargs):
            rectangles.append(pygame.Rect(rect))
            return original(painter, rect, *args, **kwargs)
        with patch.object(game.minimap, 'cartography', return_value=ChartFixture()), \
                patch.object(Painter, 'panel', record):
            game.draw()
        alert = next(rect for rect in rectangles if rect.width == 456)
        self.assertLess(alert.bottom, game.minimap.rect.top)
        hints = [rect for rect in rectangles if rect.x == 12 and rect.bottom == 308]
        self.assertTrue(hints)
        self.assertTrue(all(rect.right < game.minimap.rect.left for rect in hints))


if __name__ == '__main__':
    unittest.main()
