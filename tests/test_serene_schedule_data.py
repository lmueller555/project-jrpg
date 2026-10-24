"""Data-contract and collision checks for Serene's cross-room schedule."""
import json
from collections import deque
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "assets/maps/eldenmere/playable/map.json"
ROUTINE = ROOT / "assets/maps/eldenmere/routines/serene.json"
ANIMATIONS = ROOT / "assets/characters/serene/routines/animations.json"
ROOMS = ROOT / "assets/maps/eldenmere/building_interiors/rooms"


def read(path):
    return json.loads(path.read_text())


class SereneScheduleData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.town = read(MAP)
        cls.routine = read(ROUTINE)
        cls.animations = read(ANIMATIONS)
        cls.collisions = {}
        for scene in ("sanctuary_dining", "sanctuary_hall"):
            room = read(ROOMS / scene / "map.json")
            cls.collisions[scene] = Image.open(ROOT / room["collision"]).convert("L")

    def can_stand(self, scene, point):
        image = self.collisions[scene]
        width, height = self.routine["probe_size"]
        left = round(point[0]) - width // 2
        top = round(point[1]) - height // 2
        if left < 0 or top < 0 or left + width > image.width or top + height > image.height:
            return False
        return image.crop((left, top, left + width, top + height)).getbbox() is None

    def route_exists(self, scene, start, goal):
        """Mirror the runtime's bounded, cardinal 2px path search."""
        start = tuple(round(value / 2) * 2 for value in start)
        goal = tuple(goal)
        if not self.can_stand(scene, goal):
            return False
        low = (min(start[0], goal[0]) - 96, min(start[1], goal[1]) - 96)
        high = (max(start[0], goal[0]) + 96, max(start[1], goal[1]) + 96)
        pending = deque([start])
        visited = {start}
        while pending and len(visited) < 15000:
            point = pending.popleft()
            if point == goal:
                return True
            for candidate in ((point[0] + 2, point[1]), (point[0] - 2, point[1]),
                              (point[0], point[1] + 2), (point[0], point[1] - 2)):
                if candidate in visited:
                    continue
                if not (low[0] <= candidate[0] <= high[0] and
                        low[1] <= candidate[1] <= high[1]):
                    continue
                if self.can_stand(scene, candidate):
                    visited.add(candidate)
                    pending.append(candidate)
        return False

    def test_manifest_registers_one_persistent_serene(self):
        records = self.town["persistent_npcs"]
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["id"], "mother_serene")
        self.assertEqual(record["scene"], self.routine["start_scene"])
        self.assertEqual(record["position"], self.routine["start_position"])
        self.assertEqual(record["probe_size"], self.routine["probe_size"])
        self.assertEqual(record["behavior"], ROUTINE.relative_to(ROOT).as_posix())
        self.assertEqual(record["animation"],
                         "assets/characters/serene/routines/animations.json")
        self.assertEqual(record["draw_anchor"], [12, 30])
        self.assertNotIn("mother_serene", {record["id"] for record in self.town["npcs"]})

    def test_actions_and_review_stations_share_the_runtime_contract(self):
        actions = [step for step in self.routine["steps"] if step["type"] == "action"]
        self.assertEqual({step["animation"] for step in actions},
                         {"sort_provisions", "consult_list", "tend_hearth", "arrange_hall"})
        for step in actions:
            metadata = self.animations["animations"][step["animation"]]
            self.assertEqual(step["facing"], metadata["facing"], step["id"])
        scene = self.routine["start_scene"]
        position = self.routine["start_position"]
        for step in self.routine["steps"]:
            if step["type"] == "move":
                position = step["waypoints"][-1]
            elif step["type"] == "transfer":
                scene, position = step["scene"], step["position"]
            elif step["id"] in self.routine["review"]:
                review = self.routine["review"][step["id"]]
                self.assertEqual((review["scene"], review["station"]), (scene, position))

    def test_every_route_leg_and_room_transfer_is_clear(self):
        scene = self.routine["start_scene"]
        position = self.routine["start_position"]
        self.assertTrue(self.can_stand(scene, position))
        transfers = []
        for step in self.routine["steps"]:
            if step["type"] == "move":
                for waypoint in step["waypoints"]:
                    self.assertTrue(self.route_exists(scene, position, waypoint),
                                    (step["id"], scene, position, waypoint))
                    position = waypoint
            elif step["type"] == "transfer":
                transfers.append((scene, step["scene"], tuple(position), tuple(step["position"])))
                scene, position = step["scene"], step["position"]
                self.assertTrue(self.can_stand(scene, position), step["id"])
        self.assertEqual(transfers, [
            ("sanctuary_dining", "sanctuary_hall", (216, 294), (264, 90)),
            ("sanctuary_hall", "sanctuary_dining", (264, 90), (216, 294)),
        ])
        self.assertEqual((scene, position),
                         (self.routine["start_scene"], self.routine["start_position"]))


if __name__ == "__main__":
    unittest.main()
