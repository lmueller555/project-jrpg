"""Deterministic world-space fire, wind and ice accents for Rhea's duel.

The fireballs use eight authored drawings. Their birth sites are registered to
the six gold diamond patterns in the existing rune; no effect moves that rune.
"""
from __future__ import annotations

from collections import OrderedDict
import json
import math
from pathlib import Path

import pygame

from ice_reaper_action import V3, phase, smooth


ROOT = Path(__file__).resolve().parent
TAU = math.tau
FIREBALL_TIMES = tuple(25.8+index*.15 for index in range(6))
FIREBALL_ANCHORS = tuple(
    (-3+math.cos(-math.pi/2+index*TAU/6)*8.2*.78,.035,
     math.sin(-math.pi/2+index*TAU/6)*8.2*.78)
    for index in range(6))


class IceReaperDuelFX:
    WIND_START = 24.
    WIND_END = 25.15
    SWORD_START = 25.70
    SWORD_END = 26.50
    CHARGE_START = 30.30
    CHARGE_END = 31.65

    def __init__(self, stage, asset_root=None):
        self.stage = stage
        self.asset_root = Path(asset_root or ROOT/'assets/story/ice_reaper_duel/fx')
        self.manifest = json.loads((self.asset_root/'animation.json').read_text())
        self.frames = tuple(pygame.image.load(str(self.asset_root/record['file'])).convert_alpha()
                            for record in self.manifest['animations']['fireball']['frames'])
        if len(self.frames) != 8 or len(self.manifest['fireball_anchors']) != 6:
            raise ValueError('The duel needs eight authored flame drawings at six rune points')
        self.anchors = tuple(V3(record['world']) for record in self.manifest['fireball_anchors'])
        self.times = FIREBALL_TIMES
        self._cache = OrderedDict()

    @staticmethod
    def _polyline(layer, camera, color, points, width=1):
        projected = [camera.project(point) for point in points]
        if all(point is not None for point in projected):
            pygame.draw.lines(layer,color,False,[(round(p[0]),round(p[1])) for p in projected],width)

    @staticmethod
    def _ring(layer, camera, center, radius, color, width=1):
        points = [V3(center)+V3(math.cos(i*TAU/32)*radius,0,
                                math.sin(i*TAU/32)*radius) for i in range(33)]
        IceReaperDuelFX._polyline(layer,camera,color,points,width)

    def _scaled_flame(self, index, scale):
        source = self.frames[index]
        size = tuple(max(1,min(640,round(value*scale))) for value in source.get_size())
        key = index,size
        if key in self._cache:
            image = self._cache.pop(key)
            self._cache[key] = image
            return image
        image = pygame.transform.scale(source,size)
        self._cache[key] = image
        if len(self._cache)>128:
            self._cache.popitem(last=False)
        return image

    def fireball_state(self, time):
        result=[]
        for index,(anchor,birth) in enumerate(zip(self.anchors,self.times)):
            rise = smooth(phase(time,birth,birth+.15))
            active = time>=birth
            height = .18+1.22*rise
            if active:
                height += math.sin((time-birth)*3.2+index*.7)*.055*rise
            result.append(dict(index=index,active=active,birth=birth,
                               ground=list(anchor),position=list(anchor+V3(0,height,0)),
                               rise=rise,diameter=.12+1.08*rise))
        return result

    def state(self, time):
        return dict(fireballs=self.fireball_state(time),
                    authored_frames=len(self.frames),rune_tip_count=len(self.anchors),
                    wind=self.WIND_START<=time<self.WIND_END+.4,
                    sword_condensation=self.SWORD_START<=time<self.SWORD_END+.25,
                    charging=self.CHARGE_START<=time<self.CHARGE_END+.2,
                    fixed_rune_radius=8.2)

    def draw_ground(self, canvas, camera, time, positions, reduced=False):
        layer = pygame.Surface(canvas.get_size(),pygame.SRCALPHA)
        for record in self.fireball_state(time):
            if not record['active']:
                continue
            center = V3(record['ground'])+V3(0,.025,0)
            strength = .25+.75*record['rise']
            for radius,alpha in ((1.18,15),(.85,24),(.55,40)):
                points = [camera.project(center+V3(math.cos(i*TAU/24)*radius,0,
                                                    math.sin(i*TAU/24)*radius)) for i in range(24)]
                if all(points):
                    pygame.draw.polygon(layer,(255,94,31,round(alpha*strength)),
                                        [(round(p[0]),round(p[1])) for p in points])
            self._ring(layer,camera,center,.43+.12*record['rise'],
                       (255,194,98,round(135*strength)),1)
        # Expanding, grounded snow pressure marks the origin of the staff gust.
        if self.WIND_START<=time<self.WIND_START+.7 and not reduced:
            age = phase(time,self.WIND_START,self.WIND_START+.7)
            center = V3(positions['rhea'])+V3(0,.05,0)
            self._ring(layer,camera,center,.5+age*5.8,
                       (198,239,255,round(140*(1-age))),2)
        canvas.blit(layer,(0,0))

    def _wind(self, canvas, camera, time, positions, reduced):
        if not self.WIND_START<=time<self.WIND_END+.4:
            return
        layer = pygame.Surface(canvas.get_size(),pygame.SRCALPHA)
        origin = V3(positions['rhea'])+V3(0,.55,0)
        direction = V3(positions['mira'])-V3(positions['rhea'])
        direction.y = 0
        direction = direction.normalize()
        side = V3(direction.z,0,-direction.x)
        count = 24 if reduced else 128
        for index in range(count):
            birth = self.WIND_START+(index%13)*.045
            age = time-birth
            if not 0<=age<.92:
                continue
            speed = 10.+index%7*1.2
            lateral = math.sin(index*7.17)*(.35+age*2.6)
            height = (index%9)/9*.9+math.sin(age/.92*math.pi)*.85
            point = origin+direction*(age*speed)+side*lateral+V3(0,height-.35,0)
            projected = camera.project(point)
            tail = camera.project(point-direction*(.28+index%4*.13))
            if projected is None or tail is None:
                continue
            opacity = max(0.,min(1.,age/.06))*(1-age/.92)
            color = (214,244,255,round(190*opacity))
            width = 1 if reduced else 1+int(index%8==0)
            pygame.draw.line(layer,(85,147,181,round(130*opacity)),
                             (round(tail[0]),round(tail[1])+1),
                             (round(projected[0]),round(projected[1])+1),width)
            pygame.draw.line(layer,color,(tail[0],tail[1]),(projected[0],projected[1]),width)
            if index%5==0:
                r = max(1,min(4,round(camera.focal/projected[2]*.05)))
                pygame.draw.polygon(layer,(235,251,255,round(220*opacity)),
                                    [(projected[0],projected[1]-r),
                                     (projected[0]+r,projected[1]),
                                     (projected[0],projected[1]+r),
                                     (projected[0]-r,projected[1])])
        if not reduced:
            for index in range(11):
                birth = self.WIND_START+index*.048
                age = time-birth
                if not 0<=age<.95:
                    continue
                base = origin+side*math.sin(index*2.4)*(.6+age)
                points = [base+direction*(age*12.-step*.3)+
                          side*(math.sin(step*.6+age*5+index)*.17)+
                          V3(0,math.cos(step*.4+index)*.14+(index%3)*.23,0)
                          for step in range(7)]
                self._polyline(layer,camera,(181,230,249,round(130*(1-age/.95))),points,2)
        canvas.blit(layer,(0,0))

    def _conjure(self, canvas, camera, time, positions, reduced):
        if not self.SWORD_START<=time<self.SWORD_END+.25:
            return
        layer = pygame.Surface(canvas.get_size(),pygame.SRCALPHA)
        progress = phase(time,self.SWORD_START,self.SWORD_END)
        hand = V3(positions.get('reaper_sword_hand',V3(positions['ice_reaper'])+V3(-.55,2.7,-.1)))
        count = 12 if reduced else 36
        for index in range(count):
            angle = index*2.399963+progress*2.4
            radius = (1-progress)*1.6+.15
            point = hand+V3(math.cos(angle)*radius,
                            ((index%9)/9-.5)*1.3*(1-progress),math.sin(angle)*radius)
            p=camera.project(point)
            if p is None:
                continue
            r=max(1,min(4,round(camera.focal/p[2]*.035)))
            pygame.draw.polygon(layer,(189,237,255,round(150*(1-progress*.6))),
                                [(p[0],p[1]-r*1.7),(p[0]+r,p[1]),
                                 (p[0],p[1]+r*1.7),(p[0]-r,p[1])])
        center=camera.project(hand)
        if center is not None:
            radius=max(2,round(camera.focal/center[2]*(.15+.25*math.sin(progress*math.pi))))
            pygame.draw.circle(layer,(169,230,255,55),(round(center[0]),round(center[1])),radius)
        canvas.blit(layer,(0,0))

    def draw_air(self, canvas, camera, time, positions, reduced=False, front=None):
        if front is not True:
            self._wind(canvas,camera,time,positions,reduced)
        if front is not False:
            self._conjure(canvas,camera,time,positions,reduced)
        rhea = camera.project(positions['rhea'])
        visible=[]
        for record in self.fireball_state(time):
            if not record['active']:
                continue
            point=V3(record['position'])
            if reduced:
                point.y=.18+1.22*record['rise']
            projected=camera.project(point)
            if projected is None:
                continue
            near = rhea is not None and projected[2]<rhea[2]
            if front is not None and near != front:
                continue
            visible.append((projected[2],record,point,projected))
        for _,record,point,projected in sorted(visible,reverse=True,key=lambda item:item[0]):
            index = (int((time-record['birth'])/.085)+record['index'])%8
            if reduced:
                index=record['index']%8
            scale=camera.focal*record['diameter']/projected[2]/self.manifest['core_pixels']
            image=self._scaled_flame(index,scale)
            ax,ay=self.manifest['anchor']
            canvas.blit(image,(round(projected[0]-ax*scale),round(projected[1]-ay*scale)))
            if not reduced:
                layer=pygame.Surface(canvas.get_size(),pygame.SRCALPHA)
                for spark in range(5):
                    age=((time-record['birth'])*.7+spark*.2+record['index']*.13)%1
                    angle=spark*2.399+record['index']
                    ember=V3(record['ground'])+V3(math.sin(angle)*age*.5,
                            .15+age*2.5,math.cos(angle)*age*.5)
                    p=camera.project(ember)
                    if p is not None:
                        pygame.draw.circle(layer,(255,182,62,round(200*(1-age))),
                                           (round(p[0]),round(p[1])),1)
                canvas.blit(layer,(0,0))

    def draw_overlay(self, canvas, camera, time, positions, reduced=False):
        if not self.CHARGE_START<=time<self.CHARGE_END+.2:
            return
        progress=phase(time,self.CHARGE_START,self.CHARGE_END)
        if reduced:
            return
        layer=pygame.Surface(canvas.get_size(),pygame.SRCALPHA)
        target = camera.project(V3(positions['ice_reaper'])+V3(0,2.8,0))
        center = (canvas.get_width()*.5,canvas.get_height()*.46) if target is None else target[:2]
        center=(max(-80,min(canvas.get_width()+80,center[0])),
                max(-60,min(canvas.get_height()+60,center[1])))
        for index in range(58):
            angle=index*2.399963
            lane=(time*1.8+index*.137)%1
            radius=95+lane*300
            length=(18+index%7*7)*(.3+.7*progress)
            a=(center[0]+math.cos(angle)*radius,center[1]+math.sin(angle)*radius*.75)
            b=(center[0]+math.cos(angle)*(radius+length),
               center[1]+math.sin(angle)*(radius+length)*.75)
            color=(182,229,255,round((50+progress*120)*(1-lane*.35)))
            pygame.draw.line(layer,color,a,b,1+int(index%9==0))
        # One restrained icy lens wash accompanies the final close approach.
        wash=math.exp(-((progress-.78)/.14)**2)
        if wash>.01:
            layer.fill((145,208,249,round(wash*38)),special_flags=pygame.BLEND_RGBA_ADD)
        canvas.blit(layer,(0,0))

    def draw_back(self, canvas, camera, time, positions, reduced=False):
        self.draw_ground(canvas,camera,time,positions,reduced)
        self.draw_air(canvas,camera,time,positions,reduced,front=False)

    def draw_front(self, canvas, camera, time, positions, reduced=False):
        self.draw_air(canvas,camera,time,positions,reduced,front=True)
        self.draw_overlay(canvas,camera,time,positions,reduced)
