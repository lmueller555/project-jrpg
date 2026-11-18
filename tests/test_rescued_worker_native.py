"""The separate cave rescue worker keeps native art and original gameplay contracts."""
import json,os,unittest
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from sanctuary_rescue import SanctuaryRescue,ROOT,ASSETS
from sanctuary_arrival import CastActor
from rendering import WorldCanvas
class Images:
 def image(self,path):return pygame.image.load(str(ROOT/path)).convert_alpha()
class RescuedWorkerNative(unittest.TestCase):
 @classmethod
 def setUpClass(cls):pygame.init();pygame.display.set_mode((1,1));cls.world=Images()
 @classmethod
 def tearDownClass(cls):pygame.quit()
 def registry(self):
  c=SanctuaryRescue.__new__(SanctuaryRescue);c.art=None;c._load_art();return c.art
 def test_only_worker_is_overridden_and_props_are_unchanged(self):
  m=self.registry();old=json.loads((ASSETS/'art.json').read_text());self.assertEqual(m['props'],old['props']);self.assertEqual(m['prop_sources'],old['prop_sources'])
  for key in old['actors']:
   if key!='worker':self.assertEqual(m['actors'][key],old['actors'][key])
  self.assertEqual(m['actors']['worker']['anchor'],[20,34]);self.assertEqual(m['actors']['worker']['frame_size'],[40,40])
 def test_all_travel_and_pose_frames_preserve_native_pixels(self):
  m=self.registry()['actors']['worker'];a=CastActor('worker',self.world,variant='male_02',art=m);self.assertEqual(a.data['id'],'sanctuary_arrival_worker');self.assertEqual(a.probe_size,(24,12));self.assertEqual(a.draw_anchor,(20,34))
  for d,frames in a.walks.items():
   self.assertEqual(a.walk_durations[d],(220,)*4)
   for s,f in zip(frames,m['walks'][d]):
    self.assertIsInstance(s,WorldCanvas);self.assertEqual(s.get_size(),(40,40));self.assertEqual(s.native.get_size(),(80,80));raw=self.world.image(f['file']);self.assertEqual(pygame.image.tostring(s.native,'RGBA'),pygame.image.tostring(raw,'RGBA'))
  for name,p in a.pose_animations.items():
   a.pose=name;self.assertEqual(a.draw_anchor,(20,34))
   for s in p['frames']:self.assertEqual(s.native.get_size(),(80,80))
 def test_original_tempos_looping_and_supported_alias_are_exact(self):
  m=self.registry()['actors']['worker'];old=json.loads((ASSETS/'art.json').read_text())['actors']['worker']
  for name,p in m['poses'].items():
   self.assertEqual(p['loop'],old['poses'][name]['loop']);self.assertEqual([f['duration_ms']for f in p['frames']],[f['duration_ms']for f in old['poses'][name]['frames']])
  self.assertEqual(m['poses']['supported']['frames'][0]['file'],m['poses']['rise']['frames'][-1]['file'])
 def test_original_portrait_identity_is_not_a_roster_swap(self):
  path=ROOT/'assets/characters/rescue_worker/activity_hd';m=json.loads((path/'identity.json').read_text());old=json.loads((ROOT/'assets/portraits/eldenmere/portraits.json').read_text())['portraits']['male_02'];self.assertEqual((path/'portrait.png').read_bytes(),(ROOT/'assets/portraits/eldenmere'/old['file']).read_bytes());self.assertEqual(m['id'],'rescue_worker')
