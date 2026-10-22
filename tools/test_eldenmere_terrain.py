"""Check the exported blob-autotile contract, joins and review reconstruction."""

import json
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "assets/terrain/eldenmere/grass_dirt"
NEIGHBORS = [((0,-1),1),((1,-1),2),((1,0),4),((1,1),8),
             ((0,1),16),((-1,1),32),((-1,0),64),((-1,-1),128)]


class TerrainExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = json.loads((PACK / "tileset.json").read_text())
        cls.tiles = [Image.open(PACK / tile["image"]).convert("RGBA") for tile in cls.meta["tiles"]]

    def test_all_neighborhoods_and_atlas(self):
        self.assertEqual(self.meta["count"],47)
        self.assertEqual(self.meta["tile_size"],[24,24])
        self.assertEqual(len(self.meta["lookup_256"]),256)
        self.assertEqual(len({tile.tobytes() for tile in self.tiles}),47)
        atlas = Image.open(PACK / self.meta["image"]).convert("RGBA")
        palette = json.loads((PACK / "palette.json").read_text())["materials"]
        allowed = {tuple(bytes.fromhex(color[1:])) for ramp in palette.values() for color in ramp.values()}
        for raw,index in enumerate(self.meta["lookup_256"]):
            expected = raw
            for diagonal,a,b in ((2,1,4),(8,4,16),(32,16,64),(128,64,1)):
                if not (raw&a and raw&b):
                    expected &= ~diagonal
            self.assertEqual(self.meta["tiles"][index]["mask"],expected)
        for record,tile in zip(self.meta["tiles"],self.tiles,strict=True):
            self.assertEqual(tile.size,(24,24))
            self.assertLessEqual(set(tile.getchannel("A").get_flattened_data()),{0,255})
            self.assertTrue(all(not p[3] or p[:3] in allowed for p in tile.get_flattened_data()))
            x,y,w,h = record["rect"]
            self.assertEqual(atlas.crop((x,y,x+w,y+h)).tobytes(),tile.tobytes())
            rebuilt = Image.new("RGBA",(24,24))
            for path,position in zip(record["quarters"],((0,0),(12,0),(0,12),(12,12)),strict=True):
                quarter = Image.open(PACK / path).convert("RGBA")
                self.assertEqual(quarter.size,(12,12))
                rebuilt.paste(quarter,position)
            self.assertEqual(rebuilt.tobytes(),tile.tobytes())
        self.assertEqual(atlas.crop((168,120,192,144)).getchannel("A").getextrema(),(0,0))
        for filename in self.meta["grass"]["images"]+self.meta["dirt_interiors"]["images"]:
            image = Image.open(PACK / filename).convert("RGBA")
            self.assertEqual(image.size,(24,24))
            self.assertEqual(image.getchannel("A").getextrema(),(255,255))

    def test_all_connected_horizontal_and_vertical_joins(self):
        # Enumerate every neighborhood around two adjacent dirt cells.
        # This detects wrong corner choices, cracks and painted border seams.
        for width,height,a,b in ((4,3,(1,1),(2,1)),(3,4,(1,1),(1,2))):
            positions = [(x,y) for y in range(height) for x in range(width) if (x,y) not in (a,b)]
            for pattern in range(1<<len(positions)):
                cells = {a,b}|{p for i,p in enumerate(positions) if pattern & 1<<i}
                masks = [sum(bit for (dx,dy),bit in NEIGHBORS if (x+dx,y+dy) in cells) for x,y in (a,b)]
                first,second = [self.tiles[self.meta["lookup_256"][mask]] for mask in masks]
                for t in range(24):
                    pa,pb = ((23,t),(0,t)) if width==4 else ((t,23),(t,0))
                    self.assertEqual(first.getpixel(pa),second.getpixel(pb),(width,pattern,t,masks))

    def test_shape_rotations(self):
        lookup = self.meta["lookup_256"]
        offsets = dict(NEIGHBORS)
        for record,tile in zip(self.meta["tiles"],self.tiles,strict=True):
            # PIL rotates counterclockwise: screen north becomes west.
            rotated = sum(offsets[(dy,-dx)] for (dx,dy),bit in NEIGHBORS if record["mask"] & bit)
            expected = self.tiles[lookup[rotated]].getchannel("A")
            actual = tile.getchannel("A").transpose(Image.Transpose.ROTATE_90)
            self.assertEqual(actual.tobytes(),expected.tobytes(),record["mask"])

    def test_scene_reconstructs_at_native_scale(self):
        scene = json.loads((PACK / "review_scene.json").read_text())
        width,height = scene["grid_size"]
        ground = Image.new("RGBA",(width*24,height*24))
        grass = [Image.open(PACK / p).convert("RGBA") for p in self.meta["grass"]["images"]]
        fills = [Image.open(PACK / p).convert("RGBA") for p in self.meta["dirt_interiors"]["images"]]
        for y in range(height):
            for x in range(width):
                ground.paste(grass[scene["grass_variants"][y][x]],(x*24,y*24))
                mask = scene["dirt_masks"][y][x]
                if mask is not None:
                    fill = scene["dirt_fill_variants"][y][x]
                    overlay = fills[fill] if fill is not None else self.tiles[self.meta["lookup_256"][mask]]
                    ground.alpha_composite(overlay,(x*24,y*24))
        self.assertEqual(ground.convert("RGB").tobytes(),Image.open(PACK / scene["ground"]).tobytes())
        for character in scene["characters"]:
            sprite = Image.open(ROOT / character["image_from_repo_root"]).convert("RGBA")
            self.assertEqual(sprite.size,(24,36))
            ground.alpha_composite(sprite,tuple(character["position"]))
        native = ground.convert("RGB")
        self.assertEqual(native.tobytes(),Image.open(PACK / scene["native"]).tobytes())
        scale = scene["review"]["scale"]
        enlarged = native.resize((native.width*scale,native.height*scale),Image.Resampling.NEAREST)
        self.assertEqual(enlarged.tobytes(),Image.open(PACK / scene["review"]["image"]).tobytes())


if __name__ == "__main__":
    unittest.main()
