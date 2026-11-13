"""Native contour registration for Caelan's authored overworld bodies.

The approved automatic contour pass stays inside the original alpha silhouette.
Only the one-pixel cardinal boundary changes; enclosed shading, clear gaps,
canvas and registration remain intact. Bright skin-edge pixels keep readable
face/hand highlights where at least two adjacent body pixels support them.
"""
from PIL import Image

INK = (18, 12, 14, 255)
STYLE = {'version': 1, 'ink_rgba': list(INK), 'width_native_pixels': 1,
         'placement': 'inside existing cardinal silhouette',
         'skin_highlights': 'retain bright supported skin-edge pixels'}


def apply_outline(image):
    source = image.convert('RGBA')
    result = source.copy()
    width, height = source.size
    def opaque(x, y):
        return 0 <= x < width and 0 <= y < height and source.getpixel((x, y))[3] != 0
    for y in range(height):
        for x in range(width):
            r, g, b, a = source.getpixel((x, y))
            if not a:continue
            neighbors = sum(opaque(nx, ny) for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)))
            if neighbors == 4:continue
            if r >= 200 and g >= 130 and b >= 90 and r > g*1.1 and g > b*1.05 and neighbors >= 2:
                continue
            result.putpixel((x, y), (*INK[:3], a))
    return result
