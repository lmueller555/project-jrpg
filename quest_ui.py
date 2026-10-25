"""Quest feedback drawn in the game's native pixel coordinates."""
from __future__ import annotations

from array import array
from collections import deque
import math
import json
from pathlib import Path

import pygame

INK = '#263c35'
PAPER = '#f7eed5'
GOLD = '#ffdc71'
EDGE = '#b7a47b'
MUTED = '#c9c9b5'


class QuestUI:
    def __init__(self, game):
        self.game = game
        self.journal_open = False
        self.scroll = 0
        self.max_scroll = 0
        self.font = pygame.font.Font(None, 16)
        self.small_font = pygame.font.Font(None, 14)
        self.heading_font = pygame.font.Font(None, 21)
        self.marker_font = pygame.font.Font(None, 20)
        self.notices = deque()
        self.current_notice = None
        self.notice_seconds = 0.0
        self._sounds = {}
        self._map_entrances = {}

    def toggle_journal(self):
        self.journal_open = not self.journal_open
        if self.journal_open:
            self.scroll = 0

    def close_journal(self):
        self.journal_open = False

    def reset(self):
        """Restoring a save starts quietly, without replaying old announcements."""
        self.close_journal()
        self.scroll = 0
        self.notices.clear()
        self.current_notice = None
        self.notice_seconds = 0.0

    def handle_event(self, event):
        if not self.journal_open:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_j, pygame.K_ESCAPE):
                if not getattr(event, 'repeat', False):
                    self.close_journal()
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.scroll = max(0, self.scroll-24)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.scroll = min(self.max_scroll, self.scroll+24)
            elif event.key == pygame.K_PAGEUP:
                self.scroll = max(0, self.scroll-160)
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll = min(self.max_scroll, self.scroll+160)
            elif event.key == pygame.K_HOME:
                self.scroll = 0
            elif event.key == pygame.K_END:
                self.scroll = self.max_scroll
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.max_scroll, self.scroll-event.y*32))
            return True
        return event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                              pygame.MOUSEMOTION, pygame.KEYUP)

    def _hidden(self):
        return self.journal_open or self.game.map_open

    def update(self, seconds):
        self.notices.extend(self.game.quests.drain_events())
        if self._hidden():
            return
        if self.current_notice is not None:
            self.notice_seconds -= max(0, seconds)
            if self.notice_seconds <= 0:
                self.current_notice = None
        if self.current_notice is None and self.notices:
            self.current_notice = self.notices.popleft()
            kind = self.current_notice['kind']
            self.notice_seconds = 4.0 if kind == 'completed' else 3.2
            self._chime(kind)

    def _chime(self, kind):
        if not getattr(getattr(self.game, 'title', None), 'music_enabled', True):
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
        image = self.marker_font.render(symbol, False, GOLD)
        outline = self.marker_font.render(symbol, False, '#15221f')
        point = image.get_rect(center=(round(center[0]), round(center[1]))).topleft
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            canvas.blit(outline, (point[0]+dx, point[1]+dy))
        canvas.blit(image, point)
        # A single restrained glint, rather than a constantly bouncing marker.
        if int(elapsed_ms) % 5400 < 180:
            canvas.set_at((max(0, min(canvas.get_width()-1, point[0]+image.get_width())),
                           max(0, min(canvas.get_height()-1, point[1]))), '#fff5c6')

    def draw_markers(self, canvas, camera):
        if self._hidden() or self.game.social.locked:
            return
        for actor in self.game.world.npcs:
            symbol = self.game.quests.marker_for(actor.data['id'])
            if symbol is None:
                continue
            image = actor.sprite(self.game.elapsed_ms)
            top = image.get_bounding_rect().top
            point = (actor.position.x-camera[0],
                     actor.position.y-actor.draw_anchor[1]+top-camera[1]-9)
            if 3 <= point[0] < canvas.get_width()-3 and 4 <= point[1] < canvas.get_height()-4:
                self._symbol(canvas, symbol, point, self.game.elapsed_ms)

    def draw_tracker(self, canvas):
        if self._hidden() or self.game.social.locked:
            return
        text = self.game.quests.tracker_text()
        if not text:
            return
        rect = pygame.Rect(246, 8, 226, 49)
        pygame.draw.rect(canvas, INK, rect)
        pygame.draw.rect(canvas, EDGE, rect, 1)
        canvas.blit(self.small_font.render('CURRENT OBJECTIVE', False, GOLD), (253, 13))
        hint = self.small_font.render('J: journal', False, MUTED)
        canvas.blit(hint, (rect.right-7-hint.get_width(), 13))
        lines = self.wrap(text, self.small_font, 212)
        if len(lines) > 2:
            lines = lines[:2]
            lines[-1] = lines[-1].rstrip('.')+'...'
            while self.small_font.size(lines[-1])[0] > 212:
                lines[-1] = lines[-1][:-4]+'...'
        for i, line in enumerate(lines):
            canvas.blit(self.small_font.render(line, False, PAPER), (253, 26+i*11))

    def _notification_content(self, event):
        labels = {'accepted': 'Quest accepted', 'objective': 'Objective completed',
                  'ready': 'Ready to report', 'completed': 'Quest completed'}
        label = labels.get(event['kind'], 'Quest updated')
        if event['kind'] in ('accepted', 'completed') and event.get('title'):
            label += ': '+event['title']
        text = event.get('text') or event.get('title', '')
        return (self.wrap(label, self.small_font, 338),
                self.wrap(text, self.font, 338))

    def draw_notifications(self, canvas):
        if self._hidden() or self.current_notice is None:
            return
        labels, lines = self._notification_content(self.current_notice)
        body_offset = 9+len(labels)*11
        height = body_offset+len(lines)*13+4
        y = 199-height if self.game.social.locked else 66
        rect = pygame.Rect(62, y, 356, height)
        pygame.draw.rect(canvas, '#101b19', rect.move(2, 2))
        pygame.draw.rect(canvas, INK, rect)
        pygame.draw.rect(canvas, EDGE, rect, 1)
        for i, line in enumerate(labels):
            canvas.blit(self.small_font.render(line, False, GOLD), (71, y+6+i*11))
        for i, line in enumerate(lines):
            canvas.blit(self.font.render(line, False, PAPER), (71, y+body_offset+i*13))

    def _journal_rows(self):
        rows = []
        labels = {'available': 'AVAILABLE', 'active': 'IN PROGRESS',
                  'ready': 'READY TO REPORT', 'completed': 'COMPLETED'}
        for identifier, definition in self.game.quests.definitions.items():
            state = self.game.quests.states[identifier]
            status = state['status']
            rows.append((labels.get(status, status.upper()), GOLD, self.small_font, 0))
            for line in self.wrap(definition['title'], self.heading_font, 396):
                rows.append((line, PAPER, self.heading_font, 0))
            for line in self.wrap(definition.get('summary', ''), self.font, 396):
                rows.append((line, MUTED, self.font, 0))
            if status == 'available':
                rows.append(('Look for ! to speak with the quest giver.', MUTED, self.font, 0))
            else:
                for objective in definition['objectives']:
                    objective_status = self.game.quests.objective_status(identifier, objective['id'])
                    prefix = '[x] ' if objective_status == 'completed' else '[-] ' if objective_status == 'queued' else '[ ] '
                    text = objective['text']
                    if objective_status == 'queued':
                        text += ' (after Halden)' if objective.get('requires') == ['halden'] else ' (queued)'
                    for i, line in enumerate(self.wrap(text, self.font, 369)):
                        rows.append(((prefix if i == 0 else '    ')+line,
                                     MUTED if objective_status == 'queued' else PAPER, self.font, 8))
                if status == 'ready':
                    rows.append(('? Return to the quest giver to finish.', GOLD, self.font, 8))
            rows.append(('', PAPER, self.font, 0))
        return rows

    def draw_journal(self, canvas):
        if not self.journal_open:
            return
        shade = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        shade.fill((12, 24, 23, 225))
        canvas.blit(shade, (0, 0))
        pygame.draw.rect(canvas, INK, (12, 14, 456, 292))
        pygame.draw.rect(canvas, EDGE, (12, 14, 456, 292), 2)
        canvas.blit(self.heading_font.render('QUEST JOURNAL', False, GOLD), (28, 25))
        pygame.draw.line(canvas, EDGE, (28, 47), (452, 47))
        viewport = pygame.Rect(28, 57, 414, 219)
        rows = self._journal_rows()
        heights = [max(14, font.get_height()+2) for _, _, font, _ in rows]
        self.max_scroll = max(0, sum(heights)-viewport.height)
        self.scroll = max(0, min(self.max_scroll, self.scroll))
        previous_clip = canvas.get_clip()
        canvas.set_clip(viewport)
        y = viewport.y-self.scroll
        if not rows:
            canvas.blit(self.font.render('No quests discovered yet.', False, MUTED), (28, y))
        for (text, color, font, indent), height in zip(rows, heights):
            canvas.blit(font.render(text, False, color), (viewport.x+indent, y))
            y += height
        canvas.set_clip(previous_clip)
        if self.max_scroll:
            pygame.draw.rect(canvas, '#526761', (450, 57, 3, 219))
            thumb = max(12, round(219*219/(self.max_scroll+219)))
            offset = round((219-thumb)*self.scroll/self.max_scroll)
            pygame.draw.rect(canvas, GOLD, (450, 57+offset, 3, thumb))
        canvas.blit(self.small_font.render('J / Esc: close    Wheel / arrows: scroll', False, MUTED), (28, 288))

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

    def draw_map_markers(self, canvas, origin, map_size):
        actors = list(self.game.town.npcs)+list(getattr(self.game, 'persistent_npcs', []))
        seen = set()
        for scene in self.game.scenes.values():
            actors.extend(scene.npcs)
        for actor in actors:
            if id(actor) in seen:
                continue
            seen.add(id(actor))
            symbol = self.game.quests.marker_for(actor.data['id'])
            if symbol is None:
                continue
            position = self._map_position(actor)
            if position is None:
                continue
            center = (origin[0]+round(position[0]*map_size[0]/self.game.town.size[0]),
                      origin[1]+round(position[1]*map_size[1]/self.game.town.size[1]))
            self._symbol(canvas, symbol, center, self.game.elapsed_ms)
