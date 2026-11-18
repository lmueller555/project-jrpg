"""Tender's inherited runtime subsets select corresponding complete native poses."""
from pathlib import Path
import copy,os,unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy');os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from bridge_crew import BridgeWorker
from regional_npc_art import actor_binding
R=Path(__file__).resolve().parents[1]
class TenderNativeSubsets(unittest.TestCase):
 def setUp(self):
  pygame.init();pygame.display.set_mode((960,640));self.addCleanup(pygame.quit)
  self.a=BridgeWorker('tender','male_03',(50,70))
  if self.a.regional_activity is None:self.skipTest('Tender activity not installed in this scoped packet')
 def assert_native_frame(self,key,index):
  a=self.a;before=copy.deepcopy(a.attachment);image,anchor=a.detailed_sprite(0);bank=a.regional_activity.meta
  f=bank['sequences'][key]['frames'][index];path=R/Path(actor_binding(a.data['id'])['activity_manifest']).parent/f['file'];expected=pygame.image.load(str(path)).convert_alpha()
  self.assertEqual(pygame.image.tobytes(image,'RGBA'),pygame.image.tobytes(expected,'RGBA'));self.assertEqual(anchor,(48,92));self.assertEqual(a.attachment,before)
  self.assertEqual(tuple(a.position),(50,70));self.assertEqual(a.blocker.size,(10,6))
 def test_three_controller_subsets_keep_exact_native_offer_frame_and_metadata(self):
  a=self.a
  for alias,start in (('set_stone',0),('take_stone',1),('set_tray',2)):
   a.pose=alias;a.facing='left';a.action_duration=1.;a.reverse=False;a.restart();a.advance(0)
   for t in (0.,.25,.75,1.):
    a.clock=t
    with self.subTest(alias=alias,time=t):self.assert_native_frame('offer_left',start+a.frame_index)
 def test_reversed_kettle_return_uses_existing_controller_index(self):
  a=self.a;a.pose='pickup';a.facing='right';a.action_duration=1.;a.reverse=True;a.restart();a.advance(0)
  for t in (0.,.3,.6,1.):
   a.clock=t
   with self.subTest(time=t):self.assert_native_frame('pickup_right',a.frame_index)
