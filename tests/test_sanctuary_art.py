"""Sanctuary V2 production art and unchanged map-collision contracts."""
import json
import unittest
from pathlib import Path
from engine.assets import validate_png, validate_manifest

ROOT = Path(__file__).resolve().parents[1]


class SanctuaryArtTests(unittest.TestCase):
    def test_v2_png_layers_decode_fully(self):
        manifest = json.loads((ROOT / "assets/manifests/assets.json").read_text())
        validate_manifest(manifest, ROOT / "assets")
        dimensions = {
            "altar": (192, 132), "banner": (56, 120), "beam": (112, 208),
            "bench": (128, 40), "bookshelf": (72, 106), "bookshelf_cabinet": (96, 106),
            "bookshelf_ladder": (96, 106), "candles": (112, 40), "communal_table": (192, 88),
            "door": (96, 128), "floor_a": (32, 32), "floor_b": (32, 32),
            "floor_sunlit": (32, 32), "floor_worn": (32, 32), "flowers": (48, 56),
            "glow": (48, 48), "motes": (80, 64), "plant": (48, 56), "pool": (104, 120),
            "rug_runner": (48, 160), "rug_small": (96, 64), "timber": (32, 96),
            "wall_dark": (32, 32), "wall_plaster": (32, 96), "wall_stone": (32, 32),
            "window_blue": (64, 128), "window_sun": (64, 128), "wood_trim": (64, 32),
            "writing_desk": (128, 72),
        }
        for name, size in dimensions.items():
            with self.subTest(name=name):
                self.assertEqual(validate_png(ROOT / "assets/atlases/interiors" / (name + ".png")), size)

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
            room = json.loads((ROOT / "maps/interiors/sanctuary.json").read_text())
            surface = pygame.Surface((640, 448), pygame.SRCALPHA)
            draw_room(surface, room, None, 0, 0, 0.0)
            first = pygame.image.tostring(surface, "RGBA")
            self.assertGreater(surface.get_at((240, 240)).a, 0)
            draw_room(surface, room, None, 0, 0, 3.0)
            self.assertNotEqual(first, pygame.image.tostring(surface, "RGBA"))
        finally:
            pygame.display.quit()


if __name__ == "__main__":
    unittest.main()
