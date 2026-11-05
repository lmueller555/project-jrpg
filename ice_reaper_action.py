"""The Ice Reaper rescue: a deterministic, perspective-projected pixel stage.

All actors, contacts, debris and the ground rune share one world.  The camera
moves around that world; authored scenic plates supply the distant landscape.
The caller owns the real-time clock, dialogue, music and playback lifecycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import math
from pathlib import Path

import pygame
import numpy as np

SIZE = (480, 320)
V3 = pygame.Vector3
TAU = math.tau


def clamp(value, low=0., high=1.):
    return max(low, min(high, value))


def smooth(value):
    value = clamp(value)
    return value*value*(3-2*value)


def phase(time, start, end):
    return clamp((time-start)/(end-start))


def lerp(a, b, amount):
    return V3(a).lerp(V3(b), clamp(amount))


@dataclass(frozen=True)
class PerspectiveCamera:
    position: tuple
    target: tuple
    focal: float = 245.
    center: tuple = (240., 158.)

    def basis(self):
        forward = (V3(self.target)-V3(self.position)).normalize()
        right = forward.cross(V3(0, 1, 0)).normalize()
        up = right.cross(forward).normalize()
        return right, up, forward

    def project(self, point):
        right, up, forward = self.basis()
        relative = V3(point)-V3(self.position)
        depth = relative.dot(forward)
        if depth <= .12:
            return None
        return (self.center[0]+relative.dot(right)*self.focal/depth,
                self.center[1]-relative.dot(up)*self.focal/depth, depth)


SHOTS = (
    (5., 7., 'reaper_launch'), (7., 7.5, 'rescue_dash'),
    (7.5, 9.5, 'slow_motion_rescue'), (9.5, 11., 'rescue_orbit'),
    (11., 12.8, 'mira_loading'), (12.8, 14.2, 'launcher_sight'),
    (14.2, 15.1, 'second_shard_intercept'), (15.1, 16.3, 'rhea_awakens'),
    (16.3, 17.2, 'prison_release'), (17.2, 20., 'rune_panorama'))


class IceReaperActionStage:
    """Render absolute time 5–20 seconds, without advancing mutable state."""

    def __init__(self, asset_root, *, strict=False):
        self.asset_root = Path(asset_root)
        self.repository = Path(__file__).resolve().parent
        self.opening = self.repository/'assets/story/ice_reaper_opening'
        self.images = {}
        self.actors = {}
        self.missing_assets = []
        self._scaled = {}
        self._load()
        if strict:
            self.validate_assets()

    def _read_image(self, path):
        path = Path(path)
        if path not in self.images:
            self.images[path] = pygame.image.load(str(path)).convert_alpha()
        return self.images[path]

    def _load(self):
        required = {
            'caelan': ('ready', 'dash', 'slash', 'land'),
            'lucan': ('dash', 'brace', 'impact'),
            'mira': ('raise', 'load', 'aim', 'fire'),
            'rhea': ('release', 'eyes'),
            'ice_reaper': ('aim', 'launch', 'recharge')}
        for actor, actions in required.items():
            folder = self.asset_root/'actors'/actor
            path = folder/'animation.json'
            if path.exists():
                manifest = json.loads(path.read_text())
                sequences = {}
                for key, entry in manifest['animations'].items():
                    frames = entry['frames'] if isinstance(entry, dict) else entry
                    sequences[key] = [(self._read_image(folder/frame['file']),
                                       frame.get('duration_ms', 100)/1000)
                                      for frame in frames]
                    if not sequences[key]:
                        raise ValueError(f'Empty rescue action: {actor}/{key}')
                anchor = tuple(manifest['anchor'])
                nominal = manifest.get('body_pixels', 155 if actor == 'ice_reaper' else 82)
                self.actors[actor] = dict(sequences=sequences, anchor=anchor,
                                          body_pixels=nominal, manifest=manifest)
                for action in actions:
                    if action not in sequences:
                        self.missing_assets.append(f'{actor}/{action}')
            else:
                self.missing_assets.append(f'{actor}/animation.json')
                if actor == 'ice_reaper':
                    source = self.opening/'actors/ice_reaper/charge.png'
                    image = self._read_image(source)
                    anchor = (image.get_width()/2, image.get_height()-8)
                else:
                    folder = self.repository/'assets/combat'/actor
                    manifest = json.loads((folder/'animation.json').read_text())
                    image = self._read_image(folder/'idle_01.png')
                    anchor = tuple(manifest['anchor'])
                self.actors[actor] = dict(sequences={key: [(image, .1)] for key in actions},
                                          anchor=anchor, body_pixels=image.get_bounding_rect().height,
                                          manifest={})
        self.plates = {}
        for key in ('rescue', 'reverse', 'aerial'):
            path = self.asset_root/'environment'/f'{key}.png'
            if not path.exists():
                self.missing_assets.append(f'environment/{key}.png')
                path = self.opening/'environment.png'
            self.plates[key] = pygame.transform.scale(self._read_image(path), (640, 427))
        self.prison_back = self._read_image(self.opening/'ice_prison_back.png')
        self.prison_front = self._read_image(self.opening/'ice_prison_front.png')
        self.shard = self._read_image(self.opening/'glacial_shard.png')
        ground_path = self.asset_root/'environment/ground.png'
        self.ground_texture = pygame.surfarray.array3d(self._read_image(ground_path)) if ground_path.exists() else None
        self._screen_x = np.arange(480, dtype=np.float32)[:,None]
        self._screen_y = np.arange(320, dtype=np.float32)[None,:]
        self.scope = None
        for path in (self.asset_root/'props/launcher_scope.png',
                     self.asset_root/'launcher_scope.png'):
            if path.exists():
                self.scope = self._read_image(path)
                break

    def validate_assets(self):
        if self.missing_assets:
            raise ValueError('Missing authored rescue assets: '+', '.join(self.missing_assets))
        required = {'caelan':('ready','dash','slash','land'), 'lucan':('dash','brace','impact'),
                    'mira':('raise','load','aim','fire'), 'rhea':('eyes','release'),
                    'ice_reaper':('aim','launch','recharge')}
        for actor, actions in required.items():
            for action in actions:
                count=len(self.actors[actor]['sequences'][action])
                if not 4 <= count <= 10:
                    raise ValueError(f'Rescue action requires 4–10 drawings: {actor}/{action}')

    def reset(self):
        # The entire visual state is a pure function of elapsed time.
        pass

    @staticmethod
    def shot(time):
        return next((name for start, end, name in SHOTS if start <= time < end),
                    'rune_panorama' if time >= 20 else 'opening')

    @staticmethod
    def actor_positions(time):
        dash = 1-(1-phase(time, 7.02, 7.5))**3
        slash = smooth(phase(time, 8.5, 9.25))
        caelan = lerp((4.7, 0, 8), (-1.5, 0, 1.25), dash)
        if time >= 7.5:
            caelan = lerp((-1.5, 0, 1.25), (-5.3, 0, -.7), slash)
        return {
            'rhea': V3(-3, 0, 0), 'caelan': caelan,
            'lucan': lerp((6.5, 0, 8), (-.8, 0, 1.15), dash),
            'mira': V3(7, 0, 10), 'ice_reaper': V3(2, 6.6, -8)}

    @classmethod
    def camera(cls, time, reduced_motion=False):
        shot = cls.shot(time)
        rescue_position = (7., 4.7, 15.)
        rescue_target = (-1.7, 1.9, .5)
        orbit_center = V3(-2, 1.7, 1)
        orbit_radius = V3(rescue_position)-orbit_center
        end_position = orbit_center+V3(-orbit_radius.x, orbit_radius.y, -orbit_radius.z)
        if shot == 'reaper_launch':
            return PerspectiveCamera((0, 8.6, 1.7), (2, 9.3, -8), 272)
        if shot in ('rescue_dash', 'slow_motion_rescue'):
            return PerspectiveCamera(rescue_position, rescue_target, 650)
        if shot == 'rescue_orbit':
            p = 1. if reduced_motion else smooth(phase(time, 9.5, 11))
            angle = p*math.pi
            x = orbit_radius.x*math.cos(angle)+orbit_radius.z*math.sin(angle)
            z = -orbit_radius.x*math.sin(angle)+orbit_radius.z*math.cos(angle)
            return PerspectiveCamera(tuple(orbit_center+V3(x, orbit_radius.y+math.sin(angle)*2, z)),
                                     tuple(lerp(rescue_target, (2.2, 1.7, 6), smooth(p))), 650-400*p)
        if shot == 'mira_loading':
            p = 1. if reduced_motion else smooth(phase(time, 11, 12.3))
            return PerspectiveCamera(tuple(lerp(end_position, (4.6, 2.5, 5.8), p)),
                                     tuple(lerp((2.2, 1.7, 6), (7, 1.45, 10), p)), 250+5*p)
        if shot in ('launcher_sight', 'second_shard_intercept'):
            p = 1. if reduced_motion else smooth(phase(time, 12.8, 14.05))
            angle = -2.62+p*math.pi
            position = V3(7+math.sin(angle)*4.2, 2.5, 10+math.cos(angle)*4.2)
            position = lerp((4.6, 2.5, 5.8), position, min(1, p*4))
            target = lerp((7, 1.45, 10), (2.1, 11.4, -8), 1. if reduced_motion else smooth(phase(time, 13, 14.05)))
            return PerspectiveCamera(tuple(position), tuple(target), 255+100*p, (240,158-33*p))
        if shot == 'rhea_awakens':
            return PerspectiveCamera((-3.1, 1.9, 2.1), (-3, 1.7, 0), 260)
        if shot == 'prison_release':
            p = 1. if reduced_motion else smooth(phase(time, 16.3, 17.2))
            return PerspectiveCamera(tuple(lerp((-3.1, 1.9, 2.1), (-3, 5.1, 7.5), p)),
                                     (-3, 1.4, 0), 260)
        p = phase(time, 17.2, 20)
        if reduced_motion:
            return PerspectiveCamera((8.5,13.8,-9.8),(-3,.8,0),245)
        if p < .34:
            q = smooth(p/.34)
            return PerspectiveCamera(tuple(lerp((-3, 5.1, 7.5), (-2, 13.8, -9.8), q)),
                                     (-3, 1, 0), 260-15*q)
        q = smooth((p-.34)/.66)
        position = (-2+10.5*q, 13.8+math.sin(q*math.pi)*.3, -9.8-math.sin(q*math.pi)*.3)
        return PerspectiveCamera(position, (-3, .8, 0), 245)

    @classmethod
    def telemetry(cls, time):
        if time < 8.5:
            prison = 'intact'
        elif time < 16.3:
            prison = 'cracked'
        else:
            prison = 'shattered'
        return dict(shot=cls.shot(time), time=time,
                    positions={key: list(value) for key, value in cls.actor_positions(time).items()},
                    prison=prison,
                    first_shard='aimed' if time < 6.86 else 'flight' if time < 9.0 else 'intercepted',
                    second_shard='absent' if time < 12.65 else 'forming' if time < 14.7 else 'destroyed',
                    rune=phase(time, 16.3, 18.3),
                    camera_position=list(cls.camera(time).position),
                    camera_target=list(cls.camera(time).target),
                    slow_motion=7.5 <= time < 9.5)

    def _scale(self, image, width, height):
        width, height = max(1, round(width)), max(1, round(height))
        width, height = min(width, 1400), min(height, 1400)
        key = (id(image), width, height)
        if key not in self._scaled:
            if len(self._scaled) > 1800:
                self._scaled.clear()
            self._scaled[key] = pygame.transform.scale(image, (width, height))
        return self._scaled[key]

    def _sequence(self, actor, action, local, duration, camera, position):
        data = self.actors[actor]
        sequences = data['sequences']
        # All viewpoint changes select authored body views, never rotate a body.
        toward = V3(-3, 0, 0)-V3(position)
        viewer = V3(camera.position)-V3(position)
        toward.y = viewer.y = 0
        dot = toward.normalize().dot(viewer.normalize()) if toward.length() > .1 and viewer.length() > .1 else 1
        suffix = '_rear' if dot < -.35 else '_side' if abs(dot) < .5 else '_front'
        for alternate in (action+suffix, 'ready'+suffix, suffix[1:]):
            if alternate in sequences and (alternate.startswith(action) or action in ('ready', 'aim', 'impact', 'recharge')):
                if duration and local < duration and len(sequences[alternate]) < 4:
                    continue
                action = alternate
                break
        sequence = sequences.get(action, sequences.get('ready', next(iter(sequences.values()))))
        if duration:
            index = min(len(sequence)-1, int(phase(local, 0, duration)*len(sequence)))
        else:
            total = sum(item[1] for item in sequence)
            t = local % total
            index = 0
            for index, (_, length) in enumerate(sequence):
                if t < length:
                    break
                t -= length
        return sequence[index][0], data

    @staticmethod
    def _action(actor, time):
        if actor == 'caelan':
            if time < 7.02: return 'ready', time, None
            if time < 7.5: return 'dash', time-7.02, .48
            if time < 9.15: return 'slash', time-7.5, 1.65
            if time < 9.7: return 'land', time-9.15, .55
            return 'ready', time-9.7, None
        if actor == 'lucan':
            if time < 7.02: return 'ready', time, None
            if time < 7.5: return 'dash', time-7.02, .48
            if time < 9.0: return 'brace', time-7.5, 1.5
            if time < 9.7: return 'impact', time-9.0, .7
            return 'brace', 2, 1.65
        if actor == 'mira':
            if time < 10.6: return 'raise', time-10, .6
            if time < 12.35: return 'load', time-10.6, 1.75
            if time < 14.2: return 'aim', time-12.35, .65
            if time < 14.95: return 'fire', time-14.2, .75
            return 'aim', 1, .65
        if actor == 'rhea':
            return ('release', time-16.3, 1.2) if time >= 16.3 else ('ready', 0, None)
        if time >= 17.75: return 'ready_rear', time-17.75, None
        if time < 6.65: return 'aim', time-5, 1.65
        if time < 7.3: return 'launch', time-6.65, .65
        return 'recharge', time-11.7, 2.4

    def _billboard(self, canvas, actor, position, camera, time, *, alpha=255):
        projected = camera.project(position)
        if projected is None:
            return
        x, y, depth = projected
        action, local, duration = self._action(actor, time)
        image, data = self._sequence(actor, action, local, duration, camera, position)
        height = 4.8 if actor == 'ice_reaper' else 1.85
        scale = camera.focal*height/depth/max(1, data['body_pixels'])
        if scale <= 0:
            return
        surface = self._scale(image, image.get_width()*scale, image.get_height()*scale)
        if alpha != 255:
            surface = surface.copy(); surface.set_alpha(alpha)
        ax, ay = data['anchor']
        canvas.blit(surface, (round(x-ax*scale), round(y-ay*scale)))
        if actor == 'caelan':
            self._fireblade(canvas, camera, position, time)

    def _background(self, canvas, camera, time):
        shot = self.shot(time)
        if shot in ('mira_loading', 'launcher_sight', 'second_shard_intercept'):
            key = 'reverse'
        elif shot in ('prison_release', 'rune_panorama'):
            key = 'aerial'
        else:
            key = 'rescue'
        plate = self.plates[key]
        # The distant plate has modest parallax; ground objects use projection.
        direction = V3(camera.target)-V3(camera.position)
        angle = math.atan2(direction.x, direction.z)
        offset = round(math.sin(angle)*58)
        canvas.blit(plate, (-80+offset, -80))
        if shot == 'rescue_orbit':
            p = smooth(phase(time, 9.5, 11))
            reverse = self.plates['reverse'].copy()
            reverse.set_alpha(round(p*255))
            canvas.blit(reverse, (-80-offset, -80))
        self._ground_plane(canvas, camera)
    def _ground_plane(self, canvas, camera):
        if self.ground_texture is None:
            return
        right, up, forward = camera.basis()
        u=(self._screen_x-camera.center[0])/camera.focal
        v=(camera.center[1]-self._screen_y)/camera.focal
        ray_y=forward.y+right.y*u+up.y*v
        distance=-camera.position[1]/np.minimum(ray_y,-.001)
        wx=camera.position[0]+distance*(forward.x+right.x*u+up.x*v)
        wz=camera.position[2]+distance*(forward.z+right.z*u+up.z*v)
        alpha=np.where(ray_y<-.015,np.clip((65-distance)/42,0,.45),0)
        # Mirror the authored snow patch at each edge so the moving ground
        # does not expose a checkerboard of hard texture-wrap seams.
        tw, th = self.ground_texture.shape[:2]
        tx=(wx*22).astype(np.int32)%(2*tw)
        tz=(wz*22).astype(np.int32)%(2*th)
        tx=np.minimum(tx,2*tw-1-tx)
        tz=np.minimum(tz,2*th-1-tz)
        texture=self.ground_texture[tx,tz].astype(np.float32)
        target=pygame.surfarray.pixels3d(canvas)
        target[:]=(target.astype(np.float32)*(1-alpha[:,:,None])+texture*alpha[:,:,None]).astype(np.uint8)
        del target

    @staticmethod
    def _line3(canvas, camera, color, points, width=1):
        projected = [camera.project(point) for point in points]
        if all(projected):
            pygame.draw.lines(canvas, color, False, [(round(p[0]),round(p[1])) for p in projected], width)

    def _shadow(self, canvas, camera, position, radius=.5):
        points = [camera.project((position.x+math.cos(a)*radius, .025,
                                  position.z+math.sin(a)*radius*.55))
                  for a in [i*TAU/16 for i in range(16)]]
        if all(points):
            pygame.draw.polygon(canvas, '#67869d', [(p[0],p[1]) for p in points])

    def _prison(self, canvas, camera, position, time, front):
        if time >= 16.45:
            return
        image = self.prison_front if front else self.prison_back
        p = camera.project(position)
        if p is None:
            return
        scale = camera.focal*2.55/p[2]/128
        surface = self._scale(image, image.get_width()*scale, image.get_height()*scale)
        if time >= 16.3:
            surface = surface.copy();surface.set_alpha(round(255*(1-phase(time,16.3,16.45))))
        canvas.blit(surface, (round(p[0]-44*scale), round(p[1]-130*scale)))
        if front and 8.5 <= time < 16.4:
            for i in range(7):
                start = V3(position)+V3(-.55+i*.17, .7+(i%3)*.4, -.08)
                points = [start, start+V3(.18,.25,0), start+V3(-.03,.45,0),start+V3(.15,.7,0)]
                self._line3(canvas,camera,'#f2ffff',points,2)
                self._line3(canvas,camera,'#3e7b9c',[p+V3(.025,0,0) for p in points],1)

    def _fireblade(self, canvas, camera, position, time):
        if not 8.45 < time < 9.0:
            return
        if time < 7.5:
            base = V3(position)+V3(-.2,1.0,.1); tip=base+V3(-1.0,.75,0)
        else:
            p = phase(time,7.5,9.15)
            angle = -1.7+p*3.7
            base=V3(position)+V3(-.25,1.05,0)
            tip=base+V3(math.sin(angle)*1.5, math.cos(angle)*1.5,0)
        # The blade itself is authored into every pose.  Only hot contact
        # sparks and a short arc are added here, so the weapon never detaches.
        contact = V3(-3, 1.15, .12)
        for i in range(14):
            angle = -1.4+phase(time,8.45,9.0)*2.7-i*.035
            point = contact+V3(math.cos(angle)*.6, math.sin(angle)*.8,0)
            q = camera.project(point)
            if q: pygame.draw.circle(canvas, '#ffd78c', q[:2], max(1,3-i//6))

    def _dash_snow(self, canvas, camera, positions, time, reduced):
        if not 7.02 <= time <= 10:return
        for actor in ('caelan','lucan'):
            origin=V3((4.7,0,8) if actor=='caelan' else (6.5,0,8))
            destination=positions[actor]
            for i in range(26 if not reduced else 8):
                birth=7.02+(i%9)/9*.44
                age=time-birth
                if age < 0 or age > 1.65:continue
                progress=(i%9)/9
                source=origin.lerp(destination,progress)
                source+=V3(math.sin(i*4.9)*age*.75, math.sin(min(1,age/1.4)*math.pi)*(.2+i%4*.12),math.cos(i*6.2)*age*.65)
                p=camera.project(source)
                if p:pygame.draw.circle(canvas,('#d8edfa','#edf8ff','#bcd9ec')[i%3],p[:2],max(1,round(camera.focal/p[2]*(.035+i%3*.025))))

    def _draw_shard(self, canvas, camera, point, target, *, size=2.8, alpha=255):
        p=camera.project(point)
        direction=V3(target)-V3(point)
        q=camera.project(V3(point)+direction.normalize()*.5) if direction.length() else p
        if not p or not q:return
        length=max(6,camera.focal*size/p[2])
        image=self._scale(self.shard,self.shard.get_width()/self.shard.get_height()*length,length)
        angle=math.degrees(math.atan2(q[0]-p[0],q[1]-p[1]))
        image=pygame.transform.rotate(image,angle)
        if alpha!=255:image.set_alpha(alpha)
        canvas.blit(image,image.get_rect(center=(round(p[0]),round(p[1]))))

    def _fragments(self, canvas, camera, origin, time, birth, count, *, fire=False):
        age=time-birth
        if age < 0 or age > 2.5:return
        for i in range(count):
            angle=i*2.39996
            speed=1.3+(i%7)*.35
            point=V3(origin)+V3(math.cos(angle)*speed*age,
                               (1.3+i%5*.55)*age-2.4*age*age,
                               math.sin(angle)*speed*age)
            point.y=max(.03,point.y)
            p=camera.project(point)
            if not p:continue
            r=max(1,min(6,round(camera.focal/p[2]*(.03+i%4*.025))))
            color=('#fff0bd','#ffb14e','#e98042')[i%3] if fire else ('#e0f8ff','#8bc6ed','#d7edfc')[i%3]
            pygame.draw.polygon(canvas,color,[(p[0],p[1]-r*1.8),(p[0]+r,p[1]),(p[0],p[1]+r),(p[0]-r,p[1])])

    def _projectiles(self, canvas, camera, positions, time, reduced):
        # Keep the overhead shard clear of her face in the dialogue shot.
        start=V3(3.6,12.0,-8);shield=V3(-.8,1.35,1.15)
        if time < 6.86:
            self._draw_shard(canvas,camera,start,shield)
        elif time < 9.0:
            u=.68*phase(time,6.86,7.5) if time<7.5 else .68+.32*phase(time,7.5,9.0)
            point=start.lerp(shield,u)
            self._line3(canvas,camera,'#b4e6fc',[point,start.lerp(shield,max(0,u-.12))],3)
            self._draw_shard(canvas,camera,point,shield)
        else:
            self._fragments(canvas,camera,shield,time,9.0,22 if not reduced else 8)
            if time<9.17:
                p=camera.project(shield)
                if p:pygame.draw.circle(canvas,'#f1faff',p[:2],max(1,round((1-phase(time,9.0,9.17))*17)),2)
        second=V3(2.1,11.4,-8)
        if 12.65 <= time < 14.7:
            grow=.2+.8*smooth(phase(time,12.65,14.2))
            self._draw_shard(canvas,camera,second,positions['mira'],size=2.8*grow)
        if 14.25 <= time < 14.7:
            muzzle=positions['mira']+V3(-.18,1.45,-.45)
            u=phase(time,14.25,14.7)
            point=muzzle.lerp(second,u)
            self._line3(canvas,camera,'#ffe9a9',[point,muzzle.lerp(second,max(0,u-.1))],4)
            q=camera.project(point)
            if q:pygame.draw.circle(canvas,'#fff5da',q[:2],3)
        if 14.7<=time<15.4:
            self._fragments(canvas,camera,second,time,14.7,32 if not reduced else 10)
            p=camera.project(second)
            if p:
                age=phase(time,14.7,15.25)
                pygame.draw.circle(canvas,'#d8f6ff',p[:2],max(1,round(age*42)),2)
                if time<14.86:pygame.draw.circle(canvas,'#fff2d2',p[:2],max(1,round((1-age)*18)))

    def _rune(self, canvas, camera, time, reduced):
        if time < 16.3:return
        reveal=smooth(phase(time,16.3,17.8))
        radius=8.2*reveal
        center=V3(-3,.035,0)
        glow=pygame.Surface(SIZE,pygame.SRCALPHA)
        for factor,alpha in ((1.16,13),(1.04,19),(.96,24),(.78,18),(.36,35)):
            points=[camera.project(center+V3(math.cos(i*TAU/80)*radius*factor,0,
                                            math.sin(i*TAU/80)*radius*factor)) for i in range(80)]
            if all(points):
                pygame.draw.polygon(glow,(245,42,67,round(alpha*(.55 if reduced else 1))),
                                    [(p[0],p[1]) for p in points])
        for r in (radius,radius-.35,radius-1.):
            if r <= 0: continue
            points=[center+V3(math.cos(i*TAU/100)*r,0,math.sin(i*TAU/100)*r) for i in range(101)]
            self._line3(glow,camera,(255,47,63,70 if not reduced else 28),points,7)
        canvas.blit(glow,(0,0))
        for offset,color,width in ((0,'#fa584c',2),(-.35,'#ffb27d',1),(-1.0,'#ad334b',1)):
            r=max(0,radius+offset)
            points=[center+V3(math.cos(i*TAU/100)*r,0,math.sin(i*TAU/100)*r) for i in range(101)]
            self._line3(canvas,camera,color,points,width)
        for i in range(12):
            a=i*TAU/12
            points=[center+V3(math.cos(a)*radius*.78,0,math.sin(a)*radius*.78),
                    center+V3(math.cos(a+.1)*radius*.9,0,math.sin(a+.1)*radius*.9),
                    center+V3(math.cos(a+.16)*radius*.8,0,math.sin(a+.16)*radius*.8)]
            self._line3(canvas,camera,'#ff8b67',points,2)
            b=a+TAU*5/12
            self._line3(canvas,camera,'#c43e56',[center+V3(math.cos(a)*radius*.7,0,math.sin(a)*radius*.7),center+V3(math.cos(b)*radius*.7,0,math.sin(b)*radius*.7)],1)
        if not reduced:
            for i in range(28):
                a=i*2.39996
                point=center+V3(math.cos(a)*(1+i%8*.65),((time-16.3)*1.1+i*.19)%4,math.sin(a)*(1+i%8*.65))
                p=camera.project(point)
                if p:pygame.draw.circle(canvas,('#ff8b67','#d34462','#ffd4a1')[i%3],p[:2],1+i%2)

    def _closeup(self, canvas, time):
        data=self.actors['rhea'];sequence=data['sequences'].get('eyes')
        if not sequence:return False
        index=min(len(sequence)-1,int(phase(time,15.1,16.25)*len(sequence)))
        image=sequence[index][0]
        # Eyes assets can be authored face inserts or full-body states.  The
        # manifest marks inserts; otherwise crop a stable head/shoulders region.
        meta=data['manifest'].get('animations',{}).get('eyes',{})
        closeup=meta.get('closeup',False) or data['manifest'].get('eyes_closeup',False)
        if closeup:
            crop=image
        else:
            w,h=image.get_size()
            crop=image.subsurface((round(w*.25),round(h*.08),round(w*.5),round(h*.43)))
        surface=self._scale(crop,crop.get_width()*min(420/crop.get_width(),290/crop.get_height()),crop.get_height()*min(420/crop.get_width(),290/crop.get_height()))
        canvas.blit(surface,surface.get_rect(center=(240,169)))
        # Close foreground ice edges remain cracked until her own release.
        for i,x in enumerate((56,83,394,420)):
            pygame.draw.lines(canvas,'#9ad7f7',False,[(x,15),(x+(-1)**i*14,94),(x-8,173),(x+11,252),(x-4,319)],2)
        return True

    def _loading_insert(self, canvas, time):
        if not 11.4 <= time < 12.3:
            return
        sequence=self.actors['mira']['sequences'].get('loading_detail')
        if not sequence:
            return
        image=sequence[min(len(sequence)-1,int(phase(time,11.4,12.25)*len(sequence)))][0]
        p=smooth(phase(time,11.4,11.58))
        scale=3.85+.15*phase(time,11.4,12.3)
        surface=self._scale(image,image.get_width()*scale,image.get_height()*scale).copy()
        surface.set_alpha(round(255*p))
        canvas.blit(surface,surface.get_rect(center=(240,174)))

    def _foreground_boss(self, canvas, camera, time):
        # A matching rear-view near-field plate carries the shoulder sweep.
        # Its crop deliberately excludes the lower body, as a physical camera
        # directly above the wings would, while the arena keeps true projection.
        sequence=self.actors['ice_reaper']['sequences'].get('ready_rear')
        if not sequence:
            return
        p=smooth(phase(time,18.05,20))
        image=sequence[int((time-18.05)*3)%len(sequence)][0]
        scale=2.6
        surface=self._scale(image,image.get_width()*scale,image.get_height()*scale)
        anchor=self.actors['ice_reaper']['anchor']
        x=60+360*p
        y=600
        opacity=smooth(phase(time,18.05,18.3))
        if opacity < 1:
            surface=surface.copy();surface.set_alpha(round(opacity*255))
        canvas.blit(surface,(round(x-anchor[0]*scale),round(y-anchor[1]*scale)))

    def _scope_overlay(self, canvas, time):
        if time < 13.65 or time >= 15.1:return
        opacity=smooth(phase(time,13.65,14.15))
        if self.scope is not None:
            image=self._scale(self.scope,*SIZE).copy();image.set_alpha(round(255*opacity));canvas.blit(image,(0,0))
        else:
            mask=pygame.Surface(SIZE,pygame.SRCALPHA);mask.fill((10,19,27,round(200*opacity)))
            pygame.draw.circle(mask,(0,0,0,0),(240,125),130)
            canvas.blit(mask,(0,0))
            pygame.draw.circle(canvas,'#647a86',(240,125),132,5)
            pygame.draw.circle(canvas,'#b4bfbd',(240,125),126,1)
        # Fine sight marks leave the shard and Reaper unobscured.
        for x in (-1,1):pygame.draw.line(canvas,'#dbba76',(240+x*48,125),(240+x*17,125),1)
        for y in (-1,1):pygame.draw.line(canvas,'#dbba76',(240,125+y*40),(240,125+y*15),1)
        pygame.draw.circle(canvas,'#d9bd7c',(240,125),3,1)

    def draw(self, canvas, elapsed, reduced_motion=False):
        time=clamp(float(elapsed),5,20)
        camera=self.camera(time,reduced_motion)
        self._background(canvas,camera,time)
        if self.shot(time)=='rhea_awakens' and self._closeup(canvas,time):
            return
        positions=self.actor_positions(time)
        self._rune(canvas,camera,time,reduced_motion)
        for actor,position in positions.items():
            if actor!='ice_reaper':self._shadow(canvas,camera,position,.6 if actor=='rhea' else .45)
        self._dash_snow(canvas,camera,positions,time,reduced_motion)
        visible=[]
        for actor,position in positions.items():
            if actor == 'ice_reaper' and time >= 18.05:
                continue
            if actor == 'mira' and 7 <= time < 9.5:
                continue
            if actor in ('caelan','lucan','rhea') and 13.65 <= time < 15.1:
                continue
            p=camera.project(position)
            if p:visible.append((p[2],actor,position))
        for _,actor,position in sorted(visible,reverse=True):
            if actor=='rhea':self._prison(canvas,camera,position,time,False)
            self._billboard(canvas,actor,position,camera,time)
            if actor=='rhea':self._prison(canvas,camera,position,time,True)
        self._projectiles(canvas,camera,positions,time,reduced_motion)
        self._fragments(canvas,camera,positions['rhea']+V3(0,1.1,0),time,16.3,48 if not reduced_motion else 12)
        if time >= 18.05:
            self._foreground_boss(canvas,camera,time)
        self._loading_insert(canvas,time)
        self._scope_overlay(canvas,time)
