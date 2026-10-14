"""Standard-library integrity tests for editable world map data."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class WorldDataTests(unittest.TestCase):
    def test_map_rows_and_legend(self):
        for path in ("maps/towns/eldenmere.json", "maps/interiors/sanctuary.json"):
            with self.subTest(path=path):
                data = read(path)
                rows = data["tiles"]
                self.assertTrue(rows)
                self.assertGreater(len(rows[0]), 15)
                self.assertTrue(all(len(row) == len(rows[0]) for row in rows))
                self.assertEqual(data["tile_size"], 16)
                self.assertTrue(set("".join(rows)).issubset(data["legend"]))
                sx, sy = data["player_spawn"]
                self.assertIn(rows[sy][sx], data["legend"])
                self.assertNotIn(data["legend"][rows[sy][sx]], ("water", "trees", "wall"))
                for obj in data["objects"]:
                    self.assertGreater(obj["w"], 0)
                    self.assertGreater(obj["h"], 0)
                    self.assertGreaterEqual(obj["x"], 0)
                    self.assertGreaterEqual(obj["y"], 0)
                    self.assertLessEqual(obj["x"] + obj["w"], len(rows[0]))
                    self.assertLessEqual(obj["y"] + obj["h"], len(rows))

    def test_households_and_landmarks(self):
        world = read("maps/towns/eldenmere.json")
        names = {obj["id"] for obj in world["objects"]}
        self.assertTrue({"sanctuary", "mill", "halden", "elira", "venn", "plaza", "bridge"} <= names)

    def test_sanctuary_door_corridor_and_transitions(self):
        hall = read("maps/interiors/sanctuary.json")
        town = read("maps/towns/eldenmere.json")
        self.assertNotEqual(hall["legend"][hall["tiles"][13][10]], "wall")
        self.assertNotEqual(hall["legend"][hall["tiles"][14][10]], "wall")
        self.assertTrue(any(o.get("transition") == "eldenmere" for o in hall["objects"]))
        self.assertTrue(any(o.get("transition") == "sanctuary_room" for o in town["objects"]))


if __name__ == "__main__":
    unittest.main()
