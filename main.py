"""Run the playable Eldenmere town: python main.py."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
try:
    import pygame
except ModuleNotFoundError:
    raise SystemExit('Install the game dependencies first: python -m pip install -r requirements.txt')

from npc_routines import Gardener
from well_routine import DrawingWell

ROOT=Path(__file__).resolve().parent
MAP_FILE=ROOT/'assets/maps/eldenmere/playable/map.json'
VIEW_SIZE=(480,320)
WINDOW_SIZE=(960,640)
WALK_SPEED=72.0
RUN_MULTIPLIER=1.5


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


class Door:
    """A reversible proximity animation and directional doorway contact sensor."""
    def __init__(self,record,world):
        self.data=record
        self.frames=[world.image(p) for p in record['frames']]
        self.progress=0.0
        self.target_open=False

    @property
    def state(self):
        if self.target_open:return 'open' if self.progress>=4 else 'opening'
        return 'closed' if self.progress<=0 else 'closing'

    def update(self,position,seconds):
        if position is None:self.target_open=False
        else:
            delta=pygame.Vector2(position)-self.data['anchor']
            front=delta.y>=-4 if self.data['entry_side']=='north' else delta.y<=4
            radius=self.data['close_radius'] if self.target_open else self.data['open_radius']
            self.target_open=front and delta.length_squared()<=radius*radius
        step=seconds*1000/self.data['frame_duration_ms']
        self.progress=max(0.0,min(4.0,self.progress+(step if self.target_open else -step)))

    def image(self):
        return self.frames[min(4,int(self.progress+1e-7))] if self.frames else None

    def can_enter(self,position,direction):
        if self.data['requires_open'] and self.state!='open':return False
        north=self.data['entry_side']=='north'
        if (direction[1]>=0 if north else direction[1]<=0):return False
        return (abs(position[0]-self.data['anchor'][0])<=self.data['entry_half_width']
                and abs(position[1]-self.data['entry_y'])<=1.5)

    def force_open(self):
        self.progress=4.0;self.target_open=True


class BenchWorker:
    """A stationary NPC with variable-duration work poses and a synced fitting."""
    def __init__(self,record,world):
        self.data=record
        self.position=pygame.Vector2(record['position'])
        path=Path(record['animation'])
        self.animation=read_json(ROOT/path)
        self.draw_anchor=self.animation['draw_anchor']
        self.frames=[(world.image((path.parent/f['file']).as_posix()),
                      world.image((path.parent/f['fitting_file']).as_posix()),f)
                     for f in self.animation['frames']]
        self.duration_ms=sum(frame[2]['duration_ms'] for frame in self.frames)
        # Ground contact only; hair, arms and tool never become solid walls.
        width,height=record['probe_size']
        self.blocker=pygame.Rect(round(self.position.x)-width//2,round(self.position.y)-height//2,width,height)

    def frame(self,elapsed_ms):
        time=elapsed_ms%self.duration_ms
        for frame in self.frames:
            if time<frame[2]['duration_ms']:return frame
            time-=frame[2]['duration_ms']
        return self.frames[-1]

    def sprite(self,elapsed_ms):return self.frame(elapsed_ms)[0]


class World:
    """Approved town art, animated world objects, and pixel-accurate blockers."""
    def __init__(self,path=MAP_FILE,image_cache=None):
        self.path=Path(path).resolve()
        self.data=read_json(path)
        self.size=tuple(self.data['size_pixels'])
        self._images={} if image_cache is None else image_cache
        self.ground=[self.image(p,False) for p in self.data['ground_frames']]
        collision=self.image(self.data['collision'],False)
        # Collision exports are monochrome, so white pixels block and black
        # pixels remain walkable. Do not use alpha (the mask is opaque).
        self.blocked=pygame.mask.from_threshold(collision,(255,255,255,255),(1,1,1,255))
        self.probe_size=tuple(self.data['player_probe_size'])
        self.probe=pygame.Mask(self.probe_size,fill=True)
        self._probes={self.probe_size:self.probe}
        self.entities=[]
        for record in self.data['entities']:
            frames=[self.image(p) for p in record['frames']]
            self.entities.append({**record,'surfaces':frames,'rect':frames[0].get_rect(topleft=record['position'])})
        self.foreground=[(self.image(r['image']),tuple(r['position'])) for r in self.data['foreground']]
        self.overview=self.image(self.data['overview'],False)
        self.doors=[Door(record,self) for record in self.data.get('doors',[])]
        self.well=DrawingWell(self) if any(r['id']=='well' for r in self.entities) else None
        self.npcs=[]
        for record in self.data.get('npcs',[]):
            actor=Gardener if record['routine']=='watering' else BenchWorker
            self.npcs.append(actor(record,self))

    def image(self,path,alpha=True):
        key=(path,alpha)
        if key not in self._images:
            image=pygame.image.load(str(ROOT/path))
            self._images[key]=image.convert_alpha() if alpha else image.convert()
        return self._images[key]

    def probe_rect(self,position,size=None):
        width,height=self.probe_size if size is None else size
        return pygame.Rect(round(position[0])-width//2,round(position[1])-height//2,width,height)

    def can_stand(self,position,size=None,ignore_npc=None,player_blocker=None):
        """Ground-probe centre; player defaults to the established 24×12 size."""
        size=self.probe_size if size is None else tuple(size)
        rect=self.probe_rect(position,size);x,y=rect.topleft
        if x<0 or y<0 or rect.right>self.size[0] or rect.bottom>self.size[1]:
            return False
        if size not in self._probes:self._probes[size]=pygame.Mask(size,fill=True)
        return (self.blocked.overlap(self._probes[size],(x,y)) is None
                and not any(npc is not ignore_npc and npc.blocker.colliderect(rect) for npc in self.npcs)
                and (player_blocker is None or not player_blocker.colliderect(rect)))

    def location(self,position):
        if self.data.get('kind')=='interior':return self.data['name']
        nearest=min(self.data['landmarks'],key=lambda p:pygame.Vector2(p['position']).distance_squared_to(position))
        return nearest['name'] if pygame.Vector2(nearest['position']).distance_to(position)<130 else 'Village paths'

    def draw(self,target,camera,player,elapsed_ms):
        target.fill('#24302d')
        viewport=pygame.Rect(camera,VIEW_SIZE)
        phase=int(elapsed_ms//self.data['ground_frame_duration_ms'])%len(self.ground)
        target.blit(self.ground[phase],(-camera[0],-camera[1]))
        self.draw_doors(target,camera,None)
        # Full sprite bounds cull roof/canopy overhangs; ground baselines sort
        # objects so Caelan can walk in front of and behind the same building.
        ordered=[(r['sort_y'],r.get('sort_priority',0),'entity',r) for r in self.entities if r['rect'].colliderect(viewport)]
        for npc in self.npcs:
            if 'fitting_sort_y' in npc.data:ordered.append((npc.data['fitting_sort_y'],1,'fitting',npc))
            ordered.append((npc.position.y+self.probe_size[1]/2,2,'npc',npc))
        ordered.append((player.position.y+self.probe_size[1]/2,3,'player',player))
        for _,_,kind,record in sorted(ordered,key=lambda r:(r[0],r[1])):
            if kind=='player':
                anchor=self.data['player_draw_anchor']
                target.blit(player.sprite(),(round(player.position.x)-anchor[0]-camera[0],
                                              round(player.position.y)-anchor[1]-camera[1]))
            elif kind=='npc':
                anchor=record.draw_anchor
                target.blit(record.sprite(elapsed_ms),(round(record.position.x)-anchor[0]-camera[0],
                                                       round(record.position.y)-anchor[1]-camera[1]))
            elif kind=='fitting':
                x,y=record.data['fitting_position']
                target.blit(record.frame(elapsed_ms)[1],(x-camera[0],y-camera[1]))
            else:
                phase=(int(elapsed_ms//record['frame_duration_ms'])+record['phase_offset'])%len(record['surfaces'])
                surface=self.well.sprite(elapsed_ms) if record['id']=='well' and self.well else record['surfaces'][phase]
                target.blit(surface,(record['position'][0]-camera[0],record['position'][1]-camera[1]))
                self.draw_doors(target,camera,record['id'])
        # Southern bridge rails occlude actors crossing on the deck.
        for image,position in self.foreground:
            target.blit(image,(position[0]-camera[0],position[1]-camera[1]))

    def draw_doors(self,target,camera,host):
        for door in self.doors:
            if door.data['host']!=host:continue
            image=door.image()
            if image is not None:
                x,y=door.data['position'];target.blit(image,(x-camera[0],y-camera[1]))


class Player:
    def __init__(self,world):
        self.position=pygame.Vector2(world.data['spawn'])
        self.facing='front'
        self.moving=False
        self.walk_ms=0.0
        self.idles={d:world.image(f'assets/characters/caelan/idle_{d}.png') for d in ('front','left','right','back')}
        self.walks={}
        for direction in self.idles:
            folder=ROOT/f'assets/characters/caelan/walk_{direction}'
            metadata=read_json(folder/'animation.json')
            self.walks[direction]=[(world.image((folder/r['file']).relative_to(ROOT).as_posix()),r['duration_ms'])
                                   for r in metadata['frames']]
        if not world.can_stand(self.position):raise ValueError('Player spawn is blocked')

    def update(self,direction,seconds,world,running=False):
        vector=pygame.Vector2(direction)
        self.moving=False
        if not vector.length_squared():
            self.walk_ms=0
            return
        vector=vector.normalize()
        facing=('right' if vector.x>0 else 'left') if abs(vector.x)>abs(vector.y) else ('front' if vector.y>0 else 'back')
        if facing!=self.facing:self.walk_ms=0
        self.facing=facing
        speed=WALK_SPEED*(RUN_MULTIPLIER if running else 1)
        displacement=vector*speed*seconds
        # Small steps prevent tunnelling through thin banks, rails and walls.
        steps=max(1,math.ceil(max(abs(displacement.x),abs(displacement.y))))
        delta=displacement/steps
        start=self.position.copy()
        for _ in range(steps):
            candidate=self.position+pygame.Vector2(delta.x,0)
            if world.can_stand(candidate):self.position.x=candidate.x
            candidate=self.position+pygame.Vector2(0,delta.y)
            if world.can_stand(candidate):self.position.y=candidate.y
        self.moving=self.position.distance_squared_to(start)>1e-8
        if self.moving:self.walk_ms+=seconds*1000*(RUN_MULTIPLIER if running else 1)
        else:self.walk_ms=0

    def sprite(self):
        if not self.moving:return self.idles[self.facing]
        frames=self.walks[self.facing]
        time=self.walk_ms%sum(duration for _,duration in frames)
        for image,duration in frames:
            if time<duration:return image
            time-=duration
        return frames[-1][0]


def camera_for(position,world_size,view_size=VIEW_SIZE):
    return tuple((size-view)//2 if size<view else max(0,min(size-view,round(value-view/2)))
                 for value,size,view in zip(position,world_size,view_size))


class Game:
    def __init__(self,window_size=WINDOW_SIZE):
        pygame.display.init();pygame.font.init()
        self.window=pygame.display.set_mode(window_size,pygame.RESIZABLE)
        pygame.display.set_caption('Project JRPG — Eldenmere')
        self.canvas=pygame.Surface(VIEW_SIZE)
        self.font=pygame.font.Font(None,16)
        self.small_font=pygame.font.Font(None,14)
        self.world=World()
        self.town=self.world
        self.scenes={self.world.path:self.world}
        self.exterior_position=pygame.Vector2(self.world.data['spawn'])
        self.transfer_cooldown=0.0
        self.player=Player(self.world)
        self.elapsed_ms=0.0
        self.map_open=False
        self.fullscreen=False
        self.windowed_size=window_size
        self.map_size=(220,round(220*self.world.size[1]/self.world.size[0]))
        self.map_image=pygame.transform.scale(self.world.overview,self.map_size)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type==pygame.QUIT:return False
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:
                    if self.map_open:self.map_open=False
                    else:return False
                elif event.key==pygame.K_m:self.map_open=not self.map_open
                elif event.key==pygame.K_F11:
                    self.fullscreen=not self.fullscreen
                    if self.fullscreen:
                        self.windowed_size=self.window.get_size()
                        self.window=pygame.display.set_mode((0,0),pygame.FULLSCREEN)
                    else:self.window=pygame.display.set_mode(self.windowed_size,pygame.RESIZABLE)
            elif event.type==pygame.VIDEORESIZE and not self.fullscreen:
                self.window=pygame.display.set_mode((max(480,event.w),max(320,event.h)),pygame.RESIZABLE)
        return True

    def update(self,seconds,direction=None,running=None):
        self.elapsed_ms+=seconds*1000
        if direction is None:
            keys=pygame.key.get_pressed()
            direction=(int(keys[pygame.K_d] or keys[pygame.K_RIGHT])-int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
                       int(keys[pygame.K_s] or keys[pygame.K_DOWN])-int(keys[pygame.K_w] or keys[pygame.K_UP]))
            running=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        for scene in self.scenes.values():
            for door in scene.doors:door.update(self.player.position if scene is self.world else None,seconds)
        direction=(0,0) if self.map_open else direction
        self.player.update(direction,seconds,self.world,bool(running))
        for scene in self.scenes.values():
            blocker=scene.probe_rect(self.player.position) if scene is self.world else None
            for npc in scene.npcs:
                if isinstance(npc,Gardener):npc.update(seconds,scene,blocker)
        self.transfer_cooldown=max(0,self.transfer_cooldown-seconds)
        if not self.map_open and not self.transfer_cooldown:
            for door in self.world.doors:
                if door.can_enter(self.player.position,direction):
                    self.enter(door)
                    break

    def enter(self,door):
        path=(ROOT/door.data['destination']).resolve()
        if path not in self.scenes:self.scenes[path]=World(path,self.town._images)
        destination=self.scenes[path]
        spawn=door.data['spawn']
        if not destination.can_stand(spawn):raise ValueError(f'Blocked arrival for {door.data["id"]}: {spawn}')
        if self.world is self.town:self.exterior_position.update(door.data['anchor'])
        self.world=destination
        self.player.position.update(spawn)
        self.player.facing=door.data['arrival_facing']
        self.player.moving=False;self.player.walk_ms=0
        self.transfer_cooldown=.25
        arrival=next((d for d in destination.doors if d.data['id']==door.data['arrival_door']),None)
        if arrival:arrival.force_open()

    def text(self,text,position,font=None,color='#f7eed5'):
        self.canvas.blit((font or self.font).render(text,False,color),position)

    def draw_map(self):
        shade=pygame.Surface(VIEW_SIZE,pygame.SRCALPHA);shade.fill((12,24,23,210));self.canvas.blit(shade,(0,0))
        pygame.draw.rect(self.canvas,'#263c35',(12,28,456,266))
        pygame.draw.rect(self.canvas,'#b7a47b',(12,28,456,266),1)
        self.text('ELDENMERE',(28,40))
        origin=(28,66)
        self.canvas.blit(self.map_image,origin)
        for i,landmark in enumerate(self.town.data['landmarks'],1):
            x=origin[0]+round(landmark['position'][0]*self.map_size[0]/self.town.size[0])
            y=origin[1]+round(landmark['position'][1]*self.map_size[1]/self.town.size[1])
            pygame.draw.circle(self.canvas,'#2b2924',(x,y),5)
            self.text(str(i),(x-2,y-4),self.small_font)
            self.text(f'{i}. {landmark["name"]}',(266,68+(i-1)*23),self.small_font)
        position=self.player.position if self.world is self.town else self.exterior_position
        x=origin[0]+round(position.x*self.map_size[0]/self.town.size[0])
        y=origin[1]+round(position.y*self.map_size[1]/self.town.size[1])
        pygame.draw.circle(self.canvas,'#15282b',(x,y),4)
        pygame.draw.circle(self.canvas,'#ffdc71',(x,y),2)
        self.text('You are here',(266,242),self.small_font,color='#ffdc71')
        self.text('M or Esc: close map',(28,274),self.small_font)

    def draw(self):
        camera=camera_for(self.player.position,self.world.size)
        self.world.draw(self.canvas,camera,self.player,self.elapsed_ms)
        pygame.draw.rect(self.canvas,'#263c35',(8,8,190,21))
        if self.world is self.town:
            self.text('Eldenmere',(15,13))
            self.text(self.world.location(self.player.position),(88,14),self.small_font)
        else:self.text(self.world.data['name'],(15,13))
        pygame.draw.rect(self.canvas,'#263c35',(0,302,480,18))
        self.text('WASD / arrows: move   Shift: run   M: map   F11: fullscreen   Esc: quit',(8,307),self.small_font)
        if self.map_open:self.draw_map()
        width,height=self.window.get_size()
        scale=max(1,min(width//VIEW_SIZE[0],height//VIEW_SIZE[1]))
        size=(VIEW_SIZE[0]*scale,VIEW_SIZE[1]*scale)
        self.window.fill('#101b19')
        self.window.blit(pygame.transform.scale(self.canvas,size),((width-size[0])//2,(height-size[1])//2))
        pygame.display.flip()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless',action='store_true',help='Run without a visible window for verification')
    parser.add_argument('--frames',type=int,default=0,help='Exit after this many frames (0: play until quit)')
    parser.add_argument('--screenshot',type=Path,help='Save the final rendered window as a PNG')
    args=parser.parse_args(argv)
    if args.frames<0:parser.error('--frames must be nonnegative')
    if args.headless:os.environ['SDL_VIDEODRIVER']='dummy'
    if not MAP_FILE.is_file():raise SystemExit('Playable town data is missing. Restore assets/maps/eldenmere/playable from the repository.')
    game=Game()
    clock=pygame.time.Clock()
    limit=args.frames or (1 if args.headless else 0)
    count=0
    try:
        while game.handle_events():
            seconds=1/60 if args.headless else min(clock.tick(60)/1000,.1)
            game.update(seconds);game.draw();count+=1
            if limit and count>=limit:break
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True,exist_ok=True)
            pygame.image.save(game.window,str(args.screenshot))
    finally:pygame.quit()
    return 0


if __name__=='__main__':raise SystemExit(main())
