"""Georeferenced, deterministic bird-led camera prelude for Aldric's arrival.

Painted landscape planes share the regional tile coordinates. A four-point
projection keeps the gate and arriving party registered during the descent;
no camera, bird or simulation clock advances from drawing a frame.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pygame

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT/'assets/story/regent_aerial'
PHASES = ('aerial_region', 'aerial_bank', 'aerial_gate', 'aerial_descent')
DURATIONS = (12., 4., 6., 6.)
DURATION = sum(DURATIONS)
SIZE = (480, 320)


def ease(value):
    x = max(0., min(1., value))
    return x*x*x*(x*(x*6-15)+10)


def lerp(a, b, amount):
    return a+(b-a)*amount


def hermite(a, b, va, vb, t, seconds):
    return ((2*t**3-3*t*t+1)*np.asarray(a)+(t**3-2*t*t+t)*seconds*np.asarray(va)
            +(-2*t**3+3*t*t)*np.asarray(b)+(t**3-t*t)*seconds*np.asarray(vb))


def homography(source, target):
    rows, rhs = [], []
    for (x,y),(u,v) in zip(source,target):
        rows.extend(((x,y,1,0,0,0,-u*x,-u*y), (0,0,0,x,y,1,-v*x,-v*y)))
        rhs.extend((u,v))
    return np.append(np.linalg.solve(np.asarray(rows), np.asarray(rhs)),1.).reshape(3,3)


def project(matrix, point):
    p = matrix@np.array((point[0],point[1],1.))
    return [float(p[0]/p[2]),float(p[1]/p[2])]


class RegentAerial:
    def __init__(self, owner):
        self.owner = owner
        self.planes = None
        self.actors = {}
        self.manifest = None
        self.canopy = None
        self._canopy_cache = None
        yy,xx = np.mgrid[0:SIZE[1],0:SIZE[0]]
        self.grid = np.stack((xx.ravel(),yy.ravel(),np.ones(xx.size)))
        self.layer = pygame.Surface(SIZE)
        self.alpha_layer = pygame.Surface(SIZE,pygame.SRCALPHA)
        self.ground = pygame.Surface(SIZE)

    @staticmethod
    def _bird_path(seconds):
        t = max(0.,min(DURATION,float(seconds)))
        if t <= 12:return np.array((105-53*t/12,-28.))
        if t <= 16:return hermite((52,-28),(28,-4),(-53/12,0),(0,12),(t-12)/4,4)
        if t <= 22:return hermite((28,-4),(28,104),(0,12),(0,18),(t-16)/6,6)
        return hermite((28,104),(28,154),(0,18),(0,10),(t-22)/6,6)

    @staticmethod
    def _stage(seconds):
        return PHASES[next((i for i,v in enumerate((12,16,22,28)) if seconds<v),3)]

    def sample(self, seconds, reduced_motion=False):
        actual = max(0.,min(DURATION,float(seconds)))
        stage = self._stage(actual)
        # Reduced motion uses a composed, stable view for each beat. Wingbeats
        # remain independent from the restrained camera's fixed spatial sample.
        t = {'aerial_region':6.,'aerial_bank':14.,'aerial_gate':21.4,
             'aerial_descent':27.999999}[stage] if reduced_motion else actual
        if reduced_motion and actual >= DURATION:t = DURATION
        bird = self._bird_path(t)
        delta = self._bird_path(min(28.,t+.001))-self._bird_path(max(0.,t-.001))
        heading = math.degrees(math.atan2(float(delta[0]),-float(delta[1])))
        sway = 0. if reduced_motion else math.sin(t*1.17)*.85
        bird = bird+np.array((sway, math.sin(t*.73)*.22 if not reduced_motion else 0.))
        lag = 0. if reduced_motion else math.sin((t-.38)*1.17)*.65
        keys = ((0,25,-10,270,132,.16),(12,-28,-10,250,132,.16),
                (16,28,14,140,90,.16),(22,28,100,52,34,.16),(28,29.5,100,13,6,.55))
        for a,b in zip(keys,keys[1:]):
            if t <= b[0]:
                f=ease((t-a[0])/(b[0]-a[0]));values=[lerp(x,y,f) for x,y in zip(a[1:],b[1:])];break
        else:values=list(keys[-1][1:])
        focus_x,focus_y,span,altitude,tilt=values
        if t <= 22:
            focus_x = float(self._bird_path(max(0.,t-.38))[0])-80*(1-ease((t-12)/4))+lag*.32
        else:focus_x += lag*.32*(1-ease((t-22)/6))
        if t <= 16:focus_y = float(bird[1]+18)
        elif t <= 22:focus_y = float(bird[1]+lerp(18,-4,(t-16)/6))
        else:
            edge_y=float(self._bird_path(22)[1])+math.sin(22*.73)*.22-4
            focus_y=lerp(edge_y,100,ease((t-22)/6))
        focus_y += math.sin((t-.3)*.73)*.12 if not reduced_motion else 0.
        # The diagnostic camera is the very same ground-track state used by
        # the perspective projection, with its north-looking elevation offset.
        camera_x = focus_x;camera_y = focus_y+altitude*.25
        roll=0. if reduced_motion else math.sin((t-.38)*1.17)*.65
        bank=(-22*math.sin(math.pi*(t-12)/4) if 12<t<16 else math.sin(t*1.17)*3)
        if reduced_motion:bank=0.
        view={'focus':[focus_x,focus_y],'span':span,'tilt':tilt,'roll':roll}
        bx,by = self._project_world(bird,view)
        by -= 36+altitude*.08
        mix=1. if t>=23.45 else 0.
        canopy_surface,canopy_coverage=self._canopy_frame(t) if t>=23.0 else (None,0.)
        actors=self._actors_sample(t,view)
        viewport=self.ground_viewport(t) if mix else None
        if mix and reduced_motion:viewport=[380.,140.,480.,320.]
        if mix:
            vx,vy,vw,vh=viewport
            scale_x,scale_y=480/vw,320/vh
            hold=min(8.,max(0.,28-t)*40)
            native={'aldric':[725+hold,375],'caravan':[905+hold,375],
                    'guard_west':[530,375],'guard_east':[690,345]}
            for key,p in native.items():
                actors[key].update(screen_xy=[(p[0]-vx)*scale_x,(p[1]-vy)*scale_y],
                                   view='ground',scale=scale_x,standing=t<27.8)
                if key=='aldric':actors[key]['world_xy']=[29+hold*.02,104]
                if key=='caravan':actors[key]['world_xy']=[32+hold*.02,105.5]
        landmarks={key:self._project_world(p,view) for key,p in
                   {'south_gate':[28,96],'west_post':[26,96],'east_post':[30,96],
                    'eldenmere':[12,-28],'broken_bridge':[-111,30]}.items()}
        if mix:
            landmarks={key:[(p[0]-vx)*scale_x,(p[1]-vy)*scale_y] for key,p in
                       {'south_gate':[575,292],'west_post':[481,296],'east_post':[670,287]}.items()}
        return {'stage':stage,'seconds':actual,'spatial_seconds':t,
                'bird':{'world_xy':[float(x) for x in bird],'altitude':float(altitude*.82),
                        'heading':heading,'bank':bank,'screen_xy':[bx,by]},
                'camera':{'world_xy':[camera_x,camera_y],'altitude':altitude,
                          'target_xy':[focus_x,focus_y],'roll':roll,
                          'projection':'ground_plate' if mix else 'geographic_plane',
                          'plate_viewport':viewport},
                'view':view,'ground_viewport':viewport,'ground_mix':mix,'ground_handoff':bool(mix),
                'canopy':{'progress':max(0.,min(1.,(t-23.0)/.9)),
                          'coverage':canopy_coverage,'full_occlusion':canopy_coverage==1.,
                          'world_anchor':[25,96]},'projected_actors':actors,
                'landmarks':landmarks}

    @staticmethod
    def _view_matrix(view):
        cx,cy=view['focus'];span=view['span'];height=span*SIZE[1]/SIZE[0]
        source=((cx-span/2,cy-height/2),(cx+span/2,cy-height/2),
                (cx+span/2,cy+height/2),(cx-span/2,cy+height/2))
        inset=SIZE[0]*view['tilt']*.22
        target=((inset,-8),(SIZE[0]-inset,-8),(SIZE[0]+inset,328),(-inset,328))
        h=homography(source,target)
        angle=math.radians(view['roll']);c,s=math.cos(angle),math.sin(angle)
        r=np.array(((c,-s,240-240*c+160*s),(s,c,160-240*s-160*c),(0,0,1)))
        return r@h

    def _project_world(self, point, view):return project(self._view_matrix(view),point)

    def _actors_sample(self,t,view):
        f=ease((t-16)/12)
        positions={'aldric':[29,lerp(110,104,f)],'caravan':[32,lerp(114,105.5,f)],
                   'guard_west':[26,93],'guard_east':[31,92]}
        result={}
        for key,world in positions.items():
            result[key]={'world_xy':world,'screen_xy':self._project_world(world,view),
                         'view':'overhead','scale':min(1.4,max(.12,480/view['span']*.055))}
        return result

    def _load(self):
        if self.planes is not None:return
        path=ASSETS/'landscape/manifest.json'
        self.manifest=json.loads(path.read_text())
        self.planes={}
        for key in ('region','gate_overhead','gate_oblique'):
            if key not in self.manifest:continue
            item=self.manifest[key]
            image=pygame.image.load(str(path.parent/item['file'])).convert()
            self.planes[key]={'image':image,'pixels':pygame.surfarray.array3d(image),**item}
        path=ASSETS/'actors/manifest.json'
        actors=json.loads(path.read_text())['actors']
        for key,name in actors.items():
            source=path.parent/name;data=json.loads(source.read_text());folder=source.parent
            poses={p:pygame.image.load(str(folder/f)).convert_alpha() for p,f in data['poses'].items()}
            loops={p:[(pygame.image.load(str(folder/f['file'])).convert_alpha(),f['duration_ms']/1000)
                      for f in seq] for p,seq in data.get('loops',{}).items()}
            self.actors[key]={**data,'poses':poses,'loops':loops}

    @staticmethod
    def _texture_matrix(plane,world_matrix):
        x,y,w,h=plane['bounds_tiles'];tw,th=plane['image'].get_size()
        pixel_to_world=np.array(((w/tw,0,x),(0,h/th,y),(0,0,1)))
        return world_matrix@pixel_to_world

    def _warp(self,plane,matrix,background=None,feather=False,feather_radius=100):
        inverse=np.linalg.inv(matrix);coords=inverse@self.grid
        valid=np.abs(coords[2])>1e-8
        denominator=np.where(valid,coords[2],1.)
        xs=np.nan_to_num(coords[0]/denominator,nan=-1e6,posinf=1e6,neginf=-1e6)
        ys=np.nan_to_num(coords[1]/denominator,nan=-1e6,posinf=1e6,neginf=-1e6)
        x=np.rint(np.clip(xs,-1e6,1e6)).astype(np.int32)
        y=np.rint(np.clip(ys,-1e6,1e6)).astype(np.int32)
        pixels=plane['pixels'];valid &= (x>=0)&(y>=0)&(x<pixels.shape[0])&(y<pixels.shape[1])
        rgb=pixels[np.clip(x,0,pixels.shape[0]-1),np.clip(y,0,pixels.shape[1]-1)].copy()
        if feather:
            edge=np.minimum.reduce((xs,ys,pixels.shape[0]-1-xs,pixels.shape[1]-1-ys))
            alpha=(np.clip(edge/feather_radius,0,1)*255 if feather_radius else np.full(len(x),255.))
            alpha[~valid]=0
            if 'alpha' in plane:
                alpha*=plane['alpha'][np.clip(x,0,pixels.shape[0]-1),np.clip(y,0,pixels.shape[1]-1)]/255
            pygame.surfarray.blit_array(self.alpha_layer,rgb.reshape(SIZE[1],SIZE[0],3).transpose(1,0,2))
            target=pygame.surfarray.pixels_alpha(self.alpha_layer)
            target[:]=alpha.reshape(SIZE[1],SIZE[0]).T.astype(np.uint8);del target
            return self.alpha_layer
        pygame.surfarray.blit_array(self.layer,rgb.reshape(SIZE[1],SIZE[0],3).transpose(1,0,2))
        return self.layer

    @staticmethod
    def ground_viewport(t):
        amount=ease((t-23.45)/(28-23.45))
        return [lerp(a,b,amount) for a,b in zip((320,50,640,426),(400,140,480,320))]

    def _sprite(self,canvas,key,pose,point,scale,clock,angle=0,size=None):
        data=self.actors[key]
        if pose in data['loops']:
            seq=data['loops'][pose];time=clock%sum(d for _,d in seq);image=seq[-1][0]
            for frame,duration in seq:
                if time<duration:image=frame;break
                time-=duration
        else:image=data['poses'][pose]
        factor=np.array((scale,scale))
        if size is not None:
            box=image.get_bounding_rect();factor=np.asarray(size)/[max(1,box.width),max(1,box.height)]
        anchor=np.asarray(data['anchor'])*factor
        image=pygame.transform.scale(image,(max(1,round(image.get_width()*factor[0])),max(1,round(image.get_height()*factor[1]))))
        if angle:
            # Bird is registered at its torso; rotations do not orbit the canvas.
            image=pygame.transform.rotate(image,angle);rect=image.get_rect(center=(round(point[0]),round(point[1])))
        else:rect=image.get_rect(topleft=(round(point[0]-anchor[0]),round(point[1]-anchor[1])))
        canvas.blit(image,rect)

    def _load_canopy(self):
        if self.canopy is not None:return
        path=ASSETS/'landscape/manifest.json'
        if not path.is_file():return
        data=json.loads(path.read_text());spec=data.get('foreground_canopy',data.get('canopy'))
        if spec is None:return
        source=pygame.image.load(str(path.parent/spec['file']))
        x,y,w,h=spec['coverage_rect'];factor=max(600/w,400/h,.8)
        if factor>4:raise ValueError('Canopy opaque area is too small for a bounded foreground pass')
        image=pygame.transform.scale(source,(round(source.get_width()*factor),round(source.get_height()*factor)))
        self.canopy={'image':image,'anchor':((x+w/2)*factor,(y+h/2)*factor)}

    def _canopy_frame(self,t):
        if not 23.0<=t<=23.9:return None,0.
        self._load_canopy()
        if self.canopy is None:return None,0.
        if self._canopy_cache is not None and self._canopy_cache[0]==t:
            return self._canopy_cache[1:]
        if t<23.35:travel=lerp(-800,-8,ease((t-23.0)/.35))
        elif t<=23.55:travel=lerp(-8,8,(t-23.35)/.2)
        else:travel=lerp(8,800,ease((t-23.55)/.35))
        image=self.canopy['image'];ax,ay=self.canopy['anchor']
        frame=pygame.Surface(SIZE,pygame.SRCALPHA)
        frame.blit(image,(round(240-ax+travel),round(160-ay+travel*.5)))
        coverage=float(np.count_nonzero(pygame.surfarray.array_alpha(frame)==255)/(SIZE[0]*SIZE[1]))
        self._canopy_cache=(t,frame,coverage)
        return frame,coverage

    def _closed_gate(self,canvas,snapshot):
        if snapshot['spatial_seconds']<19:return
        west=self._project_world((26.4,96),snapshot['view'])
        east=self._project_world((29.6,96),snapshot['view'])
        width=max(1,round(math.dist(west,east)))
        source=self.owner.scenery['gate']['gate_leaf']['image']
        image=pygame.transform.scale(source,(width,2))
        angle=-math.degrees(math.atan2(east[1]-west[1],east[0]-west[0]))
        image=pygame.transform.rotate(image,angle)
        canvas.blit(image,image.get_rect(center=(round((west[0]+east[0])/2),round((west[1]+east[1])/2-1))))

    def draw(self,canvas,seconds,draw_ground,reduced_motion=False):
        self._load();snapshot=self.sample(seconds,reduced_motion);t=snapshot['spatial_seconds']
        if snapshot['ground_handoff']:
            draw_ground(canvas,min(0.,t-DURATION),viewport=snapshot['ground_viewport'],standing=t<27.8)
        else:
            region=self.planes['region'];h=self._texture_matrix(region,self._view_matrix(snapshot['view']))
            canvas.blit(self._warp(region,h),(0,0))
            local=self.planes.get('gate_overhead')
            if local is not None and t>19:
                image=self._warp(local,self._texture_matrix(local,self._view_matrix(snapshot['view'])),feather=True).copy()
                image.set_alpha(round(255*ease((t-19)/3)));canvas.blit(image,(0,0))
            self._closed_gate(canvas,snapshot)
            if t>18:
                for key,item in sorted(snapshot['projected_actors'].items(),key=lambda pair:pair[1]['screen_xy'][1]):
                    actor='guard' if key.startswith('guard') else key
                    self._sprite(canvas,actor,'overhead',item['screen_xy'],item['scale'],seconds)
            bird=snapshot['bird']
            if -80<bird['screen_xy'][1]<400:
                pose='flap_north'
                if abs(bird['bank'])>10:pose='bank_left_north' if bird['bank']<0 else 'bank_right_north'
                scale=.82+(.08*ease((t-22)/4) if t>22 else 0)
                self._sprite(canvas,'bird',pose,bird['screen_xy'],scale,seconds,-bird['heading']+bird['bank']*.3)
        canopy,coverage=self._canopy_frame(t)
        if canopy is not None:canvas.blit(canopy,(0,0))
        if t>=DURATION-1e-5:draw_ground(canvas,0.)
