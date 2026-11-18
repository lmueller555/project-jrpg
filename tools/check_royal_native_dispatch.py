"""Run after merging the six royal packages; no save or scene state mutation."""
import os,sys
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
pygame.init();pygame.display.set_mode((1,1))
import regent_actors,npc_roster_art,regent_native_activity,rendering
class World:
 data={'id':'royal_test'}
 def image(self,path):
  p=ROOT/path
  return pygame.image.load(str(p)).convert_alpha()
w=World()
for who in ['regent_clerk','regent_driver','regent_survivor']:
 art='assets/story/regent_emergency/animation.json' if who=='regent_survivor' else f'assets/story/regent/actors/{who}/animation.json'
 a=regent_actors.StoryActor({'id':who,'position':[30,40],'art':art,'draw_anchor':[12,30]},w)
 assert a.named_art and a.draw_anchor==(12,30) and a.probe_size==(8,4)
 for dr in ['front','right','back','left']:
  a.facing=dr;a.moving=False;im=a.sprite(0);assert im.get_size()==(24,36) and im.native.get_size()==(48,72)
  a.moving=True;a.walk_ms=300;im=a.sprite(0);assert im.get_size()==(24,36) and im.native.get_size()==(48,72);assert len(a.walks[dr])==8
 if who=='regent_clerk':
  a.moving=False;a.set_pose('read');assert a.pose_animations['read']['durations']==(140,110,100,140,180,200)
  assert a.sprite(0).get_size()==(24,36) and a.sprite(0).native.get_size()==(48,72)
 print(who,'native base/pose dispatch logical canvas/anchors OK')
for path in regent_native_activity.ALIASES:
 im=regent_native_activity.image(w,path);assert im is not None and im.get_size()==(24,36) and im.native.get_size()==(48,72)
print('All4 exact legacy static aliases registered; no scene positions changed')
assert regent_native_activity.image(w,'unrelated.png') is None
pygame.quit()
