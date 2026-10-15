"""Reusable, display-resolution dialogue UI with identity-gated portraits."""
from dataclasses import dataclass
from pathlib import Path
import pygame

@dataclass(frozen=True)
class DialogueMessage:
    text: str
    speaker: str = ""
    mode: str = "narration"
    portrait: str | None = None

class FontManager:
    def __init__(self):
        self.cache = {}

    def get(self, size, bold=False):
        key = (size, bold)
        if key not in self.cache:
            self.cache[key] = pygame.font.SysFont("georgia,dejavu sans", size, bold=bold)
        return self.cache[key]

def wrap(text, font, width):
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = (line + " " + word).strip()
            if line and font.size(candidate)[0] > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines

class DialogueBox:
    def __init__(self, assets=None):
        self.assets = Path(assets) if assets else None
        self.fonts = FontManager()
        # Registry entries are identity-reviewed source crops, never generic art.
        self.approved_portraits = {
            f'caelen.{mood}': f'portraits/caelen/{mood}.png'
            for mood in ('neutral', 'happy', 'concerned', 'determined', 'surprised')
        }
        self._portrait_cache = {}
        self.message = None
        self.page = 0

    def show(self, text, speaker="", mode="narration", portrait=None):
        if mode not in ("character", "narration"):
            raise ValueError("Invalid dialogue mode")
        if portrait is None and mode == "character" and speaker.strip().lower() == "caelen":
            portrait = "caelen.neutral"
        self.message = DialogueMessage(text, speaker, mode, portrait)
        self.page = 0

    def _portrait(self):
        if not self.message or self.message.mode != "character":
            return None
        name = self.approved_portraits.get(self.message.portrait)
        if not name or not self.assets:
            return None
        path = self.assets / name
        if not path.is_file():
            return None  # Honest fallback while portrait assets are being installed.
        if name not in self._portrait_cache:
            result = pygame.image.load(str(path)).convert_alpha()
            if result.get_size() != (96, 96):
                raise ValueError("Approved portrait must be 96x96")
            self._portrait_cache[name] = result
        return self._portrait_cache[name]

    def _layout(self, size):
        w, h = size
        scale = min(w / 960, h / 672)
        panel_w = min(w - 20, max(280, round(900 * scale)))
        panel_h = min(h - 20, max(130, round(180 * scale)))
        x, y = (w - panel_w) // 2, h - panel_h - max(10, round(18 * scale))
        portrait = self._portrait()
        slot = min(round(96 * max(1, scale)), panel_h - 32) if portrait else 0
        text_x = x + 20 + (slot + 20 if portrait else 0)
        font_size = max(15, round(22 * scale))
        return (x, y, panel_w, panel_h, text_x, slot, portrait, font_size)

    def _pages(self, size):
        if not self.message:
            return []
        x, y, w, h, text_x, slot, portrait, fs = self._layout(size)
        font = self.fonts.get(fs)
        lines = wrap(self.message.text, font, max(80, x + w - text_x - 22))
        capacity = max(1, (h - 77) // (font.get_linesize() + 4))
        return [lines[i:i + capacity] for i in range(0, len(lines), capacity)] or [[""]]

    def advance(self, size):
        if not self.message:
            return False
        if self.page + 1 < len(self._pages(size)):
            self.page += 1
        else:
            self.message = None
            self.page = 0
        return True

    def draw(self, surface):
        if not self.message:
            return
        x, y, w, h, text_x, slot, portrait, fs = self._layout(surface.get_size())
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (15, 27, 45, 241), panel.get_rect(), border_radius=11)
        pygame.draw.rect(panel, (205, 161, 91), panel.get_rect(), 3, border_radius=11)
        pygame.draw.rect(panel, (89, 113, 142), panel.get_rect().inflate(-12, -12), 1, border_radius=7)
        surface.blit(panel, (x, y))
        if portrait:
            rect = pygame.Rect(x + 18, y + 17, slot, slot)
            pygame.draw.rect(surface, (205, 161, 91), rect.inflate(6, 6), 2)
            surface.blit(pygame.transform.smoothscale(portrait, rect.size), rect)
        name_font = self.fonts.get(max(17, fs + 2), bold=True)
        body_font = self.fonts.get(fs)
        label = self.message.speaker or "Notice"
        surface.blit(name_font.render(label, True, (245, 204, 138)), (text_x, y + 13))
        baseline = y + 50
        for line in self._pages(surface.get_size())[self.page]:
            surface.blit(body_font.render(line, True, (248, 239, 222)), (text_x, baseline))
            baseline += body_font.get_linesize() + 4
        marker_x, marker_y = x + w - 26, y + h - 23
        pygame.draw.polygon(surface, (245, 204, 138),
                    ((marker_x, marker_y), (marker_x + 12, marker_y),
                     (marker_x + 6, marker_y + 8)))
