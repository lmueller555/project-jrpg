"""Named Venn child bank contract; no movement added to resident."""
import os,tempfile,unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
import main
from npc_roster_art import RosterArt
from rendering import snapshot,WorldCanvas
ROOT=Path(__file__).resolve().parents[1]
class VennChildNative(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();p=Path(cls.tmp.name);cls.g=main.Game(fullscreen=False,start_on_title=True,save_path=p/'s.json',settings_path=p/'settings.json')
 @classmethod
 def tearDownClass(cls):cls.g.music.stop();pygame.quit();cls.tmp.cleanup()
 def test_exact_native_bank_and_unchanged_gameplay_contract(self):
  a=self.g.venn_visit.family['child'];bank=RosterArt(self.g.venn_visit.home,'venn_child',named=True);self.assertEqual(bank.draw_anchor,(12,30));self.assertEqual(bank.foot_anchor,(12,34));self.assertFalse(hasattr(a,'moving'));self.assertEqual(a.blocker.size,(0,0))
  for dr in ('front','back','left','right'):
   png=ROOT/f'assets/characters/named_hd/venn_child/idle_{dr}.png';self.assertEqual(pygame.image.tobytes(snapshot(bank.idles[dr]),'RGBA'),pygame.image.tobytes(pygame.image.load(str(png)),'RGBA'));self.assertEqual(len(bank.walks[dr]),8)
   for i,(im,duration) in enumerate(bank.walks[dr]):
    self.assertEqual(duration,70);self.assertIs(bank.sprite(dr,True,i*70),im);canvas=WorldCanvas((24,36),pygame.SRCALPHA);canvas.blit(im,(0,0));png=ROOT/f'assets/characters/named_hd/venn_child/walk_{dr}/frame_{i+1:02}.png';self.assertEqual(pygame.image.tobytes(snapshot(canvas),'RGBA'),pygame.image.tobytes(pygame.image.load(str(png)),'RGBA'))

 def test_live_native_bedrest_activates_without_collision_or_blink_changes(self):
  a=self.g.venn_visit.family['child'];self.assertEqual(a.story_position,(60,112));self.assertEqual(a.story_draw_anchor,(12,12));self.assertEqual(a.story_sort_y,167);self.assertEqual(a.blocker.size,(0,0))
  for t,name in [(0,'rest_head'),(4639,'rest_head'),(4640,'rest_blink'),(4799,'rest_blink'),(4800,'rest_head')]:
   im=a.sprite(t);png=ROOT/f'assets/characters/named_hd/venn_child/bedrest/{name}.png';self.assertEqual(pygame.image.tobytes(snapshot(im),'RGBA'),pygame.image.tobytes(pygame.image.load(str(png)),'RGBA'));a.request_conversation('right');self.assertIs(a.sprite(t),im);a.end_conversation()

class VennChildActivationGate(unittest.TestCase):
 def test_activity_stays_dormant_without_replacement_design(self):
  import json,venn_visit
  from unittest.mock import patch
  class World:
   def image(self,path):return path
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);bank=root/'assets/characters/named_hd/venn_child';rest=bank/'bedrest';rest.mkdir(parents=True);(rest/'animation.json').write_text(json.dumps({'frames':[{'file':'rest_head.png'},{'file':'rest_blink.png'}]}))
   with patch.object(venn_visit,'ROOT',root),patch.object(venn_visit,'load_art',side_effect=lambda world,path,meta:'native:'+path):
    a=venn_visit.VennResident(World(),'child',(88,138),'Venn child');self.assertFalse(any(h.startswith('native:') for h in a.heads));self.assertEqual(a.blocker.size,(0,0))
    (bank/'design.json').write_text('{}');a=venn_visit.VennResident(World(),'child',(88,138),'Venn child');self.assertTrue(all(h.startswith('native:') for h in a.heads));self.assertEqual(a.blocker.size,(0,0));self.assertEqual(a.story_position,(60,112))
