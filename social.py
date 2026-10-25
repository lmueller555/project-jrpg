"""Proximity conversations, speaker portraits, and routine-safe interruptions."""
import json
import math
from pathlib import Path

import pygame
from speech_bubble import SpeechBubble, TEXT_WIDTH, MAX_LINES

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
        self._scripted = False
        self._script_callback = None
        self._script_origin = None
        self._conversation_world = None
        self.script_identifier = None
        self.font = pygame.font.Font(None, 18)
        self.name_font = pygame.font.Font(None, 20)
        self.hint_font = pygame.font.Font(None, 14)
        self.portraits = {}
        manifest = json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())
        for speaker in self.data['speakers'].values():
            key = speaker['portrait']
            record = manifest['portraits'][key]
            self.portraits[key] = game.town.image('assets/portraits/eldenmere/'+record['file'])
        self.bubble = SpeechBubble(self)

    @property
    def locked(self):
        """Legacy busy flag: reserves one exchange, never movement or camera."""
        return self.actor is not None or self._scripted

    @property
    def scripted(self):return self._scripted

    @property
    def active(self):return self.locked and not self.pending

    @property
    def page(self):return self.pages[self.page_index] if self.active else None

    @property
    def choosing(self):return self.active and self._choosing

    @property
    def choice_options(self):
        if not self.choosing:return []
        return self.conversation.get('choices', [
            {'text': "I'll help", 'action': 'accept'},
            {'text': 'Not just yet', 'action': 'decline'}])

    @property
    def choice_prompt(self):
        return (self.conversation or {}).get('choice_prompt', 'Will you help?')

    @property
    def choice_rects(self):
        if not self.choosing:return []
        return self.bubble.layout().choice_rects

    def resolve_speaker(self):
        """Resolve the page's speaker in this room, rather than the initiator."""
        if self.pending:return self.actor
        if self.page is None:return None
        speaker = self.page['speaker']
        if speaker == 'caelan':return self.game.player
        identifier = self.data['speakers'][speaker].get('actor_id', speaker)
        return next((actor for actor in self.game.world.npcs
                     if actor.data['id'] == identifier), None)

    def anchor_position(self):
        """World-space opaque head position, including authored action poses."""
        actor = self.resolve_speaker()
        if actor is None:
            # A voice through a doorway belongs at that doorway, never above
            # another person's body. The portrait still identifies the voice.
            speaker = self.page['speaker'] if self.page else None
            identifier = self.data['speakers'].get(speaker, {}).get('actor_id', speaker)
            remote = next((npc for npc in getattr(self.game, 'persistent_npcs', [])
                           if npc.data['id'] == identifier), None)
            for door in getattr(self.game.world, 'doors', []):
                destination = door.data.get('destination', '')
                if remote is not None and remote.scene_id in Path(destination).parts:
                    x, y = door.data['anchor']
                    return (x, y-24)
            actor = self.game.player
        opening = getattr(self.game, 'opening', None)
        if actor is self.game.player and getattr(opening, '_sleeping', False):
            x, y = opening.data['sleep_head_origin']
            return (x+12, y)
        position = getattr(actor, 'story_position', None) or actor.position
        anchor = getattr(actor, 'story_draw_anchor', None)
        if anchor is None:
            anchor = (getattr(self.game.world, 'data', {}).get('player_draw_anchor', (12, 30))
                      if actor is self.game.player else getattr(actor, 'draw_anchor', (12, 30)))
        image = getattr(actor, 'story_sprite', None)
        if image is None and hasattr(actor, 'sprite'):
            image = (actor.sprite() if actor is self.game.player
                     else actor.sprite(getattr(self.game, 'elapsed_ms', 0)))
        top = image.get_bounding_rect().top if isinstance(image, pygame.Surface) else 0
        return (position[0], position[1]-anchor[1]+top)

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
            departed = self._conversation_world is not None and self._conversation_world is not game.world
            if self.actor is not None:
                departed = (departed or self.actor not in game.world.npcs or
                            game.player.position.distance_to(self.actor.position) > self.data['release_radius'])
            elif self._script_origin is not None:
                departed = departed or game.player.position.distance_to(self._script_origin) > self.data['release_radius']
            if departed:
                self.cancel()
                return
            if self.pending and self.actor is not None and self.actor.conversation_ready:
                self.pending = False
            if self.actor is not None:
                self.actor.conversation_facing = facing_toward(game.player.position-self.actor.position)
            return
        if (game.map_open or getattr(getattr(game, 'quest_ui', None), 'journal_open', False)
                or game.transfer_cooldown or not pygame.Vector2(direction).length_squared()):return
        forward = pygame.Vector2(FACING[game.player.facing])
        candidates = []
        opening = getattr(game, 'opening', None)
        for actor in game.world.npcs:
            if actor in self.blocked or actor.data['id'] not in self.profiles:continue
            if opening is not None and not opening.can_speak(actor.data['id']):continue
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
        if self.locked:return False
        opening = getattr(self.game, 'opening', None)
        if opening is not None and not opening.can_speak(actor.data['id']):return False
        profile = self.profiles[actor.data['id']]
        conversation = next((c for c in profile['conversations'] if self._eligible(c)), None)
        if conversation is None:return False
        self.pages = self._make_pages(conversation['lines'])
        self.actor = actor
        self.conversation = conversation
        self._choosing = False
        self.page_index = 0
        self.pending = True
        self._conversation_world = self.game.world
        delta = self.game.player.position-actor.position
        actor.request_conversation(facing_toward(delta))
        self.pending = not actor.conversation_ready
        return True

    def _make_pages(self, lines):
        pages = []
        for line in lines:
            wrapped = self.wrap(line['text'], TEXT_WIDTH)
            for offset in range(0, len(wrapped), MAX_LINES):
                page = {'speaker': line['speaker'], 'lines': wrapped[offset:offset+MAX_LINES]}
                # Scene actions belong to the line's first page, so wrapping
                # cannot accidentally repeat a handoff or other story cue.
                if offset == 0 and 'cue' in line:page['cue'] = line['cue']
                pages.append(page)
        return pages

    def start_script(self, lines, on_complete=None, identifier=None):
        """Read a scene's dialogue without impersonating an ambient NPC.

        The caller owns scene staging and progression. The callback runs once,
        after the conversation is cleared, and can safely start another scene.
        """
        if self.locked or not isinstance(lines, (list, tuple)) or not lines:return False
        if on_complete is not None and not callable(on_complete):return False
        if any(not isinstance(line, dict) or not isinstance(line.get('speaker'), str)
               or line['speaker'] not in self.data['speakers']
               or not isinstance(line.get('text'), str) or not line['text'].strip()
               or ('cue' in line and not isinstance(line['cue'], str)) for line in lines):
            return False
        pages = self._make_pages(lines)
        self.actor = None
        self.pages = pages
        self.page_index = 0
        self.pending = False
        self.conversation = {'id': identifier or 'scripted_scene', 'scripted': True}
        self._choosing = False
        self._scripted = True
        self._script_callback = on_complete
        self._script_origin = tuple(self.game.player.position)
        self._conversation_world = self.game.world
        self.script_identifier = identifier
        return True

    def cancel_script(self):
        """Discard a scene dialogue without advancing its story checkpoint."""
        if not self.scripted:return False
        self.actor = None
        self.pages = []
        self.page_index = 0
        self.pending = False
        self.conversation = None
        self._choosing = False
        self._scripted = False
        self._script_callback = None
        self._script_origin = None
        self._conversation_world = None
        self.script_identifier = None
        return True

    def cancel(self):
        """Walk away without applying flags, choices or a quest turn-in."""
        if not self.locked:return False
        if self.scripted:
            identifier = self.script_identifier
            self.cancel_script()
            hook = getattr(getattr(self.game, 'opening', None), 'on_dialogue_cancelled', None)
            if hook is not None:hook(identifier)
        else:
            self.blocked.add(self.actor)
            self.actor.end_conversation()
            self.actor = None
            self.pages = []
            self.page_index = 0
            self.pending = False
            self.conversation = None
            self._choosing = False
            self._conversation_world = None
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
            # Long names or unspaced text must not escape the bubble column.
            while self.font.size(current)[0] > width and len(current) > 1:
                end = 1
                while end < len(current) and self.font.size(current[:end+1])[0] <= width:
                    end += 1
                lines.append(current[:end])
                current = current[end:]
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
        # A camera/position change between frames must not accept a stale offer.
        if self.locked:self.update((0, 0))
        if not self.active:return False
        if not self.choosing:
            self.advance()
            return True
        if point is None:return False
        choice = next((i for i, rect in enumerate(self.choice_rects) if rect.collidepoint(point)), None)
        if choice is None:return False
        accepted = None
        option = self.choice_options[choice]
        if option.get('action') == 'accept':
            if not self.game.quests.accept(self.conversation['quest']['id']):return False
            accepted = self.conversation['quest']['id']
        self._finish(accepted)
        return True

    def _finish(self, accepted_quest=None):
        if self.scripted:
            callback = self._script_callback
            self.cancel_script()
            if callback is not None:callback()
            return
        condition = self.conversation.get('quest', {})
        if condition.get('action') == 'turn_in':
            self.game.quests.turn_in(condition['id'], self.actor.data['id'])
        self.flags.update(self.conversation.get('sets', []))
        self.blocked.add(self.actor)
        self.actor.end_conversation()
        self.actor = None
        self.pages = []
        self.page_index = 0
        self.pending = False
        self._conversation_world = None
        self.conversation = None
        self._choosing = False
        opening = getattr(self.game, 'opening', None)
        if accepted_quest is not None and opening is not None:
            opening.on_quest_accepted(accepted_quest)
        save = getattr(self.game, 'save_progress', None)
        if save is not None:save()

    def draw(self, canvas, elapsed_ms, camera=None):
        return self.bubble.draw(canvas, camera=camera, elapsed_ms=elapsed_ms)
