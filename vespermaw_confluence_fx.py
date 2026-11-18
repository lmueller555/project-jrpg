"""Clocked crystal-to-body confluence ribbons and original elemental sound.

The model owns form changes. These effects only sample its current free action;
no draw calls advance clocks, commit forms, or create combat events.
"""
from array import array
import math
import random

import pygame


COLORS = {
    'fire': ((242, 116, 44), (255, 193, 93), (255, 237, 183)),
    'ice': ((135, 193, 221), (192, 231, 247), (241, 252, 255)),
    'water': ((46, 125, 218), (100, 196, 242), (196, 241, 255)),
}


def clamp(value):return max(0., min(1., value))


class VespermawConfluenceEffects:
    def __init__(self):
        self.layer = pygame.Surface((480, 320), pygame.SRCALPHA)

    def draw(self, target, source, spine, foot, action, *, bounds,
             reduced_motion=False, foreground=False):
        if action is None or action.action != 'vespermaw_attune':return
        layer = self.layer;layer.fill((0, 0, 0, 0));layer.set_clip(bounds)
        source, spine, foot = map(pygame.Vector2, (source, spine, foot))
        colors = COLORS[getattr(action, 'channel_to', None) or action.active_gem]
        progress = clamp(action.elapsed/action.duration)
        incoming = clamp((progress-.12)/.30)
        fading = 1-clamp((progress-.78)/.22)
        weight = incoming*fading
        if reduced_motion:
            if not foreground:
                pygame.draw.line(layer, (*colors[0], 75), source, spine, 1)
                pygame.draw.circle(layer, (*colors[1], 95), spine, 7, 1)
            target.blit(layer, (0, 0));return
        if not foreground:
            # Three distinct helical strands draw toward the registered spine.
            # The beam's head travels before its body settles into a full flow.
            reach = clamp((progress-.12)/.22)
            delta = spine-source
            normal = pygame.Vector2(-delta.y, delta.x)
            if normal.length_squared():normal.normalize_ip()
            for strand in range(3):
                points = []
                for i in range(49):
                    t = i/48*reach
                    envelope = math.sin(math.pi*t)
                    twist = math.sin(t*math.tau*2.4-action.elapsed*8+strand*math.tau/3)
                    point = source+delta*t+normal*twist*envelope*(5+strand*2)
                    point.y -= math.sin(math.pi*t)*11
                    points.append(tuple(point))
                if len(points)>1:
                    pygame.draw.lines(layer, (*colors[0], round(35*weight)), False, points, 7)
                    pygame.draw.lines(layer, (*colors[strand % 3], round(150*weight)), False, points, 1)
            # Packets and shape language distinguish sparks, flakes and drops.
            for i in range(24):
                t = (action.elapsed*(.65+i%3*.08)+i/24)%1
                if t>reach:continue
                point=source.lerp(spine,t)+normal*math.sin(t*17-action.elapsed*9+i)*math.sin(t*math.pi)*8
                self._particle(layer, point, colors, action.channel_to,
                               round(180*weight), i, action.elapsed)
            # Grounded light spills beneath the animal, not over the whole UI.
            for i in range(3):
                rect=pygame.Rect(0,0,54+i*13,12+i*4);rect.center=foot
                pygame.draw.ellipse(layer, (*colors[0], round((25-i*5)*weight)),rect)
        else:
            burst = math.sin(math.pi*clamp((progress-.58)/.32))
            for i in range(18):
                angle=i*math.tau/18+action.elapsed*.45
                radius=8+burst*(14+(i%4)*3)
                point=spine+pygame.Vector2(math.cos(angle)*radius,
                                          math.sin(angle)*radius*.62)
                self._particle(layer, point, colors, action.channel_to,
                               round(150*burst), i, action.elapsed)
            if .64<progress<.90:
                q=clamp((progress-.64)/.26)
                rect=pygame.Rect(0,0,round(20+q*66),round(6+q*18));rect.center=foot
                pygame.draw.ellipse(layer,(*colors[1],round(120*(1-q))),rect,1)
        target.blit(layer, (0,0))

    @staticmethod
    def _particle(layer, point, colors, element, alpha, index, clock):
        if alpha<=0:return
        x,y=round(point.x),round(point.y);color=(*colors[1+index%2],alpha)
        if element=='ice':
            pygame.draw.line(layer,color,(x-2,y),(x+2,y),1)
            pygame.draw.line(layer,color,(x,y-2),(x,y+2),1)
        elif element=='water':
            pygame.draw.line(layer,color,(x,y-2),(x,y+1),2)
            pygame.draw.line(layer,(*colors[2],alpha),(x,y-1),(x,y),1)
        else:
            pygame.draw.line(layer,color,(x,y),(x+index%2,y-2-index%3),1)


class VespermawChannelAudio:
    """One original 2.5 s cue; freeze/resume the same voice on pause/focus."""
    def __init__(self, game):
        self.game=game;self.action=None;self.voice=None;self.sound=None
        self.sounds={};self.played=False

    def prepare(self):
        """Generate during battle loading, never on the transformation frame."""
        if (not pygame.mixer.get_init()
                or getattr(getattr(self.game,'audio',None),'effects_volume',0)<=0):return
        for element in COLORS:self._sound(element)

    def _sound(self, element):
        rate,fmt,channels=pygame.mixer.get_init()
        key=(element,rate,fmt,channels)
        if key in self.sounds:return self.sounds[key]
        if fmt!=-16:return None
        rng=random.Random('vespermaw-confluence-'+element)
        data=array('h');low=0.;phase=0.
        frames=round(rate*2.5)
        for i in range(frames):
            t=i/rate;q=t/2.5
            envelope=math.sin(math.pi*q)**1.2
            # A low breath and rising harmonic bow lead into a resonant crest.
            phase+=(85+q*q*170)*math.tau/rate
            crest=math.exp(-((t-1.65)/.14)**2)
            raw=rng.uniform(-1,1);low=low*.96+raw*.04
            base=(math.sin(phase)*.15+math.sin(phase*1.502)*.07)*envelope
            if element=='fire':texture=raw*.06*envelope+low*.4*crest
            elif element=='ice':
                texture=(math.sin(t*math.tau*1350)*.025+math.sin(t*math.tau*2011)*.02)*envelope
                texture+=raw*.03*crest
            else:texture=low*.65*envelope+math.sin(t*math.tau*(350+30*math.sin(t*9)))*.025*envelope
            value=base+texture+math.sin(t*math.tau*62)*.18*crest
            for channel in range(channels):
                pan=1 if channels==1 else .85+.15*math.sin(t*2.1+channel*math.pi)
                data.append(round(max(-.8,min(.8,value))*15000*pan))
        sound=pygame.mixer.Sound(buffer=data);self.sounds[key]=sound;return sound

    def sync(self, action, paused=False):
        if action is None or action.action!='vespermaw_attune':
            self.stop();self.action=None;return
        if action is not self.action:
            self.stop();self.action=action;self.played=False
        if paused:
            self.pause();return
        volume=getattr(getattr(self.game,'audio',None),'effects_volume',0)
        if self.voice is not None:
            if self.voice.get_sound() is self.sound:
                self.voice.set_volume(volume*.7);self.voice.unpause()
            else:self.voice=None
        if not self.played:
            self.played=True
            if not pygame.mixer.get_init() or volume<=0:return
            try:
                sound=self._sound(action.channel_to)
                if sound is None:return
                # Slice to the simulation clock if entering partway through.
                rate,_,channels=pygame.mixer.get_init()
                start=round(max(0.,action.elapsed)*rate)*channels*2
                self.sound=pygame.mixer.Sound(buffer=sound.get_raw()[start:])
                self.voice=self.sound.play()
                if self.voice:self.voice.set_volume(volume*.7)
            except (pygame.error,ValueError):self.voice=None

    def pause(self):
        if self.voice is not None and self.voice.get_sound() is self.sound:self.voice.pause()

    def stop(self):
        if self.voice is not None and self.voice.get_sound() is self.sound:self.voice.stop()
        self.voice=None
