"""Eldenmere's readable quest ledger, quiet tracker and world markers."""
from __future__ import annotations

from array import array
from collections import deque
import math
import json
from pathlib import Path

import pygame

from ui_style import UIStyle, FOREST, FOREST_LIGHT, FOREST_DARK, IVORY, BRASS, GOLD, INK, PARCHMENT, PARCHMENT_DARK, MUTED

PAPER = IVORY
EDGE = BRASS


class QuestUI:
    def __init__(self, game):
        self.game = game
        self.style = getattr(game, 'ui', None) or UIStyle(game)
        self.journal_open = False
        self.scroll = 0
        self.max_scroll = 0
        self.list_scroll = 0
        self.selected_quest = None
        self.focus = 'details'
        self.notices = deque()
        self.current_notice = None
        self.notice_seconds = 0.0
        self._sounds = {}
        self._map_entrances = {}
        self._dragging = False
        self._drag_offset = 0
        self._hover = None
        self._tracker_held = False
        self.close_rect = pygame.Rect(438, 20, 22, 22)
        self.list_viewport = pygame.Rect(24, 64, 126, 214)
        self.detail_viewport = pygame.Rect(171, 64, 264, 214)
        self.scrollbar_rect = pygame.Rect(442, 64, 10, 214)
        self.scrollbar_thumb = self.scrollbar_rect.copy()
        self.quest_rects = {}
        self._quest_content = {}
        self.tracker_rect = pygame.Rect(286, 8, 186, 48)
        self.tracker_toggle_rect = pygame.Rect(451, 10, 17, 18)
        self._painter(pygame.Surface((480, 320)))

    def _painter(self, canvas=None):
        if canvas is None:
            canvas = getattr(self.game, 'ui_surface', None)
            if canvas is None:canvas = pygame.Surface((480, 320))
        painter = self.style.painter(canvas)
        self.font = painter.font('body')
        self.small_font = painter.font('small')
        self.small_bold_font = painter.font('small', bold=True)
        self.heading_font = painter.font('name', bold=True)
        self.marker_font = painter.font('name', bold=True)
        return painter

    def _point(self, point):
        converter = getattr(self.game, 'to_canvas', None)
        return converter(point) if converter is not None else point

    def _visible_quests(self):
        result = []
        opening = getattr(self.game, 'opening', None)
        for identifier, definition in self.game.quests.definitions.items():
            status = self.game.quests.status(identifier) if hasattr(self.game.quests, 'status') else self.game.quests.states[identifier]['status']
            if status == 'locked':continue
            if status == 'available' and opening is not None and not opening.can_speak(definition['giver']):continue
            result.append(identifier)
        return result

    def _ensure_selection(self):
        choices = self._visible_quests()
        if self.selected_quest not in choices:
            self.selected_quest = choices[0] if choices else None
            self.scroll = 0
        return choices

    def toggle_journal(self):
        self.journal_open = not self.journal_open
        self._dragging = False
        if self.journal_open:
            self.scroll = self.list_scroll = 0
            self._ensure_selection()
            self.style.sound('confirm')
        else:self.style.sound('back')

    def close_journal(self):
        self.journal_open = False
        self._dragging = False

    def reset(self):
        """Restoring a journey never replays earlier progress announcements."""
        self.close_journal()
        self.scroll = self.list_scroll = 0
        self.selected_quest = None
        self.notices.clear()
        self.current_notice = None
        self.notice_seconds = 0.0

    def _select(self, identifier):
        if identifier not in self._visible_quests():return
        if self.selected_quest != identifier:
            self.selected_quest = identifier
            self.scroll = 0
            self.style.sound('move')

    def _next_quest(self, direction):
        choices = self._ensure_selection()
        if choices:
            index = choices.index(self.selected_quest)
            self._select(choices[(index+direction) % len(choices)])
            # Keep keyboard selection visible in a longer quest list.
            content = self._quest_content.get(self.selected_quest)
            if content is not None:
                top, height = content
                if top < self.list_scroll:self.list_scroll = top
                elif top+height > self.list_scroll+self.list_viewport.height:
                    self.list_scroll = top+height-self.list_viewport.height

    def handle_event(self, event):
        if not self.journal_open:return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_j, pygame.K_ESCAPE):
                if not getattr(event, 'repeat', False):
                    self.close_journal();self.style.sound('back')
            elif event.key in (pygame.K_TAB, pygame.K_LEFT, pygame.K_RIGHT):
                self.focus = ('list' if event.key == pygame.K_LEFT else 'details' if event.key == pygame.K_RIGHT
                              else 'details' if self.focus == 'list' else 'list')
            elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                direction = -1 if event.key in (pygame.K_UP, pygame.K_w) else 1
                if self.focus == 'list':self._next_quest(direction)
                else:self.scroll = max(0, min(self.max_scroll, self.scroll+direction*24))
            elif event.key == pygame.K_PAGEUP:self.scroll = max(0, self.scroll-160)
            elif event.key == pygame.K_PAGEDOWN:self.scroll = min(self.max_scroll, self.scroll+160)
            elif event.key == pygame.K_HOME:self.scroll = 0
            elif event.key == pygame.K_END:self.scroll = self.max_scroll
            return True
        if event.type == pygame.MOUSEWHEEL:
            point = self._point(pygame.mouse.get_pos())
            if point is not None and self.list_viewport.collidepoint(point):
                self.list_scroll = max(0, self.list_scroll-event.y*32)
            else:self.scroll = max(0, min(self.max_scroll, self.scroll-event.y*32))
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
            return True
        if event.type == pygame.MOUSEMOTION:
            point = self._point(event.pos)
            self._hover = point
            if self._dragging and point is not None and self.max_scroll:
                travel = self.scrollbar_rect.height-self.scrollbar_thumb.height
                ratio = (point[1]-self.scrollbar_rect.top-self._drag_offset)/max(1, travel)
                self.scroll = round(max(0, min(1, ratio))*self.max_scroll)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            point = self._point(event.pos)
            if point is None:return True
            if self.close_rect.collidepoint(point):
                self.close_journal();self.style.sound('back');return True
            for identifier, rect in self.quest_rects.items():
                if rect.collidepoint(point):
                    self._select(identifier);self.focus = 'list';return True
            if self.max_scroll and self.scrollbar_rect.collidepoint(point):
                if self.scrollbar_thumb.collidepoint(point):
                    self._dragging = True
                    self._drag_offset = point[1]-self.scrollbar_thumb.top
                else:
                    self.scroll = max(0, min(self.max_scroll, self.scroll+(160 if point[1] > self.scrollbar_thumb.bottom else -160)))
            return True
        return event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.KEYUP)

    def _hidden(self):
        return (self.journal_open or self.game.map_open or
                getattr(getattr(self.game, 'inventory_ui', None), 'is_open', False))

    def _notices_hidden(self):
        return self._hidden() or self.game.social.locked

    def _tracker_hidden(self):
        return (self._hidden() or self.game.social.locked or
                getattr(getattr(self.game, 'opening', None), 'locks_player', False) or
                getattr(getattr(self.game, 'pause', None), 'is_open', False))

    def _toggle_tracker(self):
        audio = getattr(self.game, 'audio', None)
        if audio is None:return
        visible = not getattr(audio, 'tracker_visible', True)
        setter = getattr(audio, 'set_tracker_visible', None)
        if setter is not None:setter(visible)
        else:audio.tracker_visible = visible
        self.style.sound('confirm')

    def handle_hud_event(self, event):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._tracker_held = False
        if self._tracker_hidden() or not self._tracker_text():return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            point = self._point(event.pos)
            if point is not None and self.tracker_toggle_rect.collidepoint(point):
                if not self._tracker_held:self._toggle_tracker()
                self._tracker_held = True
                return True
        return False

    def update(self, seconds):
        self.notices.extend(self.game.quests.drain_events())
        if self._notices_hidden():return
        if self.current_notice is not None:
            self.notice_seconds -= max(0, seconds)
            if self.notice_seconds <= 0:self.current_notice = None
        if self.current_notice is None and self.notices:
            self.current_notice = self.notices.popleft()
            self.notice_seconds = 4.0 if self.current_notice['kind'] == 'completed' else 3.2
            self._chime(self.current_notice['kind'])

    def _chime(self, kind):
        audio = getattr(self.game, 'audio', None)
        volume = audio.effects_volume if audio is not None else float(getattr(getattr(self.game, 'title', None), 'music_enabled', True))
        if volume <= 0:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            rate, sample_format, channels = pygame.mixer.get_init()
            if sample_format != -16:
                return
            key = (kind, rate, channels)
            if key not in self._sounds:
                notes = {'accepted': (587.33, 880.0), 'objective': (880.0,),
                         'ready': (880.0, 1174.66),
                         'completed': (587.33, 880.0, 1174.66)}.get(kind, ())
                samples = array('h')
                for frequency in notes:
                    count = round(rate*.15)
                    for i in range(count):
                        t = i/rate
                        envelope = max(0, min(1, t/.012, (.15-t)/.07))
                        value = round(3200*envelope*math.sin(2*math.pi*frequency*t))
                        samples.extend([value]*channels)
                if not samples:
                    return
                self._sounds[key] = pygame.mixer.Sound(buffer=samples)
            self._sounds[key].set_volume(volume)
            self._sounds[key].play()
        except (pygame.error, OSError):
            # Quest text and symbols remain fully usable without audio hardware.
            return

    @staticmethod
    def wrap(text, font, width):
        """Wrap even long individual words so journal text stays inside its panel."""
        lines = []
        line = ''
        for word in str(text).split():
            candidate = f'{line} {word}'.strip()
            if font.size(candidate)[0] <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
                line = ''
            while font.size(word)[0] > width and len(word) > 1:
                end = 1
                while end < len(word) and font.size(word[:end+1])[0] <= width:
                    end += 1
                lines.append(word[:end])
                word = word[end:]
            line = word
        if line:
            lines.append(line)
        return lines or ['']

    def _symbol(self, canvas, symbol, center, elapsed_ms=0):
        painter = self._painter(canvas)
        x, y = center
        plate = pygame.Rect(round(x)-7, round(y)-11, 14, 22)
        painter.rect(FOREST_DARK, plate)
        painter.rect(BRASS, plate, 1)
        painter.text(symbol, (x, y-1), role='name', color=GOLD, anchor='center', bold=True)
        reduced = getattr(getattr(self.game, 'audio', None), 'reduced_motion', False)
        if not reduced and int(elapsed_ms) % 5400 < 180:
            painter.rect(IVORY, (plate.right-2, plate.top+1, 1, 1))

    def _marker_for(self, npc_id):
        opening = getattr(self.game, 'opening', None)
        if opening is not None and not opening.can_speak(npc_id):return None
        conclusion = getattr(self.game, 'opening_conclusion', None)
        if conclusion is not None and not conclusion.can_speak(npc_id):return None
        lantern=getattr(self.game,'lantern_quest',None)
        if lantern is not None:
            result=lantern.marker_for(npc_id)
            if result is not NotImplemented:return result
        regent=getattr(self.game,'regent_quest',None)
        if regent is not None:
            result=regent.marker_for(npc_id)
            if result is not NotImplemented:return result
        mill=getattr(self.game,'mill_quest',None)
        if mill is not None:
            result=mill.marker_for(npc_id)
            if result is not NotImplemented:return result
        return self.game.quests.marker_for(npc_id)

    def draw_markers(self, canvas, camera):
        if self._hidden() or self.game.social.locked:return
        for actor in self.game.world.npcs:
            symbol = self._marker_for(actor.data['id'])
            if symbol is None:continue
            image = actor.sprite(self.game.elapsed_ms)
            top = image.get_bounding_rect().top
            point = (actor.position.x-camera[0], actor.position.y-actor.draw_anchor[1]+top-camera[1]-12)
            if 8 <= point[0] < 472 and 12 <= point[1] < 308:
                self._symbol(canvas, symbol, point, self.game.elapsed_ms)

    def _tracker_text(self):
        opening = getattr(self.game, 'opening', None)
        visits = getattr(self.game, 'household_visits', ())
        return ((opening.hint_text() if opening is not None else '') or
                next((text for visit in visits if (text:=visit.tracker_text())), '') or self.game.quests.tracker_text())

    def draw_tracker(self, canvas):
        if self._tracker_hidden():return
        text = self._tracker_text()
        if not text:return
        painter = self._painter(canvas)
        visible = getattr(getattr(self.game, 'audio', None), 'tracker_visible', True)
        if not visible:
            self.tracker_rect = pygame.Rect(444, 8, 28, 24)
            self.tracker_toggle_rect = self.tracker_rect.copy()
            painter.panel(self.tracker_rect)
            painter.lantern(self.tracker_rect.center, size=10)
            return
        lines = painter.wrap(text, 166, role='small')
        line_height = painter.font('small').get_linesize()+1
        height = 26+min(3, len(lines))*line_height+(line_height+2 if len(lines) > 3 else 0)
        self.tracker_rect = pygame.Rect(286, 8, 186, height)
        self.tracker_toggle_rect = pygame.Rect(451, 10, 17, 18)
        painter.panel(self.tracker_rect)
        painter.lantern((298, 20), size=8)
        painter.text('Current errand', (308, 13), role='small', color=GOLD, bold=True)
        painter.text('−', self.tracker_toggle_rect.center, role='body', color=GOLD, anchor='center')
        for index, line in enumerate(lines[:3]):
            painter.text(line, (296, 30+index*line_height), role='small', color=IVORY)
        if len(lines) > 3:
            painter.text('…  J: journal', (462, self.tracker_rect.bottom-3), role='small', color=MUTED, anchor='bottomright')

    def _notification_content(self, event):
        labels = {'accepted': 'Quest accepted', 'objective': 'Objective completed',
                  'ready': 'Ready to report', 'completed': 'Quest completed', 'unlocked': 'New request available'}
        label = labels.get(event['kind'], 'Quest updated')
        if event['kind'] in ('accepted', 'completed', 'unlocked') and event.get('title'):label += ': '+event['title']
        return (self.wrap(label, self.small_bold_font, 300), self.wrap(event.get('text') or event.get('title', ''), self.font, 308))

    def draw_notifications(self, canvas):
        if self._notices_hidden() or self.current_notice is None:return
        painter = self._painter(canvas)
        labels, lines = self._notification_content(self.current_notice)
        small_h = max(self.small_font.get_linesize(), self.small_bold_font.get_linesize())+1
        body_h = painter.font('body').get_linesize()+2
        height = 18+len(labels)*small_h+len(lines)*body_h
        rect = pygame.Rect(72, 76, 336, height)
        painter.panel(rect)
        painter.lantern((85, rect.top+15), size=9)
        for index, line in enumerate(labels):
            painter.text(line, (96, rect.top+8+index*small_h), role='small', color=GOLD, bold=True)
        for index, line in enumerate(lines):
            painter.text(line, (86, rect.top+12+len(labels)*small_h+index*body_h), role='body', color=IVORY)

    def _journal_rows(self):
        self._ensure_selection()
        identifier = self.selected_quest
        if identifier is None:return []
        definition = self.game.quests.definitions[identifier]
        status = self.game.quests.states[identifier]['status']
        labels = {'available': 'AVAILABLE', 'active': 'IN PROGRESS', 'ready': 'READY TO REPORT', 'completed': 'COMPLETED'}
        rows = [(labels.get(status, status.upper()), FOREST, self.small_font, 0)]
        for line in self.wrap(definition['title'], self.heading_font, self.detail_viewport.width):
            rows.append((line, INK, self.heading_font, 0))
        rows.append(('', INK, self.small_font, 0))
        for line in self.wrap(definition.get('summary', ''), self.font, self.detail_viewport.width):
            rows.append((line, INK, self.font, 0))
        rows.append(('', INK, self.small_font, 0))
        if status == 'available':
            for line in self.wrap('Find the ! marker to hear this request.', self.font, self.detail_viewport.width):
                rows.append((line, FOREST, self.font, 0))
        else:
            rows.append(('Your errands', FOREST, self.heading_font, 0))
            lantern = getattr(self.game, 'lantern_quest', None) if identifier == 'CH01_MQ04' else None
            for objective in definition['objectives']:
                if lantern is not None and objective['id'] not in lantern.journal_objectives():continue
                progress = self.game.quests.objective_status(identifier, objective['id'])
                prefix = {'active': 'Next: ', 'queued': 'Later: ', 'completed': 'Done: '}.get(progress, '')
                text = prefix+objective['text']
                visit = getattr(self.game, 'halden_visit', None)
                if objective['id'] == 'halden' and progress == 'active' and visit is not None:
                    text += ' '+visit.journal_detail()
                visit = getattr(self.game, 'elira_visit', None)
                if objective['id'] == 'elira' and progress == 'active' and visit is not None:
                    text += ' '+visit.journal_detail()
                visit = getattr(self.game, 'venn_visit', None)
                if objective['id'] == 'venn' and progress == 'active' and visit is not None:
                    text += ' '+visit.journal_detail()
                if progress == 'queued' and objective.get('requires'):
                    # Keep the opening's approved prerequisite wording concise.
                    text += ' (after Halden)' if objective.get('requires') == ['halden'] else ' (after earlier errands)'
                color = '#655c48' if progress in ('queued', 'completed') else INK
                for line in self.wrap(text, self.font, self.detail_viewport.width-14):
                    rows.append((line, color, self.font, 14))
                rows.append(('', INK, self.small_font, 0))
            if lantern is not None:
                for line in self.wrap(lantern.journal_detail(), self.font, self.detail_viewport.width):
                    rows.append((line, FOREST, self.font, 0))
            if status == 'ready':
                for line in self.wrap('Return to the ? marker to report back.', self.font, self.detail_viewport.width):
                    rows.append((line, FOREST, self.font, 0))
        while rows and not rows[-1][0]:rows.pop()
        return rows

    def _row_height(self, font):return font.get_linesize()+2

    def _journal_list(self, painter):
        choices = self._ensure_selection()
        font = painter.font('body')
        small = painter.font('small')
        records = []
        total = 0
        for identifier in choices:
            lines = painter.wrap(self.game.quests.definitions[identifier]['title'], self.list_viewport.width-16)
            height = max(48, 18+len(lines)*font.get_linesize()+small.get_linesize())
            records.append((identifier, lines, height))
            total += height+5
        self.list_scroll = max(0, min(self.list_scroll, max(0, total-self.list_viewport.height)))
        self.quest_rects = {}
        self._quest_content = {}
        painter.clip(self.list_viewport)
        y = self.list_viewport.top-self.list_scroll
        labels = {'available': 'Available', 'active': 'In progress', 'ready': 'Report back', 'completed': 'Completed'}
        for identifier, lines, height in records:
            self._quest_content[identifier] = (y-self.list_viewport.top+self.list_scroll, height)
            row = pygame.Rect(self.list_viewport.left, y, self.list_viewport.width, height)
            clipped = row.clip(self.list_viewport)
            if clipped.height:
                self.quest_rects[identifier] = clipped
                selected = identifier == self.selected_quest
                hovered = self._hover is not None and clipped.collidepoint(self._hover)
                painter.rect(FOREST if selected else ('#dfd0aa' if hovered else PARCHMENT_DARK), row)
                if selected:painter.rect(BRASS, row, 1)
                color = IVORY if selected else INK
                for index, line in enumerate(lines):
                    painter.text(line, (row.left+8, row.top+7+index*font.get_linesize()), color=color)
                state = self.game.quests.states[identifier]['status']
                painter.text(labels.get(state, state), (row.left+8, row.bottom-7), role='small', color=GOLD if selected else FOREST, anchor='bottomleft')
            y += height+5
        painter.clip(None)

    def draw_journal(self, canvas):
        if not self.journal_open:return
        painter = self._painter(canvas)
        painter.veil(205)
        painter.panel((12, 12, 456, 296), parchment=True)
        painter.lantern((32, 34), color=FOREST, size=13)
        painter.text("Caelan's journal", (48, 20), role='heading', color=FOREST, bold=True)
        painter.button(self.close_rect, '×', selected=self._hover is not None and self.close_rect.collidepoint(self._hover))
        painter.line(BRASS, (24, 53), (456, 53))
        painter.line(BRASS, (159, 63), (159, 279))
        self._journal_list(painter)
        rows = self._journal_rows()
        heights = [self._row_height(font) for _, _, font, _ in rows]
        self.max_scroll = max(0, sum(heights)-self.detail_viewport.height)
        self.scroll = max(0, min(self.max_scroll, self.scroll))
        painter.clip(self.detail_viewport)
        y = self.detail_viewport.top-self.scroll
        if not rows:
            opening = getattr(self.game, 'opening', None)
            hint = (opening.hint_text() if opening is not None else '') or 'Your journal is quiet for now. Requests will appear here as you discover them.'
            for line in painter.wrap(hint, self.detail_viewport.width):
                painter.text(line, (self.detail_viewport.left, y), color=INK)
                y += painter.font('body').get_linesize()+3
        for (text, color, font, indent), height in zip(rows, heights):
            role = 'name' if font is self.heading_font else 'small' if font is self.small_font else 'body'
            if text.startswith(('Next:', 'Later:', 'Done:')):
                x = self.detail_viewport.left+4
                center = y+min(height//2, 8)
                if text.startswith('Next:'):painter.lantern((x, center), color=FOREST, size=7)
                elif text.startswith('Done:'):
                    painter.line(FOREST, (x-3, center), (x-1, center+2))
                    painter.line(FOREST, (x-1, center+2), (x+4, center-3))
                else:
                    painter.rect('#8e8062', (x-3, center-3, 6, 6), 1)
                    painter.line('#8e8062', (x, center-1), (x, center+2))
            painter.text(text, (self.detail_viewport.left+indent, y), role=role, color=color, bold=font is self.heading_font)
            y += height
        painter.clip(None)
        self.scrollbar_thumb = self.scrollbar_rect.copy()
        if self.max_scroll:
            painter.rect(PARCHMENT_DARK, self.scrollbar_rect)
            thumb = max(22, round(self.scrollbar_rect.height*self.detail_viewport.height/(self.max_scroll+self.detail_viewport.height)))
            offset = round((self.scrollbar_rect.height-thumb)*self.scroll/self.max_scroll)
            self.scrollbar_thumb = pygame.Rect(self.scrollbar_rect.x, self.scrollbar_rect.y+offset, self.scrollbar_rect.width, thumb)
            painter.rect(FOREST_LIGHT if self._dragging else BRASS, self.scrollbar_thumb)
        footer = 'J / Esc: close   •   Wheel / arrows: read   •   Tab: quest list'
        if painter.font('small').size(footer)[0] > 428:footer = 'J / Esc: close   •   Wheel: read   •   Tab: list'
        painter.text(footer, (26, 291), role='small', color=INK)

    def _map_position(self, actor):
        """Project an indoor giver through doorway links to its town entrance."""
        game = self.game
        if actor in game.town.npcs:
            return tuple(actor.position)
        scene = getattr(game, '_routine_worlds', {}).get(actor)
        if scene is None:
            scene = next((s for s in game.scenes.values() if actor in s.npcs), None)
        if scene is None:
            return None
        if scene.data['id'] in self._map_entrances:
            return self._map_entrances[scene.data['id']]
        # Walk from exterior entrances into their reachable rooms. Read only
        # metadata for uncached rooms; opening the map must not instantiate NPCs.
        loaded = {s.data['id']: s for s in game.scenes.values()}
        pending = [(Path(door.data['destination']), tuple(door.data['anchor']))
                   for door in reversed(game.town.doors)]
        visited = set()
        while pending:
            destination, anchor = pending.pop()
            scene_id = destination.parent.name
            if scene_id in visited:
                continue
            visited.add(scene_id)
            self._map_entrances.setdefault(scene_id, anchor)
            if scene_id == scene.data['id']:
                return anchor
            room = loaded.get(scene_id)
            if room is not None:
                doors = [door.data for door in room.doors]
            else:
                path = destination if destination.is_absolute() else Path(__file__).parent/destination
                try:
                    doors = json.loads(path.read_text(encoding='utf-8')).get('doors', [])
                except (OSError, ValueError):
                    continue
            for door in doors:
                path = Path(door['destination'])
                if path.parent.name != 'playable':
                    pending.append((path, anchor))
        return None

    def draw_map_markers(self, canvas, origin, map_size, avoid_point=None):
        actors = list(self.game.town.npcs)+list(getattr(self.game, 'persistent_npcs', []))
        seen = set()
        for scene in self.game.scenes.values():
            actors.extend(scene.npcs)
        for actor in actors:
            if id(actor) in seen:
                continue
            seen.add(id(actor))
            symbol = self._marker_for(actor.data['id'])
            if symbol is None:
                continue
            position = self._map_position(actor)
            if position is None:
                continue
            center = (origin[0]+round(position[0]*map_size[0]/self.game.town.size[0]),
                      origin[1]+round(position[1]*map_size[1]/self.game.town.size[1]))
            if avoid_point is not None and pygame.Vector2(center).distance_to(avoid_point) < 18:
                # A quest giver and player can share an exterior doorway.
                # Keep both symbols visible without changing their world anchor.
                x = center[0]+16
                if x > origin[0]+map_size[0]-8:x = center[0]-16
                center = (max(origin[0]+8, min(origin[0]+map_size[0]-8, x)),
                          max(origin[1]+12, min(origin[1]+map_size[1]-12, center[1]-8)))
            self._symbol(canvas, symbol, center, self.game.elapsed_ms)
