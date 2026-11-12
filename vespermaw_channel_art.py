"""Shaded elemental fur and the registered 2.5-second channel performance.

The cached material treatment applies to every original pose. The transformation
has its own complete-body acting clock, travelling ridge ignition and a fur
reveal tied to the model's 1650 ms commitment, rather than a whole-sprite flash.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pygame

ROOT=Path(__file__).resolve().parent
COLORS={'fire':((255,111,48),(255,221,141)),
        'ice':((139,209,255),(236,253,255)),
        'water':((39,143,226),(145,242,255))}
RAMPS={'fire':((45,28,31),(109,44,39),(181,70,43),(236,132,70),(255,221,171)),
       'ice':((33,42,65),(73,104,137),(127,169,200),(196,229,240),(250,253,255)),
       'water':((20,31,53),(30,64,105),(41,112,164),(75,177,207),(171,238,243))}


def smooth(q):
    q=max(0.,min(1.,q));return q*q*(3-2*q)


class VespermawChannelArt:
    def __init__(self, root=ROOT):
        self.root=Path(root)
        self.data=json.loads((self.root/'assets/combat/vespermaw/channeling/performance.json').read_text())
        self.frames=[pygame.image.load(str(self.root/f['file'])).convert_alpha() for f in self.data['frames']]
        self._tinted={};self._channels={}

    def tint(self, surface, element):
        """Retain opaque shading, eyes, outlines and details in every pose."""
        if element not in RAMPS:return surface
        # Keep the source surface in the key: temporary callers cannot recycle
        # an id into a different pose and accidentally receive an old tint.
        key=(surface,element)
        if key in self._tinted:return self._tinted[key]
        rgb=pygame.surfarray.array3d(surface).astype(float)
        light=(rgb[:,:,0]*.299+rgb[:,:,1]*.587+rgb[:,:,2]*.114)
        levels=np.array((0,65,115,175,255))
        ramp=np.array(RAMPS[element])
        material=np.stack([np.interp(light,levels,ramp[:,c]) for c in range(3)],axis=2)
        # Keep the original near-black structural lines and tiny dark eyes.
        strength=np.clip((light-28)/32,0,1)[:,:,None]*.92
        mapped=np.rint(rgb*(1-strength)+material*strength).astype(np.uint8)
        image=surface.copy();pygame.surfarray.pixels3d(image)[:]=mapped
        if len(self._tinted)>1600:self._tinted.clear()
        self._tinted[key]=image
        return image

    def _index(self, elapsed_ms):
        elapsed=max(0.,min(self.data['duration_ms']-1,float(elapsed_ms)))
        for i,frame in enumerate(self.data['frames']):
            if elapsed<frame['start_ms']+frame['duration_ms']:return i
        return len(self.frames)-1

    def anchors(self, elapsed_ms):
        return dict(self.data['frames'][self._index(elapsed_ms)]['anchors'])

    def channel_frame(self, elapsed_ms, from_element, to_element, reduced_motion=False):
        index=self._index(elapsed_ms);record=self.data['frames'][index]
        target=to_element if to_element in COLORS else 'fire'
        previous=from_element if from_element in COLORS else target
        # A positional wipe starts at the shoulder ridge and spreads through
        # fur. At commitment it has completed, matching the new damage profile.
        committed=elapsed_ms>=self.data['commit_ms']
        key=(index,previous,target, bool(reduced_motion),committed)
        if key not in self._channels:
            base=self.frames[index]
            old=self.tint(base,previous);new=self.tint(base,target)
            old_rgb=pygame.surfarray.array3d(old);new_rgb=pygame.surfarray.array3d(new)
            xx,yy=np.indices(base.get_size())
            spine=record['anchors']['spine']
            distance=np.sqrt(((xx-spine[0])*.82)**2+((yy-spine[1])*1.1)**2)
            progress=1. if committed else smooth((record['start_ms']-550)/1100)
            alpha=pygame.surfarray.array_alpha(base)
            radius=float(distance[alpha>0].max())+9
            reveal=np.clip((progress*radius-distance)/9,0,1)[:,:,None]
            if progress>=1:reveal[:]=1
            image=base.copy()
            pygame.surfarray.pixels3d(image)[:]=np.rint(old_rgb*(1-reveal)+new_rgb*reveal).astype(np.uint8)
            self._channel_highlights(image,record,target,record['start_ms'],reduced_motion)
            self._channels[key]=image
        return self._channels[key],tuple(self.data['anchor'])

    def _channel_highlights(self,image,record,element,milliseconds,reduced):
        color,hot=COLORS[element];q=milliseconds/2500
        surge=math.sin(math.pi*smooth((milliseconds-350)/1800))
        tips=record['crystal_tips']
        # Sequential point ignition and small facets are clipped to the body;
        # the silhouette and crisp native shading remain legible underneath.
        overlay=pygame.Surface(image.get_size(),pygame.SRCALPHA)
        for number,(x,y) in enumerate(tips):
            age=milliseconds-(480+number*72)
            if age<0:continue
            pulse=(.78 if reduced else .65+.35*math.sin(age/115))
            alpha=round((85+155*max(0,surge))*pulse)
            pygame.draw.circle(overlay,(*color,min(180,alpha)),(x,y),4)
            pygame.draw.line(overlay,(*hot,min(255,alpha+45)),(x,y-2),(x+1,y+2),1)
            if number:
                prior=tips[number-1]
                pygame.draw.line(overlay,(*color,min(170,alpha)),prior,(x,y),1)
        # Mask every inner highlight against opaque animal pixels.
        overlay.blit(image,(0,0),special_flags=pygame.BLEND_RGBA_MULT)
        image.blit(overlay,(0,0),special_flags=pygame.BLEND_RGBA_ADD)
        if .42<q<.91:
            mouth=record['anchors']['mouth']
            eye=(mouth[0]-10,mouth[1]-7)
            if 0<=eye[0]<image.get_width() and 0<=eye[1]<image.get_height() and image.get_at(eye).a:
                pygame.draw.line(image,hot,eye,(eye[0]+2,eye[1]),1)

    def draw_motes(self,target,foot,scale,element,elapsed_ms,reduced_motion=False,intensity=1.):
        """Distinct low-density material motion; no red lightning charge aura."""
        if element not in COLORS:return
        color,hot=COLORS[element]
        seconds=elapsed_ms/1000
        if reduced_motion:return
        layer=pygame.Surface(target.get_size(),pygame.SRCALPHA)
        for i in range(12):
            phase=(seconds*(.45 if element=='water' else .7)+i*.173)%1
            x=foot[0]+(math.sin(i*2.4+seconds*.65)*40)*scale
            y=foot[1]-(12+phase*69)*scale
            a=round(145*math.sin(math.pi*phase)*max(0,min(1,intensity)))
            point=(round(x),round(y));r=max(1,round(scale*.7))
            if element=='fire':
                pygame.draw.line(layer,(*color,a),point,(point[0]-1,point[1]+round(3*scale)),r)
                pygame.draw.circle(layer,(*hot,a),point,1)
            elif element=='ice':
                pygame.draw.line(layer,(*hot,a),(point[0]-r,point[1]),(point[0]+r,point[1]),1)
                pygame.draw.line(layer,(*color,a),(point[0],point[1]-r),(point[0],point[1]+r),1)
            else:
                pygame.draw.circle(layer,(*color,a),point,r+1,1)
                pygame.draw.circle(layer,(*hot,a),(point[0]-1,point[1]-1),1)
        target.blit(layer,(0,0))
