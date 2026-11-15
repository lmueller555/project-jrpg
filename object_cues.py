"""State-aware object discovery, drawn in the object's normal world depth pass."""
import hashlib
import math

import pygame
from rendering import WorldCanvas, SurfaceCache, artwork


class ObjectCues:
    ENTER_DISTANCE=10.
    EXIT_DISTANCE=12.
    FADE_SECONDS=.12
    GLINT_SECONDS=.28

    def __init__(self,records=()):
        self.records=tuple(records)
        self.states={}
        self.clock=0.
        self.enabled=False
        self.reduced_motion=False
        self.cache=SurfaceCache(8*1024*1024)

    def reset(self):
        self.states.clear();self.clock=0.;self.enabled=False

    @staticmethod
    def timing(identifier):
        seed=int.from_bytes(hashlib.sha256(identifier.encode()).digest()[:4],'big')
        period=3+(seed%2001)/1000
        offset=period*(.15+((seed>>12)%501)/1000)
        return period,offset

    @staticmethod
    def nearest_boundary(position,boundary):
        x,y,w,h=boundary
        return pygame.Vector2(max(x,min(x+w,position[0])),max(y,min(y+h,position[1])))

    @staticmethod
    def clear_approach(world,start,end):
        delta=end-start
        # Include every approach sample, stopping only at the support edge.
        count=math.ceil(delta.length())
        for index in range(count):
            point=start+delta*(index/max(1,count))
            x,y=round(point.x),round(point.y)
            if not (0<=x<world.size[0] and 0<=y<world.size[1]):return False
            if world.blocked.get_at((x,y)):return False
        return True

    def update(self,seconds,world,player,conditions,enabled=True,reduced_motion=False):
        self.enabled=bool(enabled);self.reduced_motion=reduced_motion
        available={r['entity']:r for r in self.records if r['available_when'] in conditions}
        # Exhausted/inapplicable actions lose all cues immediately, including on
        # save restoration. Cue state is presentation only, never a quest receipt.
        self.states={key:state for key,state in self.states.items() if key in available}
        if not enabled:return
        self.clock+=max(0,seconds)
        for key,record in available.items():
            state=self.states.setdefault(key,{'near':False,'alpha':0.,'record':record})
            closest=self.nearest_boundary(player.position,record['interaction_boundary'])
            distance=player.position.distance_to(closest)
            threshold=self.EXIT_DISTANCE if state['near'] else self.ENTER_DISTANCE
            state['near']=(distance<=threshold and self.clear_approach(world,player.position,closest))
            goal=1. if state['near'] else 0.
            step=max(0,seconds)/self.FADE_SECONDS
            state['alpha']+=max(-step,min(step,goal-state['alpha']))

    def _outline(self,surface):
        found=self.cache.get(surface)
        if found is not None:return found
        image=surface.native if isinstance(surface,WorldCanvas) else pygame.transform.scale(
            surface,(surface.get_width()*2,surface.get_height()*2))
        mask=pygame.mask.from_surface(image)
        expanded=pygame.Mask((image.get_width()+4,image.get_height()+4))
        for dx,dy in ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)):
            expanded.draw(mask,(2+dx,2+dy))
        expanded.erase(mask,(2,2))
        result=artwork(expanded.to_surface(setcolor=(244,211,92,255),unsetcolor=(0,0,0,0)),2)
        self.cache[surface]=result
        return result

    def draw_outline(self,target,entity,surface,position):
        state=self.states.get(entity['id'])
        if not self.enabled or state is None or state['alpha']<=0:return
        outline=self._outline(surface)
        outline.set_alpha(round(255*state['alpha']))
        target.blit(outline,(position[0]-1,position[1]-1))

    def draw_glint(self,target,entity,surface,position):
        state=self.states.get(entity['id'])
        if not self.enabled or state is None:return
        period,offset=self.timing(state['record']['id'])
        phase=(self.clock+offset)%period
        opacity=(.35 if self.reduced_motion else
                 max(0,1-abs(phase/self.GLINT_SECONDS*2-1)) if phase<self.GLINT_SECONDS else 0)
        if not opacity:return
        # A tiny seven-render-pixel cross, never an object-wide pulse or glow.
        image=pygame.Surface((8,8),pygame.SRCALPHA)
        color=(255,232,156,round(220*opacity))
        pygame.draw.line(image,color,(3,0),(3,6))
        pygame.draw.line(image,color,(0,3),(6,3))
        image.set_at((3,3),(255,255,235,round(255*opacity)))
        glint=artwork(image,2)
        x,y=state['record']['glint_anchor']
        target.blit(glint,(position[0]+x-1.5,position[1]+y-1.5))
