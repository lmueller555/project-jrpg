"""Authored, elapsed-time driven Rhea awakening insert for the rescue cinematic.

The camera continues to render the real scene underneath this insert. Its final
reframe registers the illustrated eyes with that scene before the prison breaks.
No assets are loaded while drawing, so pause and gallery seeking are identical.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame


def _phase(value, start, end):
    return max(0.0, min(1.0, (value-start)/(end-start)))


def _smooth(value):
    return value*value*(3.0-2.0*value)


class RheaAwakeningCloseup:
    """A contained upper-body portrait, glass enclosure, and registered eye VFX."""

    START = 15.1
    OPEN = 16.4
    BREAKOUT = 17.3
    # Portrait is smaller than the enclosure: hair and the staff stay inside ice.
    PORTRAIT_SCALE = .70
    PORTRAIT_OFFSET = pygame.Vector2(58, 50)
    EXPRESSION_TIMES = (
        (15.1, 'neutral_closed'), (15.55, 'strain_begin'),
        (15.85, 'strain_mid'), (16.13, 'strain_peak'),
        (16.4, 'opening_01'), (16.53, 'opening_02'),
        (16.67, 'angry_open'), (16.9, 'angry_hold'),
    )

    def __init__(self, asset_root):
        self.asset_root = Path(asset_root)
        self.manifest = json.loads((self.asset_root/'manifest.json').read_text())
        self.size = tuple(self.manifest['canvas'])
        self.frames = {}
        self.eyes = {}
        self._cache = {}
        back = self._load(self.manifest['ice_back'])
        front = self._load(self.manifest['ice_front'])
        # A soft bottom matte is invisible in the close crop, and avoids a hard
        # cut torso edge as the insert recedes into the full-body scene.
        matte = pygame.Surface(self.size, pygame.SRCALPHA)
        matte.fill((255, 255, 255, 255))
        for y in range(414, self.size[1]):
            alpha = round(255*(1-_smooth(_phase(y, 414, self.size[1]-1))))
            pygame.draw.line(matte, (255, 255, 255, alpha), (0,y), (self.size[0],y))
        self.front = front.copy()
        self.front.blit(matte, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        for name, record in self.manifest['frames'].items():
            portrait = self._load(record['file'])
            frame = back.copy()
            portrait = pygame.transform.scale(portrait, (
                round(self.size[0]*self.PORTRAIT_SCALE),
                round(self.size[1]*self.PORTRAIT_SCALE)))
            frame.blit(portrait, self.PORTRAIT_OFFSET)
            frame.blit(matte, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            self.frames[name] = frame
            self.eyes[name] = tuple(
                pygame.Vector2(point)*self.PORTRAIT_SCALE+self.PORTRAIT_OFFSET
                for point in record['eyes'])

    def _load(self, relative):
        path = (self.asset_root/relative).resolve()
        if not path.is_relative_to(self.asset_root.resolve()):
            raise ValueError('Close-up image must remain in its asset directory')
        surface = pygame.image.load(str(path))
        if surface.get_size() != self.size:
            raise ValueError(f'Unregistered Rhea close-up layer: {relative}')
        return surface.convert_alpha() if pygame.display.get_surface() else surface.copy()

    def state(self, elapsed):
        """Return inspectable timing without advancing any animation state."""
        expression = self.EXPRESSION_TIMES[0][1]
        for start, name in self.EXPRESSION_TIMES:
            if elapsed >= start:
                expression = name
        opening = _smooth(_phase(elapsed, self.OPEN, 16.73))
        # A short corneal gleam blooms *with* the opening, never on closed lids.
        gleam_in = _smooth(_phase(elapsed, 16.44, 16.62))
        gleam_out = 1-_smooth(_phase(elapsed, 16.62, 16.88))
        pullback = _smooth(_phase(elapsed, 16.95, self.BREAKOUT))
        opacity = 1-_smooth(_phase(elapsed, 17.04, self.BREAKOUT))
        return {
            'active': self.START <= elapsed < self.BREAKOUT,
            'expression': expression,
            'eyes_closed': elapsed < self.OPEN,
            'openness': self.manifest['frames'][expression]['openness'],
            'eye_glow': opening if elapsed >= self.OPEN else 0.0,
            'gleam_strength': gleam_in*gleam_out if self.OPEN <= elapsed < self.BREAKOUT else 0.0,
            'pullback': pullback,
            'overlay_alpha': opacity,
            'closed_hold_end': self.OPEN,
            'breakout': self.BREAKOUT,
        }

    def geometry(self, canvas_size, elapsed, target_eyes=None, reduced=False,
                 pullback=None):
        """Describe the illustrated-to-world registration for rendering and QA."""
        state = self.state(elapsed)
        source = self.eyes[state['expression']]
        midpoint = (source[0]+source[1])*.5
        width, height = canvas_size
        # The body and ice continue far below the frame throughout the hold.
        advance = _smooth(_phase(elapsed, self.START, 16.95))
        scale = width/400*(1+(0 if reduced else .025*advance))
        destination = pygame.Vector2(width*.5, height*.4)
        angle = 0.0
        amount = state['pullback'] if pullback is None else max(0., min(1., pullback))
        if target_eyes is not None:
            targets = tuple(pygame.Vector2(point) for point in target_eyes)
            target_midpoint = (targets[0]+targets[1])*.5
            source_line = source[1]-source[0]
            target_line = targets[1]-targets[0]
            final_scale = target_line.length()/source_line.length()
            final_angle = math.degrees(math.atan2(source_line.y,source_line.x)
                                       -math.atan2(target_line.y,target_line.x))
            # Geometric interpolation gives a steady lens pullback at this ratio.
            scale = math.exp(math.log(scale)*(1-amount)+math.log(max(.001,final_scale))*amount)
            destination = destination.lerp(target_midpoint,amount)
            angle = final_angle*amount
        center = pygame.Vector2(self.size)*.5
        image_center = destination-(midpoint-center).rotate(-angle)*scale
        mapped = tuple(image_center+(point-center).rotate(-angle)*scale for point in source)
        bottom = image_center+(pygame.Vector2(self.size[0]*.5,self.size[1])-center).rotate(-angle)*scale
        return {'scale':scale, 'angle':angle, 'center':image_center,
                'eyes':mapped, 'bottom':bottom, 'pullback':amount}

    def _transformed(self, key, source, scale, angle):
        size = (max(1,round(self.size[0]*scale)), max(1,round(self.size[1]*scale)))
        rotation = round(angle, 2)
        cache_key = (key,size,rotation)
        if cache_key not in self._cache:
            if len(self._cache) >= 96:
                self._cache.pop(next(iter(self._cache)))
            image = pygame.transform.scale(source,size)
            if abs(rotation) > .01:
                image = pygame.transform.rotate(image,rotation)
            self._cache[cache_key] = image
        return self._cache[cache_key]

    @staticmethod
    def _place(canvas, image, center, alpha):
        if alpha <= 0:
            return
        if alpha < .999:
            image = image.copy()
            image.set_alpha(round(255*alpha))
        canvas.blit(image,image.get_rect(center=(round(center.x),round(center.y))))

    def draw(self, canvas, elapsed, reduced=False, pullback=None, target_eyes=None):
        state = self.state(elapsed)
        if not state['active']:
            return
        layout = self.geometry(canvas.get_size(),elapsed,target_eyes,reduced,pullback)
        expression = state['expression']
        opacity = state['overlay_alpha']
        base = self._transformed(expression,self.frames[expression],layout['scale'],layout['angle'])
        self._place(canvas,base,layout['center'],opacity)
        # Eye light is embedded behind glass; the glass picks up green light too.
        self._eye_light(canvas,layout['eyes'],state,reduced,opacity*.65,behind=True)
        front = self._transformed('front',self.front,layout['scale'],layout['angle'])
        self._place(canvas,front,layout['center'],opacity)
        self._eye_light(canvas,layout['eyes'],state,reduced,1.0,behind=False)
        self._glass_glints(canvas,layout,state,elapsed,reduced,opacity)

    @staticmethod
    def _eye_light(canvas, eyes, state, reduced, opacity, behind=False):
        strength = state['eye_glow']
        if strength <= 0 or opacity <= 0:
            return
        layer = pygame.Surface(canvas.get_size(),pygame.SRCALPHA)
        distance = pygame.Vector2(eyes[0]).distance_to(eyes[1])
        gleam = state['gleam_strength']*(.42 if reduced else 1)
        radius = max(2,round(distance*(.42 if behind else .14)))
        for eye in eyes:
            point = (round(eye.x),round(eye.y))
            if behind:
                for fraction, alpha in ((1.,12),(.72,19),(.4,25)):
                    pygame.draw.circle(layer,(35,255,100,round(alpha*strength*opacity)),
                                       point,max(1,round(radius*fraction)))
            else:
                # Keep the authored angry lids and green irises readable after
                # the gleam. Persistent emission is a narrow iris, not a disk.
                iris_width = max(2,round(distance*.15))
                iris_height = max(1,round(distance*.055))
                iris = pygame.Rect(0,0,iris_width,iris_height)
                iris.center = point
                pygame.draw.ellipse(layer,(81,255,151,round(125*strength*opacity)),iris)
                core = pygame.Rect(0,0,max(1,iris_width//2),max(1,iris_height//2))
                core.center = point
                pygame.draw.ellipse(layer,(190,255,211,round(150*strength*opacity)),core)
                if gleam > .01:
                    length = max(3,round(distance*.64*gleam))
                    alpha = round(235*gleam*opacity)
                    pygame.draw.line(layer,(145,255,188,alpha),(point[0]-length,point[1]),
                                     (point[0]+length,point[1]),1)
                    pygame.draw.line(layer,(220,255,230,alpha),(point[0],point[1]-max(2,length//3)),
                                     (point[0],point[1]+max(2,length//3)),1)
        canvas.blit(layer,(0,0))

    def _glass_glints(self, canvas, layout, state, elapsed, reduced, opacity):
        if opacity < .01:
            return
        layer = pygame.Surface(canvas.get_size(),pygame.SRCALPHA)
        center = pygame.Vector2(self.size)*.5
        def point(x,y):
            p=layout['center']+(pygame.Vector2(x,y)-center).rotate(-layout['angle'])*layout['scale']
            return round(p.x),round(p.y)
        shimmer = .6 if reduced else .6+.15*math.sin((elapsed-self.START)*3.2)
        color=(166,225,255,round(75*shimmer*opacity))
        # Fine glints follow authored pane edges, leaving the eyes unobscured.
        pygame.draw.lines(layer,color,False,[point(92,154),point(81,219),point(58,254)],1)
        pygame.draw.lines(layer,color,False,[point(282,146),point(305,198),point(298,250)],1)
        green = state['eye_glow']*(.35+.65*state['gleam_strength'])
        if green:
            tint=(77,255,166,round(100*green*opacity))
            pygame.draw.line(layer,tint,point(111,170),point(140,149),1)
            pygame.draw.line(layer,tint,point(237,132),point(262,157),1)
        canvas.blit(layer,(0,0))
