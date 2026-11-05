"""Replay only the approved awakening using the production scene renderer.

The short review and full cinematic now share one implementation. This wrapper
provides a local 0–5.9-second clock for the focused capture tool.
"""
from pathlib import Path

from ice_reaper_action import IceReaperActionStage
from rhea_scene_awakening import RheaSceneAwakening

ROOT = Path(__file__).resolve().parents[1]


class RheaSceneAwakeningStudy:
    DURATION = RheaSceneAwakening.DURATION
    BREAKOUT = RheaSceneAwakening.BREAKOUT
    RETREAT_END = RheaSceneAwakening.RETREAT_END
    CAMERA_SETTLED = RheaSceneAwakening.CAMERA_SETTLED
    EXPRESSION_TIMES = RheaSceneAwakening.EXPRESSION_TIMES
    CLOSE = RheaSceneAwakening.CLOSE
    WIDE = RheaSceneAwakening.WIDE
    OPPOSITE_SHOULDER = RheaSceneAwakening.OPPOSITE_SHOULDER
    canonical_time = staticmethod(RheaSceneAwakening.canonical_time)
    study_camera = staticmethod(RheaSceneAwakening.camera)

    def __init__(self, asset_root=None):
        self.stage = IceReaperActionStage(asset_root or ROOT/'assets/story/ice_reaper_rescue', strict=True)
        self.awakening = self.stage.awakening

    @property
    def last_draw_trace(self):
        return self.awakening.last_draw_trace

    def telemetry(self, elapsed):
        return self.awakening.telemetry(elapsed)

    def draw(self, canvas, elapsed, reduced_motion=False):
        self.awakening.draw(canvas, elapsed, reduced_motion)
