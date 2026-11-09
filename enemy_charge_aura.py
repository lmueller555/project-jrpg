"""Original red lightning-flame warning around a prepared heavy attacker.

This effect knows no combat rules. The scene supplies a living enemy's occupied
bounds and a paused scene clock while that enemy is preparing or holding a
powerful attack. Back and front passes preserve the enemy's readable silhouette.
"""
from __future__ import annotations

import math

import pygame


CRIMSON = (119, 12, 31, 128)
RED = (231, 40, 55, 184)
EMBER = (255, 102, 73, 220)
HOT = (255, 215, 180, 235)


def _xy(point):
    return round(point[0]), round(point[1])


class EnemyChargeAura:
    """A deterministic, bounded warning with a static reduced-motion frame."""

    def __init__(self):
        self._layer = None
        self._canvas_size = None

    @staticmethod
    def sample(body_rect, elapsed, *, actor_key='enemy', reduced_motion=False,
               bounds=None):
        """Return native-pixel geometry without consulting time or random state.

        The broad plumes are drawn behind the sprite. Foreground lightning is
        restricted to its sides; the center remains clear. Fixed color/opacity
        and gently changing geometry avoid brightness flashes.
        """
        body = pygame.Rect(body_rect)
        if body.width <= 0 or body.height <= 0:
            raise ValueError('A charge aura requires occupied enemy bounds')
        if (type(elapsed) not in (int, float) or not math.isfinite(elapsed)
                or elapsed < 0):
            raise ValueError('Charge aura time must be finite and nonnegative')
        if not isinstance(actor_key, str):
            raise TypeError('Charge aura actor identity must be text')
        clip = None if bounds is None else pygame.Rect(bounds)
        if clip is not None and (clip.width <= 0 or clip.height <= 0):
            raise ValueError('Charge aura bounds must have positive dimensions')
        age = .42 if reduced_motion else float(elapsed)
        seed = sum((index + 1) * ord(letter)
                   for index, letter in enumerate(actor_key)) % 127 / 17
        phase = age * 3.6 + seed
        margin = max(5, min(18, round(body.width * .14)))
        rise = max(9, min(28, round(body.height * .3)))
        base_y = body.bottom + 3
        aura = pygame.Rect(body.left - margin - 3, body.top - rise - 3,
                           body.width + margin * 2 + 6,
                           body.height + rise + 12)
        if clip is not None:
            aura = aura.clip(clip)
        count = max(7, min(15, body.width // 12 + 7))
        flames, cores, back_arcs = [], [], []
        for index in range(count):
            fraction = index / (count - 1)
            edge = abs(fraction * 2 - 1)
            outward = fraction * 2 - 1
            wave = math.sin(phase + index * .91)
            width = max(2., min(7., (body.width + margin * 2) / count * .46))
            root_x = body.left - margin * .7 + fraction * (body.width + margin * 1.4)
            root_x += wave * min(2., margin * .17)
            length = body.height * (1.06 - edge * .19)
            length += rise * (.65 + .4 * math.sin(phase * .71 + index * 1.73))
            tip_x = root_x + outward * margin * .42
            tip_x += math.sin(phase * .84 + index * 1.31) * width * .65
            tip_y = base_y - length
            points = (
                (root_x - width, base_y),
                (root_x - width * .55, base_y - length * .21),
                (root_x - width * 1.1, base_y - length * .37),
                (root_x + width * .1, base_y - length * .53),
                (tip_x - width * .45, tip_y + length * .2),
                (tip_x, tip_y),
                (tip_x + width * .65, tip_y + length * .25),
                (root_x + width * 1.3, base_y - length * .4),
                (root_x + width * .5, base_y - length * .18),
                (root_x + width, base_y),
            )
            flames.append(tuple(_xy(point) for point in points))
            cores.append(tuple(_xy(point) for point in (
                (root_x, base_y - 1),
                (root_x + width * .3, base_y - length * .31),
                (root_x - width * .65, base_y - length * .55),
                (root_x + width * .7, base_y - length * .73),
                (tip_x - width * .55, tip_y + length * .12),
                (tip_x, tip_y + 2),
            )))
            if index % 2 == 0:
                back_arcs.append(cores[-1][1:])
        front_arcs = []
        for side in (-1, 1):
            edge_x = body.left if side < 0 else body.right - 1
            sway = math.sin(phase * .83 + side * 1.7)
            points = (
                (edge_x + side * margin * .23, body.bottom - 3),
                (edge_x + side * (margin * .48 + sway), body.top + body.height * .72),
                (edge_x - side * 1, body.top + body.height * .61),
                (edge_x + side * margin * .65, body.top + body.height * .43),
                (edge_x + side * margin * .25, body.top + body.height * .31),
                (edge_x + side * (margin * .55 - sway), body.top + body.height * .12),
            )
            front_arcs.append(tuple(_xy(point) for point in points))
        glows = (
            body.inflate(margin * 2, rise).move(0, -rise // 4),
            body.inflate(margin + 2, rise // 2).move(0, -rise // 5),
        )
        return {'body': body, 'region': aura, 'flames': tuple(flames),
                'cores': tuple(cores), 'back_arcs': tuple(back_arcs),
                'front_arcs': tuple(front_arcs), 'glows': glows,
                'reduced_motion': bool(reduced_motion)}

    def _surface(self, canvas, size):
        """Keep one reusable surface, bounded by the current field canvas."""
        canvas_size = canvas.get_size()
        if self._layer is None or self._canvas_size != canvas_size:
            self._layer = pygame.Surface(size, pygame.SRCALPHA)
            self._canvas_size = canvas_size
        elif self._layer.get_width() < size[0] or self._layer.get_height() < size[1]:
            capacity = (max(size[0], self._layer.get_width()),
                        max(size[1], self._layer.get_height()))
            self._layer = pygame.Surface(capacity, pygame.SRCALPHA)
        self._layer.fill((0, 0, 0, 0))
        return self._layer

    def draw(self, canvas, body_rect, elapsed, *, actor_key='enemy',
             reduced_motion=False, bounds=None, foreground=False):
        """Draw the back glow/plumes or sparse front arcs; return its clip rect.

        Draw the normal sprite between the two passes. Both use the same clock
        and body bounds, so scrubbing or pausing yields the same result.
        """
        sample = self.sample(body_rect, elapsed, actor_key=actor_key,
                             reduced_motion=reduced_motion, bounds=bounds)
        region = sample['region'].clip(canvas.get_rect())
        if region.width <= 0 or region.height <= 0:
            return region
        layer = self._surface(canvas, region.size)
        offset = pygame.Vector2(region.topleft)

        def points(sequence):
            return [_xy(pygame.Vector2(point) - offset) for point in sequence]

        if foreground:
            for arc in sample['front_arcs']:
                local = points(arc)
                pygame.draw.lines(layer, CRIMSON, False, local, 3)
                pygame.draw.lines(layer, EMBER, False, local, 1)
                pygame.draw.line(layer, HOT, local[-2], local[-1], 1)
        else:
            for glow, color in zip(sample['glows'], ((85, 8, 27, 46), (160, 17, 38, 48))):
                pygame.draw.ellipse(layer, color, glow.move(-region.x, -region.y))
            for plume, core in zip(sample['flames'], sample['cores']):
                pygame.draw.polygon(layer, CRIMSON, points(plume))
                pygame.draw.lines(layer, RED, False, points(core), 3)
            for arc in sample['back_arcs']:
                local = points(arc)
                pygame.draw.lines(layer, EMBER, False, local, 1)
                pygame.draw.line(layer, HOT, local[-2], local[-1], 1)
        canvas.blit(layer, region, pygame.Rect(0, 0, *region.size))
        return region
