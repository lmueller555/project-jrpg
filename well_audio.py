"""Short-radius well feedback, observing work rather than advancing it.

The regional engine supplies bounded, identity-checked channel leases. This
town-only controller supplies a separate material bank and a steep cubic curve;
the wider regional attenuation and all existing sources remain unchanged.
"""
from collections import OrderedDict, deque
import math

import pygame

from regional_audio import RegionalAudio, Source
from well_audio_samples import DURATIONS, samples

WELL_POSITION = (528, 864)
NEAR_RADIUS = 32
FAR_RADIUS = 80


def well_distance_gain(distance, near=NEAR_RADIUS, far=FAR_RADIUS):
    """Full level near the source, rapid cubic falloff, exact far silence."""
    if distance >= far:
        return 0.
    if distance <= near:
        return 1.
    return ((far-distance)/(far-near))**3


class WellAudio(RegionalAudio):
    durations = DURATIONS
    SOUND_CACHE_LIMIT = len(DURATIONS)*2
    SEEN_LIMIT = 128
    MAX_CUE_AGE = .125
    EVENT_SOUNDS = {'attached': ('well_hook', .34, 'well.metal'),
                    'water_contact': ('well_splash', .38, 'well.water'),
                    'water_exit': ('well_drip', .30, 'well.water'),
                    'detached': ('well_hook', .30, 'well.metal')}

    def __init__(self, game):
        super().__init__(game)
        self.cache = OrderedDict()
        self._seen = set()
        self._seen_order = deque()

    def enabled(self):
        g = self.game
        if (getattr(g, 'world', None) is not getattr(g, 'town', None)
                or getattr(g, 'town', None) is None
                or getattr(g, 'on_title', False)
                or not getattr(g, '_music_focused', True)
                or g.audio.effects_volume <= 0
                or getattr(g, 'on_gallery', False)
                or getattr(g, '_is_gallery_preview', False)
                or getattr(g, 'gallery_session', None) is not None
                or getattr(g, 'on_quest_playtest', False)
                or getattr(g, 'quest_playtest_session', None) is not None
                or getattr(g, 'game_over', False)
                or getattr(g, 'map_open', False)):
            return False
        for owner in ('pause', 'inventory_ui', 'world_map_viewer', 'party_ui',
                      'services', 'status_ui', 'save_menu'):
            if getattr(getattr(g, owner, None), 'is_open', False):
                return False
        if (getattr(getattr(g, 'quest_ui', None), 'journal_open', False)
                or getattr(getattr(g, 'social', None), 'locked', False)
                or getattr(getattr(g, 'opening', None), 'locks_player', False)
                or getattr(getattr(g, 'regent_quest', None), 'locks_player', False)
                or getattr(getattr(g, 'regent_arrival', None), 'state', None) == 'pending'):
            return False
        for owner in ('opening_cinematic', 'regent_arrival', 'sanctuary_arrival',
                      'sanctuary_rescue', 'mill_gift', 'combat'):
            if getattr(getattr(g, owner, None), 'active', False):
                return False
        return True

    def _actor(self):
        town = getattr(self.game, 'town', None)
        return next((actor for actor in getattr(town, 'npcs', ())
                     if getattr(actor, 'data', {}).get('id') == 'sanctuary_gardener'), None)

    def _gain(self, source):
        distance = math.dist(self.game.player.position, source.point())
        return source.gain*self.game.audio.effects_volume*well_distance_gain(distance, source.near, source.far)

    def _sound(self, name):
        spec = pygame.mixer.get_init()
        if not spec or spec[1] != -16:
            return None
        key = (name, *spec)
        sound = self.cache.pop(key, None)
        if sound is None:
            sound = pygame.mixer.Sound(buffer=samples(name, spec[0], spec[2]))
        self.cache[key] = sound
        while len(self.cache) > self.SOUND_CACHE_LIMIT:
            self.cache.popitem(last=False)
        return sound

    def prepare(self):
        """Warm the six current-format sounds before exploration begins.

        Synthesis is a loading cost, never a first-contact movement hitch. This
        does not request a channel, start playback or inspect gameplay events.
        """
        if self.failed:
            return False
        try:
            spec = pygame.mixer.get_init()
            if not spec or spec[1] != -16:
                return False
            for name in self.durations:
                self._sound(name)
            return True
        except (pygame.error, OSError):
            self.stop()
            self.failed = True
            return False

    def _remember(self, key):
        if key in self._seen:
            return False
        self._seen.add(key)
        self._seen_order.append(key)
        while len(self._seen_order) > self.SEEN_LIMIT:
            self._seen.discard(self._seen_order.popleft())
        return True

    @staticmethod
    def _source(key, sound, family, position, gain, ambient=False):
        return Source(key, sound, family, position, gain, NEAR_RADIUS,
                      FAR_RADIUS, 2, ambient, 0.)

    def _consume_work(self):
        actor = self._actor()
        if actor is None:
            return None, None
        state = actor.well_snapshot
        for event in actor.well_events:
            key = ('event', id(actor), event.event_id)
            if self._remember(key) and event.cue_id in self.EVENT_SOUNDS:
                age = (state.total_elapsed_ms-event.operation_elapsed_ms)/1000
                if event.operation_id != state.operation_id or age > self.MAX_CUE_AGE:
                    continue
                sound, gain, family = self.EVENT_SOUNDS[event.cue_id]
                self.play(self._source(f'well.{event.operation_id}.{event.cue_id}', sound,
                                       family, WELL_POSITION, gain))
        selection = actor.presentation_selection()
        pouring = (actor.state.startswith('water_') and selection.get('effect') == 'pour'
                   and actor.water_units > 0 and actor.pail_location == 'actor')
        if pouring:
            key = ('pour', id(actor), actor.completed_cycles, actor.step_index)
            if self._remember(key):
                flow_start = actor.POUR_MS*3/8
                if (actor.state_ms-flow_start)/1000 <= self.MAX_CUE_AGE:
                    self.play(self._source(f'well.pour.{actor.completed_cycles}.{actor.step_index}',
                                           'well_pour', 'well.water', lambda: tuple(actor.position), .32))
        return actor, pouring

    def ambient_sources(self):
        actor = self._actor()
        if actor is None:
            return
        state = actor.well_snapshot
        if (state.pail_owner == 'well' and state.required_station is None
                and state.crank_direction != 0):
            yield self._source('well.winding', 'well_winding', 'well.mechanism',
                               WELL_POSITION, .32, True)
        if state.phase_id == 'fill' and state.mouth_submerged:
            yield self._source('well.filling', 'well_fill', 'well.water',
                               WELL_POSITION, .26, True)

    def update(self, seconds):
        try:
            # Advance existing leases first. A contact observed in this call
            # starts at age zero, even when the supplied update is large.
            super().update(seconds)
            # Consume observations even while inaudible, muted or in another
            # room. Other observers retain the undrained gameplay events.
            actor, pouring = self._consume_work()
            if not pouring:
                for key in list(self.voices):
                    if key.startswith('well.pour.'):
                        self._stop(key)
        except pygame.error:
            # Device loss can also occur when an existing cue expires, after
            # successful playback. Audio failure never aborts world updates.
            self.stop()
            self.failed = True

    def reset(self):
        super().reset()
        self._seen.clear()
        self._seen_order.clear()
