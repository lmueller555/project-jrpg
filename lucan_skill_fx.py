"""Lucan's command gestures and compact, clocked support/taunt effects.

No extra combat actor or interactable is introduced. Effects follow the real
skill action and its recipients; status badges sample model-owned durations.
"""
import math

import pygame


SKILLS = frozenset(('inspire', 'bolster', 'provoke'))
COLORS = {'inspire': (243, 199, 101), 'bolster': (114, 196, 231),
          'provoke': (232, 119, 91)}


def icon(target, key, position, color):
    """Native seven-pixel sword, shield and challenge emblems."""
    x, y = map(round, position)
    if key == 'inspire':
        pygame.draw.line(target, color, (x+1,y+6), (x+6,y+1), 1)
        pygame.draw.line(target, color, (x+1,y+3), (x+4,y+6), 1)
        pygame.draw.line(target, color, (x,y+7), (x+1,y+6), 2)
        pygame.draw.line(target, color, (x+5,y+1), (x+6,y+1), 1)
    elif key == 'bolster':
        pygame.draw.polygon(target,color,[(x,y+1),(x+3,y),(x+6,y+1),
            (x+5,y+5),(x+3,y+7),(x+1,y+5)],1)
        pygame.draw.line(target,color,(x+3,y+1),(x+3,y+5),1)
    else:
        pygame.draw.circle(target,color,(x+3,y+3),3,1)
        pygame.draw.line(target,color,(x+3,y-1),(x+3,y+7),1)
        pygame.draw.line(target,color,(x-1,y+3),(x+7,y+3),1)


class LucanSkillEffects:
    def __init__(self):
        self.layer = pygame.Surface((480,320), pygame.SRCALPHA)

    def draw(self, target, action, positions, hit_point, bounds, *, reduced_motion=False):
        if action is None or action.actor != 'lucan' or action.action not in SKILLS:return
        key = action.action
        color = COLORS[key]
        layer = self.layer
        layer.fill((0,0,0,0));layer.set_clip(bounds)
        origin = pygame.Vector2(hit_point('lucan'))
        q = min(1., action.elapsed/max(.01,action.duration))
        impact = action.impact_at/max(.01,action.duration)
        # Lucan's own contracted gesture is readable before its effect reaches
        # the party. Preparation has no floating weapon or unattached tool.
        prep = min(1.,q/max(.01,impact))
        if q < impact:
            radius = 4+round(7*prep)
            pygame.draw.circle(layer,(*color,round(90*prep)),origin,radius,1)
            if not reduced_motion:
                for number in range(5):
                    angle = number*math.tau/5-action.elapsed*2
                    point = origin+pygame.Vector2(math.cos(angle),math.sin(angle))*(radius+2)
                    pygame.draw.line(layer,(*color,140),point,point+(0,-2),1)
        else:
            release = min(1.,(q-impact)/max(.01,1-impact))
            alpha = round(180*(1-release))
            for identifier in action.targets:
                if identifier not in positions:continue
                point = pygame.Vector2(hit_point(identifier))
                if key == 'provoke':
                    if reduced_motion:
                        icon(layer,key,point+(-3,-3),(*color,alpha))
                    else:
                        delta = point-origin
                        end = origin+delta*min(1.,release*3)
                        pygame.draw.line(layer,(*color,round(alpha*.35)),origin,end,1)
                        icon(layer,key,point+(-3,-3),(*color,alpha))
                        for side in (-1,1):
                            x=point.x+side*(10+release*7)
                            pygame.draw.line(layer,(*color,alpha),(x,point.y-5),(x-side*3,point.y),1)
                elif key == 'inspire':
                    for line in range(3):
                        x=point.x+(line-1)*8
                        y=point.y+12-(0 if reduced_motion else release*19)
                        pygame.draw.lines(layer,(*color,alpha),False,
                            [(x-3,y),(x,y-4),(x+3,y)],1)
                    icon(layer,key,point+(-3,-6),(*color,alpha))
                else:
                    center=point+pygame.Vector2(0,3)
                    pygame.draw.polygon(layer,(*color,round(alpha*.22)),
                        [(center.x-12,center.y-10),(center.x,center.y-14),
                         (center.x+12,center.y-10),(center.x+9,center.y+7),
                         (center.x,center.y+14),(center.x-9,center.y+7)])
                    pygame.draw.polygon(layer,(*color,alpha),
                        [(center.x-12,center.y-10),(center.x,center.y-14),
                         (center.x+12,center.y-10),(center.x+9,center.y+7),
                         (center.x,center.y+14),(center.x-9,center.y+7)],1)
        target.blit(layer,(0,0))
