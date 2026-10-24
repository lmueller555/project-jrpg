"""Registered title-water art playback; runtime depends only on Pygame."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


class TitleWater:
    def __init__(self,world):
        folder=Path('assets/ui/title/water')
        self.data=json.loads((ROOT/folder/'animation.json').read_text())
        self.position=tuple(self.data['position'])
        self.frames=[(world.image((folder/frame['file']).as_posix()),frame['duration_ms'])
                     for frame in self.data['frames']]
        self.duration=sum(duration for _,duration in self.frames)

    def draw(self,target,elapsed_seconds):
        cursor=(elapsed_seconds*1000)%self.duration
        for image,duration in self.frames:
            if cursor<duration:
                target.blit(image,self.position)
                return
            cursor-=duration
