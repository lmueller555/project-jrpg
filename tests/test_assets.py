"""Asset format, atlas bounds, timeline and render ordering regression tests."""
import json
import unittest
from pathlib import Path
import tempfile

from engine.assets import AssetError, AnimationPlayer, LAYERS, validate_manifest, validate_png, RenderQueue

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


class AssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads((ASSETS / "manifests/assets.json").read_text())

    def test_manifest_pngs_and_bounds(self):
        validate_manifest(self.doc, ASSETS)

    def test_png_signature_is_actual_bytes(self):
        signature = bytes((137, 80, 78, 71, 13, 10, 26, 10))
        for name in ("atlases/characters/caelen.png", "atlases/terrain/environment.png"):
            self.assertEqual((ASSETS / name).read_bytes()[:8], signature)
            validate_png(ASSETS / name)

    def test_all_atlases_decode_fully(self):
        for name in ("atlases/characters/caelen.png", "atlases/terrain/environment.png"):
            with self.subTest(name=name):
                width, height = validate_png(ASSETS / name)
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)

    def test_corrupt_png_does_not_pass_header_only(self):
        source = (ASSETS / "atlases/characters/caelen.png").read_bytes()
        # A truncated IDAT must be rejected rather than passing its IHDR.
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "invalid.png"
            path.write_bytes(source[:45])
            with self.assertRaises(AssetError):
                validate_png(path)

    def test_pygame_can_load_real_atlas_pixels(self):
        import os
        import pygame
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.display.init()
        try:
            pygame.display.set_mode((1, 1))
            for name, dimensions in (
                ("atlases/characters/caelen.png", (64, 96)),
                ("atlases/terrain/environment.png", (96, 32))
            ):
                with self.subTest(atlas=name):
                    image = pygame.image.load(str(ASSETS / name)).convert_alpha()
                    self.assertEqual(image.get_size(), dimensions)
        finally:
            pygame.display.quit()

    def test_required_world_clips(self):
        names = self.doc["animations"]
        for direction in ("down", "left", "right", "up"):
            self.assertIn("caelen.idle_" + direction, names)
            self.assertEqual(len(names["caelen.walk_" + direction]["frames"]), 3)
        self.assertIn("ambient.water", names)
        self.assertIn("ambient.smoke", names)

    def test_large_delta_and_loop(self):
        class DummyRegistry:
            manifest = {"animations": {
                "clip": {"mode": "loop", "frames": [
                    {"asset": "a", "duration_ms": 100},
                    {"asset": "b", "duration_ms": 100}
                ]}
            }}
        runner = AnimationPlayer(DummyRegistry(), "clip")
        runner.update(150)
        self.assertEqual(runner.frame(), "b")
        runner.update(200)
        self.assertEqual(runner.frame(), "b")

    def test_reject_missing_frame(self):
        invalid = json.loads(json.dumps(self.doc))
        invalid["animations"]["ambient.smoke"]["frames"][0]["asset"] = "missing.frame"
        with self.assertRaises(AssetError):
            validate_manifest(invalid, ASSETS)

    def test_draw_queue_layers_and_ties(self):
        seen = []
        q = RenderQueue()
        q.add("entities", 40, lambda: seen.append("b"))
        q.add("ground", 0, lambda: seen.append("ground"))
        q.add("entities", 20, lambda: seen.append("a"))
        q.add("entities", 40, lambda: seen.append("c"))
        q.flush()
        self.assertEqual(seen, ["ground", "a", "b", "c"])
        self.assertEqual(q.items, [])


if __name__ == "__main__":
    unittest.main()
