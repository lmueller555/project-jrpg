"""Small scene-owned visitors with the game's ordinary grounded registration."""
import json
from pathlib import Path
import pygame

ROOT=Path(__file__).resolve().parent

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
        self.idles={};self.walks={}
        if 'sheet' in animation:
            sheet=world.image(animation['sheet'])
            for direction,rect in animation['idles'].items():self.idles[direction]=sheet.subsurface(rect).copy()
            for direction,frames in animation['walks'].items():
                self.walks[direction]=[sheet.subsurface(frame['rect']).copy() for frame in frames]
        else:
            for direction,path in animation['idles'].items():self.idles[direction]=world.image(path)
            for direction,paths in animation['walks'].items():self.walks[direction]=[world.image(p) for p in paths]

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
            return frames[int(self.walk_ms//140)%len(frames)]
        return self.idles[direction]
