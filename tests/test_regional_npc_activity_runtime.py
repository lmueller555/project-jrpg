"""Native activity pixels follow existing frame/attachment controllers exactly."""
import json,os
from pathlib import Path
import unittest
from unittest.mock import patch
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy');os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame
from grain_farm import FarmWorker
from bridge_crew import BridgeWorker
from garden_orchard import GardenWorker
from regional_npc_activity import for_actor
from regional_npc_art import actor_binding
from dense_art import draw_actor
from rendering import WorldCanvas
ROOT=Path(__file__).resolve().parents[1]
class NativeActivityRuntimeTests(unittest.TestCase):
 def setUp(self):pygame.init();pygame.display.set_mode((960,640))
 def tearDown(self):pygame.quit()
 def actors(self):return [FarmWorker('loader','male_02',(50,70)),FarmWorker('coworker','male_03',(50,70)),BridgeWorker('mason','male_01',(50,70)),BridgeWorker('tender','male_03',(50,70)),GardenWorker('gardener','female_01',(50,70)),GardenWorker('picker','male_02',(50,70))]
 def active_garden(self):
  a=GardenWorker('gardener','female_01',(50,70))
  if a.regional_activity is None:self.skipTest('Blue activity selector not installed in this scoped packet')
  return a
 def test_only_explicit_activity_bindings_activate(self):
  for a in self.actors():
   binding=actor_binding(a.data['id']);self.assertEqual(bool(a.regional_activity),bool(binding and binding['activation']['activity']))
  with patch('regional_npc_activity.actor_binding',return_value=None):self.assertIsNone(for_actor(self.actors()[0]))
 def test_farm_controller_selects_exact_native_frame_without_attachment_change(self):
  checked=0
  for a in self.actors():
   if not hasattr(a,'clips') or a.regional_activity is None:continue
   for direction in ('front','back','left','right'):
    if 'carry_'+direction not in a.clips:continue
    a.pose='carry';a.facing=direction;a.moving=True;a.restart();a.advance(0);a.advance(.35)
    checked+=1
    before=a.attachment.copy();image,anchor=a.detailed_sprite(0);frame=a.regional_activity.meta['sequences'][a.animation_key]['frames'][a.frame_index]
    file=Path(actor_binding(a.data['id'])['activity_manifest']).parent/frame['file'];expected=pygame.image.load(str(ROOT/file)).convert_alpha()
    self.assertEqual(pygame.image.tobytes(image,'RGBA'),pygame.image.tobytes(expected,'RGBA'));self.assertEqual(anchor,(48,92));self.assertEqual(a.attachment,before)
  if not checked:self.skipTest('Farm activity selectors not installed in this scoped packet')
 def test_native_actor_render_preserves_pixels_and_exact_ground_registration(self):
  a=self.active_garden();a.pose='carry';a.facing='front';a.moving=False
  image,anchor=a.detailed_sprite(0);target=WorldCanvas((100,100),pygame.SRCALPHA);draw_actor(target,a,a.sprite(0),(30,32),0)
  expected=pygame.Surface((200,200),pygame.SRCALPHA);expected.blit(image,(60,64))
  self.assertEqual(pygame.image.tobytes(target.native,'RGBA'),pygame.image.tobytes(expected,'RGBA'));self.assertEqual(tuple(a.position),(50,70));self.assertEqual(a.blocker.size,(10,6))
 def test_idle_uses_roster_and_blocked_occupied_hold_stays_static(self):
  a=self.active_garden();a.pose='idle';self.assertIsNone(a.detailed_sprite(0));a.pose='carry';a.facing='front';a.moving=False
  first=pygame.image.tobytes(a.detailed_sprite(0)[0],'RGBA')
  for _ in range(20):a.clock+=.1;self.assertEqual(pygame.image.tobytes(a.detailed_sprite(0)[0],'RGBA'),first)
 def test_picker_lower_is_presentation_only_and_rest_retains_existing_anchor(self):
  a=GardenWorker('picker','male_02',(50,70))
  if a.regional_activity is None:self.skipTest('Picker selector not installed in this scoped packet')
  a.pose='carry';a.facing='front';a.native_action_key='lower';a.native_action_progress=.5
  before=(a.pose,a.facing,tuple(a.position),a.draw_anchor);im,anchor=a.detailed_sprite(0)
  path=ROOT/Path(actor_binding(a.data['id'])['activity_manifest']).parent/'lower_front_02.png';expected=pygame.image.load(str(path)).convert_alpha();self.assertEqual(pygame.image.tobytes(im,'RGBA'),pygame.image.tobytes(expected,'RGBA'));self.assertEqual(before,(a.pose,a.facing,tuple(a.position),a.draw_anchor))
  a.native_action_key=None;a.pose='rest';a.draw_anchor=(20,44);self.assertEqual(a.detailed_sprite(0)[1],(40,88))
 def test_wildlife_owner_ignores_stale_garden_presentation_override(self):
  a=self.active_garden();a.wildlife_owned=True;a.pose='weed';a.facing='front';a.native_action_key='lower';a.native_action_progress=.5;a.action_progress=.5
  image,anchor=a.detailed_sprite(0);self.assertEqual(anchor,(40,76));self.assertTrue(image.get_bounding_rect())
