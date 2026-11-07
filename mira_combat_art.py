"""Seekable Mira pose anchors on the same clock as her authored combat frames.

The asset manifest owns floor, muzzle and controller registration. Effects use
those points without reading pixels, moving her formation position or changing
combat timing. Projectile release is distinct from the model's damage impact.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path


ART = Path(__file__).resolve().parent / 'assets/combat/mira'


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


class MiraCombatArt:
    """Load anchor metadata once; frame selection performs no I/O."""

    def __init__(self, root=ART, *, data=None):
        self.manifest = (json.loads((Path(root) / 'animation.json').read_text())
                         if data is None else deepcopy(data))
        self.floor = tuple(self.manifest['anchor'])
        self.animations = self.manifest['animations']
        for animation in self.animations.values():
            if not animation['frames'] or type(animation['loop']) is not bool:
                raise ValueError('Invalid Mira combat animation')
            for record in animation['frames']:
                duration = record['duration_ms']
                if type(duration) is not int or duration <= 0:
                    raise ValueError('Invalid Mira frame duration')
                for point in record.get('anchors', {}).values():
                    if (not isinstance(point, (list, tuple)) or len(point) != 2
                            or any(not _number(value) for value in point)):
                        raise ValueError('Invalid Mira frame anchor')
        release_ms = self.animations['attack'].get('release_ms', 280)
        contact_ms = self.animations['attack'].get('contact_ms', 400)
        if (type(release_ms) is not int or type(contact_ms) is not int
                or not 0 < release_ms < contact_ms):
            raise ValueError('Mira shot release must precede impact')
        self.release_at = release_ms / 1000

    def frame_record(self, state, elapsed_ms):
        """Select exactly like CombatSprites, clamping finished nonloop poses."""
        if not _number(elapsed_ms):
            raise ValueError('Invalid Mira animation clock')
        animation = self.animations.get(state, self.animations['idle'])
        time = max(0., elapsed_ms)
        duration = sum(record['duration_ms'] for record in animation['frames'])
        if animation['loop']:
            time %= duration
        for record in animation['frames']:
            if time < record['duration_ms']:
                return record
            time -= record['duration_ms']
        return animation['frames'][-1]

    def anchors(self, state, elapsed_ms):
        """Return canvas-local anchors for the currently selected drawing."""
        record = self.frame_record(state, elapsed_ms)
        return {'floor': self.floor, **{name: tuple(point)
                for name, point in record.get('anchors', {}).items()}}

    def world_anchor(self, state, elapsed_ms, name, floor_point):
        """Convert a drawing attachment to the field's existing twofold scale."""
        anchors = self.anchors(state, elapsed_ms)
        point, floor = anchors[name], anchors['floor']
        return tuple(floor_point[axis] + (point[axis] - floor[axis]) * 2
                     for axis in range(2))

    def shot(self, elapsed, impact_at, floor_point, target_point, *, resolved=False):
        """Sample a bolt from its release drawing's muzzle to the impact point.

        Its origin stays fixed throughout flight even as the weapon recoils.
        There is no projectile before release or after the authoritative impact.
        """
        if not _number(elapsed) or not _number(impact_at) or impact_at <= self.release_at:
            raise ValueError('Invalid Mira shot clock')
        origin = self.world_anchor('attack', self.release_at * 1000, 'muzzle', floor_point)
        muzzle = self.world_anchor('attack', elapsed * 1000, 'muzzle', floor_point)
        fraction = None
        projectile = None
        if not resolved and self.release_at <= elapsed < impact_at:
            fraction = (elapsed - self.release_at) / (impact_at - self.release_at)
            projectile = tuple(origin[axis] + (target_point[axis] - origin[axis]) * fraction
                               for axis in range(2))
        return {'release_at': self.release_at, 'origin': origin, 'muzzle': muzzle,
                'target': tuple(target_point), 'fraction': fraction, 'projectile': projectile,
                'flash': self.release_at <= elapsed < self.release_at + .06}
