"""Sparse floor-clipped elemental chamber ambience and original crystal hums.

The owner never changes music or reserves mixer channels. Geometry comes from
the live cave and guardian registry; no second chamber coordinate table exists.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass
import math
import random

import pygame


HUM_SECONDS = 4
HUM_GAIN = {'fire': .22, 'ice': .13}


def synth_hum(element, rate, channels):
    """Original bounded signed-16-bit PCM with a periodic four-second seam."""
    if element not in HUM_GAIN or type(rate) is not int or not 4000 <= rate <= 192000:
        raise ValueError('Invalid elemental crystal hum format')
    if type(channels) is not int or channels not in (1, 2):
        raise ValueError('Elemental crystal hum supports mono or stereo')
    # Every partial completes an integer number of cycles in four seconds.
    frequencies = (174.5, 261.75, 349.) if element == 'fire' else (262.5, 393.75, 525.)
    amplitudes = (.026, .013, .006)
    result = array('h')
    for index in range(rate*HUM_SECONDS):
        seconds = index/rate
        swell = .82+.18*math.cos(2*math.pi*seconds/HUM_SECONDS)
        value = swell*sum(gain*math.sin(2*math.pi*frequency*seconds)
                         for gain, frequency in zip(amplitudes, frequencies))
        sample = max(-32768, min(32767, round(value*32767)))
        result.extend([sample]*channels)
    return result


@dataclass
class Room:
    element: str
    bounds: pygame.Rect
    floor: pygame.Mask
    alpha: pygame.Surface
    layer: pygame.Surface
    particles: tuple
    wisps: tuple


class ElementalRoomEffects:
    """One low-volume hum and bounded native-pixel ambience for two rooms."""
    def __init__(self, game):
        self.game = game
        self.elapsed = 0.
        self._world = None
        self._rooms = {}
        self._channel = self._sound = self._audio_room = None
        self._sounds = {}
        bind = getattr(game.audio, 'bind_effects', None)
        if bind is not None:bind(self)

    def _in_cave(self):
        return getattr(getattr(self.game, 'world', None), 'data', {}).get('id') == 'sanctuary_cave'

    def _visible(self):
        game = self.game
        return (self._in_cave() and not getattr(game, 'on_title', False)
                and not getattr(game, 'on_gallery', False)
                and not getattr(game, '_is_gallery_preview', False)
                and getattr(game, 'gallery_session', None) is None
                and not getattr(getattr(game, 'combat', None), 'active', False)
                and not getattr(getattr(game, 'opening_cinematic', None), 'active', False))

    def _available(self):
        game = self.game
        return (self._visible() and getattr(game, '_music_focused', True)
                and not getattr(game, 'map_open', False)
                and not getattr(game, 'household_action', False)
                and not getattr(game, 'transfer_cooldown', 0)
                and not getattr(game, 'opening_fade', 0)
                and not getattr(getattr(game, 'quest_ui', None), 'journal_open', False)
                and not getattr(getattr(game, 'social', None), 'active', False)
                and not getattr(getattr(game, 'social', None), 'locked', False)
                and not getattr(getattr(game, 'opening', None), 'locks_player', False)
                and not getattr(getattr(game, 'elemental_bosses', None), 'acquisition_active', False)
                and not any(getattr(getattr(game, key, None), 'is_open', False)
                            for key in ('pause', 'inventory_ui', 'world_map_viewer', 'party_ui', 'status_ui')))

    def _geometry(self):
        if not self._in_cave():return
        world = self.game.world
        if self._world is world:return
        # Import after construction: the registry and controller may themselves
        # create this ambience owner without an import cycle.
        from elemental_bosses import REGISTRY
        definitions = {entry['id']:entry for entry in world.data.get('cave', {}).get('rooms', [])}
        rooms = {}
        for identifier, guardian in REGISTRY.items():
            definition = definitions.get(guardian['room'])
            if definition is None:continue
            points = definition['polygon']
            left, top = min(point[0] for point in points), min(point[1] for point in points)
            right, bottom = max(point[0] for point in points)+1, max(point[1] for point in points)+1
            bounds = pygame.Rect(left, top, right-left, bottom-top)
            polygon = pygame.Surface(bounds.size, pygame.SRCALPHA)
            pygame.draw.polygon(polygon, (255, 255, 255, 255),
                                [(x-left, y-top) for x, y in points])
            floor = pygame.mask.from_surface(polygon)
            blocked = getattr(world, 'blocked', None)
            if blocked is not None:floor.erase(blocked, (-left, -top))
            alpha = floor.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(255, 255, 255, 0))
            rng = random.Random('elemental-room:'+identifier)

            def positions(count):
                found = []
                for _ in range(count*80):
                    x, y = rng.randrange(bounds.width), rng.randrange(bounds.height)
                    if floor.get_at((x, y)):
                        found.append((x, y, rng.random(), rng.uniform(7., 13.)))
                        if len(found) == count:break
                return tuple(found)

            rooms[identifier] = Room(guardian['element'], bounds, floor, alpha,
                pygame.Surface(bounds.size, pygame.SRCALPHA),
                positions(12 if guardian['element'] == 'fire' else 10), positions(3))
        self._rooms, self._world = rooms, world

    def _listener_room(self):
        if not self._in_cave():return None
        self._geometry()
        position = getattr(getattr(self.game, 'player', None), 'position', None)
        if position is None:return None
        for identifier, room in self._rooms.items():
            point = (round(position[0])-room.bounds.x, round(position[1])-room.bounds.y)
            if (0 <= point[0] < room.bounds.width and 0 <= point[1] < room.bounds.height
                    and room.floor.get_at(point)):return identifier
        return None

    def stop_audio(self):
        channel, sound = self._channel, self._sound
        self._channel = self._sound = self._audio_room = None
        try:
            if channel is not None and channel.get_sound() is sound:channel.stop()
        except pygame.error:pass

    def sync_audio(self):
        """Call before world/menu early returns to release ambience immediately."""
        try:
            mixer = pygame.mixer.get_init()
            if not mixer:
                self.stop_audio();self._sounds.clear();return
            if (not self._available() or self.game.audio.effects_volume <= 0
                    or mixer[1] != -16 or mixer[2] not in (1, 2)):
                self.stop_audio();return
            identifier = self._listener_room()
            if identifier is None:
                self.stop_audio();return
            if self._audio_room != identifier:self.stop_audio()
            if self._channel is not None and self._channel.get_sound() is not self._sound:
                # A channel lease can expire while another effect takes it.
                self._channel = self._sound = self._audio_room = None
            room = self._rooms[identifier]
            if self._channel is None:
                channel = pygame.mixer.find_channel(False)
                if channel is None:return
                cache_key = (room.element, *mixer)
                if cache_key not in self._sounds:
                    self._sounds[cache_key] = pygame.mixer.Sound(
                        buffer=synth_hum(room.element, mixer[0], mixer[2]))
                sound = self._sounds[cache_key]
                channel.set_volume(HUM_GAIN[room.element]*self.game.audio.effects_volume)
                channel.play(sound, loops=-1)
                self._channel, self._sound, self._audio_room = channel, sound, identifier
            elif self._channel.get_sound() is self._sound:
                self._channel.set_volume(HUM_GAIN[room.element]*self.game.audio.effects_volume)
        except pygame.error:self.stop_audio()

    def refresh_volume(self):self.sync_audio()

    def update(self, seconds):
        self.sync_audio()
        if (self._available() and not getattr(self.game.audio, 'reduced_motion', False)
                and isinstance(seconds, (int, float)) and math.isfinite(seconds)):
            self.elapsed += max(0., seconds)

    def draw(self, canvas, camera):
        if not self._visible():return
        self._geometry()
        viewport = pygame.Rect(round(camera[0]), round(camera[1]), *canvas.get_size())
        reduced = getattr(self.game.audio, 'reduced_motion', False)
        time = 0. if reduced else self.elapsed
        for room in self._rooms.values():
            if not room.bounds.colliderect(viewport):continue
            layer = room.layer
            layer.fill((0, 0, 0, 0))
            for index, (origin_x, origin_y, phase, speed) in enumerate(room.particles):
                if reduced:x, y = origin_x, origin_y
                elif room.element == 'fire':
                    x = origin_x+3*math.sin(time*.45+phase*math.tau)
                    y = (origin_y-time*speed*.7) % room.bounds.height
                else:
                    x = (origin_x+time*speed*.2) % room.bounds.width
                    y = (origin_y+time*speed*.25) % room.bounds.height
                point = (round(x), round(y))
                if room.element == 'fire':
                    pygame.draw.circle(layer, (235, 113, 36, 25), point, 2)
                    pygame.draw.circle(layer, (255, 195, 96, 145), point, 1)
                else:
                    pygame.draw.circle(layer, (190, 226, 245, 95), point, 1)
                    if index % 4 == 0:
                        pygame.draw.line(layer, (220, 239, 248, 70),
                                         (point[0]-1, point[1]), (point[0]+1, point[1]))
            if room.element == 'fire' and not reduced:
                for x, y, phase, _ in room.wisps:
                    points = [(round(x+math.sin(time*.7+phase*math.tau+step*.8)*2), y-step*3)
                              for step in range(4)]
                    pygame.draw.lines(layer, (232, 148, 87, 28), False, points, 1)
            # Intersect the complete effect, including glow radii and wisps,
            # with the actual authored floor and live collision mask.
            layer.blit(room.alpha, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            canvas.blit(layer, (room.bounds.x-viewport.x, room.bounds.y-viewport.y))
