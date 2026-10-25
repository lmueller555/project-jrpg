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
        records = [r for r in self.town["persistent_npcs"] if r['id']=='mother_serene']
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

    def test_surface_props_are_bound_to_one_station_and_rest_on_furniture(self):
        """Loose work objects use world-space furniture tops, not Serene's feet."""
        props = {record["id"]: record for record in self.routine["surface_props"]}
        expected = {
            "provision_jar_a": ("sanctuary_dining", "sort_provisions",
                                [286, 186], 210, 2, (264, 172, 48, 27)),
            "provision_jar_b": ("sanctuary_dining", "sort_second_provision_table",
                                [334, 186], 210, 2, (312, 172, 48, 27)),
            "preparation_list": ("sanctuary_hall", "consult_list",
                                 [117, 141], 174, 1, (108, 138, 24, 16)),
            "folded_linen": ("sanctuary_hall", "arrange_hall",
                             [246, 185], 210, 2, (240, 172, 48, 27)),
        }
        self.assertEqual(set(props), set(expected))
        for prop_id, (scene, action_step, position, sort_y, priority, top) in expected.items():
            with self.subTest(prop=prop_id):
                prop = props[prop_id]
                self.assertEqual(prop["scene"], scene)
                self.assertEqual(prop["action_step"], action_step)
                self.assertEqual(prop["position"], position)
                self.assertEqual(prop["sort_y"], sort_y)
                self.assertEqual(prop["sort_priority"], priority)

                path = ROOT / prop["image"]
                self.assertTrue(path.is_file(), path)
                image = Image.open(path).convert("RGBA")
                alpha_box = image.getchannel("A").getbbox()
                self.assertIsNotNone(alpha_box, path)
                left = prop["position"][0] + alpha_box[0]
                top_y = prop["position"][1] + alpha_box[1]
                right = prop["position"][0] + alpha_box[2]
                bottom = prop["position"][1] + alpha_box[3]
                surface_left, surface_top, surface_width, surface_height = top
                self.assertGreaterEqual(left, surface_left)
                self.assertGreaterEqual(top_y, surface_top)
                self.assertLessEqual(right, surface_left + surface_width)
                self.assertLessEqual(bottom, surface_top + surface_height)

        action_ids = {step["id"] for step in self.routine["steps"]
                      if step["type"] == "action" and step["animation"] != "tend_hearth"}
        self.assertEqual({record["action_step"] for record in props.values()}, action_ids)

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

    def test_revised_work_stations_match_their_furniture(self):
        action_stations = {}
        scene = self.routine["start_scene"]
        position = self.routine["start_position"]
        for step in self.routine["steps"]:
            if step["type"] == "move":
                position = step["waypoints"][-1]
            elif step["type"] == "transfer":
                scene, position = step["scene"], step["position"]
            elif step["type"] == "action":
                action_stations[step["id"]] = (scene, tuple(position))
        self.assertEqual(action_stations, {
            "sort_provisions": ("sanctuary_dining", (288, 214)),
            "sort_second_provision_table": ("sanctuary_dining", (336, 214)),
            "tend_hearth": ("sanctuary_dining", (384, 110)),
            "consult_list": ("sanctuary_hall", (120, 178)),
            "arrange_hall": ("sanctuary_hall", (264, 214)),
        })


if __name__ == "__main__":
    unittest.main()
