"""Static, native-pixel enemy targeting: a pointing glove and a ground ring.

The glove is original UI art drawn on a 15 by 20 pixel grid. It does not depend
on emoji fonts or share the battle sprite's idle/pulse clock. Callers draw the
ring behind the actor and the glove after actor sprites.
"""
from __future__ import annotations

from functools import lru_cache

import pygame


FINGER_SIZE = (15, 20)
FINGER_TIP = (6, 19)
FINGER_GAP = 2
RING_RED = '#ee4b55'
RING_OUTLINE = '#401920'


@lru_cache(maxsize=1)
def target_finger_image():
    """Original outlined white glove, with one long finger pointing down."""
    image = pygame.Surface(FINGER_SIZE, pygame.SRCALPHA)
    outline = '#18241e'
    ivory, highlight, shade = '#f8f0d9', '#fffdf0', '#baa98c'
    pygame.draw.polygon(image, outline, (
        (4, 4), (11, 4), (11, 5), (13, 5), (13, 7), (14, 7),
        (14, 11), (13, 11), (13, 12), (10, 12), (10, 14),
        (9, 14), (9, 18), (8, 18), (8, 19), (5, 19),
        (5, 18), (4, 18), (4, 11), (2, 11), (2, 10),
        (0, 10), (0, 7), (1, 7), (1, 6), (3, 6), (3, 5),
    ))
    pygame.draw.polygon(image, ivory, (
        (4, 5), (10, 5), (10, 6), (12, 6), (12, 8), (13, 8),
        (13, 10), (12, 10), (12, 11), (9, 11), (9, 13),
        (8, 13), (8, 18), (5, 18), (5, 10), (3, 10),
        (3, 9), (1, 9), (1, 8), (2, 8), (2, 7), (4, 7),
    ))
    # Cuff, bent knuckles and the thumb distinguish the hand from an arrow.
    pygame.draw.rect(image, outline, (4, 0, 8, 5))
    pygame.draw.rect(image, '#314f40', (5, 1, 6, 2))
    pygame.draw.line(image, '#f1cd77', (5, 3), (10, 3))
    pygame.draw.line(image, shade, (9, 6), (9, 10))
    pygame.draw.line(image, shade, (11, 8), (11, 10))
    pygame.draw.line(image, outline, (3, 8), (4, 9))
    pygame.draw.line(image, shade, (8, 12), (8, 17))
    pygame.draw.line(image, highlight, (5, 11), (5, 17))
    pygame.draw.line(image, highlight, (5, 5), (8, 5))
    return image


def _field_bounds(bounds):
    if bounds is None:
        return None
    area = pygame.Rect(bounds)
    if area.width <= 0 or area.height <= 0:
        raise ValueError('Target marker bounds must have positive dimensions')
    return area


def target_marker_geometry(body_rect, ground_point, *, bounds=None):
    """Return ring/finger rectangles in the same native field coordinates.

    The fingertip points at the body's horizontal center. A 22-pixel reserved
    gap above the occupied sprite bounds keeps the full glove clear of both
    the sprite and enemy nameplates. Bounds clamp the markers into the field;
    very small bounds use a nearest-scaled glove rather than a clipped glyph.
    """
    body = pygame.Rect(body_rect)
    if body.width <= 0 or body.height <= 0:
        raise ValueError('Target marker body must have positive dimensions')
    area = _field_bounds(bounds)
    width = max(26, min(108, round(body.width * .88) + 10))
    height = max(8, min(18, round(width * .2)))
    ring = pygame.Rect(0, 0, width, height)
    ring.center = (body.centerx, max(round(ground_point[1]), body.bottom - 2))
    finger = pygame.Rect(body.centerx-FINGER_TIP[0],
                         body.top-FINGER_GAP-FINGER_SIZE[1], *FINGER_SIZE)
    if area is not None:
        ring.size = min(ring.width, area.width), min(ring.height, area.height)
        # Preserve the ring's intended center after accommodating tight fields.
        ring.center = (body.centerx, max(round(ground_point[1]), body.bottom - 2))
        ring.clamp_ip(area)
        scale = min(1., area.width / finger.width, area.height / finger.height)
        if scale < 1:
            finger.size = (max(1, round(FINGER_SIZE[0] * scale)),
                           max(1, round(FINGER_SIZE[1] * scale)))
        finger.clamp_ip(area)
    return {'ring': ring, 'finger': finger}


def draw_target_ring(canvas, body_rect, ground_point, *, bounds=None):
    """Draw a red ground circle in perspective, before the enemy sprite."""
    rect = target_marker_geometry(body_rect, ground_point, bounds=bounds)['ring']
    pygame.draw.ellipse(canvas, RING_OUTLINE, rect, min(3, max(1, rect.height // 2)))
    inner = rect.inflate(-2, -2)
    if inner.width > 0 and inner.height > 0:
        pygame.draw.ellipse(canvas, RING_RED, inner, min(2, max(1, inner.height // 2)))
    return rect


def draw_target_finger(canvas, body_rect, *, bounds=None):
    """Draw the static pointing glove above the selected living enemy."""
    rect = target_marker_geometry(body_rect, (0, pygame.Rect(body_rect).bottom),
                                  bounds=bounds)['finger']
    image = target_finger_image()
    if rect.size != image.get_size():
        image = pygame.transform.scale(image, rect.size)
    canvas.blit(image, rect)
    return rect
