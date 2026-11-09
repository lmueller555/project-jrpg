"""Caelan's captured-pointer elemental gear and its pixel mechanism.

The controller only reports a seated element. Battle resources, turns, sounds,
and persistence belong to the caller. All pointer positions use logical units.
"""
from __future__ import annotations

from functools import lru_cache
import math

import pygame

from gear_state import GEM_ORDER


TAU = math.tau
QUARTER = math.pi / 2
SNAP_SECONDS = .10
BURST_SECONDS = .40
GEM_LABELS = {'nature': 'Nature', 'water': 'Water', 'fire': 'Fire', 'ice': 'Ice'}
# A different silhouette and a different engraved mark accompany every hue.
GEM_PALETTES = {
    'nature': ('#143d2a', '#397d45', '#83c968', '#dcf6ab'),
    'water': ('#153c65', '#277fb8', '#7bdcf0', '#e1fcff'),
    'fire': ('#702a22', '#cf5331', '#ffae52', '#fff2b1'),
    'ice': ('#39516e', '#739bc2', '#c9e8fb', '#ffffff'),
}


def wrap_angle(angle):
    """Shortest signed angle, including when the pointer crosses twelve."""
    return (float(angle) + math.pi) % TAU - math.pi


def _slot(angle):
    # floor(x+.5) gives deterministic half-slot catches for either direction.
    return -math.floor(angle / QUARTER + .5) % len(GEM_ORDER)


def _nearest_stop(angle):
    return math.floor(angle / QUARTER + .5) * QUARTER


def _color(value, alpha=255):
    color = pygame.Color(value)
    return color.r, color.g, color.b, alpha


def _point(radius, theta, center=(24, 25)):
    return (round(center[0] + math.sin(theta) * radius),
            round(center[1] - math.cos(theta) * radius))


def _polygon(surface, color, points, width=0):
    pygame.draw.polygon(surface, color, [(round(x), round(y)) for x, y in points], width)


def _gem(surface, gem, center, bright=False):
    """Upright faceted gems: leaf, droplet, flame and six-point ice crystal."""
    x, y = center
    dark, mid, light, glint = GEM_PALETTES[gem]
    pygame.draw.circle(surface, '#071a18', (x, y + 1), 6)
    pygame.draw.circle(surface, '#4e4937', (x, y), 5)
    pygame.draw.circle(surface, '#b4a780' if bright else '#858c7a', (x, y), 4, 1)
    if gem == 'nature':
        shape = [(x - 3, y + 3), (x - 3, y - 1), (x, y - 4),
                 (x + 3, y - 3), (x + 3, y + 1), (x, y + 4)]
        _polygon(surface, dark, shape)
        _polygon(surface, mid, [(x - 2, y + 2), (x - 2, y - 1),
                                (x + 2, y - 3), (x + 2, y + 1), (x, y + 3)])
        pygame.draw.line(surface, light, (x - 1, y + 2), (x + 1, y - 2))
        pygame.draw.line(surface, light, (x, y), (x - 1, y - 1))
    elif gem == 'water':
        _polygon(surface, dark, [(x, y - 4), (x + 3, y), (x + 3, y + 2),
                                (x + 1, y + 4), (x - 2, y + 3), (x - 3, y + 1)])
        _polygon(surface, mid, [(x, y - 3), (x + 2, y), (x + 2, y + 2),
                               (x, y + 3), (x - 2, y + 1)])
        pygame.draw.line(surface, light, (x - 1, y), (x - 1, y + 2))
        surface.set_at((x, y + 3), pygame.Color(light))
    elif gem == 'fire':
        _polygon(surface, dark, [(x - 3, y + 3), (x - 4, y), (x - 1, y - 4),
                                (x, y - 1), (x + 2, y - 3), (x + 4, y + 2), (x + 1, y + 4)])
        _polygon(surface, mid, [(x - 2, y + 2), (x - 2, y), (x - 1, y - 2),
                               (x, y + 1), (x + 2, y - 1), (x + 2, y + 3), (x, y + 3)])
        _polygon(surface, light, [(x - 1, y + 3), (x, y), (x + 1, y + 3)])
    else:
        for dx, dy in ((0, 4), (3, 2), (3, -2)):
            pygame.draw.line(surface, dark, (x - dx, y - dy), (x + dx, y + dy), 3)
            pygame.draw.line(surface, light, (x - dx, y - dy), (x + dx, y + dy))
        surface.set_at((x, y), pygame.Color(glint))
    # A fixed upper-left light keeps the gem faces upright as their mount moves.
    if bright:
        surface.set_at((x - 1, y - 2), pygame.Color(glint))


def _empty_socket(surface, center):
    """An empty brass setting, with no elemental color or engraved gem."""
    x, y = center
    pygame.draw.circle(surface, '#071a18', (x, y + 1), 6)
    pygame.draw.circle(surface, '#4e4937', (x, y), 5)
    pygame.draw.circle(surface, '#858c7a', (x, y), 4, 1)
    pygame.draw.circle(surface, '#182b26', (x, y), 3)
    pygame.draw.line(surface, '#687467', (x - 2, y + 2), (x + 1, y + 2))


@lru_cache(maxsize=1)
def _housing():
    surface = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.circle(surface, '#081b17', (24, 26), 23)
    pygame.draw.circle(surface, '#5e6854', (24, 25), 23, 1)
    pygame.draw.circle(surface, '#253f35', (24, 25), 22, 1)
    # Riveted, stepped mounting corners retain the UI's green and gold fittings.
    for x, y, sx, sy in ((2, 3, 1, 1), (45, 3, -1, 1),
                         (2, 45, 1, -1), (45, 45, -1, -1)):
        pygame.draw.line(surface, '#a49060', (x, y), (x + sx * 6, y))
        pygame.draw.line(surface, '#a49060', (x, y), (x, y + sy * 6))
        surface.set_at((x + sx * 2, y + sy * 2), pygame.Color('#e7cc8e'))
    return surface


@lru_cache(maxsize=3840)
def _mechanism(angle_step, active_index, owned_gems=GEM_ORDER):
    """Cache native pixel layers; angle quantization never affects interaction."""
    theta = angle_step * TAU / 240
    surface = pygame.Surface((48, 48), pygame.SRCALPHA)
    # Sixteen interlocking teeth, each with a shadow wall and a bevel.
    for index in range(16):
        a = theta + index * TAU / 16
        corners = [_point(radius, a + offset) for radius, offset in
                   ((18, -.115), (21, -.09), (21, .09), (18, .115))]
        _polygon(surface, '#192b28', [(x, y + 1) for x, y in corners])
        _polygon(surface, '#687467', corners)
        pygame.draw.line(surface, '#c6c9a7', corners[0], corners[1])
        pygame.draw.line(surface, '#d6c58d', corners[1], corners[2])
        pygame.draw.line(surface, '#39483e', corners[2], corners[3])
    pygame.draw.circle(surface, '#30443b', (24, 25), 19)
    pygame.draw.circle(surface, '#a5af97', (24, 25), 18, 1)
    pygame.draw.circle(surface, '#5f6e5b', (24, 25), 17)
    pygame.draw.circle(surface, '#172d26', (24, 25), 15)
    pygame.draw.circle(surface, '#bcaa72', (24, 25), 15, 1)
    pygame.draw.circle(surface, '#586853', (24, 25), 10, 1)
    # The rune engravings, radial braces and inner teeth turn with the wheel.
    for index in range(4):
        a = theta + index * QUARTER
        for shift in (-.19, .19):
            pygame.draw.line(surface, '#a09568', _point(7, a + shift), _point(10, a + shift))
        rune = a + QUARTER / 2
        for start, finish in ((-.10, .10), (-.10, -.03), (.03, .10)):
            pygame.draw.line(surface, '#293d31', _point(17, rune + start), _point(17, rune + finish))
        pygame.draw.line(surface, '#d0c68e', _point(16, rune - .04), _point(18, rune - .04))
        surface.set_at(_point(17, rune + .09), pygame.Color('#79846a'))
    pygame.draw.circle(surface, '#081d1a', (24, 26), 7)
    pygame.draw.circle(surface, '#9c8c5b', (24, 25), 6)
    pygame.draw.circle(surface, '#d5cdab', (24, 25), 5)
    pygame.draw.circle(surface, '#526458', (24, 25), 4)
    pygame.draw.circle(surface, '#203d32', (24, 25), 3)
    # A square axle and short chisel mark create a mechanical center.
    pygame.draw.rect(surface, '#b7bca2', (23, 24, 3, 3))
    pygame.draw.line(surface, '#3c5247', (23, 26), (25, 24))
    surface.set_at((23, 24), pygame.Color('#f4e7b8'))
    for index, gem in enumerate(GEM_ORDER):
        center = _point(12, theta + index * QUARTER)
        if gem in owned_gems:_gem(surface, gem, center, index == active_index)
        else:_empty_socket(surface, center)
    return surface


class GearWidget:
    """One wheel, one captured gesture, one eventual committed gem."""
    def __init__(self, active_gem='water', owned_gems=None):
        if active_gem not in GEM_ORDER:
            raise ValueError('Unknown gear gem: ' + str(active_gem))
        owned_gems = GEM_ORDER if owned_gems is None else owned_gems
        if (not isinstance(owned_gems, (tuple, list))
                or any(gem not in GEM_ORDER for gem in owned_gems)
                or len(set(owned_gems)) != len(owned_gems)
                or owned_gems and active_gem not in owned_gems):
            raise ValueError('Invalid owned gear gems')
        self.owned_gems = tuple(gem for gem in GEM_ORDER if gem in owned_gems)
        self._active_gem = active_gem
        self.rect = pygame.Rect(0, 0, 48, 48)
        self.angle = -GEM_ORDER.index(active_gem) * QUARTER
        self.dragging = False
        self.settling = False
        self.hovered = False
        self.focused = False
        self._pointer_angle = None
        self._keyboard_preview = False
        self._snap_from = self.angle
        self._snap_to = self.angle
        self._snap_time = 0.
        self._pending_commit = None
        self._burst_remaining = 0.
        self._passing_remaining = 0.
        self._notices = []
        self._reduced_motion = False

    @property
    def active_gem(self):
        return self._active_gem

    @active_gem.setter
    def active_gem(self, gem):
        if gem not in GEM_ORDER or self.owned_gems and gem not in self.owned_gems:
            raise ValueError('Unknown gear gem: ' + str(gem))
        if gem == self._active_gem:
            return
        self._active_gem = gem
        self.cancel()

    @property
    def preview_gem(self):
        return GEM_ORDER[_slot(self._nearest_owned_stop(self.angle))]

    def _nearest_owned_stop(self, angle):
        if not self.owned_gems:
            return -GEM_ORDER.index(self._active_gem) * QUARTER
        candidates = []
        for gem in self.owned_gems:
            base = -GEM_ORDER.index(gem) * QUARTER
            turn = math.floor((angle - base) / TAU + .5)
            candidates.append(base + turn * TAU)
        return min(candidates, key=lambda stop: (abs(stop - angle), -stop))

    @property
    def busy(self):
        """A captured gesture or unconfirmed keyboard preview owns input."""
        return self.dragging or self.settling or self._keyboard_preview

    @property
    def wheel_rect(self):
        side = max(0, min(self.rect.width, self.rect.height))
        return pygame.Rect(self.rect.centerx - side // 2, self.rect.top, side, side)

    def layout(self, rect):
        self.rect = pygame.Rect(rect)
        return self.rect

    def consume_notices(self):
        notices, self._notices = tuple(self._notices), []
        return notices

    def _pointer(self, point):
        wheel = self.wheel_rect
        if point is None or not wheel.width or not wheel.height:
            return None
        x = (point[0] - wheel.left) * 48 / wheel.width - 24
        y = (point[1] - wheel.top) * 48 / wheel.height - 25
        if math.hypot(x, y) < 3:
            return None
        return math.atan2(y, x)

    def _rotate_to_pointer(self, point):
        pointer = self._pointer(point)
        if pointer is None:
            self._pointer_angle = None
            return
        if self._pointer_angle is not None:
            previous = self.angle
            self.angle += wrap_angle(pointer - self._pointer_angle)
            # A quiet detent belongs to a gem crossing the fixed catch, rather
            # than to the halfway boundary that chooses its eventual snap.
            if self.angle > previous:
                crossed = math.floor(self.angle / QUARTER + 1e-9) != math.floor(previous / QUARTER + 1e-9)
            else:
                crossed = math.ceil(self.angle / QUARTER - 1e-9) != math.ceil(previous / QUARTER - 1e-9)
            if crossed:
                self._passing_remaining = .075
                self._notices.append('detent')
        self._pointer_angle = pointer

    def _finish_snap(self):
        self.angle = wrap_angle(self._snap_to)
        self.settling = False
        gem = self.preview_gem
        if gem != self._active_gem:
            self._active_gem = gem
            self._pending_commit = gem
        self._notices.append('seat')
        self._burst_remaining = 0. if self._reduced_motion else BURST_SECONDS

    def _start_snap(self, reduced_motion):
        self.dragging = False
        self._pointer_angle = None
        self._keyboard_preview = False
        self._snap_from = self.angle
        self._snap_to = self._nearest_owned_stop(self.angle)
        self._snap_time = 0.
        self._reduced_motion = bool(reduced_motion)
        self.settling = True
        if reduced_motion:
            # Move the image immediately, but retain ownership until update
            # atomically reports the commit to the battle model. A second
            # input in this frame can still cancel the uncommitted stop.
            self.angle = self._snap_to
            self._snap_time = SNAP_SECONDS

    def cancel(self):
        """Restore the committed stop without seating or emitting a new cue."""
        self.dragging = self.settling = self._keyboard_preview = False
        self._pointer_angle = None
        self._pending_commit = None
        self._burst_remaining = self._passing_remaining = 0.
        self._notices.clear()
        self.angle = -GEM_ORDER.index(self._active_gem) * QUARTER

    def handle_event(self, event, point=None, enabled=True, reduced_motion=False):
        self._reduced_motion = bool(reduced_motion)
        if not enabled:
            self.cancel()
            self.focused = False
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.settling:
                # Once released, the mechanism owns this short catch. A click
                # over another command cannot cancel it or spend the old gem.
                return True
            if point is None or not self.rect.collidepoint(point):
                if self.focused:
                    self.cancel()
                    self.focused = False
                return False
            self.focused = True
            pointer = self._pointer(point)
            if pointer is not None:
                self.dragging = True
                self._keyboard_preview = False
                self._pointer_angle = pointer
                self._burst_remaining = 0.
            return True
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self._rotate_to_pointer(point)
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            if point is not None:
                self._rotate_to_pointer(point)
            self._start_snap(reduced_motion)
            return True
        if event.type != pygame.KEYDOWN or not self.focused:
            return False
        if event.key in (pygame.K_ESCAPE, pygame.K_TAB):
            self.cancel()
            self.focused = False
            return True
        if getattr(event, 'repeat', False):
            return event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN,
                                 pygame.K_KP_ENTER, pygame.K_SPACE)
        if self.settling:
            return True
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            if len(self.owned_gems) < 2:return True
            self.dragging = False
            self._pointer_angle = None
            self._keyboard_preview = True
            direction = -QUARTER if event.key == pygame.K_LEFT else QUARTER
            self.angle = self._nearest_owned_stop(self.angle) + direction
            while GEM_ORDER[_slot(self.angle)] not in self.owned_gems:
                self.angle += direction
            self._notices.append('detent')
            self._passing_remaining = .075
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._start_snap(reduced_motion)
            return True
        return False

    def update(self, seconds, reduced_motion=False):
        seconds = float(seconds)
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Gear time must be finite and nonnegative')
        self._reduced_motion = bool(reduced_motion)
        self._burst_remaining = max(0., self._burst_remaining - seconds)
        self._passing_remaining = max(0., self._passing_remaining - seconds)
        if reduced_motion:
            self._burst_remaining = self._passing_remaining = 0.
        if self.settling:
            self._snap_time += seconds
            progress = min(1., self._snap_time / SNAP_SECONDS)
            # A crisp catch eases out, with no spring overshoot or slot ambiguity.
            eased = 1 - (1 - progress) ** 3
            self.angle = self._snap_from + (self._snap_to - self._snap_from) * eased
            if progress >= 1 or reduced_motion:
                self._finish_snap()
        commit, self._pending_commit = self._pending_commit, None
        return commit

    def draw(self, painter, elapsed=0., enabled=True, slowed=False, focused=False):
        """Blit nearest-scaled native pixels; labels use the display font bank."""
        if self.rect.width <= 0 or self.rect.height <= 0:
            return
        wheel = self.wheel_rect
        layer = _housing().copy()
        angle_step = round((self.angle % TAU) / TAU * 240) % 240
        layer.blit(_mechanism(angle_step, GEM_ORDER.index(self._active_gem), self.owned_gems), (0, 0))
        active_color = GEM_PALETTES[self._active_gem][2]
        moving = self.dragging or self.settling or self._keyboard_preview
        # The 12 o'clock catch is bolted to the housing, outside the turning bank.
        _polygon(layer, '#142c24', [(19, 0), (28, 0), (29, 6), (24, 11), (19, 6)])
        _polygon(layer, '#6c6546', [(20, 0), (27, 0), (27, 5), (24, 9), (21, 5)])
        pygame.draw.line(layer, '#f1cd77', (21, 1), (26, 1))
        pygame.draw.line(layer, '#b69e68', (21, 2), (23, 6))
        pygame.draw.line(layer, '#394b3a', (26, 2), (25, 6))
        _polygon(layer, active_color if not moving else '#dbc58b', [(23, 5), (25, 5), (24, 7)])
        if self._passing_remaining > 0 and not self._reduced_motion:
            pygame.draw.line(layer, '#aaa16b', (21, 9), (22, 10))
            pygame.draw.line(layer, '#aaa16b', (26, 9), (27, 10))
        if enabled and (self.hovered or focused or self.focused):
            for x, y, sx in ((0, 20, 1), (47, 20, -1)):
                pygame.draw.line(layer, '#f1cd77', (x, y), (x, y + 7))
                pygame.draw.line(layer, '#b59d66', (x, y), (x + sx * 2, y - 2))
        if self.dragging:
            pygame.draw.line(layer, '#d5dbba', (21, 46), (27, 46))
        if not enabled:
            veil = pygame.Surface((48, 48), pygame.SRCALPHA)
            veil.fill((13, 32, 27, 100))
            layer.blit(veil, (0, 0))
        painter.image(layer, wheel)
        if self._burst_remaining > 0 and not self._reduced_motion and enabled:
            self._draw_burst(painter)
        # Extra height belongs to a crisp display-resolution active element label.
        if self.rect.height - wheel.height >= 10:
            painter.text(GEM_LABELS[self._active_gem],
                         (self.rect.centerx, self.rect.bottom - 1), role='small',
                         color=active_color if enabled else '#829381', anchor='midbottom', bold=True)

    def _draw_burst(self, painter):
        progress = 1 - self._burst_remaining / BURST_SECONDS
        gem = self._active_gem
        _, mid, light, glint = GEM_PALETTES[gem]
        wheel = self.wheel_rect
        scale = wheel.width / 48
        # A small native layer keeps sparks as crisp as the mechanism and gives
        # their outer tips eight pixels of air beyond its mounting frame.
        overlay = pygame.Surface((64, 64), pygame.SRCALPHA)
        cx, cy = 32, 20
        alpha = round(225 * (1 - progress) ** 1.45)

        # Energy chases both engraved braces below the seated gem. The front
        # travels toward the axle; its thin afterglow fades before the sparks.
        trace_time = min(1., progress / .60)
        trace_alpha = round(210 * max(0., 1 - progress / .72))
        if trace_alpha:
            for direction in (-1, 1):
                route = [(32, 25), (32 + 3 * direction, 26),
                         (32 + 3 * direction, 28), (32, 30), (32, 33)]
                for index in range(len(route) - 1):
                    start = route[index]
                    finish = route[index + 1]
                    covered = max(0., min(1., trace_time * (len(route) - 1) - index))
                    if covered:
                        end = (round(start[0] + (finish[0] - start[0]) * covered),
                               round(start[1] + (finish[1] - start[1]) * covered))
                        pygame.draw.line(overlay, _color(light, trace_alpha), start, end)
                        if covered < 1:
                            overlay.set_at(end, _color(glint, trace_alpha))

        if gem == 'nature':
            # Paired leaf forks unfurl along four short, outward curling stems.
            for index, direction in enumerate((-1, 1, -1, 1)):
                age = max(0., min(1., progress * 1.2 - (index // 2) * .16))
                x = round(cx + direction * (4 + 13 * age))
                y = round(cy - 1 - 10 * age + 3 * age * age + (index // 2) * 5)
                pygame.draw.lines(overlay, _color(mid, alpha), False,
                                  [(x - direction, y + 3), (x, y), (x + 2 * direction, y - 2)])
                pygame.draw.line(overlay, _color(light, alpha), (x, y), (x - direction, y - 2))
                _polygon(overlay, _color(light, alpha),
                         [(x + direction, y - 1), (x + direction, y - 4),
                          (x + 3 * direction, y - 3), (x + 2 * direction, y - 1)])
                _polygon(overlay, _color(mid, alpha),
                         [(x - direction, y), (x - 3 * direction, y - 2),
                          (x - 2 * direction, y - 3), (x - direction, y - 2)])
                overlay.set_at((x + direction, y - 3), _color(glint, alpha))
        elif gem == 'water':
            # Two offset ripple fronts flatten across the brass, with faceted
            # droplets rising in a small fan and falling back toward the catch.
            radius = round(5 + progress * 12)
            pygame.draw.ellipse(overlay, _color(light, round(alpha * .70)),
                                (cx - radius, cy - radius // 2, radius * 2 + 1, radius + 1), 1)
            inner = max(2, radius - 4)
            pygame.draw.ellipse(overlay, _color(mid, round(alpha * .55)),
                                (cx - inner, cy - inner // 2 + 2, inner * 2 + 1, inner + 1), 1)
            for index, offset in enumerate((-1., -.45, .45, 1.)):
                x = round(cx + offset * (5 + 15 * progress))
                y = round(cy - 3 - 10 * progress + 11 * progress * progress + index % 2 * 2)
                _polygon(overlay, _color(light, alpha),
                         [(x, y - 2), (x + 1, y), (x + 1, y + 1),
                          (x, y + 2), (x - 1, y + 1), (x - 1, y)])
                overlay.set_at((x, y), _color(glint, alpha))
        elif gem == 'fire':
            # Thin hot heads curl upward above their fading copper-orange tails.
            for index, direction in enumerate((-1, 1, -1, 1)):
                path = []
                for step in range(6):
                    age = max(0., progress - .20 + step * .04)
                    turn = age * 5 + index * 1.45
                    path.append((round(cx + direction * (3 + 12 * age) + math.sin(turn) * 2),
                                 round(cy + index % 2 * 3 - age * 18 + math.cos(turn) * 2)))
                pygame.draw.lines(overlay, _color(mid, round(alpha * .65)), False, path, 2)
                pygame.draw.lines(overlay, _color(light, alpha), False, path[-3:])
                overlay.set_at(path[-1], _color(glint, alpha))
            if progress < .45:
                tongue = round(5 * (1 - progress / .45))
                _polygon(overlay, _color(light, alpha),
                         [(cx - 2, cy + 1), (cx, cy - tongue - 2), (cx + 2, cy + 1)])
        else:
            # Ice sends six-point crystal glints along a diamond-shaped front.
            for index, theta in enumerate((-.95, .95, math.pi - .65, math.pi + .65)):
                distance = 6 + progress * 14
                x = round(cx + math.sin(theta) * distance)
                y = round(cy - math.cos(theta) * distance)
                pulse = max(.35, math.sin(min(math.pi, (progress * 1.4 + index * .13) * math.pi)))
                strength = round(alpha * pulse)
                size = 3 if index % 2 else 2
                for dx, dy in ((0, size), (size, 1), (size, -1)):
                    pygame.draw.line(overlay, _color(light, strength),
                                     (x - dx, y - dy), (x + dx, y + dy))
                overlay.set_at((x, y), _color(glint, strength))
                if size == 3:
                    for direction in (-1, 1):
                        pygame.draw.line(overlay, _color(mid, strength),
                                         (x, y + 2 * direction), (x + direction, y + 3 * direction))

        if progress < .30:
            size = max(1, round((1 - progress / .30) * 4))
            pygame.draw.line(overlay, _color(glint, alpha), (cx - size, cy), (cx + size, cy))
            pygame.draw.line(overlay, _color(glint, alpha), (cx, cy - size), (cx, cy + size))
        painter.image(overlay, (round(wheel.left - 8 * scale), round(wheel.top - 8 * scale),
                                round(64 * scale), round(64 * scale)))
