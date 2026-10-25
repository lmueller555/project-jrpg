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

    def update(self, direction):
        game = self.game
        for actor in tuple(self.blocked):
            if actor not in game.world.npcs or game.player.position.distance_to(actor.position) > self.data['release_radius']:
                self.blocked.remove(actor)
        if self.locked:
            if self.pending and self.actor.conversation_ready:
                self.pending = False
            return
        if game.map_open or game.transfer_cooldown or not pygame.Vector2(direction).length_squared():return
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
        conversation = next(c for c in profile['conversations']
                            if set(c.get('requires', [])) <= self.flags)
        self.pages = []
        for line in conversation['lines']:
            wrapped = self.wrap(line['text'], 332)
            for offset in range(0, len(wrapped), 3):
                self.pages.append({'speaker': line['speaker'], 'lines': wrapped[offset:offset+3]})
        self.actor = actor
        self.conversation = conversation
        self.page_index = 0
        self.pending = True
        delta = self.game.player.position-actor.position
        actor.request_conversation(facing_toward(delta))
        self.pending = not actor.conversation_ready
        self.game.player.moving = False
        self.game.player.walk_ms = 0

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
        if not self.active:return
        self.page_index += 1
        if self.page_index < len(self.pages):return
        self.flags.update(self.conversation.get('sets', []))
        self.blocked.add(self.actor)
        self.actor.end_conversation()
        self.actor = None
        self.pages = []
        self.conversation = None

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
        for index, line in enumerate(self.page['lines']):
            canvas.blit(self.font.render(line, False, '#f7eed5'), (122, 240+index*17))
        hint = 'Click anywhere  /  Space'
        canvas.blit(self.hint_font.render(hint, False, '#c9c9b5'), (122, 289))
        if int(elapsed_ms//450) % 2 == 0:
            pygame.draw.polygon(canvas, '#ffdc71', [(446, 289), (454, 289), (450, 294)])
