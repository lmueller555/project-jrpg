"""Named parent bank export/identity contract; runtime glue tested separately."""
import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
WHO = "liam_mother"
BANK = ROOT / "assets/characters/named_hd" / WHO
SOURCE = ROOT / "assets/source/characters/named_hd" / WHO

class NamedParentArtTests(unittest.TestCase):
    def test_idle_registration_and_native_pixels(self):
        design = json.loads((BANK / "design.json").read_text())
        self.assertEqual(design["id"], WHO)
        self.assertEqual(design["frame_size"], [48,72])
        self.assertEqual(design["logical_size"], [24,36])
        self.assertEqual(design["draw_anchor"], [12,30])
        self.assertEqual(design["artwork_pixels_per_world_pixel"], 2)
        seen = set()
        for direction in ("front","back","left","right"):
            image = Image.open(BANK / design["frames"][direction])
            self.assertEqual(image.size, (48,72))
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(set(image.getchannel("A").tobytes()), {0,255})
            seen.add(image.tobytes())
        self.assertEqual(len(seen), 4)

    def test_approved_portrait_is_preserved(self):
        original = ROOT / "assets/portraits/eldenmere" / (WHO + "_neutral.png")
        self.assertEqual((BANK / "portrait.png").read_bytes(), original.read_bytes())

    def test_four_complete_walks_and_exact_masters(self):
        for direction in ("front","back","left","right"):
            folder = BANK / ("walk_" + direction)
            manifest = json.loads((folder / "animation.json").read_text())
            self.assertEqual(manifest["character"], WHO)
            self.assertEqual(manifest["draw_anchor"], [24,60])
            self.assertEqual(manifest["foot_anchor"], [24,69])
            self.assertEqual(len(manifest["frames"]), 8)
            self.assertEqual(sum(f["duration_ms"] for f in manifest["frames"]), 560)
            master = Image.open(ROOT / manifest["source"])
            sheet = Image.open(folder / "spritesheet.png")
            self.assertEqual(master.tobytes(), sheet.tobytes())
            seen = set()
            for index, frame in enumerate(manifest["frames"]):
                path = folder / frame["file"]
                image = Image.open(path)
                self.assertEqual(image.size, (48,72))
                self.assertEqual(set(image.getchannel("A").tobytes()), {0,255})
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), frame["sha256"])
                self.assertEqual(image.tobytes(), master.crop((48*index,0,48*(index+1),72)).tobytes())
                seen.add(image.tobytes())
            self.assertEqual(len(seen), 8)
            for filename, total in (("normal.gif",560),("half_speed.gif",1120)):
                with Image.open(folder / filename) as gif:
                    self.assertEqual(sum(f.info["duration"] for f in ImageSequence.Iterator(gif)), total)

    def test_source_provenance(self):
        recipes=json.loads((SOURCE / "idle_recipe.json").read_text())
        self.assertEqual(set(recipes), {"front","back","left","right"})
        for item in recipes.values():
            self.assertEqual(hashlib.sha256((ROOT/item["source"]).read_bytes()).hexdigest(), item["sha256"])
            self.assertIn("native_eye_points", item)

if __name__ == "__main__":
    unittest.main()
