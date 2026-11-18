"""Opt-in NPC appearance bindings, independent of map-generation and behavior.

The map remains the owner of identity, position, collision and schedule. This
registry only selects approved roster artwork for explicitly migrated actors.
"""
import json
from pathlib import Path

from rendering import load_art

ROOT = Path(__file__).resolve().parent
DIRECTIONS = ('front', 'back', 'left', 'right')
BINDINGS_PATH = ROOT/'assets/characters/npc_roster_hd/live_bindings.json'


def bindings():
    return json.loads(BINDINGS_PATH.read_text())['actors']


def bound_design(actor_id):
    return bindings().get(actor_id)


class RosterArt:
    """Density-aware idles and manifest-timed walks; anchors exposed in world units."""
    def __init__(self, world, design_id):
        self.design_id = design_id
        folder = Path('assets/characters/npc_roster_hd')/design_id
        self.design = json.loads((ROOT/folder/'design.json').read_text())
        self.draw_anchor = tuple(self.design['draw_anchor'])
        self.foot_anchor = tuple(self.design['foot_anchor'])
        self.portrait_path = (folder/self.design['portrait']).as_posix()
        self.idles = {d: load_art(world, (folder/self.design['frames'][d]).as_posix(),
                                  self.design) for d in DIRECTIONS}
        self.walks = {}
        for direction in DIRECTIONS:
            walk_folder = folder/f'walk_{direction}'
            meta = json.loads((ROOT/walk_folder/'animation.json').read_text())
            density = meta['artwork_pixels_per_world_pixel']
            if tuple(v/density for v in meta['draw_anchor']) != self.draw_anchor:
                raise ValueError(f'Walk registration differs from idle: {design_id}/{direction}')
            self.walks[direction] = tuple(
                (load_art(world, (walk_folder/f['file']).as_posix(), meta), f['duration_ms'])
                for f in meta['frames'])
            if not self.walks[direction] or any(ms <= 0 for _, ms in self.walks[direction]):
                raise ValueError('A walk needs positive frame durations')

    def sprite(self, facing='front', moving=False, elapsed_ms=0):
        if not moving:
            return self.idles[facing]
        frames = self.walks[facing]
        time = elapsed_ms % sum(ms for _, ms in frames)
        for image, duration in frames:
            if time < duration:
                return image
            time -= duration
        return frames[-1][0]
