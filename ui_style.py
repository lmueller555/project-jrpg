"""Eldenmere's shared panels and display-resolution, accessible UI text.

World sprites retain their integer scale. Each Painter maps logical layout units
onto an actual output surface and rasterizes its fonts there with antialiasing;
text never travels through the low-resolution world image.
"""
from __future__ import annotations

from array import array
import math
from pathlib import Path

import pygame
import pygame.freetype

ROOT = Path(__file__).resolve().parent
FONT_ROOT = ROOT/'assets/ui/fonts'
FOREST = '#1c3a32'
FOREST_LIGHT = '#314f40'
FOREST_DARK = '#10271f'
IVORY = '#f8f0d9'
BRASS = '#b59d66'
GOLD = '#f1cd77'
INK = '#302c24'
PARCHMENT = '#eee0bd'
PARCHMENT_DARK = '#d6c49c'
MUTED = '#b7c3af'
DISABLED = '#829381'
SHADOW = '#0a1915'
ERROR = '#f3c0a4'


def draw_ambient_speech(game, target, camera, actor, lines, parchment=True):
    """Draw a noninteractive NPC bark on the display-resolution UI layer.

    Routine state and timing remain entirely with the caller. This helper also
    works for native-resolution export tools, without the former small_font
    dependency or an assumption about the game's current render target.
    """
    style = getattr(game, 'ui', None)
    if style is None:
        style = getattr(game, '_ambient_ui_style', None)
        if style is None:
            style = UIStyle(game)
            game._ambient_ui_style = style
    # Production passes the enlarged UI surface. Export tools may pass a
    # native world crop of any size; its world/camera coordinates stay native.
    logical_size = (480, 320) if target is getattr(game, 'ui_surface', None) else target.get_size()
    painter = style.painter(target, logical_size)
    position = getattr(actor, 'story_position', None) or actor.position
    anchor = getattr(actor, 'story_draw_anchor', None) or getattr(actor, 'draw_anchor', (12, 30))
    image = getattr(actor, 'story_sprite', None)
    if image is None and hasattr(actor, 'sprite'):image = actor.sprite(getattr(game, 'elapsed_ms', 0))
    top = image.get_bounding_rect().top if isinstance(image, pygame.Surface) else 0
    head = (round(position[0]-camera[0]), round(position[1]-anchor[1]+top-camera[1]))
    if not painter.bounds.inflate(24, 24).collidepoint(head):return None
    wrapped = []
    for line in ([lines] if isinstance(lines, str) else lines):
        wrapped.extend(painter.wrap(line, 220))
    if not wrapped:return None
    line_height = painter.font().get_linesize()+2
    width = max(painter.font().size(line)[0] for line in wrapped)+18
    height = len(wrapped)*line_height+14
    bounds = painter.bounds.inflate(-12, -12)
    face = pygame.Rect(head[0]-12, head[1]-2, 24, 34)
    candidates = []
    for rect in (pygame.Rect(head[0]-width//2, head[1]-height-9, width, height),
                 pygame.Rect(head[0]-width//2, face.bottom+7, width, height),
                 pygame.Rect(face.right+8, head[1], width, height),
                 pygame.Rect(face.left-width-8, head[1], width, height)):
        rect = rect.clamp(bounds)
        covered = rect.clip(face)
        candidates.append((covered.width*covered.height, rect))
    rect = min(enumerate(candidates), key=lambda item: (item[1][0], item[0]))[1][1]
    painter.panel(rect, parchment=parchment)
    color = INK if parchment else IVORY
    for index, line in enumerate(wrapped):
        painter.text(line, (rect.x+9, rect.y+7+index*line_height), color=color)
    if head[1] >= rect.bottom:
        x = max(rect.left+10, min(rect.right-10, head[0]))
        painter.line(BRASS, (x, rect.bottom-1), (x, min(rect.bottom+7, head[1]-2)))
    elif head[1] < rect.top:
        x = max(rect.left+10, min(rect.right-10, head[0]))
        painter.line(BRASS, (x, rect.top), (x, max(rect.top-7, head[1]+3)))
    return rect


class DisplayFont:
    """Atkinson text with baseline-aligned fallback for symbols it omits.

    pygame.font.metrics can report the .notdef box as a valid glyph. FreeType
    coverage detects actual missing glyphs, so arrows never become identical
    boxes. The fallback font is bundled too and never depends on the OS.
    """
    def __init__(self, size, bold):
        filename = 'AtkinsonHyperlegible-Bold.ttf' if bold else 'AtkinsonHyperlegible-Regular.ttf'
        path = str(FONT_ROOT/filename)
        self.primary = pygame.font.Font(path, size)
        self.fallback = pygame.font.Font(str(FONT_ROOT/'DejaVuSans.ttf'), size)
        if not pygame.freetype.get_init():pygame.freetype.init()
        self.coverage = pygame.freetype.Font(path, size)
        self._supported = {}
        self._ascent = max(self.primary.get_ascent(), self.fallback.get_ascent())
        self._height = self._ascent+max(font.get_height()-font.get_ascent()
                                       for font in (self.primary, self.fallback))

    def _runs(self, text):
        previous, run = None, ''
        for character in str(text):
            if character not in self._supported:
                self._supported[character] = self.coverage.get_metrics(character)[0] is not None
            font = self.primary if self._supported[character] else self.fallback
            if font is not previous and run:
                yield previous, run
                run = ''
            run += character
            previous = font
        if run:yield previous, run

    def size(self, text):
        return sum(font.size(run)[0] for font, run in self._runs(text)), self._height

    def render(self, text, antialias, color):
        image = pygame.Surface(self.size(text), pygame.SRCALPHA)
        x = 0
        for font, run in self._runs(text):
            rendered = font.render(run, antialias, color)
            image.blit(rendered, (x, self._ascent-font.get_ascent()))
            x += rendered.get_width()
        return image

    def get_height(self):return self._height
    def get_linesize(self):return max(self.primary.get_linesize(), self.fallback.get_linesize(), self._height)
    def get_ascent(self):return self._ascent
    def get_descent(self):return self._ascent-self._height


class LogicalFont:
    """Measure an actual-resolution font in the caller's logical coordinates."""
    def __init__(self, font, scale):
        self.actual = font
        self.scale = scale

    def size(self, text):
        width, height = self.actual.size(str(text))
        return math.ceil(width/self.scale), math.ceil(height/self.scale)

    def get_height(self):return math.ceil(self.actual.get_height()/self.scale)
    def get_linesize(self):return math.ceil(self.actual.get_linesize()/self.scale)
    def get_ascent(self):return math.ceil(self.actual.get_ascent()/self.scale)
    def get_descent(self):return math.floor(self.actual.get_descent()/self.scale)


class UIStyle:
    """Shared resources; painters themselves retain no global drawing state."""
    def __init__(self, game):
        self.game = game
        self._fonts = {}
        self._sounds = {}
        self._last_move = -1000

    def painter(self, canvas, logical_size=(480, 320)):
        return Painter(self, canvas, logical_size)

    def _font(self, size, bold=False):
        key = int(size), bool(bold)
        if key not in self._fonts:
            self._fonts[key] = DisplayFont(*key)
        return self._fonts[key]

    def sound(self, kind='move'):
        """Short quiet menu cues, independent from music and safe without audio."""
        settings = getattr(self.game, 'audio', None)
        volume = getattr(settings, 'effects_volume', 0)
        if volume <= 0:return
        now = pygame.time.get_ticks()
        if kind == 'move':
            if now-self._last_move < 65:return
            self._last_move = now
        try:
            if not pygame.mixer.get_init():pygame.mixer.init()
            rate, sample_format, channels = pygame.mixer.get_init()
            if sample_format != -16:return
            key = kind, rate, channels
            if key not in self._sounds:
                frequency, duration = {'move': (440, .038), 'confirm': (659.25, .075),
                                       'back': (329.63, .055)}.get(kind, (440, .038))
                samples = array('h')
                for index in range(round(rate*duration)):
                    t = index/rate
                    envelope = min(1, t/.005)*max(0, 1-t/duration)**2
                    value = round(4200*envelope*(math.sin(2*math.pi*frequency*t)+
                                                 .12*math.sin(4*math.pi*frequency*t)))
                    samples.extend([value]*channels)
                self._sounds[key] = pygame.mixer.Sound(buffer=samples)
            sound = self._sounds[key]
            sound.set_volume(.24*volume)
            sound.play()
        except (pygame.error, OSError):
            pass


class Painter:
    def __init__(self, style, canvas, logical_size):
        self.style = style
        self.canvas = canvas
        self.logical_size = tuple(logical_size)
        self.bounds = pygame.Rect((0, 0), logical_size)
        width, height = canvas.get_size()
        self.scale = min(width/logical_size[0], height/logical_size[1])
        self.offset = ((width-logical_size[0]*self.scale)/2,
                       (height-logical_size[1]*self.scale)/2)

    def point(self, point):
        return tuple(round(self.offset[index]+point[index]*self.scale) for index in (0, 1))

    def area(self, rect):
        rect = pygame.Rect(rect)
        left, top = self.point(rect.topleft)
        right, bottom = self.point(rect.bottomright)
        return pygame.Rect(left, top, max(1, right-left), max(1, bottom-top))

    def font(self, role='body', bold=False):
        base = {'body': 9, 'small': 7.5, 'hint': 7.5, 'heading': 13,
                'name': 11, 'label': 9, 'title': 20}.get(role, 9)
        minimum = 10 if role in ('small', 'hint') else (18 if role == 'heading' else 12)
        settings = getattr(self.style.game, 'audio', None)
        text_scale = getattr(settings, 'text_scale', 1.0)
        size = max(1, round(max(minimum, round(base*self.scale))*text_scale))
        return LogicalFont(self.style._font(size, bold), self.scale)

    def text(self, text, point, role='body', color=None, anchor='topleft', bold=False):
        font = self.font(role, bold).actual
        image = font.render(str(text), True, color or IVORY)
        target = image.get_rect(**{anchor: self.point(point)})
        self.canvas.blit(image, target)
        return pygame.Rect(round((target.x-self.offset[0])/self.scale),
                           round((target.y-self.offset[1])/self.scale),
                           math.ceil(target.width/self.scale), math.ceil(target.height/self.scale))

    def wrap(self, text, width, role='body', bold=False):
        """Wrap by measured glyph widths, splitting even unspaced long labels."""
        font = self.font(role, bold)
        lines = []
        for paragraph in str(text).split('\n'):
            current = ''
            for word in paragraph.split():
                candidate = (current+' '+word).strip()
                if current and font.size(candidate)[0] > width:
                    lines.append(current)
                    current = word
                else:current = candidate
                while len(current) > 1 and font.size(current)[0] > width:
                    end = 1
                    while end < len(current) and font.size(current[:end+1])[0] <= width:end += 1
                    lines.append(current[:end])
                    current = current[end:]
            lines.append(current)
        return lines or ['']

    def rect(self, color, rect, width=0):
        pygame.draw.rect(self.canvas, color, self.area(rect), 0 if not width else max(1, round(width*self.scale)))

    def line(self, color, a, b, width=1):
        pygame.draw.line(self.canvas, color, self.point(a), self.point(b), max(1, round(width*self.scale)))

    def image(self, surface, rect):
        target = self.area(rect)
        self.canvas.blit(pygame.transform.scale(surface, target.size), target)

    def veil(self, alpha=180):
        layer = pygame.Surface(self.canvas.get_size(), pygame.SRCALPHA)
        layer.fill((10, 25, 21, max(0, min(255, round(alpha)))))
        self.canvas.blit(layer, (0, 0))

    def clip(self, rect=None):
        self.canvas.set_clip(None if rect is None else self.area(rect))

    def panel(self, rect, parchment=False):
        rect = pygame.Rect(rect)
        self.rect(SHADOW, rect.move(2, 3))
        self.rect(PARCHMENT if parchment else FOREST, rect)
        self.rect(BRASS, rect, 1)
        self.rect(PARCHMENT_DARK if parchment else FOREST_LIGHT, rect.inflate(-4, -4), 1)
        # Four understated brass corner fittings provide the hand-built frame.
        for x, y, dx, dy in ((rect.left+3, rect.top+3, 1, 1),
                             (rect.right-4, rect.top+3, -1, 1),
                             (rect.left+3, rect.bottom-4, 1, -1),
                             (rect.right-4, rect.bottom-4, -1, -1)):
            self.line(BRASS, (x, y), (x+dx*5, y))
            self.line(BRASS, (x, y), (x, y+dy*5))

    def lantern(self, point, color=None, size=8):
        color = color or GOLD
        x, y = point
        half = size/2
        self.line(color, (x-half*.4, y-size*.65), (x+half*.4, y-size*.65))
        self.line(color, (x-half*.4, y-size*.65), (x-half*.4, y-size*.42))
        self.line(color, (x+half*.4, y-size*.65), (x+half*.4, y-size*.42))
        body = pygame.Rect(round(x-half*.65), round(y-size*.4), max(3, round(size*.65)), max(4, round(size*.8)))
        self.rect(color, body, 1)
        self.line(color, (x-half*.8, y-size*.4), (x+half*.8, y-size*.4))
        self.line(color, (x, y-size*.2), (x, y+size*.18))
        self.line(color, (x-half*.75, y+size*.45), (x+half*.75, y+size*.45))

    def button(self, rect, label, selected=False, pressed=False, disabled=False):
        rect = pygame.Rect(rect)
        fill = FOREST_DARK if pressed else (FOREST_LIGHT if selected else FOREST)
        self.rect(fill, rect)
        self.rect(BRASS if not disabled else DISABLED, rect, 1)
        if selected and not disabled:self.lantern((rect.left+10, rect.centery), size=7)
        self.text(label, rect.center, color=DISABLED if disabled else (GOLD if selected else IVORY),
                  anchor='center', bold=selected)
