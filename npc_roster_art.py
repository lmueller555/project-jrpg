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
    existing=bindings().get(actor_id)
    if existing:return existing
    from regional_npc_art import bound_regional_design
    return bound_regional_design(actor_id)


NAMED_BANK = Path('assets/characters/named_hd')
NAMED_HOUSEHOLD_ACTORS = frozenset(('tessa', 'finn', 'rowan', 'ada', 'pippa',
                                    'liam_mother', 'liam_father'))


def named_household_art(world, actor_id):
    """Only explicitly supported household actors opt in once their bank lands."""
    if actor_id in NAMED_HOUSEHOLD_ACTORS and (ROOT/NAMED_BANK/actor_id/'design.json').is_file():
        return RosterArt(world, actor_id, named=True)
    return None


class RosterArt:
    """Density-aware idles and manifest-timed gait; anchors exposed in world units."""
    def __init__(self, world, design_id, *, named=False):
        self.design_id = design_id
        folder = (NAMED_BANK if named else Path('assets/characters/npc_roster_hd'))/design_id
        self.design = json.loads((ROOT/folder/'design.json').read_text())
        self.draw_anchor = tuple(self.design['draw_anchor'])
        self.foot_anchor = tuple(self.design['foot_anchor'])
        self.portrait_path = (folder/self.design['portrait']).as_posix()
        self.idles = {d: load_art(world, (folder/self.design['frames'][d]).as_posix(),
                                  self.design) for d in DIRECTIONS}
        self.walks = self._motion(world, folder, 'walk')
        self.runs = self._motion(world, folder, 'run', optional=True) if named else {}

    def _motion(self, world, folder, verb, *, optional=False):
        paths = {d: folder/f'{verb}_{d}' for d in DIRECTIONS}
        available = [(ROOT/path/'animation.json').is_file() for path in paths.values()]
        if optional and not any(available):return {}
        if not all(available):raise ValueError(f'Incomplete {verb} bank: {self.design_id}')
        motions = {}
        for direction, motion_folder in paths.items():
            meta = json.loads((ROOT/motion_folder/'animation.json').read_text())
            density = meta['artwork_pixels_per_world_pixel']
            if tuple(v/density for v in meta['draw_anchor']) != self.draw_anchor:
                raise ValueError(f'{verb} registration differs from idle: {self.design_id}/{direction}')
            motions[direction] = tuple(
                (load_art(world, (motion_folder/f['file']).as_posix(), meta), f['duration_ms'])
                for f in meta['frames'])
            if not motions[direction] or any(ms <= 0 for _, ms in motions[direction]):
                raise ValueError(f'{verb} needs positive frame durations')
        return motions

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
