"""Original, resolution-independent title screen for The Broken Covenant."""
import math
import pygame

INK = (14, 20, 36)
GOLD = (230, 191, 111)
CREAM = (244, 229, 196)
MUTED = (168, 184, 199)


class TitleScreen:
    OPTIONS = ("New Game", "Quit")

    def __init__(self):
        self.selected = 0
        self.elapsed = 0.0
        self.fonts = {}

    def update(self, dt):
        self.elapsed += max(0, dt)

    def handle_key(self, key):
        """Return 'start' / 'quit', or None if selection only changed."""
        if key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(self.OPTIONS)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(self.OPTIONS)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_e):
            return "start" if self.selected == 0 else "quit"
        elif key == pygame.K_ESCAPE:
            return "quit"
        return None

    def _font(self, size, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = pygame.font.SysFont("georgia,dejavu serif", size, bold=bold)
        return self.fonts[key]

    def _center(self, surface, text, y, size, color, bold=False):
        rendered = self._font(size, bold).render(text, True, color)
        surface.blit(rendered, rendered.get_rect(center=(320, y)))

    def draw_canvas(self, surface):
        """Draw the full title composition at the game's native 640x448."""
        surface.fill(INK)
        # A hand-composed silhouette of Eldenmere's mountains and sanctuary.
        pygame.draw.circle(surface, (74, 72, 92), (320, 210), 102)
        pygame.draw.circle(surface, (119, 99, 104), (320, 210), 71)
        pygame.draw.polygon(surface, (34, 48, 70),
                            [(0, 298), (85, 207), (142, 255), (233, 168),
                             (319, 271), (417, 187), (519, 257), (601, 194),
                             (640, 231), (640, 448), (0, 448)])
        pygame.draw.polygon(surface, (23, 39, 57),
                            [(0, 344), (99, 267), (172, 314), (273, 247),
                             (381, 338), (499, 260), (640, 323),
                             (640, 448), (0, 448)])
        # Sanctuary: a bell tower, pitched roof, windows and entrance.
        pygame.draw.rect(surface, (22, 28, 42), (261, 277, 118, 98))
        pygame.draw.polygon(surface, (14, 24, 38),
                            [(245, 283), (320, 235), (395, 283)])
        pygame.draw.rect(surface, (18, 26, 40), (302, 207, 36, 84))
        pygame.draw.polygon(surface, (14, 24, 38),
                            [(296, 212), (320, 171), (344, 212)])
        pygame.draw.rect(surface, GOLD, (316, 221, 8, 18))
        for x in (282, 350):
            pygame.draw.rect(surface, (180, 138, 76), (x, 306, 9, 22))
        pygame.draw.rect(surface, (8, 17, 29), (311, 333, 18, 42))
        pygame.draw.rect(surface, (15, 24, 36), (0, 375, 640, 73))
        for x, y in ((52, 86), (120, 151), (542, 98), (589, 183), (456, 73)):
            glow = 165 + int(40 * (0.5 + 0.5 * math.sin(self.elapsed * 1.3 + x)))
            pygame.draw.circle(surface, (glow, glow, 167), (x, y), 1)
        pygame.draw.line(surface, GOLD, (148, 62), (492, 62), 1)
        self._center(surface, "THE BROKEN", 104, 43, CREAM, True)
        self._center(surface, "COVENANT", 148, 51, GOLD, True)
        self._center(surface, "A TALE OF ELDENMERE", 181, 15, MUTED)
        pygame.draw.line(surface, GOLD, (202, 196), (438, 196), 1)
        for i, label in enumerate(self.OPTIONS):
            y = 382 + i * 30
            color = GOLD if i == self.selected else CREAM
            if i == self.selected:
                pygame.draw.polygon(surface, GOLD,
                                    [(254, y), (260, y - 4), (260, y + 4)])
            self._center(surface, label, y, 20, color, i == self.selected)
        self._center(surface, "W/S OR ARROWS   ·   ENTER TO SELECT", 443, 11, MUTED)

    def draw(self, window):
        """Letterbox without changing the world's 640x448 rendering contract."""
        canvas = pygame.Surface((640, 448))
        self.draw_canvas(canvas)
        width, height = window.get_size()
        scale = min(width / 640, height / 448)
        size = (max(1, int(640 * scale)), max(1, int(448 * scale)))
        if scale >= 1:
            integer = max(1, min(width // 640, height // 448))
            size = (640 * integer, 448 * integer)
        window.fill((9, 14, 24))
        frame = pygame.transform.scale(canvas, size)
        window.blit(frame, ((width - size[0]) // 2, (height - size[1]) // 2))
