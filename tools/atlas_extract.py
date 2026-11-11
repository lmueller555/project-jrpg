"""Connected-alpha atlas extraction shared by companion exporters."""
from collections import deque
from PIL import Image

def authored_cells(image, grid):
    """Group complete binary-alpha components into their logical source cells."""
    width, height = image.size
    columns, rows = grid
    remaining = bytearray(value >= 128 for value in image.getchannel('A').tobytes())
    groups = {index: [] for index in range(columns * rows)}
    for start in range(width * height):
        if not remaining[start]:
            continue
        remaining[start] = 0
        pending, members = deque([start]), []
        total_x = total_y = 0
        while pending:
            pixel = pending.popleft()
            x, y = pixel % width, pixel // width
            members.append(pixel)
            total_x += x
            total_y += y
            for dy in (-1, 0, 1):
                next_y = y + dy
                if not 0 <= next_y < height:
                    continue
                for dx in (-1, 0, 1):
                    next_x = x + dx
                    if (dx or dy) and 0 <= next_x < width:
                        neighbor = next_y * width + next_x
                        if remaining[neighbor]:
                            remaining[neighbor] = 0
                            pending.append(neighbor)
        # Discard detached subpixel antialias specks, retain authored effects.
        if len(members) < 16:
            continue
        center_x, center_y = total_x / len(members), total_y / len(members)
        column = min(columns - 1, int(center_x * columns / width))
        row = min(rows - 1, int(center_y * rows / height))
        groups[row * columns + column].extend(members)
    records = []
    for index, members in groups.items():
        if len(members) < 1000:
            raise ValueError(f'Missing authored source cell {index}')
        xs, ys = [p % width for p in members], [p // width for p in members]
        bounds = min(xs), min(ys), max(xs) + 1, max(ys) + 1
        left, top, right, bottom = bounds
        cutout = image.crop(bounds)
        mask = bytearray((right - left) * (bottom - top))
        for pixel in members:
            x, y = pixel % width - left, pixel // width - top
            mask[y * (right - left) + x] = 255
        cutout.putalpha(Image.frombytes('L', cutout.size, bytes(mask)))
        center = sum(xs) / len(xs), sum(ys) / len(ys)
        records.append((cutout, center, {'source_cell': index,
                                       'source_bounds': list(bounds)}))
    return records
