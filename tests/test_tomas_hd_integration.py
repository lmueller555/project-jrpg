"""Live Tomas native bindings retain actors, footprints, props and story cues."""
import os,tempfile,json,unittest
from pathlib import Path
from types import SimpleNamespace
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from main import Game
from tomas_scene_art import enabled,image,replacement
ROOT=Path(__file__).resolve().parents[1]
class TomasHDIntegrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();folder=Path(cls.tmp.name)
  cls.g=Game(fullscreen=False,start_on_title=False,save_path=folder/'save.json',settings_path=folder/'settings.json')
  cls.t=next(a for a in cls.g.persistent_npcs if a.data['id']=='tomas');cls.g.opening.restore({'version':1,'stage':'disabled'})
 @classmethod
 def tearDownClass(cls):pygame.quit();cls.tmp.cleanup()
 def test_actor_binding_survives_legacy_map_source_without_mutating_schedule(self):
  t=self.t;self.assertTrue(enabled(t));self.assertEqual(t.data['sprite_root'],'assets/characters/tomas')
  self.assertEqual(t.probe_size,(10,6));self.assertEqual(t.canvas_size,(64,48));self.assertEqual(t.draw_anchor,(32,36))
  self.assertEqual(t.behavior,json.loads((ROOT/t.data['behavior']).read_text()))
  for direction in t.DIRECTIONS:
   native=t.idles[direction].native
   self.assertEqual(native.get_size(),(128,96))
   canonical=pygame.image.load(str(ROOT/f'assets/characters/named_hd/tomas/idle_{direction}.png')).convert_alpha()
   self.assertEqual(pygame.image.tobytes(native.subsurface((40,12,48,72)),'RGBA'),pygame.image.tobytes(canonical,'RGBA'))
   self.assertEqual([ms for _,ms in t.walks[direction]],[140]*4)
  for frames in t.actions.values():
   for frame,_ in frames:self.assertEqual(frame.native.get_size(),(128,96))
 def test_native_props_preserve_world_footprint_and_single_owner_records(self):
  for prop in self.t.surface_props:
   legacy=self.g.town.image(prop['image'])
   self.assertEqual(prop['surface'].get_size(),legacy.get_size())
   self.assertEqual(prop['surface'].native.get_size(),tuple(v*2 for v in legacy.get_size()))
  original=json.loads((ROOT/'assets/characters/tomas/routines/animations.json').read_text())
  self.assertEqual(self.t.action_records,{k:v['frames'] for k,v in original['animations'].items()})
 def test_opening_body_and_walk_keep_logical_anchor_and_native_detail(self):
  o=self.g.opening;before=tuple(self.t.position)
  for name in ('tomas_seated.png','tomas_seated_glance.png','tomas_plate_push/frame_03.png','tomas_eat/frame_03.png'):
   frame=o._image(name);self.assertEqual(frame.get_size(),(24,36));self.assertEqual(frame.native.get_size(),(48,72))
  for direction in self.t.DIRECTIONS:
   o._walking_pose(self.t,'tomas',direction,.18,(198,200))
   self.assertEqual(self.t.story_sprite.native.get_size(),(48,72));self.assertEqual(self.t.story_draw_anchor,(12,30))
  self.assertEqual(tuple(self.t.position),before);o._clear_pose(self.t)
 def test_all_sack_views_and_custody_geometry_preserved(self):
  visit=self.g.halden_visit;before=tuple(self.t.position)
  for facing in self.t.DIRECTIONS:
   for kind,indices in [('hold',[None]),('carry',range(4)),('lift',range(4))]:
    for index in indices:
     visit._pose(self.t,'tomas',kind,facing,index)
     self.assertEqual(self.t.story_sprite.get_size(),(32,40));self.assertEqual(self.t.story_sprite.native.get_size(),(64,80));self.assertEqual(self.t.story_draw_anchor,(16,34))
  self.assertEqual(tuple(self.t.position),before);visit._clear_tomas_pose()
  for prop in visit.surface_props[:3]:self.assertEqual(prop['surface'].get_size(),(16,18));self.assertEqual(prop['surface'].native.get_size(),(32,36))
 def test_regent_meal_selects_independent_right_pose_not_mirrored_patch(self):
  owner=self.g.regent_quest;view=owner.scene_actions;before=(owner.stage,getattr(owner,'_meal_ready',False))
  try:
   owner.stage='hosted';owner._meal_ready=True;view._meal_clock=1;view._apply_seating()
   expected=self.g.town.image('assets/characters/tomas/activity_hd/breakfast/tomas_seated_right.png')
   self.assertEqual(pygame.image.tobytes(self.t.story_sprite.native,'RGBA'),pygame.image.tobytes(expected,'RGBA'))
   for i in range(1,5):
    path=f'assets/story/sanctuary_opening/poses/tomas_eat/frame_{i:02}.png'
    expected=self.g.town.image(f'assets/characters/tomas/activity_hd/breakfast/tomas_eat_right/frame_{i:02}.png')
    frame=image(view.dining,self.t,path,view._image,flipped=True)
    self.assertEqual(pygame.image.tobytes(frame.native,'RGBA'),pygame.image.tobytes(expected,'RGBA'))
  finally:view.release();owner.stage,owner._meal_ready=before
 def test_other_actors_props_and_cinematic_are_not_rebound(self):
  legacy=object();other=SimpleNamespace(data={'id':'mother_serene'})
  path='assets/story/sanctuary_opening/poses/tomas_seated.png'
  self.assertIs(image(self.g.town,other,path,lambda p:legacy),legacy)
  for path in ('assets/story/halden/caelan/hold_front.png','assets/story/halden/pallet.png','assets/story/regent_arrival/actors/tomas/stand_left.png'):
   self.assertIsNone(replacement(self.t,path))
if __name__=='__main__':unittest.main()
