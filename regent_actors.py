"""Small scene-owned visitors with the game's ordinary grounded registration."""
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
        self.detail_idles={direction:(world.image(data['image']),tuple(data['draw_anchor']))
                           for direction,data in animation.get('high_resolution_idles',{}).items()}
        self.pose=None;self.pose_ms=0.;self._pose_clock_origin=None
        if 'sheet' in animation:
            sheet=world.image(animation['sheet'])
            for direction,rect in animation['idles'].items():self.idles[direction]=sheet.subsurface(rect).copy()
            for direction,frames in animation['walks'].items():
                self.walks[direction]=[sheet.subsurface(frame['rect']).copy() for frame in frames]
                self.walk_durations[direction]=tuple(frame.get('duration_ms',140) for frame in frames)
            for name,pose in animation.get('poses',{}).items():
                self.pose_animations[name]={
                    'frames':tuple(sheet.subsurface(frame['rect']).copy() for frame in pose['frames']),
                    'durations':tuple(frame['duration_ms'] for frame in pose['frames']),
                    'loop':pose.get('loop',False),'facing':pose.get('facing')}
        else:
            for direction,path in animation['idles'].items():self.idles[direction]=world.image(path)
            for direction,paths in animation['walks'].items():
                self.walks[direction]=[world.image(p) for p in paths]
                self.walk_durations[direction]=tuple(140 for _ in paths)

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
            frames=self.walks[direction]
            return animation_frame(frames,self.walk_durations[direction],self.walk_ms)
        if self.pose in self.pose_animations and not self.conversation_ready:
            pose=self.pose_animations[self.pose]
            if self._pose_clock_origin is None:self._pose_clock_origin=elapsed_ms-self.pose_ms
            progress=max(self.pose_ms,elapsed_ms-self._pose_clock_origin)
            return animation_frame(pose['frames'],pose['durations'],progress,loop=pose['loop'])
        return self.idles[direction]

    def detailed_idle(self, elapsed_ms):
        direction=self.conversation_facing if self.conversation_ready else self.facing
        if self.moving or self.pose is not None or getattr(self,'story_sprite',None) is not None:
            return None
        return self.detail_idles.get(direction)
