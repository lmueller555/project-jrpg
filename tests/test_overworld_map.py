"""Regional cartography stays bounded, geographically correct, and modal."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
                  PYGAME_HIDE_SUPPORT_PROMPT='1')

import pygame

from map_ui import MapUI
from overworld_map import FIELD_STYLES, PAPER, RegionalMapUI
from ui_style import UIStyle


ROOT = Path(__file__).resolve().parents[1]


class MetadataOnlyRegion:
    is_overworld = True

    def __init__(self, data):self.region = self.data = data

    @property
    def overview(self):raise AssertionError('Regional map must never render the world')

    def draw(self, *args, **kwargs):raise AssertionError('No chunk rendering in a map')


class RegionalMapTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        window = pygame.display.set_mode((1100, 750))
        self.data = json.loads((ROOT/'assets/maps/overworld/elden_vale/region.json').read_text())
        town_data = json.loads((ROOT/'assets/maps/eldenmere/playable/map.json').read_text())
        town = SimpleNamespace(data=town_data, size=town_data['size_pixels'])
        self.game = SimpleNamespace(world=MetadataOnlyRegion(self.data), town=town, window=window,
            player=SimpleNamespace(position=pygame.Vector2(12*24, -20*24)),
            exterior_position=pygame.Vector2(516, 1284), map_open=True,
            audio=SimpleNamespace(text_scale=1, reduced_motion=False, effects_volume=0),
            social=SimpleNamespace(flags=set()), quest_ui=SimpleNamespace(draw_map_markers=Mock()))
        def to_canvas(point):
            width, height = self.game.window.get_size()
            scale = max(1, min(width//480, height//320))
            x, y = ((point[0]-(width-480*scale)//2)/scale,
                    (point[1]-(height-320*scale)//2)/scale)
            return (x, y) if 0 <= x < 480 and 0 <= y < 320 else None
        self.game.to_canvas = to_canvas
        self.game.ui = UIStyle(self.game)
        self.map_ui = MapUI(self.game)
        self.map = self.map_ui._regional_map

    def tearDown(self):pygame.quit()

    def event(self, kind, **values):
        return self.map_ui.handle_event(pygame.event.Event(kind, **values))

    def screen_point(self, point):
        width, height = self.game.window.get_size()
        scale = max(1, min(width//480, height//320))
        return (round((width-480*scale)//2+point[0]*scale),
                round((height-320*scale)//2+point[1]*scale))

    def test_negative_global_origin_preserves_player_and_landmark_coordinates(self):
        x, y, width, height = self.data['bounds_tiles']
        northwest = self.map.world_to_map((x*24, y*24))
        southeast = self.map.world_to_map(((x+width)*24, (y+height)*24))
        # Fit now frames the inhabited vale, not all distant authored context.
        # Signed world coordinates retain their exact aspect and inverse map.
        fx,fy,fw,fh = self.map.focus_bounds
        self.assertTrue(self.map.map_rect.collidepoint(self.map.tile_to_map((fx,fy))))
        self.assertTrue(self.map.map_rect.collidepoint(self.map.tile_to_map((fx+fw,fy+fh))))
        self.assertAlmostEqual((southeast[0]-northwest[0])/(southeast[1]-northwest[1]), width/height)
        for record in self.map.landmarks:
            with self.subTest(landmark=record['id']):
                point = self.map.tile_to_map(record['tile_position'])
                self.assertTrue(self.map.map_rect.collidepoint(point))
                self.assertTrue(self.map.marker_rects[record['id']].collidepoint(point))
        player = self.map.world_to_map(self.game.player.position)
        self.assertEqual(player, self.map.tile_to_map((12, -20)))
        self.assertLess(player[1], self.map.tile_to_map((12, 0))[1])
        self.assertLess(self.map.tile_to_map((-111, 30))[0], player[0])

    def test_zoom_keeps_pointer_anchor_and_drag_is_clamped_and_released(self):
        point = (self.map.map_rect.centerx+18, self.map.map_rect.centery-12)
        before = self.map.map_to_tile(point)
        self.map.zoom_at(point, 3)
        self.assertLess(self.map.map_to_tile(point).distance_to(before), .001)
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=self.screen_point(self.map.map_rect.center))
        self.event(pygame.MOUSEMOTION, pos=self.screen_point((300, 270)))
        self.event(pygame.MOUSEBUTTONUP, button=1, pos=self.screen_point((300, 270)))
        center = self.map.center.copy()
        self.event(pygame.MOUSEMOTION, pos=self.screen_point((40, 80)))
        self.assertEqual(self.map.center, center)
        self.map.zoom_at(point, 1000)
        self.assertEqual(self.map.zoom, self.map.MAX_ZOOM)
        self.map.zoom_at(point, -1000)
        self.assertEqual(self.map.zoom, self.map.min_zoom)
        self.assertEqual(self.map.center, pygame.Vector2(0, 0))

    def test_zoom_out_reaches_authored_context_while_fit_keeps_the_useful_vale(self):
        self.map.fit()
        self.assertEqual(self.map.zoom,1)
        # At this aspect the context eventually clamps horizontally. A point
        # on the horizontal centre keeps both coordinates free on the first
        # zoom-out step and verifies the genuine pointer anchor.
        point = (self.map.map_rect.centerx,self.map.map_rect.centery+16)
        before = self.map.map_to_tile(point)
        self.map.zoom_at(point,-1)
        self.assertLess(self.map.zoom,1)
        self.assertGreater(self.map.zoom,self.map.min_zoom)
        self.assertLess(self.map.map_to_tile(point).distance_to(before),.001)
        self.map.zoom_at(point,-100)
        x,y,width,height = self.map.bounds
        self.assertTrue(self.map.map_rect.collidepoint(self.map.tile_to_map((x,y))))
        self.assertTrue(self.map.map_rect.collidepoint(self.map.tile_to_map((x+width,y+height))))
        context_scale = self.map.scale
        self.map.fit()
        self.assertEqual(self.map.zoom,1)
        self.assertGreater(self.map.scale,context_scale)

    def test_letterboxed_hover_select_close_and_repeat_controls(self):
        record = next(record for record in self.map.landmarks if record['kind'] == 'bridge')
        point = self.screen_point(self.map.marker_rects[record['id']].center)
        self.event(pygame.MOUSEMOTION, pos=point)
        self.assertEqual(self.map.landmarks[self.map.hovered]['id'], record['id'])
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=point)
        self.event(pygame.MOUSEBUTTONUP, button=1, pos=point)
        self.assertEqual(self.map.selected_landmark['id'], record['id'])
        selected = self.map.selected
        self.event(pygame.KEYDOWN, key=pygame.K_RIGHT, repeat=True)
        self.assertEqual(self.map.selected, selected)
        self.event(pygame.KEYDOWN, key=pygame.K_RIGHT, repeat=False)
        self.assertEqual(self.map.selected, (selected+1) % len(self.map.landmarks))
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0))
        self.assertTrue(self.game.map_open)
        self.event(pygame.MOUSEBUTTONDOWN, button=1, pos=self.screen_point(self.map.close_rect.center))
        self.assertFalse(self.game.map_open)
        self.assertFalse(self.event(pygame.KEYDOWN, key=pygame.K_RIGHT, repeat=False))

    def test_discovery_and_progress_markers_reflect_controller_without_mutating_manifest(self):
        self.game.overworld_travel = SimpleNamespace(discovered={'eldenmere'})
        self.map.reset()
        self.assertEqual({record['kind'] for record in self.map.landmarks}, {'town', 'bridge', 'checkpoint'})
        identifier = self.data['landmarks'][0]['id']
        self.game.overworld_travel.discovered.add(identifier)
        self.map.reset()
        self.assertIn(identifier, {record['id'] for record in self.map.landmarks})
        bridge = next(record for record in self.map.landmarks if record['kind'] == 'bridge')
        self.assertIn('broken', self.map._description(bridge))
        self.game.social.flags.add(bridge['repair_flag'])
        self.assertIn('passable', self.map._description(bridge))
        self.assertNotIn('kind', self.data['bridge'])
        checkpoint = next(record for record in self.map.landmarks if record['kind'] == 'checkpoint')
        canvas = pygame.Surface((480, 320))
        painter = self.game.ui.painter(canvas)
        center = painter.point(self.map.tile_to_map(checkpoint['tile_position']))
        for clearance, destination_ready in ((False, False), (False, True), (True, False), (True, True)):
            with self.subTest(clearance=clearance, destination_ready=destination_ready):
                if clearance:self.game.social.flags.add(checkpoint['clearance_flag'])
                else:self.game.social.flags.discard(checkpoint['clearance_flag'])
                checkpoint['destination_ready'] = destination_ready
                canvas.fill('#e8d8ad')
                self.map._draw_marker(painter, checkpoint)
                closed = not (clearance and destination_ready)
                self.assertEqual(canvas.get_at(center)[:3] == (139, 79, 62), closed)
                self.assertEqual('closed' in self.map._description(checkpoint), closed)

    def test_display_resize_large_text_and_long_description_remain_bounded_and_scrollable(self):
        before = json.dumps(self.data, sort_keys=True)
        self.game.audio.text_scale = 1.5
        self.map.selected = next(i for i, record in enumerate(self.map.landmarks)
                                 if record['id'] == self.data['landmarks'][0]['id'])
        self.map.select_landmark(self.data['landmarks'][0]['id'])
        self.map.selected_landmark['description'] = 'A long woodland description with a clear view. '*25
        for size in ((480, 320), (960, 640), (1280, 720)):
            with self.subTest(size=size):
                self.game.window = pygame.display.set_mode(size)
                canvas = pygame.Surface(size)
                clip = canvas.get_rect().inflate(-2, -2)
                canvas.set_clip(clip)
                self.map_ui.draw(canvas)
                self.assertEqual(canvas.get_clip(), clip)
                self.assertGreater(self.map.detail_max_scroll, 0)
                self.assertTrue(self.map.map_rect.contains(self.map.detail_panel))
                self.assertFalse(self.map.detail_panel.colliderect(
                    self.map.marker_rects[self.map.selected_landmark['id']]))
                self.event(pygame.KEYDOWN, key=pygame.K_END, repeat=False)
                self.assertEqual(self.map.detail_scroll, self.map.detail_max_scroll)
                self.map_ui.draw(canvas)
        self.assertEqual(json.dumps(self.data, sort_keys=True), before)
        self.game.quest_ui.draw_map_markers.assert_not_called()

    def test_overview_prioritizes_geography_and_keeps_major_labels_visible(self):
        canvas = pygame.Surface((960,640))
        self.map_ui.draw(canvas)
        self.assertFalse(self.map.details_visible)
        self.assertGreater(self.map.map_rect.width*self.map.map_rect.height,480*320*.65)
        major = {record['id'] for record in self.map.landmarks
                 if record['kind'] in ('town','bridge','checkpoint')}
        self.assertTrue(major <= self.map.label_rects.keys())
        rectangles = [self.map.label_rects[key] for key in major]
        for index,rect in enumerate(rectangles):
            self.assertTrue(self.map.map_rect.contains(rect))
            self.assertFalse(any(rect.colliderect(other) for other in rectangles[index+1:]))

    def test_place_card_wheel_and_close_do_not_move_the_geography(self):
        record = next(item for item in self.map.landmarks if item['kind']=='bridge')
        self.map.select_landmark(record['id'])
        record['description'] = 'Longer description. '*100
        # The bridge uses its operational description; use an ordinary known
        # landmark to exercise genuinely scrollable content.
        ordinary = next(item for item in self.map.landmarks if item['kind']=='overlook')
        ordinary['description'] = 'A wooded trail beside the valley. '*100
        self.map.select_landmark(ordinary['id'])
        self.map_ui.draw(pygame.Surface((960,640)))
        zoom = self.map.zoom;center = self.map.center.copy()
        point = self.screen_point(self.map.detail_rect.center)
        self.event(pygame.MOUSEWHEEL,y=-2,precise_y=-2,pos=point)
        self.assertGreater(self.map.detail_scroll,0)
        self.assertEqual(self.map.zoom,zoom)
        self.assertEqual(self.map.center,center)
        self.event(pygame.MOUSEBUTTONDOWN,button=1,pos=self.screen_point(self.map.detail_close_rect.center))
        self.assertFalse(self.map.details_visible)

    def test_legacy_wheel_buttons_scroll_the_card_and_zoom_only_over_the_map(self):
        ordinary = next(item for item in self.map.landmarks if item['kind']=='overlook')
        ordinary['description'] = 'A quiet woodland trail. '*100
        self.map.select_landmark(ordinary['id'])
        self.map_ui.draw(pygame.Surface((960,640)))
        zoom = self.map.zoom;center = self.map.center.copy()
        point = self.screen_point(self.map.detail_rect.center)
        self.event(pygame.MOUSEBUTTONDOWN,button=5,pos=point)
        self.assertGreater(self.map.detail_scroll,0)
        self.assertEqual(self.map.zoom,zoom)
        self.assertEqual(self.map.center,center)
        self.event(pygame.MOUSEBUTTONDOWN,button=4,pos=point)
        self.assertEqual(self.map.detail_scroll,0)
        map_point = self.screen_point((self.map.map_rect.left+20,self.map.map_rect.top+20))
        self.assertFalse(self.map.detail_panel.collidepoint(self.map._point(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=5,pos=map_point))))
        self.event(pygame.MOUSEBUTTONDOWN,button=5,pos=map_point)
        self.assertLess(self.map.zoom,zoom)

    def test_dragging_from_a_marker_does_not_open_its_card_and_label_click_selects(self):
        self.map_ui.draw(pygame.Surface((960,640)))
        town = next(item for item in self.map.landmarks if item['kind']=='town')
        point = self.map.marker_rects[town['id']].center
        self.map.zoom_at(point,2)
        self.map_ui.draw(pygame.Surface((960,640)))
        point = self.map.marker_rects[town['id']].center
        self.event(pygame.MOUSEBUTTONDOWN,button=1,pos=self.screen_point(point))
        self.event(pygame.MOUSEMOTION,pos=self.screen_point((point[0]+20,point[1]+10)))
        self.event(pygame.MOUSEBUTTONUP,button=1,pos=self.screen_point((point[0]+20,point[1]+10)))
        self.assertFalse(self.map.details_visible)
        self.map.fit();self.map_ui.draw(pygame.Surface((960,640)))
        bridge = next(item for item in self.map.landmarks if item['kind']=='bridge')
        point = self.screen_point(self.map.label_rects[bridge['id']].center)
        self.event(pygame.MOUSEBUTTONDOWN,button=1,pos=point)
        self.event(pygame.MOUSEBUTTONUP,button=1,pos=point)
        self.assertTrue(self.map.details_visible)
        self.assertEqual(self.map.selected_landmark['id'],bridge['id'])

    def test_directional_player_remains_distinct_on_a_selected_landmark(self):
        town = next(item for item in self.map.landmarks if item['kind']=='town')
        self.game.player.position.update(pygame.Vector2(town['tile_position'])*24)
        self.map.select_landmark(town['id'])
        pictures = []
        for facing in ('back','right','front','left'):
            self.game.player.facing = facing
            canvas = pygame.Surface((960,640));self.map_ui.draw(canvas)
            painter = self.game.ui.painter(canvas)
            point = painter.point(self.map.world_to_map(self.game.player.position))
            patch_rect = pygame.Rect(point[0]-14,point[1]-14,28,28)
            pictures.append(pygame.image.tobytes(canvas.subsurface(patch_rect),'RGB'))
            self.assertIn(canvas.get_at(point)[:3],((217,170,70),(255,245,213),(52,67,55)))
            self.assertFalse(self.map.detail_panel.collidepoint(self.map.world_to_map(self.game.player.position)))
        self.assertEqual(len(set(pictures)),4)

    def test_priority_labels_survive_large_text_and_each_selected_place_card(self):
        major = {record['id'] for record in self.map.landmarks
                 if record['kind'] in ('town','bridge','checkpoint')}
        for size in ((480,320),(960,640),(1280,720)):
            for text_scale in (1,1.5):
                self.game.window = pygame.display.set_mode(size)
                self.game.audio.text_scale = text_scale
                for identifier in (None,*sorted(major)):
                    self.map.fit()
                    if identifier:self.map.select_landmark(identifier)
                    self.map_ui.draw(pygame.Surface(size))
                    for zoom in (1,self.map.min_zoom,(1+self.map.min_zoom)/2):
                        with self.subTest(size=size,text_scale=text_scale,selected=identifier,zoom=zoom):
                            self.map.zoom = zoom
                            self.map._clamp()
                            self.map_ui.draw(pygame.Surface(size))
                            self.assertTrue(major <= self.map.label_rects.keys())
                            rectangles = [self.map.label_rects[key] for key in major]
                            for index,rect in enumerate(rectangles):
                                self.assertTrue(self.map.map_rect.contains(rect))
                                self.assertFalse(any(rect.colliderect(other) for other in rectangles[index+1:]))
                                if identifier:self.assertFalse(rect.colliderect(self.map.detail_panel))

    def test_card_shortens_to_keep_selected_bridge_and_player_visible_when_panned(self):
        self.game.window = pygame.display.set_mode((480,320))
        self.game.audio.text_scale = 1.5
        self.map.zoom = 1.25
        self.map.center.update(-60,0)
        self.map.select_landmark('western_stone_bridge')
        self.map_ui.draw(pygame.Surface((480,320)))
        selected = self.map.marker_rects['western_stone_bridge']
        self.assertFalse(self.map.detail_panel.colliderect(selected))
        self.assertFalse(self.map.detail_panel.collidepoint(self.map.world_to_map(self.game.player.position)))
        self.assertLess(self.map.detail_panel.height,148)
        self.assertGreater(self.map.detail_max_scroll,0)
        self.event(pygame.KEYDOWN,key=pygame.K_END,repeat=False)
        self.assertEqual(self.map.detail_scroll,self.map.detail_max_scroll)

    def test_map_allocations_depend_on_display_instead_of_region_extent(self):
        self.data['bounds_tiles'] = [-1000000, -750000, 2000000, 1500000]
        self.map.reset()
        canvas = pygame.Surface((640, 480))
        constructor = pygame.Surface
        sizes = []
        def bounded_surface(size, *args, **kwargs):
            sizes.append(size)
            self.assertLessEqual(size[0], 640)
            self.assertLessEqual(size[1], 480)
            return constructor(size, *args, **kwargs)
        with patch('pygame.Surface', side_effect=bounded_surface):self.map_ui.draw(canvas)
        self.assertTrue(sizes)

    def test_crop_parcels_have_distinct_treatments_and_follow_row_orientation(self):
        def polygon_at(rect):
            return [list(self.map.map_to_tile(point)) for point in
                    (rect.topleft, rect.topright, rect.bottomright, rect.bottomleft)]
        self.data['terrain'] = {'fields': []}
        crops = ('grain', 'vegetables', 'fallow', 'pasture', 'orchard')
        rectangles = []
        for index, crop in enumerate(crops):
            rect = pygame.Rect(45+index*49, 92, 42, 52)
            rectangles.append(rect)
            self.data['terrain']['fields'].append({'id': crop, 'crop': crop,
                                                  'row_angle': 0, 'polygon': polygon_at(rect)})
        canvas = pygame.Surface((480, 320))
        painter = self.game.ui.painter(canvas)
        self.map._draw_terrain(painter)
        for crop, rect in zip(crops, rectangles):
            with self.subTest(crop=crop):
                # Parcel interiors retain their chart colour, with vegetation
                # hatching confined inside the field instead of bleeding out.
                self.assertEqual(canvas.get_at((rect.left+2, rect.top+2))[:3],
                                 pygame.Color(FIELD_STYLES[crop][0])[:3])
                self.assertEqual(canvas.get_at((rect.left+2, rect.top-2))[:3],
                                 pygame.Color(PAPER)[:3])
        self.assertEqual(len({canvas.get_at((rect.left+2, rect.top+2))[:3]
                              for rect in rectangles}), len(crops))
        field = self.data['terrain']['fields'][0]
        rect = rectangles[0]
        patch_rect = pygame.Rect(rect.left+2, rect.top+2, rect.width-4, rect.height-4)
        horizontal = pygame.image.tobytes(canvas.subsurface(patch_rect), 'RGB')
        field['row_angle'] = 90
        self.map._draw_terrain(painter)
        vertical = pygame.image.tobytes(canvas.subsurface(patch_rect), 'RGB')
        self.assertNotEqual(horizontal, vertical)

    def test_footpath_dashes_remain_continuous_when_curves_are_densified(self):
        canvas = pygame.Surface((480, 320))
        painter = self.game.ui.painter(canvas)
        def route(points):return {'points': [list(self.map.map_to_tile(p)) for p in points]}
        canvas.fill(PAPER)
        self.map._draw_footpath(painter, route(((70, 170), (260, 170))))
        sparse = pygame.image.tobytes(canvas, 'RGB')
        colors = [canvas.get_at((x, 170))[:3] for x in range(70, 260)]
        self.assertIn(pygame.Color(PAPER)[:3], colors)
        self.assertIn(pygame.Color('#a28f6b')[:3], colors)
        canvas.fill(PAPER)
        self.map._draw_footpath(painter, route(tuple((x, 170) for x in range(70, 261, 2))))
        self.assertEqual(pygame.image.tobytes(canvas, 'RGB'), sparse)

    def test_farmyard_cartography_does_not_add_destinations_or_discovery_ids(self):
        before_landmarks = [record['id'] for record in self.map.landmarks]
        self.game.overworld_travel = SimpleNamespace(discovered={'eldenmere'})
        tile = list(self.map.map_to_tile((140, 140)))
        self.data['setpieces'] = [{'id': 'western_farmyard', 'kind': 'farmstead',
                                  'name': 'Farmyard', 'tile_position': tile, 'props': []}]
        before_data = json.dumps(self.data, sort_keys=True)
        canvas = pygame.Surface((480, 320))
        canvas.fill(PAPER)
        self.map._draw_farmsteads(self.game.ui.painter(canvas))
        self.assertNotEqual(canvas.get_at((140, 140))[:3], pygame.Color(PAPER)[:3])
        self.assertEqual([record['id'] for record in self.map.landmarks], before_landmarks)
        self.assertEqual(self.game.overworld_travel.discovered, {'eldenmere'})
        self.assertEqual(json.dumps(self.data, sort_keys=True), before_data)

    def test_town_and_indoor_modes_keep_existing_map_and_exterior_position(self):
        region = self.game.world
        self.game.world = self.game.town
        self.map_ui.reset()
        with patch.object(self.map, 'draw') as regional_draw:
            self.map_ui.draw(pygame.Surface((480, 320)))
        regional_draw.assert_not_called()
        self.game.world = SimpleNamespace(data={'kind': 'interior'})
        self.assertEqual(self.map_ui.player_position(), tuple(self.game.exterior_position))
        self.game.world = region
        self.map_ui.reset()
        self.assertIs(self.map_ui._regional_map, self.map)

    def test_real_game_update_freezes_regional_world_until_map_closes(self):
        from main import Game
        game = Game.__new__(Game)
        game.__dict__.update(self.game.__dict__)
        game.opening_cinematic = SimpleNamespace(active=False)
        game.regent_arrival = SimpleNamespace(active=False, state='waiting', maybe_start=Mock())
        game.mill_quest = SimpleNamespace(sync_encounter_music=Mock())
        game.music = Mock()
        game._music_focused = True
        game.combat = SimpleNamespace(active=False, post_phase=False, tutorial_active=False,
            tick_world=Mock(side_effect=RuntimeError('world resumed')))
        game.social.active = False
        game.on_title = False
        game.pause = game.inventory_ui = game.world_map_viewer = SimpleNamespace(is_open=False)
        game.overworld_travel = SimpleNamespace(active=True)
        game.quest_ui.journal_open = False
        game.opening_audio = Mock()
        game.elapsed_ms = 1234
        game.opening_fade = 0
        game.update(.5, (1, 0), True)
        self.assertEqual(game.elapsed_ms, 1234)
        game.combat.tick_world.assert_not_called()
        self.assertEqual(game.player.position, pygame.Vector2(288, -480))
        regional_map = RegionalMapUI(game)
        regional_map.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, repeat=False))
        self.assertFalse(game.map_open)
        with self.assertRaisesRegex(RuntimeError, 'world resumed'):game.update(.5, (1, 0), True)
        game.combat.tick_world.assert_called_once_with(.5)


if __name__ == '__main__':unittest.main()
