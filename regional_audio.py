"""Bounded regional sound. World-space listener; no queued or serialized cues."""
from dataclasses import dataclass
from array import array
import math
import random
import pygame


@dataclass(frozen=True)
class Source:
    key: str
    sound: str
    family: str
    position: object
    gain: float = .5
    near: float = 32
    far: float = 180
    priority: int = 1
    ambient: bool = False
    cooldown: float = .6

    def point(self):
        return self.position() if callable(self.position) else self.position


def distance_gain(distance, near, far):
    """Smoothstep, including an exact zero at the hard hearing boundary."""
    if distance >= far:return 0.0
    if distance <= near:return 1.0
    t = (distance-near)/(far-near)
    return 1-t*t*(3-2*t)


DURATIONS = {'river':4., 'wind':6., 'sack':.42, 'rustle':.45,
             'creak':.65, 'stone':.24, 'cup':.22,
             'water':1.05, 'leaves':.48, 'basket':.32,
             'sheep':.55, 'bird':.22, 'wings':.30}


def samples(name, rate, channels):
    """Original deterministic material synthesis; no recordings or third-party PCM."""
    rng = random.Random(9182)
    duration = DURATIONS[name]; count = round(rate*duration)
    values = []; low = 0.
    fade = round(rate*.08) if name in ('river','wind') else 0
    for i in range(count+fade):
        t = i/rate; white = rng.uniform(-1,1)
        low += (.025 if name == 'wind' else .18)*(white-low)
        if name in ('river','wind'):
            # Periodic modulation and a short cyclic crossfade avoid loop seams.
            swell = .65+.35*math.sin(math.pi*t/duration)**2
            v = (low*.9+white*.08)*swell*.45
        elif name in ('sack','rustle'):
            env = math.sin(math.pi*t/duration)**2
            v = env*(low*.8+white*.25)*.6
            if name == 'sack':v += .48*math.exp(-23*t)*math.sin(2*math.pi*78*t)*min(1,t/.004)
        elif name == 'water':
            # A finite gentle pour: shaped broadband trickle plus small droplets.
            env = math.sin(math.pi*t/duration)**2
            droplets = math.sin(2*math.pi*(930*t+150*t*t))
            v = env*(low*.20+white*.035+droplets*.018)
        elif name == 'leaves':
            env = math.sin(math.pi*t/duration)**2
            v = env*(white*.08+low*.16)*(0.7+0.3*math.sin(41*t)**2)
        elif name == 'basket':
            # Soft fruit/wood contact with a brief wicker rustle, no metal ring.
            attack = min(1,t/.005)
            v = attack*math.exp(-24*t)*(.20*math.sin(2*math.pi*105*t)+low*.15)
            v += math.sin(math.pi*t/duration)**2*white*.025
        elif name == 'sheep':
            # A short voiced bleat: falling pitch, mild quaver and soft breath.
            env = math.sin(math.pi*t/duration)**2
            phase = 2*math.pi*(185*t-26*t*t+7/(2*math.pi*5.5)*math.sin(2*math.pi*5.5*t))
            voice = (.11*math.sin(phase)+.065*math.sin(2*phase)
                     +.04*math.sin(3*phase)+.015*math.sin(5*phase))
            v = env*(voice*(.78+.22*math.sin(2*math.pi*6*t)**2)+low*.018)
        elif name == 'bird':
            # One rounded chirp, with a smooth rise and fall in pitch.
            env = math.sin(math.pi*t/duration)**2
            phase = 2*math.pi*(2300*t+1800*t*t/duration-1200*t*t*t/duration**2)
            v = env*(.12*math.sin(phase)+white*.004)
        elif name == 'wings':
            # Three quiet feather beats; no continuous wildlife ambience.
            env = math.sin(math.pi*t/duration)**2
            flutter = .25+.75*math.sin(3*math.pi*t/duration)**2
            v = env*flutter*(white*.055+low*.18)
        elif name == 'creak':
            env = math.sin(math.pi*t/duration)**2
            phase = 2*math.pi*(91*t+65*t*t)
            v = env*(.14*math.sin(phase)+.07*math.sin(phase*3.13)+.10*low)
        else:
            env = min(1,t/.002)*math.exp(-(29 if name=='cup' else 36)*t)*min(1,(duration-t)/.02)
            frequencies = (1180,3079,4210) if name=='cup' else (740,1763,3141)
            v = env*(sum(a*math.sin(2*math.pi*f*t) for a,f in zip((.25,.10,.05),frequencies))+white*(.09 if name=='cup' else .3))
        values.append(v)
    if name in ('river','wind'):
        fade = round(rate*.08)
        for i in range(fade):
            t = i/fade
            values[i] = values[count+i]*(1-t)+values[i]*t
        values = values[:count]
    pcm = array('h')
    for v in values:pcm.extend([round(v*24000)]*channels)
    return pcm


class RegionalAudio:
    """Four voices maximum: two beds (one/family), two cues (one/family).

    Channels are leased only while get_sound matches our sound identity. Never
    reserve, steal, resize the mixer, or touch music. Dropped cues never queue.
    """
    def __init__(self, game):
        self.game = game; self.voices = {}; self.cache = {}; self.cooldowns = {}
        self.clock = 0.; self.failed = False
        self.observer = None  # Optional review sink: accepted start/gain/stop only.
        game.audio.bind_effects(self)

    def enabled(self):
        g = self.game
        return (g.overworld_travel.active and not g.on_title and not g.opening_cinematic.active
                and not g.regent_arrival.active and g.regent_arrival.state != 'pending'
                and not g.combat.active and not g.pause.is_open and not g.inventory_ui.is_open
                and not g.world_map_viewer.is_open and not g.map_open and not g.quest_ui.journal_open
                and g._music_focused and g.audio.effects_volume > 0)

    def _notify(self, action, key, **data):
        if self.observer:self.observer(action, key, **data)

    def _stop(self, key):
        source, channel, sound, age = self.voices.pop(key)
        if channel.get_sound() is sound:channel.stop()
        self._notify('stop', key)

    def reset(self):
        self.stop(); self.cooldowns.clear(); self.clock = 0.; self.failed = False

    def stop(self):
        for key in list(self.voices):
            try:self._stop(key)
            except pygame.error:self.voices.pop(key, None)

    def _gain(self, source):
        distance = math.dist(self.game.player.position, source.point())
        return source.gain*self.game.audio.effects_volume*distance_gain(distance,source.near,source.far)

    def refresh_volume(self):
        if not self.enabled():self.stop();return
        for key,(source,channel,sound,age) in list(self.voices.items()):
            try:
                gain = self._gain(source)
                if channel.get_sound() is not sound or gain <= 0:self._stop(key)
                else:
                    channel.set_volume(gain)
                    self._notify('gain', key, gain=gain)
            except pygame.error:self.stop();self.failed=True;return

    def _sound(self, name):
        spec = pygame.mixer.get_init()
        if not spec or spec[1] != -16:return None
        key = (name,*spec)
        if key not in self.cache:self.cache[key] = pygame.mixer.Sound(buffer=samples(name,spec[0],spec[2]))
        return self.cache[key]

    def play(self, source):
        self.refresh_volume()
        if self.failed or not self.enabled() or source.key in self.voices:return False
        if self.cooldowns.get(source.key,0)>self.clock:return False
        gain = self._gain(source)
        # Activation is inset by 12px; all active sources still stop at far.
        if gain<=0 or (source.ambient and math.dist(self.game.player.position,source.point())>=source.far-12):return False
        peers = [(k,v) for k,v in self.voices.items() if v[0].ambient == source.ambient]
        same = [(k,v) for k,v in peers if v[0].family == source.family]
        candidates = same or (peers if len(peers)>=2 else [])
        if candidates:
            key, voice = min(candidates,key=lambda kv:(kv[1][0].priority,self._gain(kv[1][0]),kv[0]))
            old = voice[0]
            # Stable tie: existing voice wins. Avoid churn between equal beds.
            if (source.priority,gain)<=(old.priority,self._gain(old)):return False
            self._stop(key)
        try:
            sound = self._sound(source.sound)
            if sound is None:return False
            channel = pygame.mixer.find_channel()  # force=False: never steal.
            if channel is None:return False
            channel.set_volume(gain)
            channel.play(sound, loops=-1 if source.ambient else 0)
            channel.set_volume(gain)
            self.voices[source.key] = (source,channel,sound,0.)
            self.cooldowns[source.key] = self.clock+source.cooldown
            self._notify('start',source.key,sound=source.sound,gain=gain,ambient=source.ambient)
            return True
        except (pygame.error,OSError):
            self.failed=True;self.stop();return False

    def emit(self, key, name, position, family, priority=2):
        return self.play(Source(key,name,family,position,priority=priority))

    def update(self, seconds):
        self.clock += max(0,seconds)
        sources = list(self.ambient_sources()) if self.enabled() else []
        for source in sources:
            if source.key in self.voices:
                _,channel,sound,age = self.voices[source.key]
                self.voices[source.key] = (source,channel,sound,age)
        self.refresh_volume()
        if not self.enabled():return
        for key,(source,channel,sound,age) in list(self.voices.items()):
            age += max(0,seconds)
            if not source.ambient and age>=DURATIONS[source.sound]:self._stop(key)
            else:self.voices[key]=(source,channel,sound,age)
        self.cooldowns = {k:v for k,v in self.cooldowns.items() if v>self.clock}
        for source in sorted(sources,key=lambda s:(-s.priority,-self._gain(s),s.key)):
            self.play(source)

    def ambient_sources(self):
        from overworld_world import _point_in_polygon, TILE_SIZE
        listener = pygame.Vector2(self.game.player.position)/TILE_SIZE
        terrain = self.game.world.region['terrain']
        def nearest(points, closed=False):
            best = None
            for a,b in zip(points,points[1:]+(points[:1] if closed else [])):
                a,b = pygame.Vector2(a),pygame.Vector2(b); d=b-a
                t = max(0,min(1,(listener-a).dot(d)/d.length_squared())) if d.length_squared() else 0
                p = a+d*t
                if best is None or listener.distance_squared_to(p)<listener.distance_squared_to(best):best=p
            return best
        rivers=[]
        for river in terrain.get('rivers',[]):
            p=nearest(river['points'])
            if p is not None:
                delta=listener-p
                if delta.length():p += delta.normalize()*min(delta.length(),river.get('width',8)/2)
                rivers.append(p*TILE_SIZE)
        if rivers:
            p=min(rivers,key=lambda p:p.distance_squared_to(self.game.player.position))
            yield Source('river','river','water',tuple(p),.55,36,260,1,True)
        patches=terrain.get('forests',[])+[f for f in terrain.get('fields',[]) if f.get('crop') in ('grain','orchard')]
        points=[]
        for patch in patches:
            polygon=patch['polygon']
            p=listener if _point_in_polygon(listener,polygon) else nearest(polygon,True)
            if p is not None:points.append(p*TILE_SIZE)
        if points:
            p=min(points,key=lambda p:p.distance_squared_to(self.game.player.position))
            yield Source('wind','wind','foliage',tuple(p),.45,24,150,0,True)
