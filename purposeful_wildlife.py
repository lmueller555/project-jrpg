"""Nine place-bound animals and one finite loan of the existing gardener.

Rendering/chunk caches never own animals. Only vignette steps and contacts dirty
progress; an explicit save also records motion, poses and return cooldowns.
"""
import copy
import json
import math
from pathlib import Path

import pygame
from regional_audio import Source

ART = Path(__file__).resolve().parent/'assets/characters/regional_wildlife'
REPLACED_PROP_IDS = frozenset(('south_sheep_a', 'south_sheep_b', 'east_sheep_a',
    'east_sheep_b', 'west_bird', 'clearing_bird', 'south_butterfly', 'orchard_butterfly'))
HOMES = {'south_sheep_a': (-420.,1476.), 'south_sheep_b': (-314.4,1572.),
         'east_sheep_a': (1368.,1392.), 'east_sheep_b': (1526.4,1464.),
         'west_bird': (-840.,228.), 'clearing_bird': (-1128.,-1603.2),
         'south_butterfly': (-451.4,1164.8), 'orchard_butterfly': (-132.2,-268.),
         'farm_cat': (-420.,1182.)}
FLOWERS = {'south_butterfly': (-446.4,1168.8), 'orchard_butterfly': (-127.2,-264.)}
SHEEP_ROUTES = {key: [point, (point[0]-8,point[1]+6), (point[0]+4,point[1]+10)]
                for key,point in HOMES.items() if 'sheep' in key}
GATHER_ROUTES = {
    'south_sheep_a': [HOMES['south_sheep_a'],(-420,1452),(-404,1436),(-384,1440),(-381,1433)],
    'south_sheep_b': [HOMES['south_sheep_b'],(-300,1512),(-324,1464),(-348,1440),(-347,1430)]}
CAT_ROUTE = [HOMES['farm_cat'],(-420,1206),(-450,1206),(-450,1210)]
WORKER_HOME = (-552,1164)
BASKET_HOME = (-516,1226)
BASKET_PEN = (-360,1424)
WORKER_ROUTE = [WORKER_HOME,(-532,1164),(-532,1226),(-480,1226),
                (-420,1226),(-360,1226),(-360,1408),(-384,1424)]


def walk(point):return {'target':point}
def beat(pose, duration, **kwargs):return {'pose':pose,'duration':duration,**kwargs}


VISIT = ([walk(p) for p in WORKER_ROUTE[1:3]]+
         [beat('weed',1.5,contact=.9,basket='hand',item='home')]+
         [walk(p) for p in WORKER_ROUTE[3:]]+
         [beat('sort',1.6,contact=1.,basket='pen',item='pen'),
          beat('idle',14.,gather=True), beat('weed',4.,pat=True,contact=1.2),
          beat('weed',1.5,contact=.9,basket='hand',item='pen',recall=True)]+
         [walk(p) for p in reversed(WORKER_ROUTE[2:-1])]+
         [beat('sort',1.6,contact=1.,basket='home',item='home')]+
         [walk(p) for p in reversed(WORKER_ROUTE[:2])])
GATHER_STEP = next(i for i,a in enumerate(VISIT) if a.get('gather'))
PAT_STEP = next(i for i,a in enumerate(VISIT) if a.get('pat'))
RETURN_STEP = next(i for i,a in enumerate(VISIT) if a.get('recall'))


def _number(value, low, high):
    return type(value) in (int,float) and math.isfinite(value) and low <= value <= high


def _point(value):
    return isinstance(value,list) and len(value)==2 and all(_number(v,-10000,10000) for v in value)


def _on_segment(point, a, b, tolerance=.025):
    p=pygame.Vector2(point);start=pygame.Vector2(a);delta=pygame.Vector2(b)-start
    t=max(0.,min(1.,(p-start).dot(delta)/delta.length_squared())) if delta.length_squared() else 0.
    return p.distance_to(start+delta*t)<=tolerance


def _on_route(point, route, closed=False):
    return any(_on_segment(point,a,b) for a,b in zip(route,route[1:]+(route[:1] if closed else [])))


def _species(identifier):
    return next(kind for kind in ('sheep','bird','butterfly','cat') if kind in identifier)


def flower_route(identifier):
    x,y=FLOWERS[identifier]
    return [(x-5,y-4),(x+4,y-7),(x,y-2)]


def flight_route(identifier):
    x,y=HOMES[identifier]
    return [(x,y),(x+(-38 if identifier=='west_bird' else 38),y-32)]


def _initial_actor(identifier):
    species=_species(identifier)
    return {'position':list(HOMES[identifier]), 'mode':{'sheep':'graze','bird':'peck',
            'butterfly':'settle','cat':'sleep'}[species], 'target':1, 'elapsed':0.,
            'clock':0., 'facing':'right', 'cooldown':0.}


def empty_state():
    return {'version':1,'animals':{key:_initial_actor(key) for key in HOMES},
            'vignette':{'phase':'idle','step':0,'elapsed':0.,'contact':False,
                        'position':list(WORKER_HOME),'clock':0.,'facing':'front','basket':'home','moving':False}}


def progress_state(data):
    v=data['vignette']
    return {'vignette':{key:v[key] for key in ('phase','step','contact')}}


def _basket_at(step, contact):
    result='home'
    for action in VISIT[:step]:result=action.get('basket',result)
    if contact:result=VISIT[step].get('basket',result)
    return result


def valid_state(data):
    """Reject nonfinite motion, unknown actors and feet outside authored routes."""
    if not isinstance(data,dict) or set(data)!={'version','animals','vignette'} or type(data['version']) is not int or data['version']!=1:return False
    animals=data['animals'];v=data['vignette']
    if not isinstance(animals,dict) or set(animals)!=set(HOMES):return False
    if not isinstance(v,dict) or set(v)!=set(empty_state()['vignette']):return False
    if not isinstance(v['phase'],str) or v['phase'] not in ('idle','visit','done'):return False
    if type(v['step']) is not int or not 0<=v['step']<len(VISIT):return False
    if type(v['contact']) is not bool or type(v['moving']) is not bool or not _point(v['position']):return False
    if not isinstance(v['facing'],str) or v['facing'] not in ('front','back','left','right'):return False
    if not _number(v['clock'],0,60) or not _number(v['elapsed'],0,14):return False
    if not isinstance(v['basket'],str) or v['basket'] not in ('home','hand','pen'):return False
    if v['phase']!='visit':
        if v['step'] or v['elapsed'] or v['contact'] or v['position']!=list(WORKER_HOME) or v['basket']!='home' or v['moving']:return False
    else:
        action=VISIT[v['step']]
        start=WORKER_HOME
        for previous in VISIT[:v['step']]:start=previous.get('target',start)
        if not _on_segment(v['position'],start,action.get('target',start)):return False
        if v['elapsed']>action.get('duration',0) or (v['moving'] and 'target' not in action):return False
        if v['contact']!=('contact' in action and v['elapsed']>=action['contact']):return False
        if v['basket']!=_basket_at(v['step'],v['contact']):return False
    modes={'sheep':('graze','walk','gather_home','gather','look','nuzzle','return'),
           'cat':('sleep','stretch','walk','sit','return'),
           'bird':('peck','scatter','away','land'), 'butterfly':('settle','flutter')}
    for key,s in animals.items():
        kind=_species(key)
        if not isinstance(s,dict) or set(s)!=set(_initial_actor(key)):return False
        if not isinstance(s['mode'],str) or s['mode'] not in modes[kind]:return False
        if not _point(s['position']) or type(s['target']) is not int:return False
        if not _number(s['clock'],0,60) or not _number(s['elapsed'],0,20) or not _number(s['cooldown'],0,8):return False
        if not isinstance(s['facing'],str) or s['facing'] not in ('left','right'):return False
        if kind=='sheep':
            route=SHEEP_ROUTES[key]
            gathering=s['mode'] in ('gather','look','nuzzle','return')
            if s['mode']=='gather_home' and (key not in GATHER_ROUTES or v['phase']!='visit'):return False
            if gathering:
                if key not in GATHER_ROUTES or (v['phase']!='visit' and s['mode']!='return'):return False
                route=GATHER_ROUTES[key]
                if s['mode'] in ('look','nuzzle') and (s['target']!=len(route)-1 or s['position']!=list(route[-1])):return False
                if s['mode']=='nuzzle' and (key!='south_sheep_b' or v['step'] not in (PAT_STEP,RETURN_STEP)):return False
                if not (_on_route(s['position'],route) or _on_route(s['position'],SHEEP_ROUTES[key],True)):return False
            elif not _on_route(s['position'],route,True):return False
            if not 0<=s['target']<len(route):return False
        elif kind=='cat':
            if not 0<=s['target']<len(CAT_ROUTE) or not _on_route(s['position'],CAT_ROUTE):return False
        elif kind=='bird':
            if s['target']!=1 or not _on_route(s['position'],flight_route(key)):return False
            if s['mode']=='peck' and s['position']!=list(HOMES[key]):return False
        elif not 0<=s['target']<3 or not _on_route(s['position'],flower_route(key),True):return False
    return True


def valid_context(data, garden):
    if not valid_state(data):return False
    if data['vignette']['phase']!='visit':return True
    if not isinstance(garden,dict):return False
    state=garden.get('gardener',{})
    return (isinstance(state,dict) and state.get('phase')=='rest' and state.get('read') is True
            and state.get('position')==list(WORKER_HOME))


class Animal:
    def __init__(self, identifier, clips, family):
        self.id=identifier;self.species=_species(identifier);self.clips=clips
        self.draw_anchor=tuple(family['anchor'])
        self.probe_size={'sheep':(16,8),'cat':(10,5),'bird':(6,3),'butterfly':(4,3)}[self.species]
        self.state=_initial_actor(identifier);self.position=pygame.Vector2(self.state['position'])

    @property
    def facing(self):return self.state['facing']
    @property
    def clock(self):return self.state['clock']
    @property
    def pose(self):
        mode=self.state['mode']
        return {'sheep':{'return':'walk','gather':'walk','gather_home':'walk'}, 'bird':{'scatter':'fly','away':'land','land':'fly'},
                'cat':{'return':'walk'},'butterfly':{}}[self.species].get(mode,mode)
    @property
    def animation_key(self):return self.species+'_'+self.pose+'_'+self.facing
    def sprite(self):
        clip=self.clips[self.animation_key];t=self.clock
        if clip['loop']:t%=sum(clip['durations'])
        for image,duration in zip(clip['images'],clip['durations']):
            if t<duration:return image
            t-=duration
        return clip['images'][-1]


class PurposefulWildlife:
    def __init__(self,world):
        self.world=world;self.worker=world.garden_orchard.actors[0]
        manifest=json.loads((ART/'animation.json').read_text())
        self.clips={}
        for key,clip in manifest['clips'].items():
            self.clips[key]={**clip,'images':[pygame.image.load(str(ART/f)).convert_alpha() for f in clip['frames']]}
        self.actors=[Animal(key,self.clips,manifest['families'][_species(key)]) for key in HOMES]
        self.by_id={a.id:a for a in self.actors}
        self.basket=pygame.image.load(str(ART.parent/'garden_workers/basket.png')).convert_alpha()
        self.seeds=pygame.image.load(str(ART/'seeds.png')).convert_alpha()
        self.restore()

    def restore(self,data=None):
        state=empty_state() if data is None else copy.deepcopy(data)
        if not valid_context(state,self.world.garden_orchard.to_dict()):raise ValueError('Invalid purposeful wildlife state')
        for a in self.actors:
            a.state=state['animals'][a.id];a.position.update(a.state['position'])
        self.vignette=state['vignette']
        was_owned=getattr(self.worker,'wildlife_owned',False)
        self.worker.wildlife_owned=self.vignette['phase']=='visit'
        if self.worker.wildlife_owned:self._worker_pose()
        elif was_owned:
            self.worker.position.update(self.world.garden_orchard.state['gardener']['position'])
            self.worker.clock=0.;self.worker.moving=False;self.world.garden_orchard._pose(self.worker)

    def to_dict(self):
        animals={a.id:{**a.state,'position':list(a.position)} for a in self.actors}
        v=copy.deepcopy(self.vignette)
        if v['phase']=='visit':v['position']=list(self.worker.position);v['clock']=self.worker.clock;v['moving']=self.worker.moving
        return {'version':1,'animals':copy.deepcopy(animals),'vignette':v}

    def progress_dict(self):return progress_state(self.to_dict())

    def ground_blockers(self,ignore_npc=None):
        v=self.vignette
        if v['basket']=='hand':return []
        if v['phase']=='visit':
            action=VISIT[v['step']]
            if action.get('item') and not v['contact'] and v['elapsed']>0:return []
        p=BASKET_HOME if v['basket']=='home' else BASKET_PEN
        return [pygame.Rect(round(p[0])-9,round(p[1])-2,18,4)]

    def basket_position(self):
        v=self.vignette;hand=self.worker.position+pygame.Vector2(0,-7)
        point=hand if v['basket']=='hand' else pygame.Vector2(BASKET_HOME if v['basket']=='home' else BASKET_PEN)
        if v['phase']=='visit':
            action=VISIT[v['step']]
            if action.get('item') and not v['contact']:
                ground=pygame.Vector2(BASKET_HOME if action['item']=='home' else BASKET_PEN)
                t=min(1,v['elapsed']/action['contact'])
                point=ground.lerp(hand,t) if action['basket']=='hand' else hand.lerp(ground,t)
        return point.copy()

    def props(self):
        result=[]
        for key in ('west_bird','clearing_bird'):
            x,y=HOMES[key];result.append((y-1,3,self.seeds,(round(x)-self.seeds.get_width()//2,round(y)-self.seeds.get_height()+2)))
        p=self.basket_position();sort=self.worker.position.y+6 if self.vignette['basket']=='hand' else p.y
        result.append((sort,4,self.basket,(round(p.x)-self.basket.get_width()//2,round(p.y)-self.basket.get_height())))
        for a in self.actors:
            image=a.sprite();x,y=a.draw_anchor
            result.append((a.position.y,4,image,(round(a.position.x)-x,round(a.position.y)-y)))
        return result

    def _mode(self,a,mode):
        if a.state['mode']!=mode:a.state.update(mode=mode,elapsed=0.,clock=0.)

    def _sound(self,game,a,name):
        game.regional_audio.play(Source('wildlife_'+a.id+'_'+name,name,'wildlife',
            lambda actor=a:tuple(actor.position),gain=.30 if name=='sheep' else .26,
            near=24,far=140,priority=1,cooldown=8. if name=='wings' else 4.))

    def _move(self,a,target,dt,player,speed=16,air=False):
        delta=pygame.Vector2(target)-a.position
        if delta.length()<.001:return True
        if isinstance(a,Animal):
            if abs(delta.x)>.01:a.state['facing']='right' if delta.x>0 else 'left'
        else:a.facing=('right' if delta.x>0 else 'left') if abs(delta.x)>abs(delta.y) else ('front' if delta.y>0 else 'back')
        remaining=min(delta.length(),speed*dt);direction=delta.normalize()
        while remaining>.000001:
            step=min(1.,remaining);point=a.position+direction*step
            if not air:
                old=self.world.probe_rect(a.position,a.probe_size);new=self.world.probe_rect(point,a.probe_size)
                # An already overlapping player can pass through an animal;
                # the animal may only move out of that overlap, never deepen it.
                overlap=old.colliderect(player)
                if not self.world.can_stand(point,a.probe_size,a,None if overlap else player):return False
                if overlap and new.colliderect(player):
                    if new.clip(player).width*new.clip(player).height>old.clip(player).width*old.clip(player).height or point.distance_squared_to(player.center)<a.position.distance_squared_to(player.center):return False
                for other in self.actors:
                    if other is a or other.species in ('bird','butterfly'):continue
                    if new.colliderect(self.world.probe_rect(other.position,other.probe_size)):return False
            a.position.update(point);remaining-=step
            if not isinstance(a,Animal):a.moving=True
        if a.position.distance_to(target)<.001:a.position.update(target);return True
        return False

    def _sheep(self,a,dt,game,player):
        s=a.state;mode=s['mode']
        if mode in ('gather','return'):
            route=GATHER_ROUTES[a.id]
            if self._move(a,route[s['target']],dt,player,18):
                if mode=='gather':
                    if s['target']==len(route)-1:self._mode(a,'look')
                    else:s['target']+=1
                elif s['target']==0:self._mode(a,'graze');s['target']=1
                else:s['target']-=1
        elif mode in ('walk','gather_home'):
            route=SHEEP_ROUTES[a.id]
            if self._move(a,route[s['target']],dt,player,9):
                arrived=s['target'];s['target']=(s['target']+1)%len(route)
                if mode=='gather_home':
                    if arrived==0:self._mode(a,'gather');s['target']=1
                else:self._mode(a,'graze')
        elif mode=='graze' and s['elapsed']>=4.5+(1.5 if a.id.endswith('b') else 0):self._mode(a,'walk')

    def _bird(self,a,dt,game,player):
        s=a.state;home=pygame.Vector2(HOMES[a.id]);distance=a.position.distance_to(game.player.position)
        s['cooldown']=max(0.,s['cooldown']-dt)
        if s['mode'] in ('peck','land') and (distance<=50 or (s['mode']=='land' and home.distance_to(game.player.position)<=65)):
            self._mode(a,'scatter');s['cooldown']=8.;self._sound(game,a,'wings')
        if s['mode']=='scatter':
            if self._move(a,flight_route(a.id)[1],dt,player,40,True):self._mode(a,'away')
        elif s['mode']=='away':
            if s['cooldown']==0 and distance>65 and home.distance_to(game.player.position)>80 and self.world.can_stand(home,a.probe_size,a,player):self._mode(a,'land')
        elif s['mode']=='land':
            if self._move(a,home,dt,player,28,True):self._mode(a,'peck');self._sound(game,a,'bird')

    def _cat(self,a,dt,player):
        s=a.state
        if s['mode']=='sleep' and s['elapsed']>=7:self._mode(a,'stretch')
        elif s['mode']=='stretch' and s['elapsed']>=2.2:self._mode(a,'walk');s['target']=1
        elif s['mode'] in ('walk','return'):
            returning=s['mode']=='return'
            if self._move(a,CAT_ROUTE[s['target']],dt,player,12):
                if s['target']==(0 if returning else len(CAT_ROUTE)-1):self._mode(a,'sleep' if returning else 'sit')
                else:s['target']+=-1 if returning else 1
        elif s['mode']=='sit' and s['elapsed']>=9:self._mode(a,'return');s['target']=len(CAT_ROUTE)-2

    def _butterfly(self,a,dt,player):
        s=a.state
        if s['mode']=='settle' and s['elapsed']>=2.4:self._mode(a,'flutter')
        elif s['mode']=='flutter' and self._move(a,flower_route(a.id)[s['target']],dt,player,5,True):
            self._mode(a,'settle');s['target']=(s['target']+1)%3

    def _worker_pose(self):
        v=self.vignette;a=self.worker;action=VISIT[v['step']]
        a.position.update(v['position']);a.clock=v['clock'];a.facing=v['facing'];a.draw_anchor=(20,38);a.moving=v['moving']
        a.pose=action.get('pose','carry' if v['basket']=='hand' else 'idle')
        if 'target' not in action:a.facing='front' if action.get('pat') else 'right'

    def _recall(self):
        for key,route in GATHER_ROUTES.items():
            a=self.by_id[key];s=a.state
            if s['mode']=='gather_home':self._mode(a,'walk');continue
            if s['mode']=='gather':s['target']=max(0,s['target']-1)
            elif s['mode'] in ('look','nuzzle'):s['target']=len(route)-2
            else:s['target']=0
            self._mode(a,'return')

    def _visit(self,dt,game,player):
        v=self.vignette;garden=self.world.garden_orchard
        if v['phase']=='done':return
        if game.player.position.distance_to(self.worker.position)>260:return
        if v['phase']=='idle':
            if garden.state['gardener']['phase']!='rest' or not garden.state['gardener']['read']:return
            if self.worker.position.distance_to(WORKER_HOME)>.01:return
            v['phase']='visit';self.worker.wildlife_owned=True
            # Publish the loan only after its authored pose replaces the
            # gardener's unbounded idle clock and transient movement state.
            self._worker_pose();game.save_progress()
        action=VISIT[v['step']];self._worker_pose();self.worker.moving=False
        self.worker.clock=(self.worker.clock+dt)%60
        if 'target' in action:finished=self._move(self.worker,action['target'],dt,player,22)
        else:
            if action.get('gather') and v['elapsed']==0:
                for key in GATHER_ROUTES:
                    animal=self.by_id[key]
                    if animal.position.distance_to(HOMES[key])<.001:
                        self._mode(animal,'gather');animal.state['target']=1
                    else:self._mode(animal,'gather_home')
            if action.get('pat'):
                b=self.by_id['south_sheep_b']
                if b.state['mode']=='look':self._mode(b,'nuzzle');b.state['facing']='left'
            v['elapsed']=min(action['duration'],v['elapsed']+dt)
            if 'contact' in action and not v['contact'] and v['elapsed']>=action['contact']:
                v['contact']=True
                if 'basket' in action:v['basket']=action['basket']
                if action.get('pat'):
                    sheep=self.by_id['south_sheep_a']
                    if sheep.state['mode']=='look':self._sound(game,sheep,'sheep')
                if action.get('recall'):self._recall()
                v['position']=list(self.worker.position);v['clock']=self.worker.clock
                game.save_progress()
            gathered=action.get('gather') and v['elapsed']>=2 and all(self.by_id[k].state['mode']=='look' for k in GATHER_ROUTES)
            finished=gathered if action.get('gather') else v['elapsed']>=action['duration']
        v['position']=list(self.worker.position);v['clock']=self.worker.clock;v['facing']=self.worker.facing;v['moving']=self.worker.moving
        if finished:
            v['step']+=1;v['elapsed']=0.;v['contact']=False;v['moving']=False
            if v['step']==len(VISIT):
                v.update(phase='done',step=0,position=list(WORKER_HOME),clock=0.,facing='front')
                self.worker.wildlife_owned=False;self.worker.moving=False;self.worker.clock=0.
                garden._pose(self.worker)
            else:self._worker_pose()
            game.save_progress()

    def update(self,seconds,game):
        if game.world is not self.world or game.social.locked:return
        if (game.on_title or game.pause.is_open or game.inventory_ui.is_open or game.world_map_viewer.is_open
                or game.map_open or game.quest_ui.journal_open or game.combat.active
                or game.opening_cinematic.active or game.regent_arrival.active):return
        dt=min(max(seconds,0.),.1)
        if not dt:return
        player=self.world.probe_rect(game.player.position)
        self._visit(dt,game,player)
        for a in self.actors:
            if min(a.position.distance_to(game.player.position),pygame.Vector2(HOMES[a.id]).distance_to(game.player.position))>260:continue
            a.state['clock']=(a.state['clock']+dt)%60;a.state['elapsed']=min(20.,a.state['elapsed']+dt)
            if a.species=='sheep':self._sheep(a,dt,game,player)
            elif a.species=='bird':self._bird(a,dt,game,player)
            elif a.species=='cat':self._cat(a,dt,player)
            else:self._butterfly(a,dt,player)
            a.state['position']=list(a.position)
