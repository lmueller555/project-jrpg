"""Sanctuary production tile and unchanged map-collision contracts."""
import json
import unittest
from pathlib import Path
from engine.assets import validate_png, validate_manifest

ROOT = Path(__file__).resolve().parents[1]


class SanctuaryArtTests(unittest.TestCase):
    def test_atlas_and_semantic_regions(self):
        manifest = json.loads((ROOT / "assets/manifests/assets.json").read_text())
        self.assertEqual(validate_png(ROOT / "assets/atlases/interiors/sanctuary.png"), (256, 128))
        validate_manifest(manifest, ROOT / "assets")
        names = ("floor", "floor_variant", "stone_wall", "wall_trim", "window",
                 "rug", "table", "bookshelf", "altar", "flowers", "door", "planks",
                 "candles", "bench", "beam", "motif")
        for name in names:
            with self.subTest(name=name):
                spec = manifest["assets"]["interior.sanctuary." + name]
                self.assertEqual(spec["rect"][2:], [32, 32])

    def test_existing_collision_coordinates_intact(self):
        room = json.loads((ROOT / "maps/interiors/sanctuary.json").read_text())
        self.assertEqual(room["tile_size"], 16)
        self.assertEqual(room["player_spawn"], [10, 11])
        self.assertTrue(any(o.get("transition") == "eldenmere" and
                            (o["x"], o["y"]) == (10, 14) for o in room["objects"]))

    def test_pygame_headless_room_render(self):
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame
        from engine.assets import AtlasRegistry
        from engine.sanctuary_visuals import draw_room
        pygame.display.init()
        try:
            pygame.display.set_mode((1, 1))
            registry = AtlasRegistry(ROOT / "assets")
            room = json.loads((ROOT / "maps/interiors/sanctuary.json").read_text())
            surface = pygame.Surface((640, 448), pygame.SRCALPHA)
            draw_room(surface, room, registry, 0, 0, 0.0)
            first = surface.get_at((240, 240))
            draw_room(surface, room, registry, 0, 0, 4.0)
            self.assertGreater(first.a, 0)
        finally:
            pygame.display.quit()


if __name__ == "__main__":
    unittest.main()
