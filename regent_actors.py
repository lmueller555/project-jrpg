"""Small scene-owned visitors with the game's ordinary grounded registration."""
from rendering import load_art, record_art
from rendering import scale as render_scale
import json
from pathlib import Path
import pygame

ROOT=Path(__file__).resolve().parent


def animation_frame(frames, durations, elapsed_ms, *, loop=True):
    """Select explicit authored timings, holding a completed one-shot pose."""
    total=sum(durations)
    remaining=max(0.,float(elapsed_ms))
    if loop:remaining%=total
    elif remaining>=total:return frames[-1]
    for frame,duration in zip(frames,durations):
        if remaining<duration:return frame
        remaining-=duration
    return frames[-1]

class StoryActor:
    def __init__(self, record, world):
        self.data=dict(record)
        self.position=pygame.Vector2(record['position'])
        self.probe_size=tuple(record.get('probe_size',(8,4)))
        self.draw_anchor=tuple(record.get('draw_anchor',(12,30)))
        self.scene_id=world.data['id'];self.facing=record.get('facing','front')
        self.moving=False;self.walk_ms=0.;self.opens_doors=True
        self.story_visible=False;self.story_following=False
        self.conversation_ready=False;self.conversation_facing=self.facing
        animation=json.loads((ROOT/record['art']).read_text())
        self.idles={};self.walks={};self.walk_durations={};self.pose_animations={}
        self.detail_walks={}
        self.detail_idles={direction:(world.image(data['image']),tuple(data['draw_anchor']))
                           for direction,data in animation.get('high_resolution_idles',{}).items()}
        self.named_art=None
        self.pose=None;self.pose_ms=0.;self._pose_clock_origin=None
        if 'sheet' in animation:
            sheet=world.image(animation['sheet'])
            for direction,rect in animation['idles'].items():self.idles[direction]=record_art(sheet.subsurface(rect).copy(),animation)
            for direction,frames in animation['walks'].items():
                self.walks[direction]=[record_art(sheet.subsurface(frame['rect']).copy(),animation) for frame in frames]
                self.walk_durations[direction]=tuple(frame.get('duration_ms',140) for frame in frames)
            for name,pose in animation.get('poses',{}).items():
                self.pose_animations[name]={
                    'frames':tuple(record_art(sheet.subsurface(frame['rect']).copy(),animation) for frame in pose['frames']),
                    'durations':tuple(frame['duration_ms'] for frame in pose['frames']),
                    'loop':pose.get('loop',False),'facing':pose.get('facing')}
        else:
            for direction,path in animation['idles'].items():self.idles[direction]=load_art(world,path,animation)
            for direction,paths in animation['walks'].items():
                if isinstance(paths,dict):
                    self._load_manifest_walk(direction,paths['manifest'],world)
                else:
                    self.walks[direction]=[load_art(world,p,animation) for p in paths]
                    self.walk_durations[direction]=tuple(140 for _ in paths)

        # Explicit per-actor activation requires both base and activity banks.
        from regent_native_activity import enabled as native_enabled
        if native_enabled(record.get('id')):
            from npc_roster_art import RosterArt
            self.named_art=RosterArt(world, record['id'], named=True)
            if self.named_art.draw_anchor != self.draw_anchor:
                raise ValueError('Named visitor changed its logical draw anchor')
            # Direct scene consumers (short seat approach/attention) also see
            # registered native frames, without taking ownership of scene poses.
            self.idles=dict(self.named_art.idles)
            self.walks={d:[image for image,_ in frames]
                        for d,frames in self.named_art.walks.items()}
            self.walk_durations={d:tuple(ms for _,ms in frames)
                                 for d,frames in self.named_art.walks.items()}

        from regent_native_activity import animations as native_activities
        self.pose_animations.update(native_activities(world,record.get('id')))

    def _load_manifest_walk(self,direction,path,world):
        """Keep authored 2x frames and a world-size fallback on one clock."""
        manifest_path=ROOT/path
        manifest=json.loads(manifest_path.read_text())
        density=manifest['artwork_pixels_per_world_pixel']
        if density!=2:
            raise ValueError('Detailed actor walks require 2x artwork density')
        frames=[world.image((manifest_path.parent/frame['file']).relative_to(ROOT).as_posix())
                for frame in manifest['frames']]
        durations=tuple(frame['duration_ms'] for frame in manifest['frames'])
        if not frames or any(duration<=0 for duration in durations):
            raise ValueError('Actor walk needs frames with positive durations')
        size=tuple(manifest['frame_size'])
        if any(frame.get_size()!=size for frame in frames) or any(value%2 for value in size):
            raise ValueError('Actor walk frames must match their 2x canvas')
        self.walk_durations[direction]=durations
        self.detail_walks[direction]=(frames,tuple(manifest['draw_anchor']))
        self.walks[direction]=[render_scale(frame,(size[0]//2,size[1]//2))
                               for frame in frames]

    def set_pose(self, name, elapsed_ms=0):
        """Restore an authored native pose, including a completed reading hold."""
        if name is not None and name not in self.pose_animations:
            raise ValueError('Unknown StoryActor pose: '+str(name))
        self.pose=name;self.pose_ms=max(0.,float(elapsed_ms));self._pose_clock_origin=None

    def advance_pose(self, seconds):
        self.pose_ms+=max(0.,float(seconds))*1000

    @property
    def blocker(self):
        if not self.story_visible:return pygame.Rect(round(self.position.x),round(self.position.y),0,0)
        width,height=self.probe_size
        return pygame.Rect(round(self.position.x)-width//2,round(self.position.y)-height//2,width,height)

    def request_conversation(self,facing):
        self.conversation_facing=facing;self.conversation_ready=True
    def end_conversation(self):self.conversation_ready=False
    def sprite(self,elapsed_ms):
        direction=self.conversation_facing if self.conversation_ready else self.facing
        if self.moving and not self.conversation_ready:
            if self.named_art is not None:
                return self.named_art.sprite(direction,True,self.walk_ms)
            frames=self.walks[direction]
            return animation_frame(frames,self.walk_durations[direction],self.walk_ms)
        if self.pose in self.pose_animations and not self.conversation_ready:
            pose=self.pose_animations[self.pose]
            if self._pose_clock_origin is None:self._pose_clock_origin=elapsed_ms-self.pose_ms
            progress=max(self.pose_ms,elapsed_ms-self._pose_clock_origin)
            return animation_frame(pose['frames'],pose['durations'],progress,loop=pose['loop'])
        if self.named_art is not None:return self.named_art.sprite(direction)
        return self.idles[direction]

    def detailed_idle(self, elapsed_ms):
        direction=self.conversation_facing if self.conversation_ready else self.facing
        if self.moving or self.pose is not None or getattr(self,'story_sprite',None) is not None:
            return None
        return self.detail_idles.get(direction)

    def detailed_sprite(self, elapsed_ms):
        """Match sprite() precedence; external scene poses own their artwork."""
        if getattr(self,'story_sprite',None) is not None:
            return getattr(self,'story_detail',None)
        direction=self.conversation_facing if self.conversation_ready else self.facing
        if self.moving and not self.conversation_ready:
            if direction not in self.detail_walks:return None
            frames,anchor=self.detail_walks[direction]
            return animation_frame(frames,self.walk_durations[direction],self.walk_ms),anchor
        if self.pose in self.pose_animations and not self.conversation_ready:return None
        return self.detail_idles.get(direction)
