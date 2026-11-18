"""Scoped Serene migration preserves logical art and original schedules."""
import json,os,unittest
from types import SimpleNamespace
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from npc_routines import RoutineNPC,ROOT
from rendering import WorldCanvas
from serene_scene_art import image,enabled,SPRITE_ROOT,ACTION_ROOT
class Images:
 def image(self,path):return pygame.image.load(str(ROOT/path)).convert_alpha()
class SereneNativeActivation(unittest.TestCase):
 @classmethod
 def setUpClass(cls):pygame.init();pygame.display.set_mode((1,1));cls.world=Images()
 @classmethod
 def tearDownClass(cls):pygame.quit()
 def actor(self,who='mother_serene'):
  records=json.loads((ROOT/'assets/maps/eldenmere/playable/map.json').read_text())['persistent_npcs']
  return RoutineNPC(next(r for r in records if r['id']==who),self.world)
 def test_generated_legacy_record_activates_only_serene(self):
  a=self.actor();self.assertTrue(enabled(a));self.assertEqual(a.sprite_root,SPRITE_ROOT);self.assertEqual(a.animation_path,ACTION_ROOT+'/routines/animations.json');self.assertEqual(a.data['sprite_root'],'assets/characters/serene')
  t=self.actor('tomas');self.assertFalse(enabled(t));self.assertEqual(t.animation_path,t.data['animation']);self.assertEqual(t.sprite_root,t.data['sprite_root'])
 def test_native_pixels_survive_padding_and_walk_cadence(self):
  a=self.actor();self.assertEqual(a.draw_anchor,(24,36));self.assertEqual(a.body_offset,(12,6));self.assertEqual(a.probe_size,(12,8));self.assertEqual(a.canvas_size,(48,48))
  for face,surface in a.idles.items():
   self.assertIsInstance(surface,WorldCanvas);self.assertEqual(surface.native.get_size(),(96,96));raw=self.world.image(SPRITE_ROOT+f'/idle_{face}.png')
   self.assertEqual(pygame.image.tostring(surface.native.subsurface((24,12,48,72)),'RGBA'),pygame.image.tostring(raw,'RGBA'));self.assertEqual(sum(ms for _,ms in a.walks[face]),560)
  for frames in a.actions.values():
   for surface,ms in frames:self.assertEqual(surface.get_size(),(48,48));self.assertEqual(surface.native.get_size(),(96,96));self.assertGreater(ms,0)
 def test_schedule_and_prop_records_are_exact(self):
  a=self.actor();legacy=json.loads((ROOT/'assets/characters/serene/routines/animations.json').read_text());self.assertEqual(a.action_metadata,legacy['animations']);self.assertEqual(a.behavior,json.loads((ROOT/a.data['behavior']).read_text()))
  for prop in a.surface_props:self.assertEqual(prop['surface'].get_size(),self.world.image(prop['image']).get_size())
  for step in a.steps:
   if step['type']!='action':continue
   a.select_step(step['id']);elapsed=0
   for rec in a.action_records[a.action_id]:
    a.state_ms=elapsed+rec['duration_ms']/2;self.assertEqual(a.current_action_record.get('prop_owner'),rec.get('prop_owner'));elapsed+=rec['duration_ms']
 def test_story_adapter_opt_in_and_fallback(self):
  a=self.actor();sentinel=object()
  for path in ['assets/story/regent/poses/serene_seated.png','assets/story/regent_emergency/poses/serene_aid_left.png']:
   s=image(self.world,a,path,lambda p:sentinel);self.assertEqual(s.get_size(),(24,36));self.assertEqual(s.native.get_size(),(48,72));self.assertIs(image(self.world,SimpleNamespace(data={'id':'mother_serene'}),path,lambda p:sentinel),sentinel)
  self.assertIs(image(self.world,a,'other.png',lambda p:sentinel),sentinel)
