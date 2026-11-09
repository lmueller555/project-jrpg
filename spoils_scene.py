"""Battle rewards, EXP presentation and acknowledged character growth sheets.

The encounter owner commits rewards. This view only presents a detached receipt;
animations, sound and input never mutate inventory, attributes or progression.
"""
from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path

import pygame

from character_attributes import ATTRIBUTE_IDS
from leveling import MAX_LEVEL, level_for_total_xp, total_xp_for_level, xp_to_next_level
from attribute_icons import draw_attribute_icon
from ui_style import (FOREST, FOREST_DARK, FOREST_LIGHT, GOLD, BRASS, IVORY,
                      MUTED, ERROR, PARCHMENT_DARK, INK)

ROOT = Path(__file__).resolve().parent
GROWTH_GREEN = '#176b37'
EXP_GREEN = '#83cba4'
CRYSTAL_COLORS = {
    'aether_emerald': '#76c58f', 'aether_sapphire': '#72a9e2',
    'aether_ruby': '#e58380', 'aether_amethyst': '#b995d7',
    'aether_opal': '#eee7d2', 'aether_topaz': '#e9c464',
    'aether_diamond': '#c6e4df',
}


class SpoilsScene:
    def __init__(self, game, rewards, *, party=None, model=None, progression=None,
                 background=None, loot=None):
        self.game, self.model = game, model
        self.party = tuple(party or ())
        self.rewards = self._snapshot(rewards)
        self.progression = deepcopy(progression)
        self.background = background
        self.loot = deepcopy(loot or {})
        self.awarded = self.dismissed = self.retry_requested = False
        self.result_error = ''
        self.paused = False
        self.focused = True
        self._held = self._hover = self._confirm_key_down = False
        self._elapsed = self._animation_elapsed = 0.0
        self.scroll = self.max_scroll = 0.0
        self.stat_scroll = self.stat_max_scroll = 0.0
        self._level_index = 0
        self._announced_levels = set()
        self._audio_controller = None
        self._portraits = {}
        self._hovered_item = None
        self._loot_focus = False
        self._selected_item = 0
        self.panel_rect = pygame.Rect(12, 12, 456, 296)
        self.title_rect = pygame.Rect(34, 20, 412, 24)
        self.items_view = pygame.Rect(324, 93, 130, 169)
        self.continue_rect = pygame.Rect(316, 276, 138, 28)
        self.retry_rect = self.continue_rect.copy()
        self.resume_rect = pygame.Rect(172, 171, 136, 29)
        self.level_continue_rect = pygame.Rect(324, 270, 120, 26)
        self.stat_view = pygame.Rect(34, 103, 404, 152)
        self.character_rects = {}
        self.bar_rects = {}
        self.stat_row_rects = {}
        self.item_rects = {}
        self._rows = self._footer_lines = []
        self._ids = tuple(self.progression.get('active_ids', ())) if self.progression else ()
        self._level_queue = [self.progression['characters'][identifier] for identifier in self._ids
                             if self.progression['characters'][identifier]['new_level'] >
                                self.progression['characters'][identifier]['old_level']]
        has_exp = bool(self.progression and any(
            self.progression['characters'][identifier]['accepted_xp'] for identifier in self._ids))
        self._animation_duration = 2.4 if has_exp else 0.0
        if getattr(getattr(game, 'audio', None), 'reduced_motion', False):
            self._animation_duration = 0.0

    @staticmethod
    def _snapshot(rewards):
        if (not isinstance(rewards, dict) or set(rewards) != {'drops'}
                or not isinstance(rewards.get('drops'), dict)
                or any(not isinstance(key, str) or type(value) is not int or value <= 0
                       for key, value in rewards['drops'].items())):
            raise ValueError('Invalid spoils snapshot')
        return deepcopy({'drops': rewards['drops']})

    @property
    def ready(self):return self.awarded and not self.result_error

    @property
    def tutorial_active(self):return False

    @property
    def animation_progress(self):
        if self._animation_duration <= 0:return 1.0
        return min(1.0, self._animation_elapsed / self._animation_duration)

    @property
    def level_up(self):
        if self.ready and self.animation_progress >= 1 and self._level_index < len(self._level_queue):
            return self._level_queue[self._level_index]
        return None

    @property
    def presentation_complete(self):
        return self.ready and self.animation_progress >= 1 and self._level_index >= len(self._level_queue)

    def _audio(self):
        if self._audio_controller is None:
            from spoils_audio import SpoilsAudio
            self._audio_controller = SpoilsAudio(self.game)
        return self._audio_controller

    def stop_audio(self):
        if self._audio_controller is not None:self._audio_controller.stop()

    def _sync_presentation(self):
        if not self.ready:
            if self._audio_controller is not None:self._audio_controller.stop_fill()
            return
        if self.animation_progress < 1:
            self._audio().start_fill()
        else:
            if self._audio_controller is not None:self._audio_controller.stop_fill()
            if self.level_up is not None and self._level_index not in self._announced_levels:
                if not self.paused and self.focused:
                    self._audio().level_up()
                    self._announced_levels.add(self._level_index)

    def set_pending(self):
        self.awarded = False
        self.result_error = ''
        self.retry_requested = False
        self._sync_presentation()

    def set_awarded(self, rewards=None):
        if rewards is not None:self.rewards = self._snapshot(rewards)
        self.awarded = True
        self.result_error = ''
        self.retry_requested = False
        self._sync_presentation()

    def set_error(self, message):
        self.awarded = False
        self.result_error = str(message).strip() or 'Rewards could not be collected. Please retry.'
        self.retry_requested = False
        self.stop_audio()

    def finish_animation(self):
        self._animation_elapsed = self._animation_duration
        self._sync_presentation()

    def _sound(self, kind):self.game.ui.sound(kind)

    def _name(self, identifier):
        party = getattr(self.game, 'party', None)
        if party is not None and identifier in party.definitions:return party.definitions[identifier]['name']
        return identifier.title()

    def _portrait(self, identifier):
        if identifier not in self._portraits:
            party = getattr(self.game, 'party', None)
            definition = party.definitions.get(identifier, {}) if party is not None else {}
            filename = definition.get('portrait', 'assets/portraits/eldenmere/'+identifier+'_neutral.png')
            try:self._portraits[identifier] = pygame.image.load(str(ROOT/filename)).convert_alpha()
            except (OSError, pygame.error):self._portraits[identifier] = None
        return self._portraits[identifier]

    @staticmethod
    def _glass(painter, rect, alpha=215):
        surface = pygame.Surface(painter.area(rect).size, pygame.SRCALPHA)
        surface.fill((16, 39, 31, alpha))
        painter.canvas.blit(surface, painter.area(rect))
        painter.rect(FOREST_LIGHT, rect, 1)

    def _layout(self, painter):
        small = painter.font('small').get_linesize()
        body = painter.font().get_linesize()
        heading = painter.font('heading', bold=True).get_linesize()
        self.title_rect = pygame.Rect(34, 18, 412, heading)
        self._rule_y = 65 if self._ids else self.title_rect.bottom + 10
        self._items_label_y = 73 if self._ids else self._rule_y + 12
        self._small = small
        message = self.result_error or ('Rewards received.' if self.awarded else 'Collecting rewards…')
        self._footer_lines = painter.wrap(message, 274, role='small')[:2]
        if len(painter.wrap(message, 274, role='small')) > 2:
            self._footer_lines[-1] = self._footer_lines[-1].rstrip(' .')+'…'
        self._footer_top = 304-max(28, small*len(self._footer_lines))
        button_height = max(26, body+8)
        self.continue_rect = pygame.Rect(316, 304-button_height, 138, button_height)
        self.retry_rect = self.continue_rect.copy()
        self.level_continue_rect = pygame.Rect(324, 297-button_height, 120, button_height)
        self.items_view = (pygame.Rect(324, 92, 130, 170) if self._ids else
                           pygame.Rect(26, self._items_label_y+small+7, 428,
                                       max(28, self._footer_top-10-self._items_label_y-small-7)))
        self.character_rects = {identifier: pygame.Rect(25, 70+index*65, 285, 64)
                                for index, identifier in enumerate(self._ids)}
        self.bar_rects = {}
        for identifier, rect in self.character_rects.items():
            entry = self.progression['characters'][identifier]
            ko = self.progression['end_hp'][identifier] == 0
            gain = 'KO — No EXP' if ko else '+'+format(entry['accepted_xp'], ',')+' EXP'
            gain_width = painter.font('small').size(gain)[0]
            self.bar_rects[identifier] = pygame.Rect(rect.left+50, rect.top+30,
                max(40, rect.width-70-gain_width), 6)
        definitions = getattr(getattr(self.game, 'inventory', None), 'definitions', {})
        offered = self.loot.get('offered', self.rewards['drops'])
        drops = sorted(offered, key=lambda key: definitions.get(key, {}).get('name', key).casefold())
        self._rows = []
        y = 0
        for identifier in drops:
            quantity = self.rewards['drops'].get(identifier, 0)
            lost = self.loot.get('lost', {}).get(identifier, 0)
            label = definitions.get(identifier, {}).get('name', identifier.replace('_', ' ').title())
            quantity_text = '×'+str(quantity) if quantity else 'FULL'
            quantity_width = max(28, painter.font('small', bold=True).size(quantity_text)[0]+6)
            label_width = self.items_view.width-quantity_width-34
            lines = painter.wrap(label, max(24, label_width), role='small')
            height = max(34, len(lines)*small+14)+(small if lost else 0)
            self._rows.append((identifier, lines, quantity_text,
                               pygame.Rect(self.items_view.x, y, self.items_view.width-7, height)))
            y += height+4
        self.max_scroll = max(0, y-4-self.items_view.height)
        self.scroll = max(0.0, min(self.scroll, self.max_scroll))
        self.item_rects = {}
        for identifier, _, _, rect in self._rows:
            displayed = rect.move(0, self.items_view.y-round(self.scroll))
            if displayed.colliderect(self.items_view):self.item_rects[identifier] = displayed.clip(self.items_view)
        row_height = max(17, body+4)
        # Keep the first and last visible rows whole, including at large text.
        self.stat_view.height = max(row_height, (152//row_height)*row_height)
        self.stat_max_scroll = max(0, len(ATTRIBUTE_IDS)*row_height-self.stat_view.height)
        self.stat_scroll = max(0, min(round(self.stat_scroll/row_height)*row_height, self.stat_max_scroll))
        self.stat_row_rects = {identifier: pygame.Rect(self.stat_view.x,
            self.stat_view.y+index*row_height-round(self.stat_scroll), self.stat_view.width, row_height)
            for index, identifier in enumerate(ATTRIBUTE_IDS)}

    def _confirm(self):
        if self.result_error:
            self.retry_requested = True
            self._sound('confirm')
        elif self.ready:
            if self.animation_progress < 1:
                self.finish_animation()
            elif self.level_up is not None:
                self._level_index += 1
                self.stat_scroll = 0
                self._sync_presentation()
            else:
                self.dismissed = True
                self.stop_audio()
            self._sound('confirm')

    def _scroll(self, amount):
        if self.level_up is not None:
            self.stat_scroll = max(0, min(self.stat_max_scroll, self.stat_scroll+amount))
        else:self.scroll = max(0, min(self.max_scroll, self.scroll+amount))

    def handle_event(self, event):
        if self.dismissed:return True
        self._layout(self.game.ui.painter(self.game.ui_surface))
        point = self.game.to_canvas(event.pos) if hasattr(event, 'pos') else None
        if event.type == pygame.WINDOWFOCUSLOST:
            self.focused = False;self.paused = True
            self._held = self._confirm_key_down = False
            if self._audio_controller is not None:self._audio_controller.set_paused(True)
            return True
        if event.type == pygame.WINDOWFOCUSGAINED:
            self.focused = True
            return True
        if event.type == pygame.KEYUP:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):self._confirm_key_down = False
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = False
            return True
        if event.type == pygame.KEYDOWN and not getattr(event, 'repeat', False):
            if event.key == pygame.K_ESCAPE:
                if self.focused:
                    self.paused = not self.paused
                    self._held = self._confirm_key_down = False
                    if self._audio_controller is not None:self._audio_controller.set_paused(self.paused)
                    self._sound('back' if self.paused else 'confirm')
                return True
            if self.paused or not self.focused:return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if not self._confirm_key_down:
                    self._confirm_key_down = True
                    self._confirm()
            elif event.key == pygame.K_TAB and self._rows and self.level_up is None:
                self._loot_focus = not self._loot_focus
                self._hovered_item = self._rows[self._selected_item % len(self._rows)][0] if self._loot_focus else None
            elif event.key in (pygame.K_DOWN, pygame.K_UP, pygame.K_PAGEDOWN, pygame.K_PAGEUP,
                               pygame.K_HOME, pygame.K_END):
                if self._loot_focus and self.level_up is None and self._rows and event.key in (pygame.K_DOWN, pygame.K_UP):
                    self._selected_item = (self._selected_item+(1 if event.key == pygame.K_DOWN else -1)) % len(self._rows)
                    self._hovered_item = self._rows[self._selected_item][0]
                    row = self._rows[self._selected_item][3]
                    self.scroll = max(0, min(self.max_scroll, row.y))
                elif event.key in (pygame.K_HOME, pygame.K_END):
                    value = 0 if event.key == pygame.K_HOME else (self.stat_max_scroll if self.level_up else self.max_scroll)
                    if self.level_up is not None:self.stat_scroll = value
                    else:self.scroll = value
                else:
                    step = (self.stat_view.height if self.level_up else self.items_view.height) if event.key in (pygame.K_PAGEDOWN, pygame.K_PAGEUP) else 30
                    self._scroll(step*(-1 if event.key in (pygame.K_UP, pygame.K_PAGEUP) else 1))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._held:return True
            self._held = True
            if point is None:return True
            if self.paused:
                if self.focused and self.resume_rect.collidepoint(point):
                    self.paused = False
                    if self._audio_controller is not None:self._audio_controller.set_paused(False)
                    self._sound('confirm')
                return True
            button = self.level_continue_rect if self.level_up else self.continue_rect
            if self.focused and button.collidepoint(point):self._confirm()
            elif self.level_up is None:
                self._hovered_item = next((key for key, rect in self.item_rects.items() if rect.collidepoint(point)), None)
        elif event.type == pygame.MOUSEWHEEL and self.focused and not self.paused:self._scroll(-event.y*30)
        elif event.type == pygame.MOUSEMOTION:
            button = self.level_continue_rect if self.level_up else self.continue_rect
            self._hover = point is not None and button.collidepoint(point)
            if not self._loot_focus and self.level_up is None:
                self._hovered_item = next((key for key, rect in self.item_rects.items()
                                          if point is not None and rect.collidepoint(point)), None)
        return True

    def update(self, seconds):
        if type(seconds) not in (int, float):raise TypeError('Scene time must be numeric')
        if not math.isfinite(seconds) or seconds < 0:raise ValueError('Invalid scene time')
        if not self.paused and self.focused:
            self._elapsed += seconds
            if self.ready:self._animation_elapsed = min(self._animation_duration, self._animation_elapsed+seconds)
            if self.background is not None and hasattr(self.background, 'update'):
                self.background.update(seconds)
        if self._audio_controller is not None:self._audio_controller.set_paused(self.paused or not self.focused)
        self._sync_presentation()

    def displayed_progress(self, identifier):
        entry = self.progression['characters'][identifier]
        progress = self.animation_progress
        eased = progress*progress*(3-2*progress)
        total = entry['old_total_xp']+round((entry['new_total_xp']-entry['old_total_xp'])*eased)
        level = level_for_total_xp(total)
        cost = xp_to_next_level(level)
        within = total-total_xp_for_level(level)
        return {'total_xp': total, 'level': level, 'into': within, 'required': cost,
                'remaining': max(0, cost-within), 'fill': within/cost if cost else 1.0}

    @staticmethod
    def _item_icon(painter, identifier, rect):
        color = CRYSTAL_COLORS.get(identifier)
        if color:
            x, y = rect.center
            points = [(x, y-7), (x+5, y-2), (x+3, y+5), (x, y+8), (x-4, y+4), (x-5, y-2)]
            pygame.draw.polygon(painter.canvas, color, [painter.point(point) for point in points])
            painter.line(IVORY, (x, y-5), (x-2, y-1))
        else:
            painter.rect(BRASS, rect.inflate(-7, -7), 1)
            painter.line(BRASS, (rect.centerx, rect.top+4), (rect.centerx, rect.bottom-4))

    def _draw_party(self, painter):
        for identifier, rect in self.character_rects.items():
            entry = self.progression['characters'][identifier]
            state = self.displayed_progress(identifier)
            ko = self.progression['end_hp'][identifier] == 0
            advanced = state['level'] > entry['old_level']
            self._glass(painter, rect, 228)
            if advanced:painter.rect(GOLD, rect, 1)
            portrait = self._portrait(identifier)
            face = pygame.Rect(rect.x+6, rect.y+10, 36, 43)
            if portrait is not None:painter.image(portrait, face)
            else:painter.lantern(face.center, size=15)
            painter.rect(BRASS, face, 1)
            painter.text(self._name(identifier), (rect.left+50, rect.top+4), bold=True)
            painter.text('Lv. '+str(state['level']), (rect.right-10, rect.top+5), role='small',
                         color=GOLD, anchor='topright', bold=True)
            gain = 'KO — No EXP' if ko else '+'+format(entry['accepted_xp'], ',')+' EXP'
            painter.text(gain, (rect.right-10, rect.top+33), role='small',
                         color=MUTED if ko else GOLD, anchor='midright')
            bar = self.bar_rects[identifier]
            painter.rect(FOREST_LIGHT, bar)
            fill = bar.inflate(-2, -2);fill.width = round(fill.width*state['fill'])
            if fill.width:painter.rect(MUTED if ko else EXP_GREEN, fill)
            painter.rect(BRASS, bar, 1)
            text = ('MAX LEVEL' if state['level'] == MAX_LEVEL else
                    format(state['into'], ',')+' / '+format(state['required'], ',')+' · '+
                    format(state['remaining'], ',')+' to next')
            painter.text(text, (rect.left+50, rect.top+45), role='small', color=MUTED)

    def _draw_items(self, painter):
        painter.text('Items', (self.items_view.left, self._items_label_y), role='small', color=GOLD, bold=True)
        if self._ids:self._glass(painter, self.items_view.inflate(8, 8), 225)
        painter.clip(self.items_view)
        if not self._rows:
            lines = painter.wrap('No items recovered.', self.items_view.width-12, role='small')
            for index, line in enumerate(lines):
                painter.text(line, (self.items_view.centerx, self.items_view.centery+index*self._small),
                             role='small', color=MUTED, anchor='midtop')
        for identifier, lines, quantity, relative in self._rows:
            row = relative.move(0, self.items_view.y-round(self.scroll))
            if not row.colliderect(self.items_view):continue
            painter.rect(FOREST_LIGHT if identifier == self._hovered_item else FOREST_DARK, row)
            self._item_icon(painter, identifier, pygame.Rect(row.left+2, row.top+7, 20, 22))
            for index, text in enumerate(lines):
                painter.text(text, (row.left+27, row.top+6+index*self._small), role='small')
            painter.text(quantity, (row.right-4, row.top+6), role='small', color=GOLD, anchor='topright', bold=True)
            lost = self.loot.get('lost', {}).get(identifier, 0)
            if lost:
                painter.text(str(lost)+' lost: bag full', (row.left+5, row.bottom-self._small-3),
                             role='small', color=ERROR)
        painter.clip()
        if self.max_scroll:
            track = pygame.Rect(self.items_view.right-4, self.items_view.top, 3, self.items_view.height)
            painter.rect(FOREST_LIGHT, track)
            height = max(12, round(track.height*self.items_view.height/(self.max_scroll+self.items_view.height)))
            offset = round((track.height-height)*self.scroll/self.max_scroll)
            painter.rect(BRASS, (track.x, track.y+offset, track.width, height))

    def _draw_item_detail(self, painter):
        if self._hovered_item is None or self.level_up is not None:return
        definition = getattr(self.game.inventory, 'definitions', {}).get(self._hovered_item, {})
        description = definition.get('description', '')
        if not description:return
        lines = painter.wrap(description, 350, role='small')
        title = painter.wrap(definition.get('name', self._hovered_item), 350, bold=True)
        line = painter.font('small').get_linesize()
        body = painter.font(bold=True).get_linesize()
        height = min(196, 23+len(title)*body+len(lines)*line)
        rect = pygame.Rect(45, 266-height, 390, height)
        painter.panel(rect, parchment=True)
        y = rect.top+10
        for text in title:
            painter.text(text, (rect.left+12, y), color=FOREST, bold=True);y += body
        y += 3
        painter.clip(rect.inflate(-12, -12))
        for text in lines:
            painter.text(text, (rect.left+12, y), role='small', color=INK);y += line
        painter.clip()

    def _draw_level_up(self, painter):
        entry = self.level_up
        if entry is None:return
        painter.veil(170)
        painter.panel((20, 17, 440, 288), parchment=True)
        portrait = self._portrait(entry['character_id'])
        if portrait is not None:painter.image(portrait, (33, 29, 39, 44))
        painter.rect(BRASS, (33, 29, 39, 44), 1)
        painter.text('LEVEL UP', (84, 27), role='small', color=FOREST, bold=True)
        painter.text(self._name(entry['character_id']), (84, 45), role='heading', color=FOREST, bold=True)
        painter.text('Lv. '+str(entry['old_level'])+' → '+str(entry['new_level']),
                     (444, 47), color=GROWTH_GREEN, anchor='topright', bold=True)
        painter.line(BRASS, (34, 77), (444, 77))
        painter.text('Attribute', (34, 84), role='small', color=INK, bold=True)
        painter.text('Before', (228, 84), role='small', color=INK, anchor='topright')
        painter.text('After', (307, 84), role='small', color=GROWTH_GREEN, anchor='topright', bold=True)
        definitions = self.game.attributes.definitions
        painter.clip(self.stat_view)
        for index, identifier in enumerate(ATTRIBUTE_IDS):
            row = self.stat_row_rects[identifier]
            if not row.colliderect(self.stat_view):continue
            if index % 2 == 0:painter.rect(PARCHMENT_DARK, row)
            icon = pygame.Rect(row.x+5, row.centery-5, 10, 10)
            draw_attribute_icon(painter, identifier, icon, FOREST)
            painter.text(definitions[identifier]['label'], (row.x+22, row.centery),
                         color=INK, anchor='midleft')
            before, after = entry['stats_before'][identifier], entry['stats_after'][identifier]
            painter.text(format(before, ','), (228, row.centery), color='#000000', anchor='midright')
            x, y = 250, row.centery
            painter.line(GROWTH_GREEN, (x-8, y), (x+7, y), 2)
            pygame.draw.polygon(painter.canvas, GROWTH_GREEN,
                                [painter.point(point) for point in ((x+8, y), (x+2, y-4), (x+2, y+4))])
            painter.text(format(after, ','), (307, row.centery), color=GROWTH_GREEN, anchor='midright', bold=True)
            if after > before:
                painter.text('(+'+format(after-before, ',')+')', (426, row.centery),
                             role='small', color=GROWTH_GREEN, anchor='midright', bold=True)
        painter.clip()
        if self.stat_max_scroll:
            track = pygame.Rect(443, self.stat_view.top, 3, self.stat_view.height)
            painter.rect(PARCHMENT_DARK, track)
            height = max(14, round(track.height*self.stat_view.height/(self.stat_max_scroll+self.stat_view.height)))
            offset = round((track.height-height)*self.stat_scroll/self.stat_max_scroll)
            painter.rect(BRASS, (track.x, track.y+offset, track.width, height))
            hint = 'Scroll · current HP/MP unchanged'
        else:hint = 'Current HP/MP unchanged.'
        painter.text(hint, (34, 275), role='small', color=INK)
        painter.button(self.level_continue_rect, 'Next' if self._level_index+1 < len(self._level_queue) else 'Done',
                       selected=self._hover, pressed=self._held and self._hover)

    def draw(self, world_canvas, ui_surface):
        if isinstance(self.background, pygame.Surface):
            pygame.transform.scale(self.background, world_canvas.get_size(), world_canvas)
        elif self.background is not None and hasattr(self.background, '_draw_field'):
            self.background._draw_field(world_canvas)
        else:world_canvas.fill(FOREST_DARK)
        pygame.transform.scale(world_canvas, ui_surface.get_size(), ui_surface)
        painter = self.game.ui.painter(ui_surface)
        painter.veil(105)
        painter.rect(BRASS, self.panel_rect, 1)
        painter.rect(FOREST_LIGHT, self.panel_rect.inflate(-4, -4), 1)
        self._layout(painter)
        self._glass(painter, (23, 17, 434, 49 if self._ids else self._rule_y-12), 190)
        painter.text('Spoils of Battle', (34, self.title_rect.y), role='heading', color=GOLD, bold=True)
        if self._ids:
            painter.text(format(self.progression['amount'], ',')+' EXP', (446, 27),
                         role='small', color=GOLD, anchor='midright', bold=True)
            painter.text('Full EXP for each survivor', (35, 45), role='small', color=MUTED)
        painter.line(BRASS, (26, self._rule_y), (454, self._rule_y))
        self._draw_party(painter)
        self._draw_items(painter)
        for index, text in enumerate(self._footer_lines):
            painter.text(text, (26, self._footer_top+index*self._small), role='small',
                         color=ERROR if self.result_error else GOLD if self.awarded else MUTED)
        label = 'Retry' if self.result_error else ('Finish' if self.animation_progress < 1 else 'Continue')
        painter.button(self.continue_rect, label, selected=self._hover,
                       pressed=self._held and self._hover, disabled=not self.ready and not self.result_error)
        self._draw_item_detail(painter)
        self._draw_level_up(painter)
        if self.paused:
            painter.veil(150)
            painter.panel((124, 111, 232, 100))
            painter.text('Spoils paused', (240, 126), color=GOLD, anchor='midtop', bold=True)
            painter.button(self.resume_rect, 'Resume', disabled=not self.focused)
        painter.clip()
