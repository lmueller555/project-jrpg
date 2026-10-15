"""Pure architectural topology and Pygame sanctuary integration checks."""
import json
import unittest
from pathlib import Path
from engine.architecture import resolve_architecture

ROOT = Path(__file__).resolve().parents[1]


class ArchitecturalLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = json.loads((ROOT / "maps/interiors/sanctuary.json").read_text())

    def test_collision_and_transition_geometry_remain_in_source(self):
        room = self.world
        self.assertEqual(room["tile_size"], 16)
        self.assertEqual(room["player_spawn"], [10, 11])
        layout = resolve_architecture(room)
        self.assertEqual((layout.width, layout.height), (704, 512))
        self.assertEqual((layout.door.x, layout.door.y, layout.door.width), (320, 448, 64))
        self.assertTrue(all((x, 0) in layout.wall_cells for x in range(22)))

    def test_window_pairs_are_inside_room_and_anchored_to_north_wall(self):
        layout = resolve_architecture(self.world)
        self.assertEqual(len(layout.windows), 2)
        for window in layout.windows:
            self.assertEqual(window.y, 0)
            self.assertEqual((window.width, window.height), (64, 128))
            self.assertGreaterEqual(window.x, 0)
            self.assertLessEqual(window.x + window.width, layout.width)

    def test_floor_adjacency_and_wall_boundary_are_deterministic(self):
        self.assertEqual(resolve_architecture(self.world), resolve_architecture(self.world))
        layout = resolve_architecture(self.world)
        self.assertTrue(any((dx, dy) == (0, -1) for _, _, dx, dy in layout.floor_edges))
        self.assertTrue(any((dx, dy) == (0, 1) for _, _, dx, dy in layout.floor_edges))

    def test_camera_translation_does_not_change_architecture(self):
        layout = resolve_architecture(self.world)
        for camera in ((0, 0), (32, 40), (64, 64)):
            self.assertEqual(resolve_architecture(self.world), layout)

if __name__ == "__main__":
    unittest.main()
