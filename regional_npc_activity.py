"""Explicit scoped native regional activities over unchanged work controllers.

The controller still chooses the action/frame, prop owner, transfer cue, feet and
save state. This adapter selects reviewed complete source-body pixels only. The
ordinary1x body remains a compatibility mirror for non-native targets/tests.
"""
from hashlib import sha256
import json
from pathlib import Path
import pygame
from regional_npc_art import actor_binding
ROOT=Path(__file__).resolve().parent
ALIASES={'set_stone':('offer_left',0,2),'take_stone':('offer_left',1,3),'set_tray':('offer_left',2,4)}

class NativeRegionalActivities:
    def __init__(self,record):
        self.actor_id=record['actor_id'];path=(ROOT/record['activity_manifest']).resolve()
        directory=(ROOT/'assets/characters/regional_npc_hd'/self.actor_id).resolve()
        if not path.is_relative_to(directory):raise ValueError('Activity manifest leaves actor scope')
        raw=path.read_bytes()
        if sha256(raw).hexdigest()!=record['activity_manifest_sha256']:raise ValueError('Activity manifest changed without review')
        self.meta=json.loads(raw)
        if self.meta.get('actor_id')!=self.actor_id or self.meta.get('artwork_pixels_per_world_pixel')!=2:raise ValueError('Wrong native actor/density')
        self.anchor=tuple(self.meta['draw_anchor_logical']);self.sequences={};self.images={}
        declared={r['file']:r['sha256'] for r in self.meta.get('frames',[])}
        declared.update(record.get('activity_files_sha256',{}))
        for key,clip in self.meta['sequences'].items():
            frames=[]
            for frame in clip['frames']:
                file=frame['file'];target=(path.parent/file).resolve()
                if not target.is_relative_to(path.parent):raise ValueError('Activity frame leaves scoped bank')
                if target not in self.images:
                    data=target.read_bytes()
                    if not declared.get(file) or sha256(data).hexdigest()!=declared[file]:raise ValueError('Activity drawing changed without review: '+file)
                    self.images[target]=pygame.image.load(str(target)).convert_alpha()
                frames.append((self.images[target],frame['duration_ms']))
            anchor=tuple(clip.get('draw_anchor_logical',self.anchor))
            if not frames or any(ms<=0 for _,ms in frames):raise ValueError('Empty/untimed native activity')
            self.sequences[key]={'frames':frames,'loop':clip['loop'],'anchor':anchor}

    def detailed_sprite(self,actor,elapsed_ms):
        if actor.pose=='idle' or getattr(actor,'story_sprite',None) is not None:return None
        if hasattr(actor,'clips'):
            key=actor.animation_key;index=actor.frame_index
            if key in self.sequences:clip=self.sequences[key];frames=clip['frames']
            elif self.actor_id=='bridge_tender' and key in ALIASES:
                original,start,end=ALIASES[key];clip=self.sequences[original];frames=clip['frames'][start:end]
            else:raise ValueError('Unmapped native regional activity: '+self.actor_id+'/'+key)
            image=frames[index][0]
        else:
            pose=(getattr(actor,'native_action_key',None) if not getattr(actor,'wildlife_owned',False) else None) or actor.pose
            key=pose+'_'+actor.facing
            if key not in self.sequences:raise ValueError('Unmapped native garden activity: '+key)
            clip=self.sequences[key];frames=clip['frames']
            if pose.startswith('carry') and not actor.moving:
                # One supported contact key holds without a drifting walk clock.
                image=frames[0][0]
            else:
                total=sum(ms for _,ms in frames)
                progress=getattr(actor,'native_action_progress',None) if not getattr(actor,'wildlife_owned',False) else actor.action_progress
                if progress is None:progress=actor.action_progress
                time=max(0,progress)*total if progress is not None else max(0,actor.clock)*1000
                if clip['loop'] and progress is None:time%=total
                image=frames[-1][0]
                for candidate,ms in frames:
                    if time<ms:image=candidate;break
                    time-=ms
        return image,tuple(v*2 for v in clip['anchor'])


def for_actor(actor):
    record=actor_binding(actor.data['id'])
    return NativeRegionalActivities(record) if record and record['activation']['activity'] else None
