"""An authored ground seal that constructs its strokes at a fixed world size.

The source drawing never changes scale.  Per-pixel arrival times trace its
central seal, branching filigree, counter-rotating rings and successive glyphs.
Camera rays project the same ground coordinates throughout the reveal.
"""
from __future__ import annotations

from collections import OrderedDict
import json
import math
from pathlib import Path

import numpy as np
import pygame


class RuneSeal:
    START = 16.3
    DURATION = 1.3
    WORLD_RADIUS = 8.2
    CENTER = (-3., .035, 0.)
    REVEAL_STEPS = 48

    def __init__(self, asset_path):
        self.asset_path = Path(asset_path)
        meta_path = self.asset_path.with_suffix('.json')
        self.metadata = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        image = pygame.image.load(str(self.asset_path)).convert_alpha()
        if image.get_width() != image.get_height() or image.get_width() > 1024:
            raise ValueError('The rune must have a square authored canvas no larger than 1024 pixels')
        # This is a one-time asset registration, never an animation transform.
        self.size = min(512, image.get_width())
        ratio = self.size/image.get_width()
        if ratio != 1:
            image = pygame.transform.scale(image, (self.size, self.size))
        self.texture_center = np.array(self.metadata.get('center', [image.get_width()/2]*2), dtype=np.float32)*ratio
        self.art_radius = float(self.metadata.get('outer_radius_px', image.get_width()*.42))*ratio
        if not 0 < self.art_radius <= self.size/2:
            raise ValueError('Invalid rune artwork radius')
        self.rgb = pygame.surfarray.array3d(image).astype(np.float32)
        self.alpha = pygame.surfarray.array_alpha(image)
        self.stroke = self.alpha > 32
        if not self.stroke.any():
            raise ValueError('Rune artwork has no visible strokes')
        x,y = np.indices((self.size, self.size), dtype=np.float32)
        x=(x-self.texture_center[0])/self.art_radius
        y=(y-self.texture_center[1])/self.art_radius
        self.radius = np.sqrt(x*x+y*y)
        self.angle = np.arctan2(y,x)
        self.arrival = self._arrival_field(self.radius, self.angle)
        self.textures = []
        self.stroke_count = int(np.count_nonzero(self.stroke))
        for index in range(self.REVEAL_STEPS):
            progress=index/(self.REVEAL_STEPS-1)
            clock=progress*self.DURATION
            reveal=np.clip((clock-self.arrival)/.035,0,1)
            if index == self.REVEAL_STEPS-1:
                reveal[:]=1
            alpha=np.round(self.alpha*reveal).astype(np.uint8)
            hot=np.exp(-((clock-self.arrival-.014)/.038)**2)*self.stroke
            if index == self.REVEAL_STEPS-1:
                hot[:]=0
            surface=pygame.Surface((self.size,self.size),pygame.SRCALPHA)
            surface.fill((255,255,255,0))
            pygame.surfarray.pixels_alpha(surface)[:]=alpha
            soft=pygame.transform.smoothscale(surface,(max(16,self.size//16),)*2)
            soft=pygame.transform.smoothscale(soft,(self.size,self.size))
            glow=pygame.surfarray.array_alpha(soft).astype(np.float32)/255*.55
            core=alpha.astype(np.float32)/255
            ink=self.rgb*(1-hot[:,:,None]*.45)+np.array((255.,218.,137.),dtype=np.float32)*hot[:,:,None]*.45
            combined_alpha=core+glow*(1-core)
            premultiplied=ink*core[:,:,None]+np.array((250.,51.,60.),dtype=np.float32)*glow[:,:,None]*(1-core[:,:,None])
            rgba=np.empty((self.size,self.size,4),dtype=np.uint8)
            rgba[:,:,:3]=np.clip(premultiplied,0,255).astype(np.uint8)
            rgba[:,:,3]=np.round(combined_alpha*255).astype(np.uint8)
            # Filter premultiplied pixels once. Sampling these mip levels keeps
            # small glyphs stable without twelve bilinear lookups every draw.
            texture=pygame.Surface((self.size,self.size),pygame.SRCALPHA)
            pygame.surfarray.pixels3d(texture)[:]=rgba[:,:,:3]
            pygame.surfarray.pixels_alpha(texture)[:]=rgba[:,:,3]
            levels=[rgba]
            for divisor in (2,4):
                mip=pygame.transform.smoothscale(texture,(self.size//divisor,)*2)
                packed=np.empty((self.size//divisor,self.size//divisor,4),dtype=np.uint8)
                packed[:,:,:3]=pygame.surfarray.array3d(mip)
                packed[:,:,3]=pygame.surfarray.array_alpha(mip)
                levels.append(packed)
            self.textures.append(tuple(levels))
        self._projection_cache=OrderedDict()
        self._screen_cache={}

    def _arrival_field(self, radius, angle):
        """Seconds from ignition; angular travel follows the authored ring bands."""
        top=-math.pi/2
        cw=((angle-top)%(math.tau))/math.tau
        ccw=((top-angle)%(math.tau))/math.tau
        spoke_phase=((angle-top+math.pi/6)%(math.pi/3)-math.pi/6)/(math.pi/6)
        side_branch=np.abs(spoke_phase)
        # The six principal branches lead their shorter offshoots.  Every
        # revealed pixel still belongs to an actual stroke in the source art.
        arrival=.035+.50*np.minimum(radius/.82,1)**.86+.105*side_branch
        center=radius<.31
        arrival[center]=.015+.15*(radius[center]/.31)+.035*side_branch[center]
        inner=.50+.47*cw
        outer=.56+.46*ccw
        inner_band=(radius>=.79)&(radius<.85)
        glyph_band=(radius>=.85)&(radius<=.925)
        outer_band=radius>.925
        arrival=np.where(inner_band,inner,arrival)
        arrival=np.where(glyph_band,np.minimum(inner,outer)+.035,arrival)
        arrival=np.where(outer_band,outer,arrival)
        # Normalized drawing times finish together after a brief closure accent.
        return (np.clip(arrival,0,1.05)/1.05*self.DURATION).astype(np.float32)

    def reveal_mask(self, time):
        """The fixed-coordinate stroke mask, without glow or completion pulses."""
        local=float(time)-self.START
        return self.stroke & (self.arrival <= local) if local>=0 else np.zeros_like(self.stroke)

    def state(self, time):
        local=float(time)-self.START
        progress=max(0.,min(1.,local/self.DURATION))
        stage=('dormant' if local<0 else 'ignition' if progress<.15 else
               'branches' if progress<.48 else 'rings' if progress<1 else 'complete')
        coverage=float(np.count_nonzero(self.reveal_mask(time))/self.stroke_count)
        return dict(world_radius=self.WORLD_RADIUS,center=list(self.CENTER),
                    progress=progress,stage=stage,coverage=coverage,
                    complete_at=self.START+self.DURATION,
                    geometry_scale=1.)

    def _projection(self, canvas, camera):
        """Map view pixels onto the same horizontal ground seal on every frame."""
        width,height=canvas.get_size()
        key=tuple(camera.position)+tuple(camera.target)+(camera.focal,*camera.center,width,height)
        if key in self._projection_cache:
            value=self._projection_cache.pop(key);self._projection_cache[key]=value
            return value
        # Crop to the projected texture square when it is entirely in front of
        # the lens; near-camera ground views retain the full safe viewport.
        half=self.size/2/self.art_radius*self.WORLD_RADIUS
        corners=[camera.project((self.CENTER[0]+x,self.CENTER[1],self.CENTER[2]+z))
                 for x,z in ((-half,-half),(half,-half),(half,half),(-half,half))]
        if all(corners):
            diameter=max(max(p[0] for p in corners)-min(p[0] for p in corners),
                         max(p[1] for p in corners)-min(p[1] for p in corners))
            x0=max(0,math.floor(min(point[0] for point in corners))-3)
            x1=min(width,math.ceil(max(point[0] for point in corners))+4)
            y0=max(0,math.floor(min(point[1] for point in corners))-3)
            y1=min(height,math.ceil(max(point[1] for point in corners))+4)
        else:
            diameter=self.size*2
            x0,y0,x1,y1=0,0,width,height
        if x1<=x0 or y1<=y0:
            return None
        grid_key=(width,height)
        if grid_key not in self._screen_cache:
            self._screen_cache[grid_key]=(np.arange(width,dtype=np.float32)[:,None],
                                          np.arange(height,dtype=np.float32)[None,:])
        grid_x,grid_y=self._screen_cache[grid_key]
        u=(grid_x[x0:x1]-camera.center[0])/camera.focal
        v=(camera.center[1]-grid_y[:,y0:y1])/camera.focal
        right,up,forward=camera.basis()
        ray_y=forward.y+right.y*u+up.y*v
        distance=(self.CENTER[1]-camera.position[1])/np.minimum(ray_y,-.0001)
        wx=camera.position[0]+distance*(forward.x+right.x*u+up.x*v)
        wz=camera.position[2]+distance*(forward.z+right.z*u+up.z*v)
        tx=(wx-self.CENTER[0])*self.art_radius/self.WORLD_RADIUS+self.texture_center[0]
        ty=(wz-self.CENTER[2])*self.art_radius/self.WORLD_RADIUS+self.texture_center[1]
        valid=(ray_y<-.001)&(distance>0)&(tx>=0)&(tx<self.size-1)&(ty>=0)&(ty<self.size-1)
        level=2 if diameter<self.size*.375 else 1 if diameter<self.size*.75 else 0
        divisor=2**level
        limit=self.size//divisor-1
        ix=np.clip(np.rint(tx/divisor),0,limit).astype(np.int32)
        iy=np.clip(np.rint(ty/divisor),0,limit).astype(np.int32)
        value=(x0,y0,x1,y1,ix,iy,valid,level)
        if len(self._projection_cache)>=4:self._projection_cache.popitem(last=False)
        self._projection_cache[key]=value
        return value

    def draw(self, canvas, camera, time, reduced=False):
        if time<self.START+.015:return
        progress=max(0.,min(1.,(time-self.START)/self.DURATION))
        projected=self._projection(canvas,camera)
        if projected is None:return
        x0,y0,x1,y1,ix,iy,valid,level=projected
        if reduced:
            index=self.REVEAL_STEPS-1
            fade=min(1.,max(0.,(time-self.START)/.22))*.78
        else:
            index=min(self.REVEAL_STEPS-1,int(progress*(self.REVEAL_STEPS-1)))
            fade=1.
        ink=self.textures[index][level][ix,iy].copy()
        ink[~valid]=0
        local=time-self.START-self.DURATION
        completion=0. if reduced or local<0 else math.exp(-((local-.12)/.16)**2)
        pulse=1. if reduced else .96+.035*math.sin((time-self.START)*2.4)+.065*completion
        gain=max(0,min(280,round(fade*pulse*256)))
        if gain!=256:
            ink=np.minimum((ink.astype(np.uint32 if gain>256 else np.uint16)*gain)>>8,255).astype(np.uint8)
        projected_ink=pygame.Surface((x1-x0,y1-y0),pygame.SRCALPHA)
        pygame.surfarray.pixels3d(projected_ink)[:]=ink[:,:,:3]
        pygame.surfarray.pixels_alpha(projected_ink)[:]=ink[:,:,3]
        canvas.blit(projected_ink,(x0,y0),special_flags=pygame.BLEND_PREMULTIPLIED)
        self._embers(canvas,camera,time,reduced)

    def _embers(self, canvas, camera, time, reduced):
        if reduced:return
        local=time-self.START
        for index in range(15):
            birth=.35+index*.037
            age=local-birth
            if age<0 or age>2.3:continue
            angle=index*2.399963
            radial=(1+index%5)*1.25
            point=(self.CENTER[0]+math.cos(angle)*radial,
                   self.CENTER[1]+age*(.55+index%3*.14),
                   self.CENTER[2]+math.sin(angle)*radial)
            p=camera.project(point)
            if p is not None:
                pygame.draw.circle(canvas,('#ff866b','#ffd0a0','#f84a61')[index%3],
                                   (round(p[0]),round(p[1])),1+int(index%4==0))
