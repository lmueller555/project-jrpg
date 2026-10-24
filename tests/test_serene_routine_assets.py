"""Focused contract checks for Serene's sanctuary action artwork."""

from __future__ import annotations

import json
import math
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/source/characters/serene/routines"
OUTPUT = ROOT / "assets/characters/serene/routines"
SERENE_SOURCE = ROOT / "assets/source/characters/serene"
SERENE_OUTPUT = ROOT / "assets/characters/serene"
ACTIONS = ("sort_provisions", "consult_list", "tend_hearth", "arrange_hall")
BODY_OFFSET = (12, 6)


def opened(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def opaque_colors(image: Image.Image) -> set[tuple[int, int, int, int]]:
    return {
        image.getpixel((x, y))
        for y in range(image.height)
        for x in range(image.width)
        if image.getpixel((x, y))[3]
    }


class TestSereneRoutineAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.recipe = json.loads((SOURCE / "recipe.json").read_text())
        cls.manifest = json.loads((OUTPUT / "animations.json").read_text())
        cls.palette = json.loads((SERENE_OUTPUT / "palette.json").read_text())

    def test_runtime_and_review_metadata_share_one_frame_contract(self) -> None:
        assert list(self.manifest["actions"]) == list(ACTIONS)
        assert list(self.manifest["animations"]) == list(ACTIONS)
        assert self.manifest["action_canvas"] == [48, 48]
        assert self.manifest["frame_size"] == [48, 48]
        assert self.manifest["body_frame_size"] == [24, 36]
        assert self.manifest["body_offset"] == [12, 6]
        assert self.manifest["draw_anchor"] == [24, 36]
        assert self.manifest["foot_anchor"] == [24, 40]
        for relative in self.recipe["approved_inputs"].values():
            assert (SOURCE / relative).resolve().exists()
        for relative in self.manifest["approved_inputs"].values():
            assert (ROOT / relative).exists()
        for name in ACTIONS:
            runtime = self.manifest["actions"][name]
            rich = self.manifest["animations"][name]
            assert runtime == [
                {"file": frame["file"], "duration_ms": frame["duration_ms"]}
                for frame in rich["frames"]
            ]
            assert rich["duration_ms"] == sum(frame["duration_ms"] for frame in runtime)
            assert rich["facing"] == self.recipe["actions"][name]["facing"]
            assert rich["loop"] is True

    def test_frames_use_hard_alpha_approved_colors_and_close_cleanly(self) -> None:
        palette_colors = {
            tuple(bytes.fromhex(color.removeprefix("#"))) + (255,)
            for ramp in self.palette["materials"].values()
            for color in ramp
        }
        palette_colors.update(
            tuple(bytes.fromhex(color.removeprefix("#"))) + (255,)
            for color in self.palette["eyes"].values()
        )
        palette_colors.update(
            tuple(bytes.fromhex(color.removeprefix("#"))) + (255,)
            for color in self.recipe["prop_palette"].values()
        )
        for name in ACTIONS:
            frames = [opened(OUTPUT / item["file"]) for item in self.manifest["actions"][name]]
            assert frames[0].tobytes() == frames[-1].tobytes()
            assert len({frame.tobytes() for frame in frames}) >= 6
            for frame in frames:
                assert frame.size == (48, 48)
                assert set(frame.getchannel("A").tobytes()) == {0, 255}
                assert opaque_colors(frame) <= palette_colors
                left, top, right, bottom = frame.getbbox()
                assert left > 0 and top > 0 and right < 48 and bottom < 48

    def test_approved_head_mantle_and_planted_feet_survive_pixel_exact(self) -> None:
        for name in ACTIONS:
            facing = self.manifest["animations"][name]["facing"]
            parts = SERENE_SOURCE / f"walk_{facing}/parts"
            idle_layers = SERENE_SOURCE / f"idle_{facing}_layers"
            protected = [
                opened(parts / "head.png"),
                opened(parts / "shoulder_mantle.png"),
                opened(idle_layers / "legs_and_boots.png"),
            ]
            frames = [opened(OUTPUT / item["file"]) for item in self.manifest["actions"][name]]
            for frame in frames:
                for layer in protected:
                    for y in range(layer.height):
                        for x in range(layer.width):
                            pixel = layer.getpixel((x, y))
                            if pixel[3]:
                                assert frame.getpixel((x + BODY_OFFSET[0], y + BODY_OFFSET[1])) == pixel

    def test_pose_recipe_keeps_arm_reaches_within_native_anatomy(self) -> None:
        for name, action in self.recipe["actions"].items():
            assert action["frames"][0] == action["frames"][-1]
            for frame in action["frames"]:
                assert len(frame["arms"]) == 2
                for shoulder, elbow, hand in frame["arms"]:
                    assert math.dist(shoulder, elbow) <= 7.0, (name, frame["phase"])
                    assert math.dist(elbow, hand) <= 7.0, (name, frame["phase"])
                    assert 4 <= shoulder[0] <= 20 and 14 <= shoulder[1] <= 18
                    assert 2 <= hand[0] <= 21 and 13 <= hand[1] <= 24

    def test_table_actions_begin_on_the_north_surface_and_reach_to_contact(self) -> None:
        for name in ("sort_provisions", "consult_list", "arrange_hall"):
            frames = self.recipe["actions"][name]["frames"]
            assert frames[0]["prop"] == frames[-1]["prop"]
            assert frames[0]["prop"]["anchor"][1] == 11
            reaching = [frame for frame in frames if "surface" in frame["phase"]]
            assert reaching
            assert min(hand[1] for frame in reaching for hand in (arm[-1] for arm in frame["arms"])) <= 13
            assert max(frame["prop"]["anchor"][1] for frame in frames) >= 14

    def test_hearth_action_faces_north_and_reaches_the_real_firebox(self) -> None:
        hearth = self.recipe["actions"]["tend_hearth"]
        assert hearth["facing"] == "back"
        assert self.manifest["animations"]["tend_hearth"]["facing"] == "back"
        assert {action["facing"] for action in self.recipe["actions"].values()} == {"back"}
        station = (384, 110)
        draw_anchor = self.manifest["draw_anchor"]
        body_offset = self.manifest["body_offset"]
        active = [frame for frame in hearth["frames"] if frame["prop"]["sparks"]]
        assert active
        for frame in hearth["frames"]:
            prop = frame["prop"]
            assert prop["kind"] == "poker"
            assert prop["tip"][1] < prop["grip"][1]
        for frame in active:
            tip = frame["prop"]["tip"]
            world_tip = (
                station[0] - draw_anchor[0] + body_offset[0] + tip[0],
                station[1] - draw_anchor[1] + body_offset[1] + tip[1],
            )
            assert 392 <= world_tip[0] <= 396, (frame["phase"], world_tip)
            assert 85 <= world_tip[1] <= 87, (frame["phase"], world_tip)

    def test_sheets_and_looping_previews_reproduce_every_frame(self) -> None:
        for name in ACTIONS:
            records = self.manifest["actions"][name]
            frames = [opened(OUTPUT / record["file"]) for record in records]
            sheet = opened(OUTPUT / name / "spritesheet.png")
            assert sheet.size == (48 * len(frames), 48)
            for index, frame in enumerate(frames):
                assert sheet.crop((index * 48, 0, (index + 1) * 48, 48)).tobytes() == frame.tobytes()

            with Image.open(OUTPUT / name / "preview.gif") as preview:
                assert preview.n_frames == len(frames)
                assert preview.info["loop"] == 0
                assert preview.size == (384, 384)
                for index, (frame, record) in enumerate(zip(frames, records, strict=True)):
                    preview.seek(index)
                    assert preview.info["duration"] == record["duration_ms"]
                    expected = Image.new("RGB", (48, 48), "#e8edf2")
                    expected.paste(frame, (0, 0), frame)
                    expected = expected.resize((384, 384), Image.Resampling.NEAREST)
                    assert preview.convert("RGB").tobytes() == expected.tobytes()


if __name__ == "__main__":
    unittest.main()
