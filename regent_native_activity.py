"""ID-local opt-in royal activity art, with unchanged scene ownership/timers."""
from pathlib import Path
import json
from rendering import load_art
ROOT=Path(__file__).resolve().parent
ALIASES={
 'assets/story/regent/poses/clerk_seated.png':('regent_clerk','seated'),
 'assets/story/regent/poses/driver_seated.png':('regent_driver','seated'),
 'assets/story/regent_emergency/poses/alarm_front.png':('regent_survivor','alarm_front'),
 'assets/story/regent_emergency/poses/rest_front.png':('regent_survivor','rest_front'),
}
def enabled(identifier):
 if identifier not in ('regent_clerk','regent_driver','regent_survivor'):return False
 folder=ROOT/'assets/characters/named_hd'/identifier
 activation=folder/'activation.json'
 activity=ROOT/'assets/story/royal_activity_hd'/identifier/'animation.json'
 if not activation.is_file() or not (folder/'design.json').is_file() or not activity.is_file():return False
 record=json.loads(activation.read_text())
 return record.get('id')==identifier and record.get('enabled') is True

def bank(identifier):
 if identifier not in ('regent_clerk','regent_driver','regent_survivor'):return None
 folder=Path('assets/story/royal_activity_hd')/identifier
 path=ROOT/folder/'animation.json'
 # Activity activation requires its actor's independently migrated base bank.
 if not enabled(identifier):return None
 meta=json.loads(path.read_text())
 if meta['id']!=identifier or meta['artwork_pixels_per_world_pixel']!=2 or meta['draw_anchor']!=[24,60]:
  raise ValueError('Invalid royal activity registration: '+identifier)
 return folder,meta

def image(world,path):
 target=ALIASES.get(path)
 if target is None:return None
 found=bank(target[0])
 if found is None:return None
 folder,meta=found;pose=meta['poses'].get(target[1])
 if pose is None:return None
 return load_art(world,(folder/pose['frames'][0]['file']).as_posix(),meta)

def animations(world,identifier):
 if identifier!='regent_clerk':return {}
 found=bank(identifier)
 if found is None:return {}
 folder,meta=found;result={}
 for name in ('read','read_attention','read_resume'):
  pose=meta['poses'].get(name)
  if pose is None:continue
  frames=tuple(load_art(world,(folder/f['file']).as_posix(),meta) for f in pose['frames'])
  durations=tuple(f['duration_ms'] for f in pose['frames'])
  if not frames or any(ms<=0 for ms in durations):raise ValueError('Invalid Page reading timing')
  result[name]=dict(frames=frames,durations=durations,loop=pose.get('loop',False),facing=pose.get('facing'))
 return result
