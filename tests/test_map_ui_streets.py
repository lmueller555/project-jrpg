"""Compiled street cartography replaces old roads without moving world points."""
import copy
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from map_ui import MapUI, PATH_FILL


class RecordingPainter:
    def __init__(self):
        self.lines = []
        self.rects = []

    def line(self, color, first, second, width=1):
        self.lines.append((color, tuple(first), tuple(second), width))

    def rect(self, color, rect, width=0):
        self.rects.append((color, pygame.Rect(rect), width))


class CompiledTownStreetMapTests(unittest.TestCase):
    def setUp(self):
        self.ui = MapUI.__new__(MapUI)
        town = SimpleNamespace(size=(1000, 500), data={
            'tile_size': 10,
            'cartography': {'roads': [[[400, 200], [500, 200]]]},
        })
        self.ui.game = SimpleNamespace(town=town)
        self.ui.map_rect = pygame.Rect(20, 30, 200, 100)
        self.ui._plan = {
            'roads': [{'id': 'old', 'points': [[1, 2], [3, 2]], 'width': 2}],
            'crossings': [],
        }
        self.ui._extras = [{'path_rect_tiles': [20, 20, 2, 1],
                            'plaza_rect_tiles': [30, 30, 3, 2]}]

    def draw(self, network=None, *, compiled=True):
        if compiled:
            self.ui.game.town.data['cartography']['street_network'] = network
        painter = RecordingPainter()
        self.ui._draw_roads(painter)
        return painter

    @staticmethod
    def road(identifier, *, y=200, role='secondary', material='dirt', width=48):
        return {'id': identifier, 'role': role, 'material': material,
                'points': [[100, y], [300, y]], 'width': width}

    def test_compiled_points_are_logical_world_coordinates_without_recipe_reads(self):
        record = self.road('live')
        before = copy.deepcopy(record)
        with patch('pathlib.Path.read_text', side_effect=AssertionError('No runtime street recipe')):
            painter = self.draw([record])
        self.assertEqual(len(painter.lines), 2)
        for _, first, second, _ in painter.lines:
            self.assertEqual(first, (40, 70))
            self.assertEqual(second, (80, 70))
        self.assertEqual(record, before, 'The map must not modify compiled geometry')

    def test_complete_network_replaces_all_legacy_layers_but_keeps_crossings(self):
        crossing = {'id': 'bridge', 'rect': [50, 20, 6, 2], 'orientation': 'east-west'}
        self.ui._plan['crossings'] = [crossing]
        painter = self.draw([self.road('live')])
        road_lines = [line for line in painter.lines if line[0] != '#d9c49c']
        self.assertEqual(len(road_lines), 2, 'Old plan/expansion roads were drawn a second time')
        self.assertEqual(len(painter.rects), 2, 'Old path or plaza rectangles must not reappear')
        self.assertEqual(painter.rects[0][1], self.ui._tile_rect(crossing['rect']))
        self.assertEqual(painter.rects[1][2], 1)
        self.assertTrue(any(line[0] == '#d9c49c' for line in painter.lines))

    def test_present_empty_network_does_not_silently_restore_old_roads(self):
        painter = self.draw([])
        self.assertFalse(painter.lines)
        self.assertFalse(painter.rects)

    def test_hierarchy_and_materials_remain_distinguishable_on_small_map(self):
        records = [self.road('primary', y=100, role='primary'),
                   self.road('residential', y=200, role='residential'),
                   self.road('desire', y=300, role='desire'),
                   self.road('stone', y=400, role='doorstep', material='stone')]
        painter = self.draw(records)
        widths = {}
        fills = {}
        for color, first, _, width in painter.lines:
            y = first[1]
            widths[y] = max(widths.get(y, 0), width)
            fills[y] = color
        self.assertGreater(widths[50], widths[70])
        self.assertGreater(widths[70], widths[90])
        self.assertNotEqual(fills[110], fills[70], 'Stone and dirt should not use one material color')
        self.assertTrue(all(width >= 1 for *_, width in painter.lines))
        self.assertEqual(painter.lines[0][1][1], 90, 'Low-priority desire paths draw beneath main roads')
        self.assertEqual(painter.lines[-1][1][1], 110, 'Doorstep finish should remain readable')

    def test_all_segments_fill_after_outlines_for_continuous_elbows(self):
        record = self.road('corner')
        record['points'].append([300, 300])
        painter = self.draw([record])
        self.assertEqual(len(painter.lines), 4)
        self.assertEqual(painter.lines[0][0], painter.lines[1][0])
        self.assertEqual(painter.lines[2][0], painter.lines[3][0])
        self.assertNotEqual(painter.lines[1][0], painter.lines[2][0])

    def test_explicit_plaza_rect_keeps_its_complete_world_footprint(self):
        record = self.road('square', role='junction', material='stone')
        record.update(rect=[200, 100, 120, 80], points=[[260, 140], [260, 140]])
        painter = self.draw([record])
        self.assertFalse(painter.lines, 'A square must not collapse to a zero-length road stroke')
        self.assertEqual(len(painter.rects), 2)
        self.assertEqual(painter.rects[0][1], pygame.Rect(60, 50, 24, 16))
        self.assertEqual(painter.rects[1][1], pygame.Rect(61, 51, 22, 14))

    def test_older_maps_keep_plan_expansion_and_added_path_fallback(self):
        painter = self.draw(compiled=False)
        self.assertEqual(len(painter.lines), 4)
        self.assertTrue(any(first == (22, 34) and second == (26, 34)
                            for _, first, second, _ in painter.lines))
        self.assertTrue(any(first == (100, 70) and second == (120, 70)
                            for _, first, second, _ in painter.lines))
        self.assertEqual(len(painter.rects), 2)
        self.assertTrue(all(color == PATH_FILL for color, _, _ in painter.rects))


if __name__ == '__main__':
    unittest.main()
