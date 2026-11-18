"""Real room collision/render/controller coverage without preloading the whole game."""
import json,os,unittest
from types import SimpleNamespace as NS
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame,main
from rendering import layer
from regent_actions import RegentActions
from npc_routines import ROOT,RoutineNPC
class SereneNativeScenes(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  pygame.init();pygame.display.set_mode((1,1));cls.rooms={s:main.World(ROOT/f'assets/maps/eldenmere/building_interiors/rooms/{s}/map.json')for s in ('sanctuary_dining','sanctuary_hall')}
  for w in cls.rooms.values():w.npcs.clear()
  cls.record=next(a for a in main.read_json(ROOT/'assets/maps/eldenmere/playable/map.json')['persistent_npcs']if a['id']=='mother_serene')
 @classmethod
 def tearDownClass(cls):pygame.quit()
 def setUp(self):
  for w in self.rooms.values():w.npcs.clear();w.routine_props.clear()
  self.a=RoutineNPC(self.record,self.rooms['sanctuary_dining']);self.rooms[self.a.scene_id].npcs.append(self.a)
 def test_full_real_collision_schedule_and_conversation_pause(self):
  a=self.a;seen=set();members=[]
  def transfer(actor,step):
   target=self.rooms[step['scene']]
   if not target.can_stand(step['position'],actor.probe_size,actor):return False
   self.rooms[actor.scene_id].npcs.remove(actor);target.npcs.append(actor);return True
  for _ in range(3000):
   seen.add(a.scene_id);a.update(.1,self.rooms[a.scene_id],transfer=transfer)
   self.assertEqual(sum(a in w.npcs for w in self.rooms.values()),1)
   if a.completed_cycles:break
  self.assertEqual(a.completed_cycles,1);self.assertEqual(seen,set(self.rooms));self.assertEqual(a.scene_id,'sanctuary_dining')
  a.select_step('sort_provisions');a.request_conversation('front');a.update(.1,self.rooms[a.scene_id]);self.assertTrue(a.conversation_ready);t=a.state_ms;a.update(5,self.rooms[a.scene_id]);self.assertEqual(a.state_ms,t);a.end_conversation();a.update(.1,self.rooms[a.scene_id]);self.assertGreater(a.state_ms,t)
 def test_controller_seat_and_aid_preserve_physical_position_and_release(self):
  a=self.a;dining=self.rooms['sanctuary_dining'];player=main.Player(dining)
  game=NS(player=player,pause=NS(is_open=False),inventory_ui=NS(is_open=False),map_open=False,quest_ui=NS(journal_open=False),social=NS(script_identifier='regent_emergency'))
  seat=main.read_json(ROOT/'assets/story/regent/layout.json')['meal_seats']['mother_serene']
  owner=NS(game=game,dining=dining,serene=a,tomas=None,iselin=None,clerk=None,driver=None,stage='welcome',_meal_ready=True,points={'meal_seats':{'mother_serene':seat}},_world=lambda actor:dining,_handed_off=lambda actor:False)
  view=RegentActions(owner);view._meal_clock=.5;physical=a.position.copy();view._apply_seating();self.assertEqual(a.story_draw_anchor,(12,30));self.assertEqual(a.story_sprite.native.get_size(),(48,72));self.assertEqual(a.position,physical)
  canvas=layer((480,320),pygame.SRCALPHA);player.position.update(-1000,-1000);dining.draw(canvas,(0,0),player,0,include_ui=False);self.assertEqual(canvas.native.get_size(),(960,640))
  view.release();self.assertFalse(hasattr(a,'story_sprite'));owner.stage='emergency';view._line=lambda:(0,{'cue':'survivor_aid'});view._attention=lambda line:None;view.update(.1);self.assertEqual(a.story_draw_anchor,(12,30));self.assertEqual(a.story_sprite.native.get_size(),(48,72));self.assertEqual(a.position,physical)
  game.pause.is_open=True;t=view.clock;view.update(4);self.assertEqual(view.clock,t);view.release();self.assertFalse(hasattr(a,'story_sprite'))
