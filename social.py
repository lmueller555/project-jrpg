"""Proximity conversations, speaker portraits, and routine-safe interruptions."""
import json
import math
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent
FACING = {'front': (0, 1), 'back': (0, -1), 'left': (-1, 0), 'right': (1, 0)}


def facing_toward(delta):
    return (('right' if delta.x > 0 else 'left') if abs(delta.x) > abs(delta.y)
            else ('front' if delta.y > 0 else 'back'))


def foot_gap(a, b):
    return math.hypot(max(a.left-b.right, b.left-a.right, 0),
                      max(a.top-b.bottom, b.top-a.bottom, 0))


def clear_sight(world, a, b):
    delta = b-a
    count = max(1, math.ceil(delta.length()))
    for index in range(count+1):
        point = a + delta*(index/count)
        x, y = round(point.x), round(point.y)
        if not (0 <= x < world.size[0] and 0 <= y < world.size[1]):return False
        if world.blocked.get_at((x, y)):return False
    return True


class SocialSystem:
    def __init__(self, game):
        self.game = game
        self.data = json.loads((ROOT/'assets/dialogue/eldenmere.json').read_text())
        self.profiles = self.data['characters']
        self.flags = set()
        self.blocked = set()
        self.actor = None
        self.pending = False
        self.pages = []
        self.page_index = 0
        self.conversation = None
        self._choosing = False
        self.choice_rects = [pygame.Rect(122, 263, 154, 23),
                             pygame.Rect(286, 263, 166, 23)]
        self.font = pygame.font.Font(None, 18)
        self.name_font = pygame.font.Font(None, 20)
        self.hint_font = pygame.font.Font(None, 14)
        self.portraits = {}
        manifest = json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())
        for speaker in self.data['speakers'].values():
            key = speaker['portrait']
            record = manifest['portraits'][key]
            self.portraits[key] = game.town.image('assets/portraits/eldenmere/'+record['file'])

    @property
    def locked(self):return self.actor is not None

    @property
    def active(self):return self.locked and not self.pending

    @property
    def page(self):return self.pages[self.page_index] if self.active else None

    @property
    def choosing(self):return self.active and self._choosing

    def _eligible(self, conversation):
        if not set(conversation.get('requires', [])) <= self.flags:return False
        condition = conversation.get('quest')
        if condition is None:return True
        quests = getattr(self.game, 'quests', None)
        if quests is None:return False
        if quests.status(condition['id']) != condition['status']:return False
        for identifier in condition.get('completed', []):
            if quests.objective_status(condition['id'], identifier) != 'completed':return False
        for identifier in condition.get('incomplete', []):
            if quests.objective_status(condition['id'], identifier) == 'completed':return False
        return True

    def update(self, direction):
        game = self.game
        for actor in tuple(self.blocked):
            if actor not in game.world.npcs or game.player.position.distance_to(actor.position) > self.data['release_radius']:
                self.blocked.remove(actor)
        if self.locked:
            if self.pending and self.actor.conversation_ready:
                self.pending = False
            return
        if (game.map_open or getattr(getattr(game, 'quest_ui', None), 'journal_open', False)
                or game.transfer_cooldown or not pygame.Vector2(direction).length_squared()):return
        forward = pygame.Vector2(FACING[game.player.facing])
        candidates = []
        for actor in game.world.npcs:
            if actor in self.blocked or actor.data['id'] not in self.profiles:continue
            delta = actor.position-game.player.position
            distance = delta.length()
            if distance == 0 or distance > self.data['trigger_radius']:continue
            if delta.normalize().dot(forward) < .25:continue
            if foot_gap(game.world.probe_rect(game.player.position), actor.blocker) > self.data['foot_gap']:continue
            if not clear_sight(game.world, game.player.position, actor.position):continue
            if not hasattr(actor, 'request_conversation'):continue
            candidates.append((distance, actor.data['id'], actor))
        if candidates:
            self.start(min(candidates, key=lambda item:item[:2])[2])

    def start(self, actor):
        profile = self.profiles[actor.data['id']]
        conversation = next((c for c in profile['conversations'] if self._eligible(c)), None)
        if conversation is None:return False
        self.pages = []
        for line in conversation['lines']:
            wrapped = self.wrap(line['text'], 332)
            for offset in range(0, len(wrapped), 3):
                self.pages.append({'speaker': line['speaker'], 'lines': wrapped[offset:offset+3]})
        self.actor = actor
        self.conversation = conversation
        self._choosing = False
        self.page_index = 0
        self.pending = True
        delta = self.game.player.position-actor.position
        actor.request_conversation(facing_toward(delta))
        self.pending = not actor.conversation_ready
        self.game.player.moving = False
        self.game.player.walk_ms = 0
        return True

    def wrap(self, text, width):
        lines = []
        current = ''
        for word in text.split():
            candidate = (current+' '+word).strip()
            if self.font.size(candidate)[0] > width and current:
                lines.append(current)
                current = word
            else:current = candidate
        if current:lines.append(current)
        return lines or ['']

    def advance(self):
        if not self.active or self.choosing:return
        if self.page_index + 1 < len(self.pages):
            self.page_index += 1
            return
        if self.conversation.get('quest', {}).get('action') == 'offer':
            self._choosing = True
            return
        self._finish()

    def click(self, point):
        """Advance prose anywhere; answer a quest only by clicking its button."""
        if not self.active:return False
        if not self.choosing:
            self.advance()
            return True
        if point is None:return False
        choice = next((i for i, rect in enumerate(self.choice_rects) if rect.collidepoint(point)), None)
        if choice is None:return False
        if choice == 0:
            self.game.quests.accept(self.conversation['quest']['id'])
        self._finish()
        return True

    def _finish(self):
        condition = self.conversation.get('quest', {})
        if condition.get('action') == 'turn_in':
            self.game.quests.turn_in(condition['id'], self.actor.data['id'])
        self.flags.update(self.conversation.get('sets', []))
        self.blocked.add(self.actor)
        self.actor.end_conversation()
        self.actor = None
        self.pages = []
        self.conversation = None
        self._choosing = False
        save = getattr(self.game, 'save_progress', None)
        if save is not None:save()

    def draw(self, canvas, elapsed_ms):
        if self.pending:
            name = self.actor.data.get('name', 'Your companion')
            image = self.hint_font.render(f'{name} is setting their work down...', False, '#f7eed5')
            rect = image.get_rect(midbottom=(240, 292)).inflate(16, 10)
            pygame.draw.rect(canvas, '#263c35', rect)
            canvas.blit(image, image.get_rect(center=rect.center))
        if not self.active:return
        panel = pygame.Rect(12, 204, 456, 104)
        pygame.draw.rect(canvas, '#101b19', panel.move(2, 3))
        pygame.draw.rect(canvas, '#263c35', panel)
        pygame.draw.rect(canvas, '#b7a47b', panel, 2)
        pygame.draw.rect(canvas, '#526761', panel.inflate(-6, -6), 1)
        pygame.draw.rect(canvas, '#b7a47b', (20, 214, 84, 84), 1)
        speaker = self.data['speakers'][self.page['speaker']]
        canvas.blit(self.portraits[speaker['portrait']], (26, 220))
        pygame.draw.line(canvas, '#526761', (112, 215), (112, 296))
        canvas.blit(self.name_font.render(speaker['name'], False, '#ffdc71'), (122, 216))
        if self.choosing:
            canvas.blit(self.font.render('Will you help?', False, '#f7eed5'), (122, 240))
            for text, rect in zip(("I'll help", 'Not just yet'), self.choice_rects):
                pygame.draw.rect(canvas, '#344e3e', rect)
                pygame.draw.rect(canvas, '#b7a47b', rect, 1)
                label = self.font.render(text, False, '#ffdc71')
                canvas.blit(label, label.get_rect(center=rect.center))
        else:
            for index, line in enumerate(self.page['lines']):
                canvas.blit(self.font.render(line, False, '#f7eed5'), (122, 240+index*17))
        hint = 'Click a choice to answer' if self.choosing else 'Click anywhere  /  Space'
        canvas.blit(self.hint_font.render(hint, False, '#c9c9b5'), (122, 289))
        if not self.choosing and int(elapsed_ms//450) % 2 == 0:
            pygame.draw.polygon(canvas, '#ffdc71', [(446, 289), (454, 289), (450, 294)])
