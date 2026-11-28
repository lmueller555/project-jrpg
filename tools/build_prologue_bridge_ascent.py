#!/usr/bin/env python3
"""Author the eight-second bridge crane using one fixed bridge-local world.

--previs writes clearly labelled geometric blockout pictures only. Final proof
and native-bank baking additionally require the approved complete figure banks.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import sys
from functools import lru_cache

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import numpy as np
from PIL import Image,ImageDraw

from cinematic_bridge_ascent import (ACTORS,CAMERA,GATE,ASCENT_SCENE,DURATION,FPS,
    actor_states_at,camera_at,camera_signature,performance_signature,guard_states_at,project_world,_smooth as _ease)
from tools import build_prologue_face_environment as frontal

SOURCE=ROOT/'assets/source/cinematics/fire_veinhold/bridge_ascent'
OUTPUT=ROOT/'assets/story/fire_veinhold_opening/shot08/environment'
REVIEW=ROOT/'docs/reviews/veinhold_bridge_ascent'
SIZE=(960,640)
COUNT=481
PROOFS=(0,24,36,48,60,72,96,132,180,240,348,480)
BRIDGE_LENGTH=299.0819285747636
BRIDGE_WIDTH=14.0
RAIL_HEIGHT=1.2
MATERIALS=ROOT/'assets/source/cinematics/fire_veinhold/continuation/materials'


def _json(value):return (json.dumps(value,indent=2,allow_nan=False)+'\n').encode()


def _entry(path):
    payload=path.read_bytes()
    return {'sha256':sha256(payload).hexdigest(),'bytes':len(payload)}


def scene_data():
    return {'version':1,'render_size':list(SIZE),
        'duration_seconds':DURATION,'camera':CAMERA,'actors':list(ACTORS),
        'environment':'environment/manifest.json',
        'environment_segments':{'normal':'bridge_ascent','reduced_motion':'bridge_ascent_reduced'},
        'party_performances':{actor['id']:f'characters/{actor["id"]}/actorperformance.json' for actor in ACTORS},
        'guard_performance':'guards/guardperformance.json',
        'coordinate_space':'Bridge-local metres: +Y toward Veinhold; +X runners\u2019 anatomical right; +Z above walking deck. Screen right -X, mainland up, fortress down.',
        'baked_characters':True}


def write_scene():
    ASCENT_SCENE.parent.mkdir(parents=True,exist_ok=True)
    ASCENT_SCENE.write_bytes(_json(scene_data()))


def write_camera_samples():
    samples=[]
    for index in PROOFS:
        state=actor_states_at(index/FPS)
        row={'index':index,'time':index/FPS,'global_time':47+index/FPS,
             'camera':state['camera'],'actors':[],'guards':guard_states_at(index/FPS)}
        for actor in state['runners']:
            x,y,z=actor['world_position_metres']
            head=project_world([x,y,actor['height_metres']],state['camera'])
            row['actors'].append({'id':actor['id'],'frame':actor['frame_index'],
                'elevation':actor['view_elevation_degrees'],'azimuth':actor['view_azimuth_degrees'],
                'pixels_per_metre':actor['pixels_per_metre'],
                'upright_height_px':abs(head[1]-actor['ground_anchor'][1]),
                'head':head[:2],'root':actor['ground_anchor'],
                'world_position_metres':actor['world_position_metres']})
        samples.append(row)
    SOURCE.mkdir(parents=True,exist_ok=True)
    (SOURCE/'camera_authoring_samples.json').write_bytes(_json(samples))


def _cube(origin,size):
    x,y,z=origin;w,l,h=size
    p=[(x+sx*w/2,y+sy*l/2,z+sz*h/2) for sz in (-1,1) for sy in (-1,1) for sx in (-1,1)]
    faces=((0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3))
    return [[p[i] for i in face] for face in faces]


def _project_faces(camera,shapes):
    faces=[]
    for origin,size,color in shapes:
        for n,face in enumerate(_cube(origin,size)):
            projected=[project_world(p,camera) for p in face]
            if any(p is None for p in projected):continue
            shade=(.6,.9,.72,1,.83,.67)[n]
            rgb=tuple(round(v*shade) for v in color)
            faces.append((sum(p[2] for p in projected)/4,[(p[0],p[1]) for p in projected],rgb))
    return sorted(faces,reverse=True,key=lambda row:row[0])


def proxy_picture(seconds):
    state=actor_states_at(seconds);camera=state['camera']
    image=Image.new('RGB',SIZE,'#07162a');pen=ImageDraw.Draw(image)
    shapes=[((0,BRIDGE_LENGTH/2,-.35),(14,BRIDGE_LENGTH,.7),(83,101,118)),
            ((0,-50,-5),(400,100,10),(65,89,112)),
            ((0,345,-5),(260,92,10),(86,55,55))]
    for x in (-7,7):
        shapes.append(((x,BRIDGE_LENGTH/2,.6),(.22,BRIDGE_LENGTH,1.2),(115,131,143)))
        for y in range(0,300,13):shapes.append(((x,y,.6),(.3,.3,1.2),(136,148,154)))
    for x in (-10,10):shapes.append(((x,309,14),(8,12,28),(76,65,62)))
    shapes.append(((0,309,24),(12,12,6),(83,69,64)))
    colors={'lucan':(168,90,67),'iselin':(112,145,228),'crown_soldier':(167,183,198)}
    for actor in state['runners']:
        x,y,z=actor['world_position_metres'];h=actor['height_metres']
        shapes.extend([((x,y,.83),(.7,.42,1.5),colors[actor['id']]),
                       ((x,y,h-.12),(.32,.3,.28),(204,217,230))])
    for guard in guard_states_at(seconds):
        x,y,z=guard['world_position_metres']
        shapes.append(((x,y,z+1.05),(1.1,.9,2.1),(110,191,225) if guard['kind']=='frozen' else (112,104,96)))
    for depth,points,color in _project_faces(camera,shapes):
        pen.polygon(points,fill=color,outline=(31,42,53))
    for actor in state['runners']:
        point=project_world(actor['world_position_metres'],camera)
        if point:pen.text((point[0]+8,max(38,min(607,point[1]))),actor['id'],fill='white')
    pen.rectangle((0,0,960,32),fill='#101c2c')
    pen.text((9,8),f'GEOMETRIC BLOCKOUT / NOT FINAL ART  {seconds:.3f}s  height {camera["position"][2]:.1f}m  lens {camera["focal_pixels"]:.1f}px',fill='white')
    return image


class WorldRenderer:
    """Fixed deck, sea, landing surfaces and genuinely volumetric structures.

    Approved close bridge materials keep their existing world UVs. The old
    angular painting supplies only the far sky/mountains. New top surfaces and
    sides have fixed metre-space UVs and a perspective depth buffer.
    """
    def __init__(self):
        self.bridge=frontal.PaintedBridge()
        self.rail=self.bridge.rail
        self.empty_rail=[np.zeros_like(level) for level in self.rail]
        self.materials={name:frontal._pyramid(MATERIALS/(name+'.png'))
                        for name in ('steel','masonry','schist')}
        for name in ('mainland_top','ash_top'):
            self.materials[name]=frontal._pyramid(SOURCE/'environment'/(name+'_generated.png'))
        source=Image.open(MATERIALS/'frozen_bridge_background.png').convert('RGB')
        rgb=np.asarray(source,dtype=np.float32)/255
        opacity=np.clip((rgb[:,:,1]-.22)/.45,0,1)*np.clip((rgb[:,:,2]-rgb[:,:,0]-.08)/.2,0,1)
        rgba=np.dstack((rgb,opacity));image=Image.fromarray(np.uint8(np.rint(rgba*255)),'RGBA').convert('RGBa')
        self.frost=[]
        while True:
            self.frost.append(np.asarray(image,dtype=np.float32)/255)
            if min(image.size)<=8:break
            image=image.resize((image.width//2,image.height//2),Image.Resampling.LANCZOS)
        self.yy,self.xx=np.mgrid[0:640,0:960].astype(np.float32)

    def _texture(self,name,u,v,depth,repeat=4.0,tint=(1,1,1)):
        pyramid=self.materials[name]
        h,w=pyramid[0].shape[:2]
        if name in ('mainland_top','ash_top'):
            # Two seam-avoiding, world-domain-warped material samples retain
            # metre-scale canopy/rock detail without visible rectangular tiles.
            raw_u=(np.asarray(u)+13*np.sin(np.asarray(v)*.03)+7*np.sin(np.asarray(u)*.009))/80
            raw_v=(np.asarray(v)+9*np.sin(np.asarray(u)*.017)+4*np.cos(np.asarray(v)*.013))/160
            footprint=np.maximum(1,np.asarray(depth)/self.camera['focal_pixels']*w/80)
            first=frontal._surface_samples(pyramid,raw_u*w,raw_v*h,footprint,wrap=True)
            second=frontal._surface_samples(pyramid,(raw_u+.37)*w,(raw_v+.53)*h,footprint,wrap=True)
            a=np.minimum.reduce((raw_u%1,1-raw_u%1,raw_v%1,1-raw_v%1))
            b=np.minimum.reduce(((raw_u+.37)%1,1-(raw_u+.37)%1,(raw_v+.53)%1,1-(raw_v+.53)%1))
            weight=np.clip(a/np.maximum(1e-6,a+b),0,1);weight=weight*weight*(3-2*weight)
            return (first[:,:3]*weight[:,None]+second[:,:3]*(1-weight[:,None]))*np.asarray(tint)
        footprint=np.maximum(1,np.asarray(depth)/self.camera['focal_pixels']*w/repeat)
        color=frontal._surface_samples(pyramid,np.asarray(u)/repeat*w,
            np.asarray(v)/repeat*h,footprint,wrap=True)
        return color[:,:3]*np.asarray(tint)

    def _material(self,selected,color,depth):
        # These are view-correct fixed surfaces throughout. Their first grazing
        # view retains the approved frontal reflection/paint reference; its
        # top-surface material becomes readable during the continuous tilt.
        weight=_ease(self.seconds/.6)
        self.frame[selected]=self.frame[selected]*(1-weight)+np.clip(color,0,1)*weight
        self.depth[selected]=depth

    def _horizontal(self,z,predicate,material,repeat=4,tint=(1,1,1)):
        with np.errstate(divide='ignore',invalid='ignore'):
            distance=(z-self.camera['position'][2])/self.rz
        x=self.rx*distance;y=self.camera['position'][1]+self.ry*distance
        valid=(distance>.05)&(self.rz<0)&(distance<self.depth)&predicate(x,y)
        if not np.any(valid):return
        if material=='water':
            color=self._water_color(x[valid],y[valid],distance[valid])
        else:color=self._texture(material,x[valid],y[valid],distance[valid],repeat,tint)
        self._material(valid,color,distance[valid])

    def _water_color(self,x,y,depth):
        """World-space wave normals and moon reflections, with no repeated tile."""
        dx=np.zeros_like(x);dy=np.zeros_like(y);height=np.zeros_like(x)
        view=np.column_stack((-x,self.camera['position'][1]-y,
                              np.full_like(x,self.camera['position'][2]+12.65)))
        view/=np.linalg.norm(view,axis=1)[:,None]
        footprint=np.asarray(depth)/self.camera['focal_pixels']/np.maximum(.08,view[:,2])
        warp=1.4*np.sin(x*.031+y*.023)+.6*np.sin(y*.049-x*.017)
        warp_x=1.4*.031*np.cos(x*.031+y*.023)-.6*.017*np.cos(y*.049-x*.017)
        warp_y=1.4*.023*np.cos(x*.031+y*.023)+.6*.049*np.cos(y*.049-x*.017)
        waves=((34,.35,25),(19,.18,42),(11,.1,-18),(6,.06,35),
               (3.7,.03,70),(2.4,.018,12),(1.5,.01,-40),(1.05,.007,6))
        for i,(length,amplitude,angle) in enumerate(waves):
            k=math.tau/length;theta=math.radians(angle);ux,uy=math.cos(theta),math.sin(theta)
            phase=k*(x*ux+y*uy+warp)-math.sqrt(9.81*k)*(47+self.seconds)+i*1.71
            filtered=amplitude*np.exp(-.5*(k*footprint)**2)
            height+=filtered*np.cos(phase)
            dx-=filtered*k*(ux+warp_x)*np.sin(phase);dy-=filtered*k*(uy+warp_y)*np.sin(phase)
        normal=np.column_stack((-dx,-dy,np.ones_like(x)));normal/=np.linalg.norm(normal,axis=1)[:,None]
        moon=np.array([-.38,-.43,.82]);moon/=np.linalg.norm(moon)
        half=view+moon;half/=np.linalg.norm(half,axis=1)[:,None]
        exponent=70/(1+.8*(footprint/.5)**2)
        spec=np.maximum(0,np.sum(normal*half,axis=1))**exponent
        rough=np.maximum(0,np.sum(normal*half,axis=1))**14
        ambient=.5+.5*np.maximum(0,normal@moon)
        color=np.array([.013,.047,.093])[None,:]*ambient[:,None]
        color+=rough[:,None]*np.array([.009,.023,.045])[None,:]
        color+=spec[:,None]*np.array([.13,.19,.28])[None,:]
        crest=np.clip((height-.30)/.26,0,1)**3
        color+=crest[:,None]*np.array([.008,.02,.032])[None,:]
        # Fixed directional moonlight puts the bridge shadow on the sea, rather
        # than pinning a dark stripe to the picture as the camera rises.
        along=(y-6.6);across=np.abs(x-5.85)
        shadow=np.clip((7.8-across)/1.6,0,1)*np.clip(along/2,0,1)*np.clip((BRIDGE_LENGTH-along)/2,0,1)
        color*=1-.32*shadow[:,None]
        return color

    def _triangle(self,vertices,material,tint):
        camera=self.camera
        projected=[project_world([float(value) for value in point],camera) for point in vertices]
        if any(point is None for point in projected):return
        p=np.asarray(projected);left=max(0,math.floor(p[:,0].min()));right=min(960,math.ceil(p[:,0].max())+1)
        top=max(0,math.floor(p[:,1].min()));bottom=min(640,math.ceil(p[:,1].max())+1)
        if right<=left or bottom<=top:return
        xx=self.xx[top:bottom,left:right]+.5;yy=self.yy[top:bottom,left:right]+.5
        denom=(p[1,1]-p[2,1])*(p[0,0]-p[2,0])+(p[2,0]-p[1,0])*(p[0,1]-p[2,1])
        if abs(denom)<1e-8:return
        a=((p[1,1]-p[2,1])*(xx-p[2,0])+(p[2,0]-p[1,0])*(yy-p[2,1]))/denom
        b=((p[2,1]-p[0,1])*(xx-p[2,0])+(p[0,0]-p[2,0])*(yy-p[2,1]))/denom
        c=1-a-b;inside=(a>=-1e-7)&(b>=-1e-7)&(c>=-1e-7)
        inverse=a/p[0,2]+b/p[1,2]+c/p[2,2]
        depth=np.divide(1,inverse,out=np.full_like(inverse,np.inf),where=inverse>0)
        subdepth=self.depth[top:bottom,left:right];valid=inside&(depth<subdepth)
        if not np.any(valid):return
        world=np.asarray(vertices);normal=np.abs(np.cross(world[1]-world[0],world[2]-world[0]));axis=int(normal.argmax())
        axes=((1,2),(0,2),(0,1))[axis]
        u=(a*world[0,axes[0]]/p[0,2]+b*world[1,axes[0]]/p[1,2]+c*world[2,axes[0]]/p[2,2])/inverse
        v=(a*world[0,axes[1]]/p[0,2]+b*world[1,axes[1]]/p[1,2]+c*world[2,axes[1]]/p[2,2])/inverse
        color=self._texture(material,u[valid],v[valid],depth[valid],4,tint)
        subframe=self.frame[top:bottom,left:right];weight=_ease(self.seconds/.6)
        subframe[valid]=subframe[valid]*(1-weight)+np.clip(color,0,1)*weight
        subdepth[valid]=depth[valid]
        if np.mean(world[:,2])>.4:
            subraised=self.raised_depth[top:bottom,left:right]
            subraised[valid]=np.minimum(subraised[valid],depth[valid])

    def _face(self,vertices,material,tint):
        # Clip in world coordinates against the shared camera near plane.
        near=.06;points=list(vertices);clipped=[]
        def depth(p):return sum((p[i]-self.camera['position'][i])*self.camera['forward'][i] for i in range(3))
        for first,second in zip(points,points[1:]+points[:1]):
            da,db=depth(first),depth(second)
            if da>=near:clipped.append(first)
            if (da>=near)!=(db>=near):
                blend=(near-da)/(db-da);clipped.append(tuple(first[i]+blend*(second[i]-first[i]) for i in range(3)))
        for index in range(1,len(clipped)-1):self._triangle([clipped[0],clipped[index],clipped[index+1]],material,tint)

    def _box(self,origin,size,material='steel',tint=(.52,.64,.82)):
        shades=(.42,1.0,.76,.52,.88,.66)
        for face,shade in zip(_cube(origin,size),shades):
            self._face(face,material,tuple(value*shade for value in tint))

    @staticmethod
    def mainland_shore(x):
        blend=np.clip((np.abs(x)-12)/18,0,1);blend=blend*blend*(3-2*blend)
        return (-5-.00012*x*x+8*np.sin(x*.018)+3*np.sin(x*.053)+1.8*np.sin(x*.107))*blend

    @staticmethod
    def island_shore(x):
        blend=np.clip((np.abs(x)-15)/20,0,1);blend=blend*blend*(3-2*blend)
        return BRIDGE_LENGTH+(.0003*x*x+7*np.sin(x*.02)+2*np.sin(x*.065))*blend

    def _rock(self,x,y,width,depth,height,phase,tint):
        lower=[];upper=[]
        for i in range(7):
            angle=math.tau*i/7+phase
            radius=1+.13*math.sin(i*1.73+phase)
            lower.append((x+math.cos(angle)*width/2*radius,y+math.sin(angle)*depth/2*radius,0))
            upper.append((x+math.cos(angle)*width*.34*radius,y+math.sin(angle)*depth*.34*radius,
                          height*(.85+.17*math.sin(i*1.91+phase))))
        for i in range(7):
            self._face([lower[i],lower[(i+1)%7],upper[(i+1)%7],upper[i]],'schist',tint)
            self._face([upper[i],upper[(i+1)%7],(x,y,height*1.02)],'schist',tuple(c*1.2 for c in tint))

    def _rails(self,*,compose):
        """Sample the actual cut-out brace alpha, never a solid rail rectangle.

        Underlying sea/coast is rendered before these premultiplied panels.
        Only materially occupied rail texels enter the geometry depth buffers;
        transparent brace gaps remain windows into the same physical world.
        """
        height,width=self.rail[0].shape[:2]
        for side in (-1,1):
            with np.errstate(divide='ignore',invalid='ignore'):distance=side*7/self.rx
            y=self.camera['position'][1]+self.ry*distance
            z=self.camera['position'][2]+self.rz*distance
            valid=(distance>.05)&(y>=0)&(y<=BRIDGE_LENGTH)&(z>=0)&(z<=RAIL_HEIGHT)&(distance<self.depth)
            if not np.any(valid):continue
            u=((y[valid]/4)%1)*width;v=(1-z[valid]/RAIL_HEIGHT)*(height-1)
            footprint=distance[valid]/self.camera['focal_pixels']*width/4
            pixels=frontal._surface_samples(self.rail,u,v,footprint)
            if compose:self.frame[valid]=pixels[:,:3]+self.frame[valid]*(1-pixels[:,3:4])
            if self.seconds>=2.2:
                self._frost(valid,np.full_like(y[valid],side*7),y[valid],z[valid])
            occupied=np.zeros(SIZE[::-1],bool);occupied[valid]=pixels[:,3]>.5
            self.depth[occupied]=distance[occupied]
            self.raised_depth[occupied]=distance[occupied]

    def _frost(self,selected,x,y,z):
        """Reproject only the approved landing's visible blue-white coating.

        The guard-removed source has a finite, observed foreground footprint:
        deck Y0..3.5m and the matching rail segments. It is not extrapolated
        into an invented trail toward the moving party. The initial distant
        layer follows the same inherited omission policy as its ice statues.
        """
        extent=(y>=0)&(y<=3.5)&(np.abs(x)<=7.01)
        if not np.any(extent):return
        pitch=math.atan2(-1.399999618530273,18.0)
        dy=y-6.096;dz=np.asarray(z)-1.999999618530273
        depth=-math.cos(pitch)*dy+math.sin(pitch)*dz
        vertical=math.sin(pitch)*dy+math.cos(pitch)*dz
        u=768-768*x/np.maximum(.01,depth);v=512-768*vertical/np.maximum(.01,depth)
        valid=extent&(depth>.05)&(u>=0)&(u<1535)&(v>=0)&(v<1023)
        if not np.any(valid):return
        world_footprint=self.camera['position'][2]/self.camera['focal_pixels']/max(.08,abs(math.sin(self.camera['pitch_radians'])))
        footprint=np.maximum(1,world_footprint*np.maximum(768/depth[valid],1536/depth[valid]**2))
        pixels=frontal._surface_samples(self.frost,u[valid],v[valid],footprint)
        indices=np.flatnonzero(selected)[np.flatnonzero(valid)]
        flat=self.frame.reshape(-1,3);flat[indices]=pixels[:,:3]+flat[indices]*(1-pixels[:,3:4])

    def _floor_frost(self):
        if self.seconds<2.2:return
        with np.errstate(divide='ignore',invalid='ignore'):distance=-self.camera['position'][2]/self.rz
        x=self.rx*distance;y=self.camera['position'][1]+self.ry*distance
        valid=(distance>.05)&(self.rz<0)&(np.abs(x)<=7)&(y>=0)&(y<=3.5)&(distance<=self.depth+.01)
        self._frost(valid,x[valid],y[valid],np.zeros(np.count_nonzero(valid)))

    def render(self,index,reduced_motion=False,*,beacons=True):
        self.seconds=index/FPS;self.camera=camera_at(self.seconds,reduced_motion)
        focal=self.camera['focal_pixels'];self.bridge.horizontal=(480-self.xx)/focal;self.bridge.vertical=(320-self.yy)/focal
        old=frontal.camera_at;old_sampler=frontal._surface_samples
        try:
            frontal.camera_at=lambda seconds:self.camera
            lod_bias=1+2*_ease((self.camera['position'][2]-40)/120)
            frontal._surface_samples=lambda pyramid,u,v,footprint,**kw:old_sampler(pyramid,u,v,footprint*lod_bias,**kw)
            # At the exact join retain the original compositor's rounding.
            # Later frames put genuine world surfaces behind the brace holes
            # before applying the same world-fixed painted rail panels.
            if index:self.bridge.rail=self.empty_rail
            original,_=self.bridge.render(index)
        finally:
            frontal.camera_at=old;frontal._surface_samples=old_sampler;self.bridge.rail=self.rail
        self.frame=np.asarray(original).astype(np.float32)/255
        self.depth=np.full((640,960),np.inf,dtype=np.float32)
        self.raised_depth=np.full((640,960),np.inf,dtype=np.float32)
        pitch=self.camera['pitch_radians'];horizontal=self.bridge.horizontal;vertical=self.bridge.vertical
        self.rx=horizontal;self.ry=-math.cos(pitch)+vertical*math.sin(pitch)
        self.rz=math.sin(pitch)+vertical*math.cos(pitch)
        with np.errstate(divide='ignore',invalid='ignore'):
            distance=-self.camera['position'][2]/self.rz
        x=self.rx*distance;y=self.camera['position'][1]+self.ry*distance
        width=14+(y/100)*8
        deck=(distance>.05)&(self.rz<0)&(np.abs(x)<=7)&(y>=0)&(y<=BRIDGE_LENGTH)
        approach=(distance>.05)&(self.rz<0)&(y<0)&(y>=-100)&(np.abs(x)<=width/2)
        self.depth[deck|approach]=distance[deck|approach]
        self._horizontal(-12.65,lambda x,y:np.ones_like(x,dtype=bool),'water',32,(.85,.92,1.0))
        shoreline=self.mainland_shore
        self._horizontal(0,lambda x,y:(y<=shoreline(x))&(y>=-1100),'mainland_top',80,(1,1,1))
        island_shore=self.island_shore
        self._horizontal(0,lambda x,y:(y>=island_shore(x))&(y<760)&(np.abs(x)<310),'ash_top',80,(1,1,1))
        for a,b in zip(range(-450,450,18),range(-432,468,18)):
            self._face([(a,shoreline(a),0),(b,shoreline(b),0),
                        (b,shoreline(b),-12.65),(a,shoreline(a),-12.65)],'schist',(.5,.7,.95))
            if abs(a)<310 and abs(b)<310:
                self._face([(a,island_shore(a),0),(a,island_shore(a),-12.65),
                            (b,island_shore(b),-12.65),(b,island_shore(b),0)],'schist',(.85,.45,.34))
        for i,x in enumerate(range(-320,321,22)):
            if abs(x)<25:continue
            self._rock(x,float(shoreline(x))-5,10+3*math.sin(i*1.2),7+2*math.cos(i),
                       2.5+1.6*(.5+.5*math.sin(i*.8)),i*.73,(.62,.82,1.05))
        for i,x in enumerate(range(-280,281,30)):
            if abs(x)<28:continue
            self._rock(x,float(island_shore(x))+7,9+2*math.sin(i),8,2.3+math.sin(i*.7),
                       i*.63,(.88,.5,.4))
        self._floor_frost()
        self._rails(compose=bool(index))
        for x in (-7,7):
            self._box((x,BRIDGE_LENGTH/2,1.17),(.18,BRIDGE_LENGTH,.13),'steel',(.57,.68,.82))
            for y in range(0,300,4):self._box((x,y,.6),(.16,.16,1.2),'steel',(.55,.64,.75))
        for y in (48,100,152,204,256):
            self._box((0,y,-6.7),(5.2,7.8,12.5),'masonry',(.32,.41,.53))
        self._box((0,300,-6.5),(50,24,13),'masonry',(.55,.62,.78))
        for x in (-10,10):
            self._box((x,299,14),(8,12,28),'masonry',(.75,.88,1.1))
            self._box((x,299,28.5),(9,13,1.2),'steel',(.8,.95,1.2))
            for z in (8,17,27):self._box((x,299,z),(8.7,12.7,.45),'steel',(1.5,.85,.55))
            for sx in (-1,1):
                for sy in (-1,1):
                    self._box((x+sx*4,299+sy*6,11),(1.1,1.1,22),'masonry',(.9,1,1.2))
                    self._box((x+sx*4,299+sy*6,30),(1.3,1.3,2.8),'steel',(1.1,.85,.65))
            for bx in (-3,-1.5,0,1.5,3):
                for sy in (-1,1):self._box((x+bx,299+sy*6,29.5),(1,1,1.7),'masonry',(.82,.93,1.16))
        self._box((0,GATE['center_y'],(GATE['roof_bottom_z']+GATE['roof_top_z'])/2),
                  (GATE['clear_half_width']*2,GATE['far_y']-GATE['near_y'],GATE['roof_top_z']-GATE['roof_bottom_z']),
                  'masonry',(.7,.8,1))
        for side in (-1,1):
            self._box((side*69,311,4.5),(102,4.5,9),'masonry',(.65,.76,.95))
            self._box((side*69,311,9.2),(104,5,.5),'steel',(1.3,.83,.56))
            for x in range(22,120,12):
                self._box((side*x,308,4.7),(2.8,7,9.4),'masonry',(.83,.94,1.12))
                self._box((side*x,311,10),(2,4.7,1.4),'steel',(.85,.96,1.15))
            self._box((side*103,313,7),(13,14,14),'masonry',(.75,.85,1.04))
            self._box((side*103,313,14.4),(14,15,.8),'steel',(.9,1.05,1.24))
        self._box((-37,350,10),(18,24,20),'masonry',(.36,.35,.4))
        self._box((39,355,12),(22,28,24),'masonry',(.35,.34,.4))
        self._box((0,321,-.03),(14,45,.06),'steel',(.5,.62,.78))
        output=Image.fromarray(np.clip(np.rint(self.frame*255),0,255).astype(np.uint8))
        return (self._beacons(output,reduced_motion) if beacons else output),self.raised_depth.copy()

    def _beacons(self,output,reduced_motion):
        # Beacons own their phase in complete pictures; no runtime overlay bank.
        from cinematic_perspective import CinematicPerspective
        pulse=.68 if reduced_motion else CinematicPerspective.alarm_strength(17+self.seconds)
        light=Image.new('RGBA',SIZE);pen=ImageDraw.Draw(light)
        for x in (-10,10):
            p=project_world([x,294,30.5],self.camera)
            if not p or not 0<=p[0]<960 or not 0<=p[1]<640:continue
            radius=max(1.0,min(6,self.camera['focal_pixels']/p[2]))
            for ring in (3,2,1):
                r=radius*ring;alpha=round(80*pulse/ring)
                pen.ellipse((p[0]-r,p[1]-r,p[0]+r,p[1]+r),fill=(255,38,19,alpha))
        output=Image.alpha_composite(output.convert('RGBA'),light).convert('RGB')
        return output

    def render_pair(self,index):
        # The module-patched PaintedBridge is intentionally rendered serially.
        # Both modes share this exact world/camera; only intentional warning
        # luminosity differs. Figure composition is repeated over each result.
        base,depth=self.render(index,beacons=False)
        return self._beacons(base,False),self._beacons(base,True),depth


class FigureCompositor:
    """Uniform whole-drawing composition; no limb/face/cloth transformations."""
    def __init__(self):
        import pygame
        from collections import OrderedDict
        self.pygame=pygame;self.cache=OrderedDict()
        if not pygame.display.get_init():pygame.display.init()
        if pygame.display.get_surface() is None:pygame.display.set_mode((1,1))

    def _image(self,path,cell=None):
        key=(str(path),None if cell is None else tuple(cell))
        if key in self.cache:self.cache.move_to_end(key);return self.cache[key]
        image=self.pygame.image.load(str(path)).convert_alpha().premul_alpha()
        if cell is not None:
            left,top,right,bottom=cell
            image=image.subsurface((left,top,right-left,bottom-top)).copy()
        self.cache[key]=image
        while len(self.cache)>32:self.cache.popitem(last=False)
        return image

    def _contact_shadows(self,picture,occlusion_depth,state,ordered):
        if state['camera']['position'][2]<=50:return picture
        result=picture.convert('RGBA')
        strength=round(105*_ease((state['camera']['position'][2]-50)/70))
        for depth,_,record,actor,root in ordered:
            world=actor['world_position_metres'];points=[]
            for i in range(20):
                a=math.tau*i/20;along=.76*math.cos(a);across=.27*math.sin(a)
                x=world[0]+.45+along*.65-across*.76
                y=world[1]+.55+along*.76+across*.65
                p=project_world([x,y,world[2]+.008],state['camera'])
                if p is not None:points.append(p[:2])
            if len(points)!=20:continue
            left=max(0,math.floor(min(p[0] for p in points))-2);right=min(960,math.ceil(max(p[0] for p in points))+3)
            top=max(0,math.floor(min(p[1] for p in points))-2);bottom=min(640,math.ceil(max(p[1] for p in points))+3)
            if right<=left or bottom<=top:continue
            mask=Image.new('L',((right-left)*4,(bottom-top)*4))
            ImageDraw.Draw(mask).polygon([((x-left)*4,(y-top)*4) for x,y in points],fill=strength)
            mask=mask.resize((right-left,bottom-top),Image.Resampling.LANCZOS)
            alpha=np.array(mask);hidden=occlusion_depth[top:bottom,left:right]<depth-.05;alpha[hidden]=0
            layer=Image.new('RGBA',(right-left,bottom-top),(0,0,0,0));layer.putalpha(Image.fromarray(alpha))
            result.alpha_composite(layer,(left,top))
        return result.convert('RGB')

    def compose(self,picture,occlusion_depth,state,records,*,shadows=True):
        from cinematic_bridge_run import CinematicBridgeRun
        pg=self.pygame
        stages={actor['id']:actor for actor in [*state['runners'],*state.get('guards',guard_states_at(state['local_time']))]}
        ordered=[]
        for record in records:
            actor=stages[record['id']];world=actor['world_position_metres']
            projected=project_world([world[0],world[1],world[2]+.9],state['camera'])
            root=project_world(world,state['camera'])
            if projected is None or root is None:continue
            ordered.append((projected[2],-world[1],record,actor,root))
        if shadows:picture=self._contact_shadows(picture,occlusion_depth,state,ordered)
        target=pg.image.frombytes(picture.tobytes(),SIZE,'RGB')
        for depth,_,record,actor,root in sorted(ordered,reverse=True,key=lambda row:row[:2]):
            image=self._image(record['path'],record.get('cell'))
            ppm=record['art_pixels_per_metre'];scale=state['camera']['focal_pixels']/depth/ppm
            anchor=record['anchor'];position=[root[0]-anchor[0]*scale,root[1]-anchor[1]*scale]
            layer=pg.Surface(SIZE,pg.SRCALPHA,32)
            CinematicBridgeRun._whole_drawing(layer,image,position,scale)
            hidden=occlusion_depth<depth-.05
            if np.any(hidden):
                rgb=pg.surfarray.pixels3d(layer);rgb[hidden.T]=0;del rgb
                alpha=pg.surfarray.pixels_alpha(layer);alpha[hidden.T]=0;del alpha
            target.blit(layer,(0,0),special_flags=pg.BLEND_PREMULTIPLIED)
        return Image.frombytes('RGB',SIZE,pg.image.tobytes(target,'RGB'))


def _confined(profile,filename):
    if not isinstance(filename,str) or Path(filename).is_absolute():raise ValueError('Art sources must be portable relative paths')
    path=(profile.parent/filename).resolve()
    if not path.is_relative_to(ROOT):raise ValueError('Art source leaves the repository')
    return path


def _figure_record(profile,data,record,actor_id):
    filename=record.get('file',record.get('source'));path=_confined(profile,filename)
    return {'id':actor_id,'path':path,'cell':record.get('cell'),
            'anchor':record.get('anchor',data.get('anchor')),
            'art_pixels_per_metre':record.get('art_pixels_per_metre',data.get('art_pixels_per_metre'))}


def party_records(index,*,frontal_reference=False):
    records=[];state=actor_states_at(index/FPS)
    for actor in state['runners']:
        if frontal_reference:
            profile=ROOT/f'assets/story/fire_veinhold_opening/shot07/characters/{actor["id"]}/animation.json'
            data=json.loads(profile.read_text());row=data['frames'][actor['frame_index']]
            records.append(_figure_record(profile,{**data,'art_pixels_per_metre':500},row,actor['id']))
            continue
        profile=ASCENT_SCENE.parent/f'characters/{actor["id"]}/actorperformance.json'
        data=json.loads(profile.read_text());transition=data['transition_frames']
        row=(transition[index] if index<len(transition) else data['overhead_cycle']['frames'][actor['frame_index']])
        records.append(_figure_record(profile,data,row,actor['id']))
    return records


@lru_cache(maxsize=1)
def _legacy_frozen():
    names=('left_back','right_mid','left_front','right_back');depths=(5.5,4.5,3.4,5.5)
    result=[]
    for i,(name,distance) in enumerate(zip(names,depths)):
        path=MATERIALS/f'frozen_guard_{name}.png';image=Image.open(path).convert('RGBA')
        box=image.getchannel('A').getbbox();w,h=box[2]-box[0],box[3]-box[1]
        # The original full-canvas projection used90° horizontalFOV. Its fixed
        # optical depth establishes density; occupied silhouette height does not.
        result.append({'id':f'carcovian_guard_{i+1}','path':path,'cell':list(box),
                       'anchor':[w/2,h],'art_pixels_per_metre':image.width/(2*distance)})
    return result


def guard_records(index,*,include_legacy_frontal=False):
    profile=ASCENT_SCENE.parent/'guards/guardperformance.json';data=json.loads(profile.read_text())
    state=guard_states_at(index/FPS);records=[];frozen={row['id']:row for row in data['frozen']}
    for actor in state:
        if actor['kind']=='frozen':
            if actor['view_elevation_degrees']<30:
                # The approved preceding seven shots omitted this distant
                # frontal layer. Preserve that exact join; the correct static
                # high-view figures return naturally with the overhead frustum.
                if include_legacy_frontal:
                    records.append(next(row for row in _legacy_frozen() if row['id']==actor['id']))
            else:records.append(_figure_record(profile,{},frozen[actor['id']],actor['id']))
        elif data.get('live'):
            live=data['live'];record=live['frames'][actor['frame_index']]
            records.append(_figure_record(profile,live,record,actor['id']))
    return records


def previs():
    write_scene();write_camera_samples()
    target=REVIEW/'previs';target.mkdir(parents=True,exist_ok=True)
    sheet=Image.new('RGB',(960*3,670*4),'#0b1828')
    for i,index in enumerate(PROOFS):
        picture=proxy_picture(index/FPS);picture.save(target/f'frame_{index:04d}.png')
        x,y=(i%3)*960,(i//3)*670;sheet.paste(picture,(x,y))
    sheet.resize((1440,1340),Image.Resampling.LANCZOS).save(target/'camera_contact.jpg',quality=92)
    print(target/'camera_contact.jpg')


def world_proofs():
    write_scene();write_camera_samples()
    renderer=WorldRenderer();target=REVIEW/'world_proofs';target.mkdir(parents=True,exist_ok=True)
    sheet=Image.new('RGB',(960*3,670*4),'#0b1828')
    for i,index in enumerate(PROOFS):
        picture,_=renderer.render(index)
        picture.save(target/f'environment_{index:04d}.png')
        x,y=(i%3)*960,(i//3)*670;sheet.paste(picture,(x,y))
        ImageDraw.Draw(sheet).text((x+8,y+646),f'{index:03d} / {index/FPS:.3f}s / ENVIRONMENT ONLY',fill='white')
    sheet.resize((1440,1340),Image.Resampling.LANCZOS).save(target/'environment_contact.jpg',quality=92)
    print(target/'environment_contact.jpg')


def entry_proofs():
    """Verify the real old-source composition before authoring new close poses."""
    from PIL import ImageChops
    write_scene();write_camera_samples()
    renderer=WorldRenderer();compositor=FigureCompositor()
    target=REVIEW/'entry_proofs';target.mkdir(parents=True,exist_ok=True)
    reference=Image.open(ROOT/'assets/story/fire_veinhold_opening/shot07/environment/frame_0300.png').convert('RGB')
    pictures=[('shot07 inclusive300',reference)]
    for index in range(8):
        env,depth=renderer.render(index)
        state=actor_states_at(index/FPS)
        image=compositor.compose(env,depth,state,[*guard_records(index),*party_records(index,frontal_reference=True)])
        image.save(target/f'frame_{index:04d}.png');pictures.append((f'shot08 reference{index:03d}',image))
        if index==0:
            diff=ImageChops.difference(reference,image)
            changed=int(np.count_nonzero(np.any(np.asarray(diff)>0,axis=2)))
            diff.save(target/'entry_difference.png')
            (target/'entry_match.json').write_bytes(_json({'changed_pixels':changed,'bounds':diff.getbbox(),
                'method':'Actual worldrenderer and original complete frontal figures through the same pygame viewport crop/smoothscale/premultiplied blend. No copied final frame.'}))
            print('Entry changed pixels:',changed)
    sheet=Image.new('RGB',(2880,2010),'#0c1a2b')
    for i,(label,image) in enumerate(pictures):
        x,y=(i%3)*960,(i//3)*670;sheet.paste(image,(x,y))
        ImageDraw.Draw(sheet).text((x+9,y+646),label,fill='white')
    sheet.resize((1440,1005),Image.Resampling.LANCZOS).save(target/'entry_contact.jpg',quality=93)
    print(target/'entry_contact.jpg')


def guard_proofs():
    write_scene();write_camera_samples();renderer=WorldRenderer();compositor=FigureCompositor()
    target=REVIEW/'guard_proofs';target.mkdir(parents=True,exist_ok=True)
    indices=(0,24,252,270,300,330,348,375,420,435,450,480)
    sheet=Image.new('RGB',(2880,2680),'#0c1a2b')
    for i,index in enumerate(indices):
        env,depth=renderer.render(index);state=actor_states_at(index/FPS)
        image=compositor.compose(env,depth,state,guard_records(index));image.save(target/f'frame_{index:04d}.png')
        x,y=(i%3)*960,(i//3)*670;sheet.paste(image,(x,y))
        ImageDraw.Draw(sheet).text((x+9,y+646),f'{index:03d} / {index/FPS:.3f}s / WORLD AND ACTUAL GUARDS; PARTY OMITTED',fill='white')
    sheet.resize((1440,1340),Image.Resampling.LANCZOS).save(target/'guard_contact.jpg',quality=93)
    print(target/'guard_contact.jpg')


def _png(image):
    stream=io.BytesIO();image.save(stream,format='PNG',compress_level=6)
    return stream.getvalue()


def _payload_entry(payload):
    return {'sha256':sha256(payload).hexdigest(),'bytes':len(payload)}


def _art_inputs():
    """Validate actual exported bytes, including early approved-source links."""
    performance_signature(ASCENT_SCENE,allowed_root=ROOT)
    scene=json.loads(ASCENT_SCENE.read_text());paths=set()
    profiles=[ASCENT_SCENE.parent/relative for relative in scene['party_performances'].values()]
    profiles.append(ASCENT_SCENE.parent/scene['guard_performance'])
    for profile in profiles:
        paths.add(profile);data=json.loads(profile.read_text())
        for filename,digest in data['source_sha256'].items():
            path=_confined(profile,filename)
            if _entry(path)['sha256']!=digest:
                raise ValueError('Actual exported art differs from its declared source hash: '+str(path.relative_to(ROOT)))
            paths.add(path)
    return paths


def _environment_inputs():
    paths={Path(__file__),ROOT/'cinematic_bridge_ascent.py',
        ROOT/'cinematic_perspective.py',ROOT/'cinematic_face_reveal.py',
        ROOT/'tools/build_prologue_face_environment.py',frontal.APPROACH_SOURCE,
        MATERIALS/'frozen_bridge_background.png'}
    paths.update(frontal.SOURCE.glob('*_generated.png'))
    paths.update(MATERIALS/(name+'.png') for name in ('steel','masonry','schist'))
    paths.update(path for path in (SOURCE/'environment').glob('*')
                 if path.suffix.lower() in ('.png','.json','.txt'))
    return paths


def _world_sources():
    return {path.relative_to(ROOT).as_posix():_entry(path) for path in sorted(_environment_inputs())}


def _sources():
    paths=_art_inputs()
    paths.update(_environment_inputs())
    paths.update((ROOT/'cinematic_bridge_run.py',ASCENT_SCENE))
    # Preserve all raw masters, complete authored frames, prompts and generation
    # records, in addition to the exact PNGs actually sampled above. Build
    # outputs and camera worksheets are excluded to avoid circular digests.
    for path in SOURCE.rglob('*'):
        if (path.is_file() and path.suffix.lower() in ('.png','.json','.txt','.py','.blend')
                and path.name not in ('performance_recipe.json','camera_authoring_samples.json')
                and '__pycache__' not in path.parts):paths.add(path)
    return {path.relative_to(ROOT).as_posix():_entry(path) for path in sorted(paths)}


def _metadata():
    rows=[]
    for index in range(COUNT):
        state=actor_states_at(index/FPS)
        rows.append({'index':index,'time_seconds':index/FPS,'global_time_seconds':47+index/FPS,
            'camera':state['camera'],'runners':state['runners'],'guards':guard_states_at(index/FPS),
            'art_sources':[{'id':record['id'],'source':record['path'].relative_to(ROOT).as_posix(),
                            'anchor':record['anchor'],'art_pixels_per_metre':record['art_pixels_per_metre']}
                           for record in [*party_records(index),*guard_records(index)]]})
    return rows


def _segment(paths):
    return {'duration_ms':8000,'frames':paths,'alarm_frames':['clear.png']*COUNT,
            'metadata_path':'cameras.json'}


def _manifest(normal,reduced):
    return {'version':1,'width':960,'height':640,'fps':60,'baked_characters':True,
        'camera_signature':camera_signature(),
        'performance_signature':performance_signature(ASCENT_SCENE,allowed_root=ROOT),
        'segments':{'bridge_ascent':_segment(normal),'bridge_ascent_reduced':_segment(reduced)}}


def _write_atomic(path,payload):
    temporary=path.with_name(path.name+'.tmp');temporary.write_bytes(payload);temporary.replace(path)


def prepare_world_cache(path):
    """Temporary environment work only; never a production picture bank."""
    target=Path(path).resolve();target.mkdir(parents=True,exist_ok=True)
    sources=_world_sources();renderer=WorldRenderer();rows=[];outputs={}
    for index in range(COUNT):
        normal,reduced,depth=renderer.render_pair(index)
        a,b=_png(normal),_png(reduced)
        normal_name=f'normal_{index:04d}.png'
        reduced_name=normal_name if a==b else f'reduced_{index:04d}.png'
        depth_name=f'depth_{index:04d}.npz'
        buffer=io.BytesIO();np.savez_compressed(buffer,raised_depth=depth);z=buffer.getvalue()
        for filename,payload in {normal_name:a,reduced_name:b,depth_name:z}.items():
            _write_atomic(target/filename,payload);outputs[filename]=_payload_entry(payload)
        rows.append({'index':index,'normal':normal_name,'reduced':reduced_name,'depth':depth_name})
        if index%30==0:print(f'Cached environment {index}/{COUNT-1}',flush=True)
    if _world_sources()!=sources:raise ValueError('World source changed during temporary cache render')
    record={'version':1,'render_size':list(SIZE),'fps':FPS,'samples':COUNT,
        'camera_signature':camera_signature(),'sources':sources,'frames':rows,'outputs':outputs}
    _write_atomic(target/'world_cache.json',_json(record))
    print('Temporary world cache ready: '+str(target),flush=True)


def _read_world_cache(path):
    target=Path(path).resolve();record=json.loads((target/'world_cache.json').read_text())
    if (record.get('version')!=1 or record.get('render_size')!=list(SIZE)
            or record.get('fps')!=FPS or record.get('samples')!=COUNT
            or record.get('camera_signature')!=camera_signature()
            or record.get('sources')!=_world_sources()
            or [row.get('index') for row in record.get('frames',[])]!=list(range(COUNT))):
        raise ValueError('Temporary world cache differs from actual current environment inputs')
    expected={row[key] for row in record['frames'] for key in ('normal','reduced','depth')}
    if set(record.get('outputs',{}))!=expected:raise ValueError('Incomplete temporary world cache')
    for filename,entry in record['outputs'].items():
        source=(target/filename).resolve()
        if not source.is_relative_to(target) or _entry(source)!=entry:
            raise ValueError('Temporary world cache bytes differ: '+filename)
    return target,record


def _cached_world(cache,index):
    target,record=cache;row=record['frames'][index]
    normal=Image.open(target/row['normal']).convert('RGB')
    reduced=(normal if row['normal']==row['reduced'] else Image.open(target/row['reduced']).convert('RGB'))
    with np.load(target/row['depth'],allow_pickle=False) as arrays:depth=arrays['raised_depth']
    if (normal.size!=SIZE or reduced.size!=SIZE or depth.shape!=SIZE[::-1]
            or depth.dtype!=np.float32 or np.any(np.isnan(depth)) or np.any(depth<0)):
        raise ValueError('Malformed temporary world cache frame')
    return normal,reduced,depth


def verify():
    """Fast strict source/output integrity check; no render or file mutations."""
    from cinematic_bridge_ascent import CinematicBridgeAscent
    from cinematic_perspective import _png_size
    recipe=json.loads((SOURCE/'performance_recipe.json').read_text())
    if ASCENT_SCENE.read_bytes()!=_json(scene_data()):raise ValueError('Stale ascent scene')
    if recipe['sources']!=_sources():raise ValueError('Ascent source ledger differs from actual current bytes')
    manifest=json.loads((OUTPUT/'manifest.json').read_text())
    normal=manifest['segments']['bridge_ascent']['frames']
    reduced=manifest['segments']['bridge_ascent_reduced']['frames']
    if manifest!=_manifest(normal,reduced):raise ValueError('Stale ascent bank manifest')
    if len(normal)!=COUNT or len(reduced)!=COUNT:raise ValueError('Incomplete ascent picture coverage')
    if normal!=[f'frame_{index:04d}.png' for index in range(COUNT)]:
        raise ValueError('Normal ascent frames do not cover every inclusive native sample')
    if any(filename not in (f'frame_{index:04d}.png',f'reduced_{index:04d}.png')
           for index,filename in enumerate(reduced)):
        raise ValueError('Reduced ascent frames do not match their exact native clock samples')
    expected=set(normal+reduced+['clear.png','cameras.json','manifest.json'])
    if set(recipe['outputs'])!=expected:raise ValueError('Ascent ledger does not cover every native output')
    for filename,entry in recipe['outputs'].items():
        path=(OUTPUT/filename).resolve()
        if not path.is_relative_to(OUTPUT.resolve()):raise ValueError('Ascent output leaves its bank')
        if _entry(path)!=entry:raise ValueError('Actual ascent output differs from recipe: '+filename)
        if path.suffix=='.png' and _png_size(path)!=SIZE:raise ValueError('Ascent output is not native960x640: '+filename)
    if (OUTPUT/'cameras.json').read_bytes()!=_json(_metadata()):raise ValueError('Stale ascent camera/art source metadata')
    owner=CinematicBridgeAscent(allowed_root=ROOT)
    owner.close()
    print(f'Verified actual raw/export sources and all{len(expected)} native bank files; both481-sample segments match current rig and art.')
    return recipe,manifest


def bake(*,proof=False,check=False,world_cache=None):
    if check:
        recipe,manifest=verify()
        indices=range(COUNT)
    else:
        write_scene();write_camera_samples()
        indices=PROOFS if proof else range(COUNT)
        recipe=None;manifest=None
    sources=_sources();metadata=_metadata()
    cache=None if world_cache is None else _read_world_cache(world_cache)
    renderer=None if cache else WorldRenderer();compositor=FigureCompositor()
    target=REVIEW/'performance_proofs'
    if not check:target.mkdir(parents=True,exist_ok=True)
    outputs={};normal_paths=[];reduced_paths=[];pictures=[]
    if not proof:OUTPUT.mkdir(parents=True,exist_ok=True)
    for index in indices:
        normal,reduced,depth=(_cached_world(cache,index) if cache else renderer.render_pair(index))
        state=actor_states_at(index/FPS);records=[*guard_records(index),*party_records(index)]
        image=compositor.compose(normal,depth,state,records)
        reduced_image=(image if normal.tobytes()==reduced.tobytes()
                       else compositor.compose(reduced,depth,state,records))
        payload=_png(image);reduced_payload=_png(reduced_image)
        normal_name=f'frame_{index:04d}.png'
        reduced_name=normal_name if payload==reduced_payload else f'reduced_{index:04d}.png'
        normal_paths.append(normal_name);reduced_paths.append(reduced_name)
        for filename,data in {normal_name:payload,reduced_name:reduced_payload}.items():
            if check:
                if (OUTPUT/filename).read_bytes()!=data:raise ValueError(f'Ascent frame{index} does not reproduce: '+filename)
            elif not proof:_write_atomic(OUTPUT/filename,data)
            outputs[filename]=_payload_entry(data)
        if index in PROOFS:
            pictures.append((index,image))
            if not check:
                image.save(target/f'frame_{index:04d}.png')
                reduced_image.save(target/f'reduced_{index:04d}.png')
        if not proof and index%30==0:print(f'{"Checked" if check else "Baked"} {index}/{COUNT-1}',flush=True)
    if _sources()!=sources:raise ValueError('Ascent sources changed during render; refusing a stale recipe')
    if proof:
        sheet=Image.new('RGB',(2880,2680),'#0c1a2b')
        for i,(index,picture) in enumerate(pictures):
            x,y=(i%3)*960,(i//3)*670;sheet.paste(picture,(x,y))
            ImageDraw.Draw(sheet).text((x+8,y+646),f'{index:03d} / {index/FPS:.3f}s / COMPLETE AUTHORED PERFORMANCE',fill='white')
        sheet.resize((1440,1340),Image.Resampling.LANCZOS).save(target/'performance_contact.jpg',quality=94)
        print(target/'performance_contact.jpg');return
    contents={'clear.png':_png(Image.new('RGBA',SIZE)),
              'cameras.json':_json(metadata),'manifest.json':_json(_manifest(normal_paths,reduced_paths))}
    for filename,payload in contents.items():
        if check:
            if (OUTPUT/filename).read_bytes()!=payload:raise ValueError('Ascent metadata does not reproduce: '+filename)
        else:_write_atomic(OUTPUT/filename,payload)
        outputs[filename]=_payload_entry(payload)
    record={'version':1,'command':'python tools/build_prologue_bridge_ascent.py --bake',
        'render_size':list(SIZE),'fps':FPS,'samples':COUNT,'duration_seconds':DURATION,
        'camera_signature':camera_signature(),
        'performance_signature':performance_signature(ASCENT_SCENE,allowed_root=ROOT),
        'sources':sources,'outputs':outputs,
        'construction':'Fixed metre-space ray/triangle world with actual volumetric rail/shore/gateway surfaces; complete authored figures uniformly sampled through production premultiplied viewport compositor. No copied endpoint picture, articulated parts, limb transforms, sprite tilts, or anatomy interpolation.',
        'entry_omission':'Approved preceding frontal shot omitted distant frozen figures/landing frost. Keep that inherited layer absent in its initial frustum; restore fixed high-view sources while outside the frame. No moved statues or anatomy fade.',
        'reduced_motion':'Same intentional camera and full run phases; steady warning luminosity. Identical native pictures are shared by path.'}
    if check:
        if record!=recipe:raise ValueError('Ascent export recipe does not reproduce')
        print('All481 normal/reduced full native pictures and their source/camera/art ledgers reproduce exactly.')
    else:
        _write_atomic(SOURCE/'performance_recipe.json',_json(record))
        print('Baked481 inclusive full native samples for both normal/reduced presentation modes.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previs',action='store_true')
    parser.add_argument('--world-proof',action='store_true')
    parser.add_argument('--entry-proof',action='store_true')
    parser.add_argument('--guard-proof',action='store_true')
    parser.add_argument('--proof',action='store_true',help='Render the actual complete approved figure performance at native checkpoints')
    parser.add_argument('--bake',action='store_true',help='Bake all481 inclusive normal/reduced native pictures')
    parser.add_argument('--check',action='store_true',help='Verify actual raw/export/output hashes then reproduce every native sample')
    parser.add_argument('--verify',action='store_true',help='Verify actual source/output hashes and complete metadata without rerendering')
    parser.add_argument('--prepare-world-cache',action='store_true',help='Cache481 environment-only views/depth in /tmp while complete figure art is authored')
    parser.add_argument('--world-cache',type=Path,help='Optional temporary environment-cache directory; never used by --check')
    args=parser.parse_args()
    operations=('previs','world_proof','entry_proof','guard_proof','proof','bake','check','verify','prepare_world_cache')
    if sum(bool(getattr(args,name)) for name in operations)!=1:parser.error('Select exactly one authoring/export operation')
    if args.world_cache is not None and not (args.proof or args.bake or args.prepare_world_cache):
        parser.error('--world-cache is only used by --proof, --bake or --prepare-world-cache; --check must render from sources')
    if args.previs:previs()
    elif args.world_proof:world_proofs()
    elif args.entry_proof:entry_proofs()
    elif args.guard_proof:guard_proofs()
    elif args.proof:bake(proof=True,world_cache=args.world_cache)
    elif args.bake:bake(world_cache=args.world_cache)
    elif args.check:bake(check=True)
    elif args.verify:verify()
    elif args.prepare_world_cache:prepare_world_cache(args.world_cache or Path('/tmp/veinhold-bridge-ascent-world'))


if __name__=='__main__':main()
