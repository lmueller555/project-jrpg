"""Rhea awakens within the existing scene, bursts wide, then sweeps shoulders.

A single world-space sprite and its original ice layers remain visible. The
parent stage supplies the shared cast, scenery, projection and rune renderer.
"""
from __future__ import annotations

import json
from pathlib import Path

import pygame

from ice_reaper_action import PerspectiveCamera, V3, phase, smooth


ROOT = Path(__file__).resolve().parent


class RheaSceneAwakening:
    DURATION = 5.9
    BREAKOUT = 2.2
    RETREAT_END = 2.85
    CAMERA_SETTLED = 5.15
    EXPRESSION_TIMES = (
        (0., 'neutral_closed'), (.45, 'strain_begin'), (.75, 'strain_mid'),
        (1.03, 'strain_peak'), (1.3, 'opening_01'), (1.43, 'opening_02'),
        (1.57, 'angry_open'), (1.8, 'angry_hold'),
    )
    CLOSE = PerspectiveCamera((-3.13, 1.7, 2.1), (-3.13, 1.58, 0), 500)
    WIDE = PerspectiveCamera((5.020994, 16.3, -9.059998), (-3, .8, 0), 245)
    OPPOSITE_SHOULDER = PerspectiveCamera(
        (1.6290008314606745, 16.3, -11.17999373033708), (-3, .8, 0), 245)

    def __init__(self, stage):
        self.stage = stage
        self.expression_root = ROOT/'assets/story/rhea_scene_awakening_study'
        self.expression_manifest = json.loads((self.expression_root/'manifest.json').read_text())
        if tuple(self.expression_manifest['canvas']) != (128, 128):
            raise ValueError('Rhea awakening must use registered full-body scene sprites')
        if tuple(self.expression_manifest['anchor']) != stage.actors['rhea']['anchor']:
            raise ValueError('Rhea awakening must preserve the existing scene anchor')
        self.expression_images = {
            name: stage._read_image(self.expression_root/entry['file'])
            for name, entry in self.expression_manifest['frames'].items()}
        if set(self.expression_images) != {name for _, name in self.EXPRESSION_TIMES}:
            raise ValueError('Rhea awakening expression sequence is incomplete')
        if any(image.get_size() != (128, 128) for image in self.expression_images.values()):
            raise ValueError('Rhea awakening frame has an unregistered canvas')
        self.last_draw_trace = []

    @staticmethod
    def canonical_time(elapsed):
        return 14.1+max(0., elapsed)

    @staticmethod
    def local_time(actual_elapsed):
        """Subtract the scene offset without slipping a 60 FPS key pose.

        Decimal boundaries such as 16.4-15.1 can fall just below 1.3 in binary
        floats. Only values already within numerical noise of a frame boundary
        are snapped; ordinary real-time sampling retains its elapsed clock.
        """
        local = float(actual_elapsed)-15.1
        frame = round(local*60)/60
        return frame if abs(local-frame) < 1e-10 else local

    @classmethod
    def camera(cls, elapsed, reduced=False):
        if elapsed < cls.BREAKOUT:
            # An actual camera push, keeping the same full-body actor and shell.
            amount = 1. if reduced else smooth(phase(elapsed, 0, .35))
            start = PerspectiveCamera((-3.13, 2.3, 4.1), (-3.13, 1.45, 0), 345)
            return PerspectiveCamera(
                tuple(V3(start.position).lerp(V3(cls.CLOSE.position), amount)),
                tuple(V3(start.target).lerp(V3(cls.CLOSE.target), amount)),
                start.focal+(cls.CLOSE.focal-start.focal)*amount)
        if reduced:
            return cls.WIDE
        if elapsed >= cls.RETREAT_END:
            # The approved fast retreat arrives at the first shoulder exactly.
            # Traverse behind the Reaper in world space, always targeting Rhea;
            # her foreground silhouette crosses naturally as the camera moves.
            amount = smooth(phase(elapsed, cls.RETREAT_END, cls.CAMERA_SETTLED))
            position = V3(cls.WIDE.position).lerp(V3(cls.OPPOSITE_SHOULDER.position), amount)
            return PerspectiveCamera(tuple(position), cls.WIDE.target, cls.WIDE.focal)
        amount = smooth(phase(elapsed, cls.BREAKOUT, cls.RETREAT_END))
        a = 1-amount
        points = tuple(map(V3, (cls.CLOSE.position, (.4, 7, 3),
                                (5.2, 17.2, -5.2), cls.WIDE.position)))
        position = points[0]*a**3+points[1]*3*a*a*amount+points[2]*3*a*amount**2+points[3]*amount**3
        target = V3(cls.CLOSE.target).lerp(V3(cls.WIDE.target), amount)
        focal = cls.CLOSE.focal+(cls.WIDE.focal-cls.CLOSE.focal)*amount
        return PerspectiveCamera(tuple(position), tuple(target), focal)

    def expression(self, elapsed):
        return next(name for start, name in reversed(self.EXPRESSION_TIMES) if elapsed >= start)

    @staticmethod
    def eye_state(elapsed):
        glow = smooth(phase(elapsed, 1.3, 1.63))
        gleam = smooth(phase(elapsed, 1.34, 1.52))*(1-smooth(phase(elapsed, 1.52, 1.78)))
        return glow, gleam

    def _rhea_image(self, camera, position, elapsed, time):
        expression = self.expression(min(elapsed, 2.))
        if elapsed < self.BREAKOUT:
            return self.expression_images[expression], expression, True
        azimuth, _ = self.stage.view_angles('rhea', camera, position, time)
        entries = self.stage.actors['rhea']['manifest']['animations']
        choices = [key for key in entries if key.startswith('frozen_')]
        key = min(choices, key=lambda name: abs((azimuth-entries[name]['view_azimuth_deg']+180)%360-180))
        if key == 'frozen_front':
            return self.expression_images['angry_hold'], 'angry_hold', True
        return self.stage.actors['rhea']['sequences'][key][0][0], key, False

    def _rhea(self, canvas, camera, position, elapsed, time):
        projected = camera.project(position)
        if projected is None:
            return
        image, name, frontal = self._rhea_image(camera, position, elapsed, time)
        data = self.stage.actors['rhea']
        scale = camera.focal*1.85/projected[2]/data['body_pixels']
        surface = self.stage._scale(image, image.get_width()*scale, image.get_height()*scale)
        ax, ay = data['anchor']
        origin = (round(projected[0]-ax*scale), round(projected[1]-ay*scale))
        canvas.blit(surface, origin)
        self.last_draw_trace.append({'actor':'rhea', 'representation':name,
                                     'source_canvas':list(image.get_size())})
        glow, gleam = self.eye_state(elapsed)
        if not frontal or glow <= 0:
            return
        eyes = self.expression_manifest['frames'][name]['eyes']
        light = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        for x, y in eyes:
            point = (round(origin[0]+x*scale), round(origin[1]+y*scale))
            radius = max(1, round(scale*2))
            pygame.draw.circle(light, (48,255,112,round(24*glow)), point, radius)
            iris = pygame.Rect(0,0,max(1,round(scale*1.2)),max(1,round(scale*.5)))
            iris.center = point
            pygame.draw.ellipse(light, (113,255,165,round(210*glow)), iris)
            if gleam > .01:
                reach = max(2,round(scale*4.6*gleam))
                color = (179,255,204,round(255*gleam))
                pygame.draw.line(light,color,(point[0]-reach,point[1]),(point[0]+reach,point[1]),1)
                pygame.draw.line(light,color,(point[0],point[1]-max(1,reach//3)),
                                 (point[0],point[1]+max(1,reach//3)),1)
        canvas.blit(light,(0,0))

    def _original_prison(self, canvas, camera, position, time, front):
        if time >= 16.45:
            return
        image = self.stage.prison_front if front else self.stage.prison_back
        projected = camera.project(position)
        if projected is None:
            return
        scale = camera.focal*2.55/projected[2]/128
        surface = self.stage._scale(image, image.get_width()*scale, image.get_height()*scale)
        if time >= 16.3:
            surface = surface.copy()
            surface.set_alpha(round(255*(1-phase(time,16.3,16.45))))
        canvas.blit(surface, (round(projected[0]-44*scale), round(projected[1]-130*scale)))
        self.last_draw_trace.append({'prison_layer':'front' if front else 'back',
                                     'source':'original_scene_prison'})
        # The original texture already contains fractures. Avoid the broad
        # procedural zigzags that would cover the tiny eyes in this closer view.

    @classmethod
    def state(cls, elapsed):
        expression = next(name for start, name in reversed(cls.EXPRESSION_TIMES)
                          if elapsed >= start)
        shot = ('rhea_awakens' if elapsed < cls.BREAKOUT else
                'prison_release' if elapsed < cls.RETREAT_END else
                'rune_panorama' if elapsed < cls.CAMERA_SETTLED else 'rune_hold')
        return dict(shot=shot, expression=expression, eyes_closed=elapsed<1.3,
                    green_light=cls.eye_state(elapsed),
                    prison='cracked' if elapsed<cls.BREAKOUT else 'shattered',
                    rapid_retreat_complete=elapsed>=cls.RETREAT_END,
                    shoulder_sweep=cls.RETREAT_END<elapsed<cls.CAMERA_SETTLED,
                    camera_settled=elapsed>=cls.CAMERA_SETTLED,
                    portrait_overlay=False, world_rhea_count=1)

    def telemetry(self, elapsed):
        camera = self.camera(elapsed)
        time = self.canonical_time(elapsed)
        return dict(self.state(elapsed), elapsed=elapsed,
                    camera_position=list(camera.position),
                    camera_target=list(camera.target), focal=camera.focal,
                    rhea_heading=list(self.stage.actor_heading('rhea',time)),
                    rhea_position=list(self.stage.actor_positions(time)['rhea']),
                    rune=self.stage.rune_seal.state(time))

    def draw(self, canvas, elapsed, reduced_motion=False):
        elapsed=max(0.,min(self.DURATION,float(elapsed)))
        time=self.canonical_time(elapsed)
        camera=self.camera(elapsed,reduced_motion)
        positions=self.stage.actor_positions(time)
        self.last_draw_trace=[]
        self.stage._background(canvas,camera,time)
        for actor,position in positions.items():
            if actor != 'ice_reaper':
                self.stage._shadow(canvas,camera,position,.6 if actor=='rhea' else .45)
        self.stage._rune(canvas,camera,time,reduced_motion)
        visible=[]
        for actor,position in positions.items():
            projected=camera.project(position)
            if projected is not None:
                visible.append((projected[2],actor,position))
        for _,actor,position in sorted(visible,reverse=True):
            if actor=='rhea':
                self._original_prison(canvas,camera,position,time,False)
                self._rhea(canvas,camera,position,elapsed,time)
                self._original_prison(canvas,camera,position,time,True)
            else:
                self.stage._billboard(canvas,actor,position,camera,time)
        self.stage._fragments(canvas,camera,positions['rhea']+V3(0,1.1,0),time,16.3,
                        12 if reduced_motion else 48)
