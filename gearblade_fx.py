"""Small deterministic effects registered to Caelan's authored gearblade.

The blade, guard and four jewel slots follow the selected drawing and actor
floor position. Nothing is spawned or accumulated between calls, so pause,
seek, interrupted gestures and changes in frame rate produce the same image.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

import pygame

from gear_state import GEM_COLORS, REQUIRED_GEMS
from gearblade_art import prepare_combat_art


PALETTES = {
    'nature': ((38, 99, 66), (99, 204, 124), (214, 247, 164)),
    'water': ((34, 91, 158), (90, 191, 237), (218, 250, 255)),
    'fire': ((148, 48, 45), (245, 128, 54), (255, 230, 148)),
    'ice': ((106, 158, 185), (190, 225, 242), (248, 255, 255)),
    'aether': ((100, 67, 156), (183, 145, 240), (250, 241, 255)),
}


def _get(record, name, default=None):
    return record.get(name, default) if isinstance(record, Mapping) else getattr(record, name, default)


def _clamp(value):
    return max(0., min(1., value))


def _xy(point):
    return round(point[0]), round(point[1])


def _color(color, opacity):
    return (*color, round(255*_clamp(opacity)))


class GearbladeEffects:
    """A fixed local effects layer; call after the equipped actor is drawn.

    ``point`` is the displayed floor anchor. ``time_ms`` selects the authored
    actor drawing, while ``elapsed`` is the scene clock in seconds. ``slot_age``
    is seconds since the latest gem settled, or None. ``action`` accepts a
    BattleAction or a mapping with optional ``unmastered`` presentation hint.
    Aether Edge always uses neutral purple-white energy, for every gem.
    """
    LAYER_SIZE = (176, 176)
    FLOOR = (88, 140)
    MAX_MOTES = 12

    def __init__(self, art=None, scale=2):
        if not math.isfinite(float(scale)) or scale <= 0:raise ValueError('Invalid actor scale')
        self.art = art or prepare_combat_art()
        self.scale = float(scale)
        self._layer = pygame.Surface(self.LAYER_SIZE, pygame.SRCALPHA)

    def sample(self, point, state, time_ms, gem, elapsed, slot_age=None,
               action=None, reduced_motion=False):
        """Describe the current effect without modifying battle or FX state."""
        clocks = [float(time_ms), float(elapsed), float(point[0]), float(point[1])]
        if slot_age is not None:clocks.append(float(slot_age))
        if not all(math.isfinite(value) for value in clocks):raise ValueError('Invalid effects clock or point')
        gem = gem if gem in GEM_COLORS else 'water'
        name = _get(action, 'action', '')
        kind = _get(action, 'kind', '')
        action_age = max(0., float(_get(action, 'elapsed', 0.) or 0.))
        if not math.isfinite(action_age):raise ValueError('Invalid action clock')
        aether = state == 'aether_edge' or name == 'aether_edge'
        failed = kind == 'failed_edge'
        tentative = bool(_get(action, 'unmastered', False)) or failed
        effect = 'aether' if aether else REQUIRED_GEMS.get(name, gem)
        mode = 'aether' if aether else 'failed' if failed else 'tentative' if tentative else 'elemental'
        pose = self.art.anchors(state, time_ms)
        def translate(p):
            return (float(point[0])+(p[0]-self.art.anchor[0])*self.scale,
                    float(point[1])+(p[1]-self.art.anchor[1])*self.scale)
        anchors = {key:translate(pose[key]) for key in ('guard', 'active_gem', 'blade_base', 'blade_tip')}
        anchors['gems'] = {key:translate(value) for key,value in pose['gems'].items()}
        active = bool(name) and not failed
        strength = .28 if not active else .66
        if tentative:strength *= .42
        if state == 'hurt':strength *= .35
        if state == 'defeat':strength = 0.
        # A contact accent is tied to the existing 500 ms battle impact. No
        # model cost, hit count, duration or damage timing is changed here.
        contact = max(0., 1-abs(action_age-.5)/.115) if aether and action is not None else 0.
        if reduced_motion:contact = .55 if aether and .48 <= action_age <= .62 else 0.
        return dict(effect=effect, mode=mode, gem=gem, anchors=anchors,
                    strength=strength, contact=contact, action_age=action_age,
                    clock=0. if reduced_motion else max(0.,float(elapsed)),
                    slot_age=slot_age, reduced_motion=bool(reduced_motion),
                    visible=state != 'defeat', active=active)

    def _local(self, sample, point):
        offset = pygame.Vector2(self.FLOOR)-point
        result = {key:pygame.Vector2(sample['anchors'][key])+offset
                  for key in ('guard','active_gem','blade_base','blade_tip')}
        result['gems'] = {key:pygame.Vector2(value)+offset
                          for key,value in sample['anchors']['gems'].items()}
        return result

    def _jewels(self, layer, anchors, sample):
        clock = sample['clock']
        aether = sample['effect'] == 'aether'
        for gem,point in anchors['gems'].items():
            active = aether or gem == sample['gem']
            color = PALETTES['aether'][1] if aether else GEM_COLORS[gem]
            strength = (.36 if active else .10) * (.6 if sample['mode']=='failed' else 1.)
            if active:
                radius = 3 if sample['reduced_motion'] else 3+int(math.sin(clock*3.4)>.6)
                pygame.draw.circle(layer,_color(color,strength*.25),_xy(point),radius+2)
            # Small facets preserve legibility at the native two-times scale.
            pygame.draw.polygon(layer,_color(color,strength+.25),
                                [_xy(point+v) for v in ((0,-2),(2,0),(0,2),(-2,0))])
            if active:pygame.draw.line(layer,_color((251,249,230),.78),_xy(point+(-1,-1)),_xy(point),1)
        if sample['slot_age'] is not None and 0 <= sample['slot_age'] < .56:
            age = sample['slot_age']/.56
            point = anchors['gems'][sample['gem']]
            color = PALETTES['aether'][1] if aether else GEM_COLORS[sample['gem']]
            if not sample['reduced_motion']:
                for i in range(6):
                    angle = i*math.tau/6-age*.8
                    p = point+pygame.Vector2(math.cos(angle),math.sin(angle))*(3+age*8)
                    pygame.draw.line(layer,_color(color,(1-age)*.65),_xy(p),_xy(p+pygame.Vector2(math.cos(angle),math.sin(angle))*2),1)
            pygame.draw.circle(layer,_color(color,(1-age)*.6),_xy(point),3,1)

    @staticmethod
    def _basis(anchors):
        start,end = anchors['blade_base'],anchors['blade_tip']
        delta = end-start
        direction = delta.normalize() if delta.length_squared() else pygame.Vector2(-1,0)
        return start,end,direction,pygame.Vector2(-direction.y,direction.x)

    def _blade(self, layer, anchors, sample):
        start,end,direction,normal = self._basis(anchors)
        dark,mid,light = PALETTES[sample['effect']]
        strength = sample['strength']
        clock = sample['clock']
        # A very thin edge leaves the authored metal, silhouette and body
        # unobscured. Larger detail only appears in short action bursts.
        pygame.draw.line(layer,_color(dark,strength*.28),_xy(start),_xy(end),5)
        pygame.draw.line(layer,_color(mid,strength*.7),_xy(start+normal),_xy(end+normal),2)
        pygame.draw.line(layer,_color(light,strength*.8),_xy(start-normal),_xy(end-normal),1)
        if sample['effect'] == 'nature':
            for side in (-1,1):
                vine = [start.lerp(end,i/8)+normal*(side*1.8+math.sin(i*.9+clock*2.2)*1.1) for i in range(9)]
                pygame.draw.lines(layer,_color(mid,strength*.8),False,[_xy(p) for p in vine],1)
                for i in (2,5,7):
                    p=vine[i]; tip=p+normal*side*3-direction
                    pygame.draw.polygon(layer,_color(light,strength*.65),[_xy(p-direction),_xy(tip),_xy(p+direction)])
        elif sample['effect'] == 'water':
            for side in (-1,1):
                ribbon = [start.lerp(end,i/10)+normal*math.sin(i*.65-clock*2.7+side*1.4)*2.5 for i in range(11)]
                pygame.draw.lines(layer,_color(mid,strength*.7),False,[_xy(p) for p in ribbon],1)
            p=start.lerp(end,(clock*.34+.3)%1)+normal*2
            pygame.draw.circle(layer,_color(light,strength*.8),_xy(p),1)
        elif sample['effect'] == 'fire':
            for i in range(5):
                p=start.lerp(end,(i+.5)/5)
                lift=2+math.sin(clock*6+i*1.8)*1.1
                tip=p+pygame.Vector2(-1,-lift)
                pygame.draw.polygon(layer,_color(mid,strength*.8),[_xy(p-direction*2),_xy(tip),_xy(p+direction*2)])
                pygame.draw.line(layer,_color(light,strength*.8),_xy(p),_xy(tip),1)
        elif sample['effect'] == 'ice':
            for i in (1,3,5):
                p=start.lerp(end,i/6)
                side=-1 if i==3 else 1
                pygame.draw.lines(layer,_color(light,strength*.85),False,[_xy(p-direction),_xy(p+normal*side*3),_xy(p+direction)],1)
                pygame.draw.line(layer,_color(mid,strength*.7),_xy(p),_xy(p-normal*side*2),1)
        else:
            for i in range(3):
                p=start.lerp(end,(clock*.55+i/3)%1)
                self._glint(layer,p,light,strength*.8,2)

    @staticmethod
    def _glint(layer, point, color, opacity, size=2):
        pygame.draw.line(layer,_color(color,opacity),_xy(point+(-size,0)),_xy(point+(size,0)),1)
        pygame.draw.line(layer,_color(color,opacity),_xy(point+(0,-size)),_xy(point+(0,size)),1)

    def _motes(self, layer, anchors, sample):
        start,end,direction,normal = self._basis(anchors)
        dark,mid,light = PALETTES[sample['effect']]
        count = 3 if sample['reduced_motion'] else 7 if sample['active'] else 4
        if sample['mode']=='tentative':count = min(count,3)
        for index in range(min(self.MAX_MOTES,count)):
            age = .35+index*.16 if sample['reduced_motion'] else (sample['clock']*.55+index*.237)%1
            p=start.lerp(end,(index*.413+.18)%1)
            spread = 1.5+age*(5 if sample['active'] else 3)
            p += normal*math.sin(index*2.4+age*2)*spread
            opacity=sample['strength']*(1-age)*.72
            if sample['effect']=='nature':
                p+=pygame.Vector2(-age*2,-age*3)
                pygame.draw.polygon(layer,_color(mid,opacity),[_xy(p+(-2,0)),_xy(p+(1,-2)),_xy(p+(2,1)),_xy(p)])
                pygame.draw.line(layer,_color(light,opacity*.8),_xy(p),_xy(p+(1,-1)),1)
            elif sample['effect']=='water':
                p+=pygame.Vector2(0,age*3)
                pygame.draw.polygon(layer,_color(mid,opacity),[_xy(p+(0,-2)),_xy(p+(1,1)),_xy(p+(-1,1))])
                pygame.draw.line(layer,_color(light,opacity),_xy(p),_xy(p+(0,1)),1)
            elif sample['effect']=='fire':
                p+=pygame.Vector2(math.sin(index+age*3)*2,-age*6)
                pygame.draw.line(layer,_color(mid,opacity),_xy(p),_xy(p+(0,2)),1)
                pygame.draw.circle(layer,_color(light,opacity),_xy(p),1)
            else:
                p+=pygame.Vector2(-age*2,-age*2)
                self._glint(layer,p,light,opacity,1+index%2)

    def _sputter(self, layer, anchors, sample):
        age=sample['action_age']
        if age>.70:return
        _,mid,light=PALETTES[sample['effect']]
        envelope=math.sin(math.pi*_clamp(age/.70))*.55
        p=anchors['blade_base']
        if sample['reduced_motion']:
            self._glint(layer,p,mid,envelope,2)
            return
        for i in range(5):
            phase=_clamp((age-i*.045)/.42)
            if not 0<phase<1:continue
            point=p+pygame.Vector2(-2-phase*(3+i),-math.sin(phase*math.pi)*(3+i*.8)+phase*5)
            pygame.draw.line(layer,_color(mid,envelope*(1-phase)),_xy(point),_xy(point+(1,2)),1)
            if i%2==0:pygame.draw.circle(layer,_color(light,envelope*(1-phase)),_xy(point),1)

    def _aether(self, layer, anchors, sample):
        start,end,direction,normal=self._basis(anchors)
        _,mid,light=PALETTES['aether']
        age=sample['action_age']
        gather=_clamp(age/.5) if age<.5 else _clamp((.9-age)/.4)
        if age<.5:
            count=3 if sample['reduced_motion'] else 8
            for i in range(count):
                angle=i*2.399963+sample['clock']*2
                radius=(1-gather)*9+3
                p=anchors['guard']+pygame.Vector2(math.cos(angle),math.sin(angle))*radius
                self._glint(layer,p,mid,gather*.55,1)
        contact=sample['contact']
        if contact>0:
            # Two compact sword-aligned streaks make the contact frame clear,
            # without a screen flash, actor shake or elemental hue.
            for side in (-1,1):
                pygame.draw.line(layer,_color(mid,contact*.8),_xy(start+normal*side*3),_xy(end+direction*5+normal*side*2),2)
            pygame.draw.line(layer,_color(light,contact),_xy(start),_xy(end+direction*7),2)
            self._glint(layer,end+direction*3,light,contact,4 if not sample['reduced_motion'] else 2)

    def draw(self, canvas, point, state, time_ms, gem, elapsed, slot_age=None,
             action=None, reduced_motion=False):
        sample=self.sample(point,state,time_ms,gem,elapsed,slot_age,action,reduced_motion)
        if not sample['visible']:return sample
        layer=self._layer
        layer.fill((0,0,0,0))
        local=self._local(sample,pygame.Vector2(point))
        self._jewels(layer,local,sample)
        if sample['mode']=='failed':self._sputter(layer,local,sample)
        else:
            self._blade(layer,local,sample)
            self._motes(layer,local,sample)
            if sample['effect']=='aether':self._aether(layer,local,sample)
        canvas.blit(layer,(round(point[0]-self.FLOOR[0]),round(point[1]-self.FLOOR[1])))
        return sample
