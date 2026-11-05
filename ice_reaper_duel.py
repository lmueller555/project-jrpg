"""Rhea takes the field: one world-space finale on the 21–32 second clock.

The parent stage owns the cast/scenery caches. This renderer moves the camera
and those same five actors; it never introduces a second Rhea or scenic plate.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame

from ice_reaper_action import IceReaperActionStage, PerspectiveCamera, V3, phase, smooth


ROOT = Path(__file__).resolve().parent


class IceReaperDuel:
    START = 21.
    DURATION = 32.
    WIND_START = 24.
    PAN_END = 25.15
    PAN_UP_END = 25.65
    ORBIT_START = 26.7
    ORBIT_END = 29.15
    PUSH_END = 29.55
    CHARGE_START = 30.3
    CHARGE_END = 31.65
    FADE_START = 31.1
    RHEA = (-3., 0., 0.)
    MIRA = (7., 0., 10.)
    CAELAN_END = (4.6, 0., 10.2)
    LUCAN_END = (8.8, 0., 8.5)
    ORBIT_CENTER = (-.23500053, 5.2, -4.42399915)
    ORBIT_CAMERA = (-12., 3., 12.)
    REAR_CAMERA = (-6., .6, 3.)
    REAR_TARGET = (-.235, 4., -4.424)
    MIRA_CAMERA = (12., 4.5, 15.)
    CHARGE_CAMERA = (-.8, 7.2, -3.7)

    def __init__(self, stage, asset_root=None):
        self.stage = stage
        self.asset_root = Path(asset_root or ROOT/'assets/story/ice_reaper_duel')
        self.authored = {}
        self.asset_records = []
        self.last_draw_trace = []
        for path in sorted(self.asset_root.rglob('animation.json')):
            if not any(part in ('men', 'women') for part in path.parts):
                continue
            manifest = json.loads(path.read_text())
            actor = manifest.get('actor', path.parent.name)
            if actor == 'reaper':
                actor = 'ice_reaper'
            if actor not in stage.actors:
                continue
            data = dict(anchor=tuple(manifest.get('anchor', stage.actors[actor]['anchor'])),
                        body_pixels=manifest.get('body_pixels',stage.actors[actor]['body_pixels']))
            records = self.authored.setdefault(actor, {})
            for action, entry in manifest.get('animations', {}).items():
                frames = entry.get('frames', []) if isinstance(entry,dict) else entry
                images = [stage._read_image(path.parent/record['file']) for record in frames]
                if not images:
                    continue
                angle = entry.get('view_azimuth_deg') if isinstance(entry,dict) else None
                if angle is None:
                    metadata = stage._view_metadata(action, {})
                    angle = metadata[0] if metadata is not None else 0.
                records[action] = dict(images=images,angle=float(angle),data=data)
                self.asset_records.append(dict(actor=actor,action=action,drawings=len(images),
                                               source=str(path.relative_to(ROOT))))
        # Keep validation and capture telemetry pointed at the wardrobe art
        # actually drawn, while the earlier approved artwork stays on disk.
        self.authored['rhea'] = {}
        self.asset_records = [record for record in self.asset_records if record['actor'] != 'rhea']
        winter = stage.winter
        for name, sequence in winter.actions.items():
            self.authored['rhea'][name] = dict(images=[image for image,_ in sequence],
                angle=winter.manifest['actions'][name]['view_azimuth_deg'], data=winter.data)
        for name, sequence in winter.energy.items():
            self.authored['rhea']['cast_hold_'+name] = dict(images=[image for image,_ in sequence],
                angle=winter.manifest['energy'][name]['view_azimuth_deg'], data=winter.data)
        for name, record in self.authored['rhea'].items():
            self.asset_records.append(dict(actor='rhea', action=name, drawings=len(record['images']),
                                           source=str(winter.path.relative_to(ROOT))))
        from ice_reaper_duel_fx import IceReaperDuelFX
        self.fx = IceReaperDuelFX(stage)
        self.validate_assets()

    def validate_assets(self):
        required={
            'rhea':('staff_sweep','cast','cast_rear','cast_hold'),
            'ice_reaper':('sword_conjure','sword_windup','sword_charge','sword_hold'),
            'caelan':('wind_front','wind_rear','wind_right','wind_left'),
            'lucan':('wind_front','wind_rear','wind_right'),
            'mira':('brace_front','brace_rear','brace_right')}
        missing=[]
        for actor,actions in required.items():
            for action in actions:
                records=[entry for name,entry in self.authored.get(actor,{}).items()
                         if name==action or name.startswith(action+'_')]
                if not records:
                    missing.append(actor+'/'+action)
                elif action not in ('sword_hold','cast_hold') and max(len(entry['images']) for entry in records)<4:
                    raise ValueError('Duel action needs at least four authored drawings: '+actor+'/'+action)
        if missing:
            raise ValueError('Missing authored duel actions: '+', '.join(missing))
        expected={-180.,-135.,-90.,-45.,0.,45.,90.,135.}
        for actor,family in (('rhea','cast_hold'),('ice_reaper','sword_hold')):
            views={((record['angle']+180)%360)-180
                   for name,record in self.authored[actor].items() if name.startswith(family+'_')}
            if views != expected:
                raise ValueError('Duel orbit needs eight authored held views: '+actor+'/'+family)

    @staticmethod
    def _direction(vector):
        result=V3(vector);result.y=0
        return result.normalize() if result.length_squared()>1e-8 else V3(0,0,1)

    @staticmethod
    def _turn(before, after, amount):
        start=math.atan2(before.x,before.z)
        end=math.atan2(after.x,after.z)
        delta=(end-start+math.pi)%math.tau-math.pi
        angle=start+delta*amount
        return V3(math.sin(angle),0,math.cos(angle))

    @classmethod
    def actor_positions(cls, elapsed):
        positions={actor:V3(point) for actor,point in IceReaperActionStage.actor_positions(20.).items()}
        for actor, start, end, destination, lift in (
                ('caelan',24.12,25.05,cls.CAELAN_END,1.15),
                ('lucan',24.18,25.15,cls.LUCAN_END,.65)):
            progress=smooth(phase(elapsed,start,end))
            positions[actor]=positions[actor].lerp(V3(destination),progress)
            positions[actor].y=math.sin(progress*math.pi)*lift if 0<progress<1 else 0.
        if elapsed>=cls.CHARGE_START:
            camera=cls.camera(cls.PUSH_END)
            direction=(V3(camera.target)-V3(camera.position)).normalize()
            # Her sternum approaches the lens. The final drawing remains in
            # front of its near plane until the already-opaque fade takes over.
            destination=V3(camera.position)-V3(0,2.3,0)+direction*.28
            progress=phase(elapsed,cls.CHARGE_START,cls.CHARGE_END)**2.25
            positions['ice_reaper']=positions['ice_reaper'].lerp(destination,progress)
        return positions

    @classmethod
    def caelan_heading(cls, elapsed):
        """Enter the crosswind watching the boss, then recover without a spin.

        The wind translates him sideways independently of his gaze. Freeze
        both facing targets on the established staging: tracking Rhea from a
        moving position made his body whip around as he passed her, and a
        second gust-only initial heading snapped away from his dialogue pose.
        """
        initial=IceReaperActionStage.actor_positions(20.)
        before=cls._direction(initial['ice_reaper']-initial['caelan'])
        after=cls._direction(initial['ice_reaper']-V3(cls.CAELAN_END))
        start,end=24.12,25.05
        duration=end-start
        # Resist the first impact before turning in the airborne portion. The
        # landing frames already face the fixed recovery direction.
        amount=smooth(phase(elapsed,start+duration*.22,start+duration*.75))
        return cls._turn(before,after,amount)

    @classmethod
    def headings(cls, elapsed):
        positions=cls.actor_positions(elapsed)
        toward_boss=cls._direction(positions['ice_reaper']-positions['rhea'])
        result={'rhea':toward_boss, 'ice_reaper':cls._direction(positions['rhea']-positions['ice_reaper']),
                'caelan':cls.caelan_heading(elapsed)}
        before=IceReaperActionStage.actor_heading('lucan',20.)
        after=cls._direction(positions['rhea']-positions['lucan'])
        result['lucan']=cls._turn(before,after,smooth(phase(elapsed,24.18,24.18+.6)))
        initial_mira=IceReaperActionStage.actor_heading('mira',20.)
        result['mira']=cls._direction(initial_mira.lerp(
            cls._direction(positions['rhea']-positions['mira']),smooth(phase(elapsed,23.8,24.6))))
        if elapsed>=cls.CHARGE_START:
            result['ice_reaper']=cls._direction(V3(cls.CHARGE_CAMERA)-positions['ice_reaper'])
        return result

    @classmethod
    def camera(cls, elapsed, reduced=False):
        boss=IceReaperActionStage.reaper_position(20.)
        upper=tuple(boss+V3(0,2.5,0))
        if elapsed<cls.WIND_START:
            return PerspectiveCamera(cls.REAR_CAMERA,cls.REAR_TARGET,235)
        if elapsed<cls.PAN_END:
            q=1. if reduced else smooth(phase(elapsed,cls.WIND_START,cls.PAN_END))
            # Ninety counterclockwise degrees in the ground plane, growing the
            # radius to arrive physically behind Mira rather than changing sets.
            angle=-math.pi/4+q*math.pi/2
            radius=math.sqrt(18)+(math.sqrt(450)-math.sqrt(18))*q
            position=V3(cls.RHEA)+V3(math.sin(angle)*radius,.6+3.9*q,math.cos(angle)*radius)
            target=V3(cls.REAR_TARGET).lerp(V3(-3,1.15,0),smooth(min(1,q*1.8)))
            return PerspectiveCamera(tuple(position),tuple(target),235+20*q)
        if elapsed<cls.PAN_UP_END:
            q=1. if reduced else smooth(phase(elapsed,cls.PAN_END,cls.PAN_UP_END))
            return PerspectiveCamera(cls.MIRA_CAMERA,tuple(V3(-3,1.15,0).lerp(V3(upper),q)),255)
        orbit=PerspectiveCamera(cls.ORBIT_CAMERA,cls.ORBIT_CENTER,255)
        if elapsed<cls.ORBIT_START:
            return orbit
        if elapsed<cls.ORBIT_END:
            amount=0. if reduced else smooth(phase(elapsed,cls.ORBIT_START,cls.ORBIT_END))
            angle=amount*math.tau
            center=V3(cls.ORBIT_CENTER)
            relative=V3(cls.ORBIT_CAMERA)-center
            position=center+V3(relative.x*math.cos(angle)+relative.z*math.sin(angle),
                               relative.y,-relative.x*math.sin(angle)+relative.z*math.cos(angle))
            return PerspectiveCamera(tuple(position),cls.ORBIT_CENTER,255)
        final=PerspectiveCamera(cls.CHARGE_CAMERA,upper,300)
        if elapsed<cls.PUSH_END:
            q=1. if reduced else smooth(phase(elapsed,cls.ORBIT_END,cls.PUSH_END))
            return PerspectiveCamera(tuple(V3(orbit.position).lerp(V3(final.position),q)),
                                     tuple(V3(orbit.target).lerp(V3(final.target),q)),255+45*q)
        return final

    @classmethod
    def state(cls, elapsed):
        shot=('rhea_takes_over' if elapsed<24 else 'wind_rescue' if elapsed<25.15 else
              'reaper_reaction' if elapsed<25.65 else 'elemental_standoff' if elapsed<26.7 else
              'duel_orbit' if elapsed<29.15 else 'charge_push' if elapsed<29.55 else
              'reaper_windup' if elapsed<30.3 else 'reaper_charge')
        return dict(shot=shot,time=elapsed,world_rhea_count=1,
                    wind_progress=phase(elapsed,24.12,25.15),
                    pan_degrees=-90*smooth(phase(elapsed,24,25.15)),
                    orbit_degrees=360*smooth(phase(elapsed,26.7,29.15)),
                    sword_progress=phase(elapsed,25.7,26.5),
                    fireball_progress=phase(elapsed,25.8,26.7),
                    charge_progress=phase(elapsed,30.3,31.65)**2.25,
                    fade_progress=smooth(phase(elapsed,31.1,32.)))

    def telemetry(self, elapsed):
        camera=self.camera(elapsed)
        result=dict(self.state(elapsed),positions={key:list(point) for key,point in self.actor_positions(elapsed).items()},
                    headings={key:list(point) for key,point in self.headings(elapsed).items()},
                    camera_position=list(camera.position),camera_target=list(camera.target),focal=camera.focal,
                    authored_actions=self.asset_records)
        if self.fx is not None and hasattr(self.fx,'state'):
            result['effects']=self.fx.state(elapsed)
        return result

    def _azimuth(self, actor, camera, position, elapsed):
        heading=self.headings(elapsed)[actor]
        viewer=self._direction(V3(camera.position)-position)
        right=V3(heading.z,0,-heading.x)
        return math.degrees(math.atan2(viewer.dot(right),viewer.dot(heading)))

    @staticmethod
    def _action(actor, elapsed):
        if actor=='rhea':
            if 24<=elapsed<24.8:return 'staff_sweep',phase(elapsed,24,24.8),False
            if 25.65<=elapsed<26.7:return 'cast',phase(elapsed,25.65,26.7),False
            if elapsed>=26.7:return 'cast_hold',1.,True
            return 'frozen',1.,True
        if actor=='ice_reaper':
            if elapsed<25.7:return 'ready',1.,True
            if elapsed<26.5:return 'sword_conjure',phase(elapsed,25.7,26.5),False
            if elapsed<29.55:return 'sword_hold',1.,True
            if elapsed<30.3:return 'sword_windup',phase(elapsed,29.55,30.3),False
            return 'sword_charge',phase(elapsed,30.3,31.65),False
        if actor=='mira':return ('brace',phase(elapsed,24,25.15),True) if elapsed>=23.8 else ('aim',1.,True)
        start,end=(24.12,25.05) if actor=='caelan' else (24.18,25.15)
        if elapsed<start:return ('ready' if actor=='caelan' else 'hold_brace'),1.,True
        if elapsed<end:
            u=phase(elapsed,start,end)
            if u<.22:return 'wind_hit',u/.22,False
            if u<.75:return 'wind_flight',(u-.22)/.53,False
            return 'wind_land',(u-.75)/.25,False
        return 'wind_land',1.,True

    def _image(self, actor, camera, position, elapsed):
        action,progress,held=self._action(actor,elapsed)
        azimuth=self._azimuth(actor,camera,position,elapsed)
        if actor == 'rhea':
            reduced = getattr(self, '_reduced_motion', False)
            if action in ('staff_sweep', 'cast'):
                return self.stage.winter.action(action, azimuth, progress, elapsed,
                                                reduced=reduced)
            return self.stage.winter.hold(azimuth, elapsed, reduced=reduced)
        candidates=self.authored.get(actor,{})
        records=[(key,entry) for key,entry in candidates.items() if key==action or key.startswith(action+'_')]
        if records:
            key,record=min(records,key=lambda item:abs((azimuth-item[1]['angle']+180)%360-180))
            images=record['images']
            image=images[min(len(images)-1,int(progress*len(images)))]
            return image,record['data'],key
        data=self.stage.actors[actor]
        family='frozen' if actor=='rhea' else 'hold_brace' if actor=='lucan' else 'ready' if actor=='caelan' else 'aim' if actor=='mira' else 'ready'
        entries=data['manifest'].get('animations',{})
        options=[]
        for key,sequence in data['sequences'].items():
            if key.startswith(family+'_'):
                if actor=='caelan' and not entries.get(key,{}).get('held_view'):
                    # Older rescue-only ready artwork has inferred direction
                    # labels and can tie a registered eight-view hold. It must
                    # not replace that hold at the dialogue/gust handoff.
                    continue
                view=self.stage._view_metadata(key,entries.get(key,{}))
                if view is not None:
                    # This atlas names the direction the artwork faces on the
                    # image, opposite the signed viewer angle used here. Scope
                    # the correction to the finale; keep the rescue untouched.
                    angle=-view[0] if actor=='caelan' else view[0]
                    options.append((abs((azimuth-angle+180)%360-180),key,sequence))
        if options:
            _,key,sequence=min(options,key=lambda item:item[0]);return sequence[-1][0],data,key
        key=family if family in data['sequences'] else next(iter(data['sequences']))
        return data['sequences'][key][-1][0],data,key

    def _draw_actor(self,canvas,actor,position,camera,elapsed):
        projected=camera.project(position)
        image,data,action=self._image(actor,camera,position,elapsed)
        self.last_draw_trace.append(dict(actor=actor,action=action,position=list(position),source_canvas=list(image.get_size())))
        if actor=='ice_reaper' and elapsed>=self.CHARGE_START:
            chest=camera.project(position+V3(0,2.3,0))
            if chest is None:return
            scale=camera.focal*4.8/chest[2]/data['body_pixels']
            surface=self.stage._scale(image,image.get_width()*scale,image.get_height()*scale)
            ax,ay=data['anchor'];chest_row=ay-data['body_pixels']*.48
            # The shared scale cache caps very large surfaces. Register the
            # actual result so the near-lens charge cannot slide offscreen.
            sx=surface.get_width()/image.get_width()
            sy=surface.get_height()/image.get_height()
            canvas.blit(surface,(round(chest[0]-ax*sx),round(chest[1]-chest_row*sy)))
            return
        if actor=='ice_reaper':
            self.stage._projected_boss(canvas,image,data,position,camera)
            return
        if projected is None:return
        scale=camera.focal*1.85/projected[2]/data['body_pixels']
        surface=self.stage._scale(image,image.get_width()*scale,image.get_height()*scale)
        ax,ay=data['anchor']
        canvas.blit(surface,(round(projected[0]-ax*scale),round(projected[1]-ay*scale)))
        if actor == 'rhea':
            self.stage.winter.draw_energy(canvas, camera, position, elapsed,
                                         reduced=getattr(self, '_reduced_motion', False))

    def draw(self,canvas,elapsed,reduced=False):
        self._reduced_motion = reduced
        elapsed=max(self.START,min(self.DURATION,float(elapsed)))
        camera=self.camera(elapsed,reduced)
        positions=self.actor_positions(elapsed)
        self.last_draw_trace=[]
        self.stage._background(canvas,camera,elapsed)
        for actor,position in positions.items():
            if actor!='ice_reaper':self.stage._shadow(canvas,camera,position,.6 if actor=='rhea' else .45)
        self.stage._rune(canvas,camera,20.,reduced)
        if self.fx is not None:
            self.fx.draw_ground(canvas,camera,elapsed,positions,reduced)
            self.fx.draw_air(canvas,camera,elapsed,positions,reduced,front=False)
        visible=[]
        for actor,position in positions.items():
            point=camera.project(position+V3(0,2.3,0) if actor=='ice_reaper' and elapsed>=self.CHARGE_START else position)
            if point is not None:visible.append((point[2],actor,position))
        for _,actor,position in sorted(visible,reverse=True):
            self._draw_actor(canvas,actor,position,camera,elapsed)
        if self.fx is not None:
            self.fx.draw_air(canvas,camera,elapsed,positions,reduced,front=True)
            self.fx.draw_overlay(canvas,camera,elapsed,positions,reduced)
