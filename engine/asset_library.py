"""Browse registered game sprites and approved dialogue portraits without altering gameplay."""
from pathlib import Path
import pygame

BG = (14, 20, 36)
PANEL = (25, 34, 53)
GOLD = (230, 191, 111)
CREAM = (244, 229, 196)
MUTED = (165, 185, 202)
COLUMNS = 4
PAGE_SIZE = 12
CELL_W, CELL_H = 101, 86
GRID_X, GRID_Y = 28, 87


def window_to_canvas(pos, size):
    """Inverse of centered integer-scale presentation; offscreen bars return None."""
    w, h = size
    factor = min(w / 640, h / 448)
    if factor >= 1:
        factor = max(1, min(w // 640, h // 448))
    rw, rh = int(640 * factor), int(448 * factor)
    ox, oy = (w - rw) // 2, (h - rh) // 2
    if not (ox <= pos[0] < ox + rw and oy <= pos[1] < oy + rh):
        return None
    return ((pos[0] - ox) * 640 / rw, (pos[1] - oy) * 448 / rh)


class AssetLibrary:
    """Manifest-first gallery with bounded selection, category and page state."""

    def __init__(self, registry, asset_root):
        self.registry = registry
        self.asset_root = Path(asset_root)
        entries = []
        for asset_id, spec in sorted(registry.manifest["assets"].items()):
            entries.append((asset_id, spec["atlas"], tuple(spec["rect"]), spec["layer"], "atlas"))
        for mood in ("neutral", "happy", "concerned", "determined", "surprised"):
            path = "portraits/caelen/" + mood + ".png"
            if (self.asset_root / path).is_file():
                entries.append(("portrait.caelen." + mood, path, (0, 0, 96, 96), "portrait", "portrait"))
        self.entries = sorted(entries)
        self.categories = ["All"] + sorted({e[0].split(".")[0].title() for e in entries})
        self.category = 0
        self.selected = 0
        self.image_cache = {}
        self.font_cache = {}

    @property
    def filtered(self):
        if self.category == 0:
            return self.entries
        cat = self.categories[self.category].lower()
        return [e for e in self.entries if e[0].split(".")[0] == cat]

    @property
    def page(self):
        return self.selected // PAGE_SIZE

    def change_category(self, delta):
        self.category = (self.category + delta) % len(self.categories)
        self.selected = 0

    def move(self, delta):
        if self.filtered:
            self.selected = max(0, min(len(self.filtered) - 1, self.selected + delta))

    def handle_key(self, key):
        """Return 'back' when leaving the viewer, otherwise consume navigation."""
        if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            return "back"
        if key in (pygame.K_TAB, pygame.K_RIGHTBRACKET):
            self.change_category(1)
        elif key == pygame.K_LEFTBRACKET:
            self.change_category(-1)
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.move(-1)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.move(1)
        elif key in (pygame.K_UP, pygame.K_w):
            self.move(-COLUMNS)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.move(COLUMNS)
        elif key in (pygame.K_PAGEDOWN, pygame.K_n):
            self.move(PAGE_SIZE)
        elif key in (pygame.K_PAGEUP, pygame.K_p):
            self.move(-PAGE_SIZE)
        elif key == pygame.K_HOME:
            self.selected = 0
        elif key == pygame.K_END and self.filtered:
            self.selected = len(self.filtered) - 1
        return None

    def handle_click(self, pos, window_size):
        point = window_to_canvas(pos, window_size)
        if point is None:
            return None
        x, y = point
        if 17 <= x <= 92 and 15 <= y <= 44:
            return "back"
        if 20 <= y <= 78:
            if 436 <= x <= 468:
                self.change_category(-1)
            elif 595 <= x <= 628:
                self.change_category(1)
        if GRID_X <= x < GRID_X + COLUMNS * CELL_W and GRID_Y <= y < GRID_Y + 3 * CELL_H:
            col = int((x - GRID_X) // CELL_W)
            row = int((y - GRID_Y) // CELL_H)
            index = self.page * PAGE_SIZE + row * COLUMNS + col
            if index < len(self.filtered):
                self.selected = index
        if 25 <= y <= 78 and 260 <= x <= 298:
            self.move(-PAGE_SIZE)
        if 25 <= y <= 78 and 310 <= x <= 348:
            self.move(PAGE_SIZE)
        return None

    def _font(self, size, bold=False):
        key = (size, bold)
        if key not in self.font_cache:
            self.font_cache[key] = pygame.font.SysFont("georgia,dejavu sans", size, bold=bold)
        return self.font_cache[key]

    def _text(self, surf, content, pos, size=14, color=CREAM, bold=False):
        surf.blit(self._font(size, bold).render(content, True, color), pos)

    def _image(self, entry):
        asset_id, path, _, _, kind = entry
        if asset_id not in self.image_cache:
            try:
                if kind == "atlas":
                    self.image_cache[asset_id] = self.registry.image(asset_id)
                else:
                    self.image_cache[asset_id] = pygame.image.load(str(self.asset_root / path)).convert_alpha()
            except (pygame.error, OSError, KeyError, ValueError):
                self.image_cache[asset_id] = None
        return self.image_cache[asset_id]

    def _preview(self, surf, image, area):
        if image is None:
            self._text(surf, "Unavailable", (area.x + 8, area.centery), 13, MUTED)
            return
        w, h = image.get_size()
        if not (w and h):
            return
        factor = min(area.width / w, area.height / h)
        if factor >= 1:
            factor = max(1, int(factor))
        dest = (max(1, int(w * factor)), max(1, int(h * factor)))
        scaled = pygame.transform.scale(image, dest)
        surf.blit(scaled, scaled.get_rect(center=area.center))

    def draw_canvas(self, surf):
        surf.fill(BG)
        pygame.draw.rect(surf, GOLD, (10, 10, 620, 428), 2)
        self._text(surf, "BACK", (28, 22), 15, GOLD, True)
        self._text(surf, "ASSET LIBRARY", (113, 18), 24, CREAM, True)
        self._text(surf, "<", (443, 54), 18, GOLD, True)
        self._text(surf, self.categories[self.category], (469, 56), 14, CREAM)
        self._text(surf, ">", (603, 54), 18, GOLD, True)
        options = self.filtered
        total_pages = max(1, (len(options) + PAGE_SIZE - 1) // PAGE_SIZE)
        self._text(surf, f"{len(options)} assets  |  Page {self.page+1}/{total_pages}", (28, 62), 13, MUTED)
        self._text(surf, "<", (270, 39), 20, GOLD)
        self._text(surf, ">", (322, 39), 20, GOLD)
        for local, entry in enumerate(options[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]):
            row, col = divmod(local, COLUMNS)
            cell = pygame.Rect(GRID_X + col * CELL_W, GRID_Y + row * CELL_H, CELL_W - 5, CELL_H - 5)
            pygame.draw.rect(surf, PANEL, cell)
            if self.page * PAGE_SIZE + local == self.selected:
                pygame.draw.rect(surf, GOLD, cell, 2)
            self._preview(surf, self._image(entry), pygame.Rect(cell.x+5, cell.y+4, cell.width-10, 56))
            name = entry[0].split(".")[-1][:12]
            self._text(surf, name, (cell.x + 7, cell.y + 64), 12, CREAM)
        box = pygame.Rect(445, 87, 174, 255)
        pygame.draw.rect(surf, PANEL, box)
        pygame.draw.rect(surf, GOLD, box, 1)
        if options:
            entry = options[self.selected]
            self._preview(surf, self._image(entry), pygame.Rect(454, 94, 156, 136))
            self._text(surf, "Selected", (454, 237), 13, GOLD)
            label = entry[0]
            # Long semantic identifiers wrap without overflowing the preview panel.
            for row, start in enumerate(range(0, len(label), 23)):
                if row >= 2:
                    break
                self._text(surf, label[start:start+23], (454, 255 + row*16), 12)
            self._text(surf, f"Size: {entry[2][2]}x{entry[2][3]}", (454, 292), 12, MUTED)
            self._text(surf, f"Layer: {entry[3][:15]}", (454, 312), 12, MUTED)
        else:
            self._text(surf, "No assets", (454, 158), 13, MUTED)
        pygame.draw.line(surf, GOLD, (24, 353), (618, 353))
        self._text(surf, "Arrows/WASD: select    Tab/[ ]: category    PgUp/PgDn: page", (29, 370), 13, CREAM)
        self._text(surf, "Home/End: first/last    Mouse: select    Esc: title screen", (29, 390), 13, MUTED)

    def draw(self, window):
        canvas = pygame.Surface((640, 448))
        self.draw_canvas(canvas)
        w, h = window.get_size()
        factor = min(w / 640, h / 448)
        if factor >= 1:
            factor = max(1, min(w // 640, h // 448))
        size = (max(1, int(640*factor)), max(1, int(448*factor)))
        window.fill((9, 14, 24))
        preview = pygame.transform.scale(canvas, size)
        window.blit(preview, ((w-size[0])//2, (h-size[1])//2))
