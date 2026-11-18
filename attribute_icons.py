"""Small attribute symbols drawn at the shared UI's display resolution.

Each symbol has its own silhouette and can be drawn on parchment or a selected
card without a background image. Coordinates describe a 16-unit design, scaled
into the caller's logical rectangle; icons do not scale with text settings.
"""
import pygame

from character_attributes import ATTRIBUTE_IDS


ICON_IDS = ATTRIBUTE_IDS


def draw_attribute_icon(painter, identifier, rect, color):
    """Draw one icon inside ``rect`` without changing the caller's clip.

    ``rect`` uses Painter's logical coordinates, normally 12–16 units square.
    The supplied foreground color keeps selected and ordinary cards consistent
    with the rest of the menu. Unknown identifiers are configuration errors.
    """
    if identifier not in ICON_IDS:
        raise ValueError('Unknown attribute icon: '+str(identifier))
    rect = pygame.Rect(rect)
    if rect.width <= 0 or rect.height <= 0:
        raise ValueError('Attribute icon rectangles must have positive size')
    side = min(rect.size)
    square = pygame.Rect(0, 0, side, side)
    square.center = rect.center
    target = painter.area(square)
    canvas = painter.canvas
    original_clip = canvas.get_clip()
    canvas.set_clip(original_clip.clip(target))
    stroke = max(1, round(min(target.size)/16))

    def point(x, y):
        return (target.left+round(x*(target.width-1)/15),
                target.top+round(y*(target.height-1)/15))

    def polygon(points, width=0):
        pygame.draw.polygon(canvas, color, [point(*p) for p in points],
                            stroke if width else 0)

    def line(points, width=1):
        pygame.draw.lines(canvas, color, False, [point(*p) for p in points],
                          max(1, round(stroke*width)))

    def circle(center, radius, width=0):
        pygame.draw.circle(canvas, color, point(*center),
                           max(1, round(radius*min(target.size)/16)),
                           stroke if width else 0)

    try:
        if identifier == 'hp':
            # A broad heart with two separate lobes and a single lower point.
            polygon(((1, 4), (3, 2), (5, 2), (7.5, 4), (10, 2),
                     (12, 2), (14, 4), (14, 7), (7.5, 14), (1, 7)))
        elif identifier == 'mp':
            # The open facets distinguish the crystal from a solid diamond.
            polygon(((7.5, 1), (13, 5), (11, 12), (7.5, 15),
                     (4, 12), (2, 5)), 1)
            line(((2, 5), (13, 5)))
            line(((7.5, 1), (5, 5), (7.5, 15), (10, 5), (7.5, 1)))
        elif identifier == 'str':
            polygon(((5, 9), (11, 1), (14, 1), (14, 4), (7, 11)))
            line(((3, 8), (8, 13)), 2)
            line(((5, 11), (2, 14)), 2)
        elif identifier == 'mag':
            # Uneven pointed rays communicate a forceful magical impact.
            polygon(((8, 0), (10, 5), (15, 3), (12, 8), (15, 11),
                     (10, 11), (8, 15), (6, 11), (1, 13), (4, 8),
                     (0, 5), (6, 5)))
        elif identifier == 'spr':
            # A healing cross over cupped hands, distinct from the damage burst.
            line(((8, 1), (8, 8)), 2)
            line(((5, 4), (11, 4)), 2)
            polygon(((1, 9), (3, 8), (5, 11), (8, 12), (11, 11),
                     (13, 8), (15, 9), (13, 13), (8, 15), (3, 13)))
        elif identifier == 'def':
            polygon(((2, 2), (13, 2), (13, 8), (11, 11),
                     (7.5, 14), (4, 11), (2, 8)), 1)
            line(((7.5, 3), (7.5, 12)))
        elif identifier == 'm_def':
            polygon(((1, 3), (4, 3), (7.5, 1), (11, 3), (14, 3),
                     (13, 9), (10, 12), (7.5, 14), (5, 12), (2, 9)), 1)
            polygon(((7.5, 4), (10, 7), (7.5, 10), (5, 7)), 1)
        elif identifier == 'speed':
            # A boot with a projecting toe and two short motion strokes.
            polygon(((6, 1), (11, 1), (10, 9), (13, 10), (15, 12),
                     (14, 14), (4, 14), (3, 12), (5, 9)))
            line(((0, 4), (3, 4)))
            line(((1, 7), (3, 7)))
        elif identifier == 'acc':
            circle((7.5, 7.5), 5, 1)
            line(((7.5, 0), (7.5, 4)))
            line(((7.5, 11), (7.5, 15)))
            line(((0, 7.5), (4, 7.5)))
            line(((11, 7.5), (15, 7.5)))
            circle((7.5, 7.5), 1)
        elif identifier == 'eva':
            # A light diagonal feather, with an exposed shaft and open barbs.
            polygon(((13, 1), (14, 3), (13, 7), (10, 11),
                     (5, 12), (4, 8), (7, 4)), 1)
            line(((1, 15), (12, 3)))
            line(((5, 10), (5, 7)))
            line(((8, 7), (11, 7)))
        elif identifier == 'lck':
            # Four rounded leaves and a curved stem make a lucky clover.
            for center in ((4, 4), (10, 4), (4, 10), (10, 10)):
                circle(center, 3)
            polygon(((6, 6), (8, 6), (8, 8), (6, 8)))
            line(((7, 9), (8, 13), (11, 15)), 2)
    finally:
        canvas.set_clip(original_clip)

    return target
