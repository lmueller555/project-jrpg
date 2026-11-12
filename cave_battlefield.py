"""Cached native cave battlefields sampled on the battle simulation clock."""
from __future__ import annotations

import json
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parent
CAVE_BATTLEFIELDS = frozenset(('cave_outer', 'cave_grotto', 'cave_hollow', 'cave_depths',
                              'cave_echo_chamber', 'cave_embervein', 'cave_stillfrost'))


class CaveBattlefield:
    def __init__(self, identifier, root=ROOT):
        if identifier not in CAVE_BATTLEFIELDS:
            raise ValueError('Unknown cave battlefield')
        root = Path(root)
        self.data = json.loads((root/'assets/combat'/identifier/'battlefield.json').read_text())
        data = self.data
        if (not isinstance(data, dict) or type(data.get('version')) is not int
                or data['version'] != 1 or data.get('id') != identifier
                or data.get('size') != [480, 320]
                or type(data.get('frame_duration_ms')) is not int or data['frame_duration_ms'] <= 0
                or not isinstance(data.get('background_frames'), list) or not data['background_frames']):
            raise ValueError('Invalid cave battlefield')
        self.frames = []
        for filename in data['background_frames']:
            if not isinstance(filename, str) or Path(filename).is_absolute() or '..' in Path(filename).parts:
                raise ValueError('Invalid cave battlefield frame')
            frame = pygame.image.load(str(root/filename)).convert()
            if frame.get_size() != (480, 320):raise ValueError('Invalid cave battlefield size')
            self.frames.append(frame)
        static = data.get('reduced_motion_frame', 0)
        if type(static) is not int or not 0 <= static < len(self.frames):
            raise ValueError('Invalid reduced-motion battlefield frame')
        self.name = data.get('name', 'Sanctuary Cave')
        self.elemental_crystals = None
        if identifier == 'cave_echo_chamber':
            from vespermaw_crystals import ElementalCrystals
            self.elemental_crystals = ElementalCrystals(root)

    def frame(self, elapsed_ms, reduced_motion=False):
        index = (self.data.get('reduced_motion_frame', 0) if reduced_motion else
                 int(max(0, elapsed_ms)//self.data['frame_duration_ms']) % len(self.frames))
        return self.frames[index]

    def crystal_origin(self, element, vertical_offset=0):
        from vespermaw_crystals import crystal_origin
        return crystal_origin(element,0 if self.elemental_crystals is not None else vertical_offset)

    def draw(self, target, elapsed_ms, reduced_motion=False, *, vertical_offset=0,
             elemental_state=None):
        frame = self.frame(elapsed_ms, reduced_motion)
        offset = min(160, max(0, int(vertical_offset)))
        # The boss's three wall lenses are essential visual information. Keep
        # their authored rear-wall composition in view when a larger HUD
        # reframes the actors; cropping the vault would hide their identities.
        if self.elemental_crystals is not None:offset=0
        target.blit(frame, (0, -offset))
        if offset:
            # HUD growth reframes the scene upward. Continue the clear lower
            # floor beneath it, including when a victory banner hides the HUD.
            target.blit(frame, (0, 320-offset), pygame.Rect(0, 320-offset, 480, offset))
        if self.elemental_crystals is not None:
            self.elemental_crystals.draw(target,elapsed_ms,elemental_state,reduced_motion,offset)
