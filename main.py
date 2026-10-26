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

from npc_routines import Gardener, RoutineNPC
from daisy_routine import DaisyRoutine
from liam_daisy_play import PlayActor, LiamDaisyPlay
from liam_blocks import LiamBlocks
from daisy_bone import DaisyBone
from well_routine import DrawingWell
from social import SocialSystem
from title_screen import TitleScreen
from quests import QuestLog
from quest_ui import QuestUI
from save_game import SaveStore
from opening import OpeningSequence
from opening_audio import MorningAudio
from audio_settings import AudioSettings
from pause_menu import PauseMenu
from camera_director import CameraDirector
from ui_style import UIStyle, IVORY, GOLD, MUTED, ERROR
from map_ui import MapUI
from inventory import Inventory
from inventory_ui import InventoryUI
from halden_visit import HaldenVisit
from elira_visit import EliraVisit

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

    def update(self,position,seconds,other_positions=()):
        positions=list(other_positions)
        if position is not None:positions.append(position)
        radius=self.data['close_radius'] if self.target_open else self.data['open_radius']
        self.target_open=False
        for candidate in positions:
            delta=pygame.Vector2(candidate)-self.data['anchor']
            front=delta.y>=-4 if self.data['entry_side']=='north' else delta.y<=4
            if front and delta.length_squared()<=radius*radius:
                self.target_open=True
                break
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


class StationaryNPC:
    """One fixed pose with a foot blocker and no behavior or social hooks."""
    def __init__(self,record,world):
        self.data=record
        self.position=pygame.Vector2(record['position'])
        self.draw_anchor=record['draw_anchor']
        self._sprite=world.image(record['sprite'])
        width,height=record['probe_size']
        self.blocker=pygame.Rect(round(self.position.x)-width//2,
                                 round(self.position.y)-height//2,width,height)

    def sprite(self,elapsed_ms):return self._sprite


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
        self.routine_props=[]
        for record in self.data.get('npcs',[]):
            actor=(StationaryNPC if record.get('kind')=='stationary' else
                   PlayActor if record.get('kind')=='play_actor' else
                   DaisyRoutine if record.get('kind')=='daisy_routine' else
                   Gardener if record.get('routine')=='watering' else BenchWorker)
            self.npcs.append(actor(record,self))

    def attach_routine_props(self,actor):
        """Permanently register one actor's nonblocking props for this room."""
        registered={(id(owner),prop['id']) for owner,prop in self.routine_props}
        for prop in actor.surface_props:
            key=(id(actor),prop['id'])
            if prop['scene']==self.data['id'] and key not in registered:
                self.routine_props.append((actor,prop));registered.add(key)

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
                and not any(npc is not ignore_npc and not getattr(npc,'story_following',False)
                            and npc.blocker.colliderect(rect) for npc in self.npcs)
                and not any(block.colliderect(rect) for block in getattr(self,'task_blockers',lambda:())())
                and (player_blocker is None or not player_blocker.colliderect(rect)))

    def location(self,position):
        if self.data.get('kind')=='interior':return self.data['name']
        nearest=min(self.data['landmarks'],key=lambda p:pygame.Vector2(p['position']).distance_squared_to(position))
        return nearest['name'] if pygame.Vector2(nearest['position']).distance_to(position)<130 else 'Village paths'

    def set_entity_state(self,identifier,state,owner=None):
        """Change a registered prop image in this cached scene, without moving it."""
        entity=next((e for e in self.entities if e['id']==identifier),None)
        if entity is None:raise KeyError(identifier)
        if state not in entity.get('state_images',{}):raise ValueError(f'Unknown state {state!r} for {identifier}')
        if entity.get('reserved_by') not in (None,owner):return False
        path=entity['state_images'][state];surface=self.image(path)
        if surface.get_size()!=entity['surfaces'][0].get_size():raise ValueError('Prop states must share frame dimensions')
        entity.update(state=state,frames=[path],surfaces=[surface])
        raw=next(e for e in self.data['entities'] if e['id']==identifier)
        raw.update(state=state,frames=[path])
        return True

    def draw(self,target,camera,player,elapsed_ms,include_ui=True):
        target.fill('#24302d')
        viewport=pygame.Rect(camera,VIEW_SIZE)
        phase=int(elapsed_ms//self.data['ground_frame_duration_ms'])%len(self.ground)
        target.blit(self.ground[phase],(-camera[0],-camera[1]))
        self.draw_doors(target,camera,None)
        # Full sprite bounds cull roof/canopy overhangs; ground baselines sort
        # objects so Caelan can walk in front of and behind the same building.
        ordered=[(r['sort_y'],r.get('sort_priority',0),'entity',r) for r in self.entities if r['rect'].colliderect(viewport)]
        for owner,prop in self.routine_props:
            if not owner.surface_prop_visible(prop):continue
            surface=prop['surface'];rect=surface.get_rect(topleft=prop['position'])
            if rect.colliderect(viewport):
                ordered.append((prop.get('sort_y',rect.bottom),prop.get('sort_priority',1.5),
                                'routine_prop',(surface,prop['position'])))
        for npc in self.npcs:
            if not getattr(npc,'story_visible',True):continue
            if 'fitting_sort_y' in npc.data:ordered.append((npc.data['fitting_sort_y'],1,'fitting',npc))
            sort_y=getattr(npc,'sort_y',None)
            if getattr(npc,'story_sort_y',None) is not None:sort_y=npc.story_sort_y
            ordered.append((npc.position.y+self.probe_size[1]/2 if sort_y is None else sort_y,2,'npc',npc))
        if getattr(player,'story_visible',True):
            ordered.append((getattr(player,'story_sort_y',None) or player.position.y+self.probe_size[1]/2,3,'player',player))
        for _,_,kind,record in sorted(ordered,key=lambda r:(r[0],r[1])):
            if kind=='player':
                anchor=getattr(player,'story_draw_anchor',None) or self.data['player_draw_anchor']
                position=getattr(player,'story_position',None) or player.position
                target.blit(player.sprite(),(round(position[0])-anchor[0]-camera[0],
                                              round(position[1])-anchor[1]-camera[1]))
            elif kind=='npc':
                anchor=getattr(record,'story_draw_anchor',None) or record.draw_anchor
                position=getattr(record,'story_position',None) or record.position
                surface=getattr(record,'story_sprite',None)
                if surface is None:surface=record.sprite(elapsed_ms)
                if hasattr(record,'draw_background'):record.draw_background(target,camera)
                target.blit(surface,(round(position[0])-anchor[0]-camera[0],
                                     round(position[1])-anchor[1]-camera[1]))
                if hasattr(record,'draw_foreground'):record.draw_foreground(target,camera)
            elif kind=='fitting':
                x,y=record.data['fitting_position']
                target.blit(record.frame(elapsed_ms)[1],(x-camera[0],y-camera[1]))
            elif kind=='routine_prop':
                surface,position=record
                target.blit(surface,(position[0]-camera[0],position[1]-camera[1]))
            else:
                phase=(int(elapsed_ms//record['frame_duration_ms'])+record['phase_offset'])%len(record['surfaces'])
                surface=self.well.sprite(elapsed_ms) if record['id']=='well' and self.well else record['surfaces'][phase]
                target.blit(surface,(record['position'][0]-camera[0],record['position'][1]-camera[1]))
                self.draw_doors(target,camera,record['id'])
        # Southern bridge rails occlude actors crossing on the deck.
        for image,position in self.foreground:
            target.blit(image,(position[0]-camera[0],position[1]-camera[1]))
        if include_ui:
            for routine in getattr(self,'play_routines',[]):routine.draw(target,camera,self)

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
        if getattr(self,'story_sprite',None) is not None:return self.story_sprite
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
    def __init__(self,window_size=WINDOW_SIZE,fullscreen=True,start_on_title=True,save_path=None,settings_path=None):
        pygame.display.init();pygame.font.init()
        self.fullscreen=fullscreen
        self.windowed_size=tuple(window_size)
        self.window=pygame.display.set_mode((0,0) if fullscreen else self.windowed_size,
                                            pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
        pygame.display.set_caption('Project JRPG — Eldenmere')
        self.canvas=pygame.Surface(VIEW_SIZE)
        self.audio=AudioSettings(settings_path)
        self.ui=UIStyle(self)
        self.ui_surface=None
        self._ensure_ui_surface()
        self.location_label=None
        self.location_seconds=3.5
        self.world=World()
        self.town=self.world
        self.scenes={self.world.path:self.world}
        self.persistent_npcs=[]
        self._routine_worlds={}
        self.exterior_position=pygame.Vector2(self.world.data['spawn'])
        self.transfer_cooldown=0.0
        self.player=Player(self.world)
        self.elapsed_ms=0.0
        self.map_open=False
        self.map_size=(220,round(220*self.world.size[1]/self.world.size[0]))
        self.map_image=pygame.transform.scale(self.world.overview,self.map_size)
        self._setup_persistent_npcs()
        for scene_id in self.town.data.get('ambient_scenes',[]):self._scene_by_id(scene_id)
        self.play_routines=[]
        for scene in list(self.scenes.values()):
            if scene.data.get('play_routine'):
                routine=LiamDaisyPlay(self,scene,scene.data['play_routine']);self.play_routines.append(routine)
                scene.play_routines=[routine];self.town.play_routines=[routine]
        self.block_routines=[]
        for shared in self.play_routines:
            if shared.home.data.get('block_routine'):
                routine=LiamBlocks(self,shared.home,shared,shared.home.data['block_routine'])
                self.block_routines.append(routine);shared.home.play_routines.append(routine)
        self.bone_routines=[]
        for shared in self.play_routines:
            if shared.home.data.get('bone_routine'):
                self.bone_routines.append(DaisyBone(self,shared.home,shared,shared.home.data['bone_routine']))
        self.quests=QuestLog()
        self.inventory=Inventory()
        self.social=SocialSystem(self)
        self._mouse_held=False
        self.on_title=start_on_title
        self.title=TitleScreen(self)
        self.quest_ui=QuestUI(self)
        self.map_ui=MapUI(self)
        self.inventory_ui=InventoryUI(self)
        self.opening=OpeningSequence(self)
        self.halden_visit=HaldenVisit(self)
        self.elira_visit=EliraVisit(self)
        self.household_visits=(self.halden_visit,self.elira_visit)
        self.opening_audio=MorningAudio(self)
        self.camera=CameraDirector(self)
        self.pause=PauseMenu(self)
        self.save_store=SaveStore(save_path)
        self.save_error=None
        self.saved_journey=self._read_saved_journey()
        self._saved_progress=self._progress_signature()
        self._save_retry_seconds=0.0
        self.opening_fade=0.0

    def _progress_signature(self):
        return json.dumps({'quests':self.quests.to_dict(),
                           'dialogue_flags':sorted(self.social.flags),
                           'inventory':self.inventory.to_dict(),
                           'halden_visit':self.halden_visit.to_dict(),
                           'elira_visit':self.elira_visit.to_dict(),
                           'opening':self.opening.to_dict()},sort_keys=True)

    @property
    def household_action(self):return any(visit.locks_player for visit in self.household_visits)

    def _sync_inventory(self):
        """Grant entrusted supplies once; reconcile older quest-only journeys."""
        for quest in self.inventory.grants:
            if self.quests.status(quest) in ('active','ready','completed'):
                self.inventory.grant_quest(quest)
        for delivery in self.inventory.deliveries.values():
            quest,objective=delivery['quest'],delivery['objective']
            if self.quests.objective_status(quest,objective)=='completed':
                self.inventory.deliver(quest,objective,delivery['recipient'])

    def accept_quest(self,identifier):
        """Update quest and supplies together, before the scene checkpoints."""
        if self.quests.status(identifier)!='available':return False
        prior=self.inventory.to_dict()
        if identifier in self.inventory.grants and not self.inventory.was_granted(identifier):
            if not self.inventory.grant_quest(identifier):return False
        if self.quests.accept(identifier):return True
        self.inventory.restore(prior)
        return False

    def deliver_quest_item(self,quest,objective,recipient):
        """Called by a successful NPC handoff, never by entering its room.

        A delivered medicine does not finish Halden's remaining sack task.
        Receipts survive reloads so the handoff cannot consume a second item.
        """
        if self.quests.objective_status(quest,objective)!='active':return False
        self._sync_inventory()
        if not self.inventory.deliver(quest,objective,recipient):return False
        self.save_progress()
        return True

    def _read_saved_journey(self):
        """Validate a save without mutating the fresh world behind the title."""
        data=self.save_store.load()
        if data is None:
            self.save_error=self.save_store.error
            return None
        def point(value):
            return (isinstance(value,list) and len(value)==2 and
                    all(type(n) in (int,float) and abs(n)<1e7 and math.isfinite(n) for n in value))
        scene_ids={self.town.data['id'],*self.town.data.get('interior_scenes',{})}
        player=data.get('player')
        valid=(type(data.get('version')) is int and data['version']==1 and
               isinstance(player,dict) and isinstance(player.get('scene'),str) and
               player['scene'] in scene_ids and point(player.get('position')) and
               player.get('facing') in ('front','back','left','right') and
               point(data.get('exterior_position')) and
               isinstance(data.get('dialogue_flags'),list) and
               len(data['dialogue_flags'])<=256 and
               all(isinstance(flag,str) and 0<len(flag)<=128 for flag in data['dialogue_flags']) and
               QuestLog().restore(data.get('quests')) and
               ('inventory' not in data or self._valid_inventory_snapshot(data)) and
               ('opening' not in data or self.opening.valid_snapshot(data['opening'])) and
               ('halden_visit' not in data or self._valid_halden_snapshot(data)) and
               ('elira_visit' not in data or EliraVisit.valid_journey(data)))
        if not valid:
            self.save_error='The saved journey could not be read.'
            return None
        return data

    @staticmethod
    def _valid_inventory_snapshot(data):
        inventory=Inventory()
        quests=QuestLog()
        if not inventory.restore(data['inventory']) or not quests.restore(data.get('quests')):return False
        for quest,bundle in inventory.grants.items():
            accepted=quests.status(quest) in ('active','ready','completed')
            if inventory.was_granted(quest)!=accepted:return False
            if not accepted:continue
            outstanding=dict(bundle)
            for key in inventory.to_dict()['deliveries']:
                delivery=inventory.deliveries[key]
                if delivery['quest']!=quest:continue
                if quests.objective_status(quest,delivery['objective'])=='queued':return False
                for item,amount in delivery['items'].items():outstanding[item]=outstanding.get(item,0)-amount
            if any(inventory.quantity(item)<amount for item,amount in outstanding.items()):return False
        return True

    @property
    def has_saved_journey(self):return self.saved_journey is not None

    @staticmethod
    def _valid_halden_snapshot(data):
        record=data['halden_visit']
        if not HaldenVisit.valid_snapshot(record):return False
        quests=QuestLog();quests.restore(data['quests'])
        accepted=quests.status('CH01_MQ01')!='available'
        completed=quests.objective_status('CH01_MQ01','halden')=='completed'
        has_progress=bool(record['stored_sacks'] or record['carried_sack'] is not None or record['concluded'] or record['departed'])
        if has_progress and not accepted:return False
        if has_progress:
            inventory=Inventory()
            if 'inventory' in data:
                if not inventory.restore(data['inventory']) or not inventory.was_delivered('CH01_MQ01','halden'):return False
            elif not completed:return False
        if completed:
            return record['stored_sacks']==[0,1,2] and record['departed']
        return True

    def begin_journey(self,continue_saved=False):
        """Continue quest facts, not an interrupted conversation or NPC action."""
        data=self.saved_journey if continue_saved else None
        if continue_saved and data is None:return False
        self.elira_visit.release_pose()
        if data is None:
            self.quests.restore(QuestLog().to_dict())
            self.inventory=Inventory()
            self.social.flags.clear()
            self.world=self.town
            position=self.town.data['spawn']
            self.player.facing='front'
            self.exterior_position.update(position)
        else:
            self.quests.restore(data['quests'])
            self.inventory=Inventory()
            if 'inventory' in data:self.inventory.restore(data['inventory'])
            self.social.flags=set(data['dialogue_flags'])
            self.world=self._scene_by_id(data['player']['scene'])
            position=data['player']['position']
            self.player.facing=data['player']['facing']
            self.exterior_position.update(data['exterior_position'])
        # Residents resume their own routines on launch. A saved standing spot
        # can now be occupied, so use a clear nearby landing or the room entry.
        if not self.world.can_stand(position):
            candidates=[self.world.data['spawn']]
            for radius in range(4,49,4):
                for dx,dy in ((0,radius),(radius,0),(0,-radius),(-radius,0)):
                    candidates.append((position[0]+dx,position[1]+dy))
            position=next((p for p in candidates if self.world.can_stand(p)),None)
            if position is None:
                self.world=self.town
                position=self.town.data['spawn']
        self.player.position.update(position)
        self.player.moving=False;self.player.walk_ms=0
        self.social.blocked.clear()
        self.map_open=False
        self.quest_ui.reset()
        self.inventory_ui.reset()
        self._sync_inventory()
        self.transfer_cooldown=.25
        self.on_title=False
        self.opening_fade=.5
        self._mouse_held=False
        if data is None:self.opening.start_new_game()
        else:self.opening.restore(data.get('opening',{'version':1,'stage':'disabled'}))
        self.halden_visit.restore(data.get('halden_visit') if data else None)
        self.elira_visit.restore(data.get('elira_visit') if data else None)
        # Story staging can reserve a different NPC station than an older
        # checkpoint used. Recheck after those actors have been positioned.
        if not self.world.can_stand(self.player.position):
            entry=self.world.data['spawn']
            candidates=[entry]
            for radius in range(4,49,4):
                for dx,dy in ((0,radius),(radius,0),(0,-radius),(-radius,0)):
                    candidates.append((entry[0]+dx,entry[1]+dy))
            landing=next((p for p in candidates if self.world.can_stand(p)),None)
            if landing is None:
                self.world=self.town
                landing=self.town.data['spawn']
            self.player.position.update(landing)
        self.opening_audio.reset()
        self.pause.close()
        self.camera.reset()
        self.save_progress()
        return True

    def save_progress(self):
        """Checkpoint on story changes, conversations, door transfers and quit."""
        if self.on_title or not self.save_store.enabled:return False
        self._sync_inventory()
        data={'version':1,'quests':self.quests.to_dict(),'opening':self.opening.to_dict(),
              'inventory':self.inventory.to_dict(),
              'halden_visit':self.halden_visit.to_dict(),
              'elira_visit':self.elira_visit.to_dict(),
              'dialogue_flags':sorted(self.social.flags),
              'player':{'scene':self.world.data['id'],
                        'position':list(self.player.position),'facing':self.player.facing},
              'exterior_position':list(self.exterior_position)}
        if not self.save_store.write(data):
            self.save_error=self.save_store.error
            self._save_retry_seconds=10.0
            return False
        self.saved_journey=data
        self.save_error=None
        self._save_retry_seconds=0.0
        self._saved_progress=self._progress_signature()
        return True

    def to_canvas(self,point):
        """Match draw's integer scaling, including fullscreen letterboxing."""
        width,height=self.window.get_size()
        scale=max(1,min(width//VIEW_SIZE[0],height//VIEW_SIZE[1]))
        x=(point[0]-(width-VIEW_SIZE[0]*scale)//2)/scale
        y=(point[1]-(height-VIEW_SIZE[1]*scale)//2)/scale
        return (x,y) if 0<=x<VIEW_SIZE[0] and 0<=y<VIEW_SIZE[1] else None

    def _ensure_ui_surface(self):
        """UI pixels follow the display; world pixels retain integer scaling."""
        width,height=self.window.get_size()
        scale=max(1,min(width//VIEW_SIZE[0],height//VIEW_SIZE[1]))
        size=(VIEW_SIZE[0]*scale,VIEW_SIZE[1]*scale)
        if self.ui_surface is None or self.ui_surface.get_size()!=size:
            self.ui_surface=pygame.Surface(size)
        return scale,size,((width-size[0])//2,(height-size[1])//2)

    def _load_scene(self,path):
        path=Path(path).resolve()
        if path not in self.scenes:self.scenes[path]=World(path,self.town._images)
        return self.scenes[path]

    def _scene_by_id(self,scene_id):
        if scene_id==self.town.data['id']:return self.town
        try:path=self.town.data['interior_scenes'][scene_id]
        except KeyError as error:raise ValueError(f'Unknown routine scene: {scene_id}') from error
        return self._load_scene(ROOT/path)

    def _setup_persistent_npcs(self):
        """Create each cross-room actor once and attach it to its initial room."""
        for record in self.town.data.get('persistent_npcs',[]):
            scene_id=record['scene']
            world=self._scene_by_id(scene_id)
            actor=RoutineNPC(record,world,scene_id)
            if not world.can_stand(actor.position,actor.probe_size,actor):
                raise ValueError(f'Blocked persistent NPC spawn for {record["id"]}: {tuple(actor.position)}')
            world.npcs.append(actor)
            self.persistent_npcs.append(actor)
            self._routine_worlds[actor]=world
            # Register props with every referenced room once. They stay on the
            # furniture when the persistent actor transfers to another room.
            for scene_id in {prop['scene'] for prop in actor.surface_props}:
                self._scene_by_id(scene_id).attach_routine_props(actor)

    def _transfer_routine_npc(self,actor,step):
        """Move one persistent actor between rooms without cloning or resetting it."""
        origin=self._routine_worlds[actor]
        departure=next((d for d in origin.doors if d.data['id']==step.get('departure_door')),None)
        if departure and departure.data['requires_open'] and departure.state!='open':return None
        destination=self._scene_by_id(step['scene'])
        position=step['position']
        player_blocker=destination.probe_rect(self.player.position) if destination is self.world else None
        if not destination.can_stand(position,actor.probe_size,actor,player_blocker):return None
        if actor in origin.npcs:origin.npcs.remove(actor)
        actor.position.update(position)
        actor.scene_id=step['scene']
        if actor not in destination.npcs:destination.npcs.append(actor)
        self._routine_worlds[actor]=destination
        arrival=next((d for d in destination.doors if d.data['id']==step.get('arrival_door')),None)
        if arrival:arrival.force_open()
        return destination

    def toggle_fullscreen(self):
        self.fullscreen=not self.fullscreen
        if self.fullscreen:
            self.windowed_size=self.window.get_size()
            self.window=pygame.display.set_mode((0,0),pygame.FULLSCREEN)
        else:self.window=pygame.display.set_mode(self.windowed_size,pygame.RESIZABLE)
        self._ensure_ui_surface()

    def handle_events(self):
        advanced=False
        resumed=False
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                self.save_progress()
                return False
            if event.type==pygame.KEYDOWN and event.key==pygame.K_F11:
                self.toggle_fullscreen()
                continue
            if event.type==pygame.VIDEORESIZE and not self.fullscreen:
                self.window=pygame.display.set_mode((max(480,event.w),max(320,event.h)),pygame.RESIZABLE)
                self._ensure_ui_surface()
                continue
            if self.on_title:
                if not self.title.handle_event(event):return False
                continue
            if event.type==pygame.MOUSEBUTTONUP and event.button==1:
                self._mouse_held=False
                self.social.pointer(self.to_canvas(getattr(event,'pos',pygame.mouse.get_pos())),pressed=False)
                self.quest_ui.handle_hud_event(event)
            if resumed:continue
            if self.pause.is_open:
                overlay=getattr(self.pause,'overlay',None)
                if not self.pause.handle_event(event):
                    self.save_progress()
                    return False
                resumed=not self.pause.is_open or (overlay is not None and self.pause.overlay is None)
                continue
            if self.inventory_ui.is_open:
                self.inventory_ui.handle_event(event)
                resumed=not self.inventory_ui.is_open
                self.social.clear_pointer()
                continue
            if self.quest_ui.journal_open:
                self.quest_ui.handle_event(event)
                resumed=not self.quest_ui.journal_open
                self.social.clear_pointer()
                continue
            if self.map_open:
                if (event.type==pygame.KEYDOWN and event.key==pygame.K_j
                        and not getattr(event,'repeat',False)):
                    self.map_open=False
                    self.quest_ui.toggle_journal()
                else:self.map_ui.handle_event(event)
                resumed=not self.map_open
                self.social.clear_pointer()
                continue
            if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                if getattr(event,'repeat',False):continue
                self.social.clear_pointer()
                self.pause.open()
                continue
            if event.type==pygame.MOUSEMOTION:
                self.social.pointer(self.to_canvas(event.pos),pressed=self._mouse_held)
            if (not self.social.locked and not self.opening.locks_player
                    and event.type==pygame.MOUSEBUTTONDOWN and event.button==1
                    and self.to_canvas(event.pos) is not None and
                    self._hud_menu_rect().collidepoint(self.to_canvas(event.pos))):
                self.social.clear_pointer()
                self.pause.open()
                self.ui.sound('confirm')
                continue
            if not self.social.locked and self.quest_ui.handle_hud_event(event):continue
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                self.social.pointer(self.to_canvas(event.pos),pressed=True)
                if (not self._mouse_held and not advanced and self.social.active
                        and not self.map_open):
                    self.social.click(self.to_canvas(event.pos));advanced=True
                self._mouse_held=True
            if event.type==pygame.KEYDOWN:
                if (self.social.active and not self.map_open and
                        event.key in (pygame.K_SPACE,pygame.K_e)):
                    if not getattr(event,'repeat',False) and not advanced:
                        self.social.advance();advanced=True
                    continue
                if self.opening.locks_player and event.key in (pygame.K_m,pygame.K_j,pygame.K_i):continue
                if event.key==pygame.K_i and not getattr(event,'repeat',False):
                    self.inventory_ui.open()
                    self.social.clear_pointer()
                if event.key==pygame.K_m:
                    self.map_open=True
                    self.map_ui.reset()
                    self.social.clear_pointer()
                    self.ui.sound('confirm')
                elif event.key==pygame.K_j and not getattr(event,'repeat',False):
                    self.map_open=False
                    self.quest_ui.toggle_journal()
                    self.social.clear_pointer()
                elif (event.key==pygame.K_e and not getattr(event,'repeat',False) and
                      not self.map_open and not self.quest_ui.journal_open):
                    if not any(visit.interact() for visit in self.household_visits):self.opening.inspect_nearby()
        return True

    def update(self,seconds,direction=None,running=None):
        if self.on_title:
            self.title.update(seconds)
            return
        self.opening_audio.set_paused(self.pause.is_open or self.inventory_ui.is_open)
        if self.pause.is_open or self.inventory_ui.is_open:
            self.opening_audio.update(0)
            return
        self.opening_fade=max(0,self.opening_fade-seconds)
        self.elapsed_ms+=seconds*1000
        self.location_seconds=max(0.0,self.location_seconds-seconds)
        self.opening.update(seconds)
        self.opening_audio.update(seconds)
        if direction is None:
            keys=pygame.key.get_pressed()
            direction=(int(keys[pygame.K_d] or keys[pygame.K_RIGHT])-int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
                       int(keys[pygame.K_s] or keys[pygame.K_DOWN])-int(keys[pygame.K_w] or keys[pygame.K_UP]))
            running=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        if not self.map_open and not self.quest_ui.journal_open:
            self.opening.request_movement(direction)
        for scene in self.scenes.values():
            for door in scene.doors:
                door.update(self.player.position if scene is self.world else None,seconds,
                            (npc.position for npc in scene.npcs if isinstance(npc,RoutineNPC) or getattr(npc,'opens_doors',False)))
        direction=(0,0) if (self.map_open or self.quest_ui.journal_open or
                           self.opening.locks_player or self.household_action or self.opening_fade) else direction
        if not self.opening.controls_player:
            previous=self.player.position.copy()
            self.player.update(direction,seconds,self.world,bool(running))
            if self.world.data.get('kind')=='interior' and self.opening.stage in ('explore','assignment','done'):
                self.opening.record_footsteps(self.player.position.distance_to(previous))
        if not self.quest_ui.journal_open:self.social.update(direction)
        for visit in self.household_visits:visit.update(seconds)
        for scene in self.scenes.values():
            blocker=scene.probe_rect(self.player.position) if scene is self.world else None
            for npc in scene.npcs:
                if isinstance(npc,(Gardener,DaisyRoutine)):npc.update(seconds,scene,blocker)
        for npc in self.persistent_npcs:
            if getattr(npc,'story_paused',False):continue
            scene=self._routine_worlds[npc]
            blocker=scene.probe_rect(self.player.position) if scene is self.world else None
            npc.update(seconds,scene,blocker,self._transfer_routine_npc)
        for routine in self.play_routines:routine.update(seconds)
        for routine in self.block_routines:routine.update(seconds)
        for routine in self.bone_routines:routine.update(seconds)
        self.social.update((0,0))
        self.transfer_cooldown=max(0,self.transfer_cooldown-seconds)
        if (not self.map_open and not self.quest_ui.journal_open and
                not self.opening.locks_player and not self.household_action and not self.transfer_cooldown):
            for door in self.world.doors:
                if door.can_enter(self.player.position,direction):
                    self.enter(door)
                    break
        self.quest_ui.update(seconds)
        self._sync_inventory()
        self._save_retry_seconds=max(0.0,self._save_retry_seconds-seconds)
        if (self.save_store.enabled and not self._save_retry_seconds and
                self._progress_signature()!=self._saved_progress):
            self.save_progress()
        self.camera.update(seconds)
        location=(self.world.data['name'] if self.world is not self.town
                  else self.world.location(self.player.position))
        if location!=self.location_label:
            self.location_label=location
            self.location_seconds=3.5

    def enter(self,door):
        if (self.pause.is_open or self.inventory_ui.is_open or self.quest_ui.journal_open or
                self.opening.locks_player or self.household_action):return False
        path=(ROOT/door.data['destination']).resolve()
        destination=self._load_scene(path)
        spawn=door.data['spawn']
        # A moving resident can cross a doorway. Keep the transition armed and
        # let the next update enter as soon as the landing is clear.
        if not destination.can_stand(spawn):
            arrival_probe=destination.probe_rect(spawn)
            if any(npc.blocker.colliderect(arrival_probe) for npc in destination.npcs):return False
            raise ValueError(f'Blocked arrival for {door.data["id"]}: {spawn}')
        # A valid transfer ends live speech without accepting choices or
        # completing prose that the player left unread.
        if self.social.locked:self.social.cancel()
        if self.world is self.town:self.exterior_position.update(door.data['anchor'])
        self.world=destination
        self.player.position.update(spawn)
        self.player.facing=door.data['arrival_facing']
        self.player.moving=False;self.player.walk_ms=0
        self.transfer_cooldown=.25
        arrival=next((d for d in destination.doors if d.data['id']==door.data['arrival_door']),None)
        if arrival:arrival.force_open()
        self.opening.on_enter_scene()
        self.save_progress()
        return True

    def text(self,text,position,font=None,color=IVORY):
        """Compatibility helper for captures; gameplay text uses display pixels."""
        return self.ui.painter(self.ui_surface).text(text,position,color=color)

    def draw_map(self):
        self.map_ui.draw(self.ui_surface)

    def _hud_menu_rect(self):
        painter=self.ui.painter(self.ui_surface)
        font=painter.font()
        width=max(64,font.size('Menu')[0]+30)
        height=max(22,font.get_height()+8)
        self.menu_rect=pygame.Rect(VIEW_SIZE[0]-12-width,VIEW_SIZE[1]-12-height,width,height)
        return self.menu_rect

    def draw_hud(self,canvas):
        if (self.pause.is_open or self.social.locked or self.opening.locks_player
                or self.map_open or self.quest_ui.journal_open or self.inventory_ui.is_open):return
        painter=self.ui.painter(canvas)
        menu=self._hud_menu_rect()
        pointer=self.to_canvas(pygame.mouse.get_pos())
        painter.button(menu,'Menu',selected=pointer is not None and menu.collidepoint(pointer),
                       pressed=self._mouse_held and pointer is not None and menu.collidepoint(pointer))
        if self.location_seconds>0:
            fade=1.0 if self.audio.reduced_motion else min(1.0,self.location_seconds/.45)
            layer=canvas if fade>=1 else pygame.Surface(canvas.get_size(),pygame.SRCALPHA)
            plaque=self.ui.painter(layer)
            title='Eldenmere' if self.world is self.town else self.world.data['name']
            subtitle=self.world.location(self.player.position) if self.world is self.town else ''
            title_lines=plaque.wrap(title,180,role='name',bold=True)
            subtitle_lines=plaque.wrap(subtitle,180,role='small') if subtitle else []
            title_height=plaque.font('name',bold=True).get_linesize()
            small_height=plaque.font('small').get_linesize()
            height=16+len(title_lines)*title_height+len(subtitle_lines)*small_height
            widths=([plaque.font('name',bold=True).size(line)[0]+40 for line in title_lines]+
                    [plaque.font('small').size(line)[0]+40 for line in subtitle_lines])
            width=max(118,min(220,max(widths or [118])))
            plaque.panel((12,12,width,height))
            plaque.lantern((24,23),size=8)
            y=19
            for line in title_lines:
                plaque.text(line,(35,y),role='name',bold=True)
                y+=title_height
            for line in subtitle_lines:
                plaque.text(line,(35,y),role='small',color=MUTED)
                y+=small_height
            if layer is not canvas:
                layer.set_alpha(round(fade*255))
                canvas.blit(layer,(0,0))
        hint=self.opening.interaction_hint() or next((hint for visit in self.household_visits
                                                     if (hint:=visit.interaction_hint())), '')
        if hint:
            hint=hint.replace(': ',' — ',1)
            available=menu.left-24
            lines=painter.wrap(hint,available-18,role='body')
            line_height=painter.font().get_linesize()
            rect=pygame.Rect(12,VIEW_SIZE[1]-12-(len(lines)*line_height+14),
                             min(available,max(painter.font().size(line)[0] for line in lines)+18),
                             len(lines)*line_height+14)
            painter.panel(rect)
            for index,line in enumerate(lines):
                painter.text(line,(rect.x+9,rect.y+7+index*line_height),color=GOLD)

    def draw(self):
        if self.on_title:
            self.title.draw()
            return
        camera=self.camera.position()
        self.world.draw(self.canvas,camera,self.player,self.elapsed_ms,include_ui=False)
        self.opening.draw_world(self.canvas,camera)
        for visit in self.household_visits:visit.draw_world(self.canvas,camera)
        _,size,origin=self._ensure_ui_surface()
        pygame.transform.scale(self.canvas,size,self.ui_surface)
        for routine in getattr(self.world,'play_routines',[]):
            routine.draw(self.ui_surface,camera,self.world)
        self.quest_ui.draw_markers(self.ui_surface,camera)
        self.draw_hud(self.ui_surface)
        self.quest_ui.draw_tracker(self.ui_surface)
        if not self.map_open and not self.quest_ui.journal_open:
            self.social.draw(self.ui_surface,self.elapsed_ms,camera=camera)
        self.quest_ui.draw_notifications(self.ui_surface)
        if self.save_error and not self.quest_ui.journal_open:
            painter=self.ui.painter(self.ui_surface)
            lines=painter.wrap('Progress could not be saved. Check the saves folder.',436,role='small')
            height=len(lines)*painter.font('small').get_linesize()+14
            y=VIEW_SIZE[1]-self._hud_menu_rect().height-22-height
            painter.panel((12,y,456,height))
            for index,line in enumerate(lines):
                painter.text(line,(22,y+7+index*painter.font('small').get_linesize()),
                             role='small',color=ERROR)
        if self.opening_fade and not self.audio.reduced_motion:
            self.ui.painter(self.ui_surface).veil(round(255*self.opening_fade/.5))
        self.pause.draw(self.ui_surface)
        if self.map_open:self.draw_map()
        self.quest_ui.draw_journal(self.ui_surface)
        self.inventory_ui.draw(self.ui_surface)
        self.window.fill('#101b19')
        self.window.blit(self.ui_surface,origin)
        pygame.display.flip()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless',action='store_true',help='Run without a visible window for verification')
    parser.add_argument('--windowed',action='store_true',help='Launch in a resizable window instead of fullscreen')
    parser.add_argument('--frames',type=int,default=0,help='Exit after this many frames (0: play until quit)')
    parser.add_argument('--screenshot',type=Path,help='Save the final rendered window as a PNG')
    args=parser.parse_args(argv)
    if args.frames<0:parser.error('--frames must be nonnegative')
    if args.headless:os.environ['SDL_VIDEODRIVER']='dummy'
    if not MAP_FILE.is_file():raise SystemExit('Playable town data is missing. Restore assets/maps/eldenmere/playable from the repository.')
    game=Game(fullscreen=not (args.headless or args.windowed),save_path=ROOT/'saves/journey.json',
              settings_path=ROOT/'saves/settings.json')
    if not args.headless:
        game.opening_audio.prepare()
        game.title.start_music()
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
    finally:
        game.save_progress()
        game.opening_audio.reset()
        pygame.quit()
    return 0


if __name__=='__main__':raise SystemExit(main())
