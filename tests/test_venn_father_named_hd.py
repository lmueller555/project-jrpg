"""Named Venn father bank contract; no movement added to resident."""
import os,tempfile,unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
import main
from npc_roster_art import RosterArt
from rendering import snapshot,WorldCanvas
ROOT=Path(__file__).resolve().parents[1]
class VennFatherNative(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();p=Path(cls.tmp.name);cls.g=main.Game(fullscreen=False,start_on_title=True,save_path=p/'s.json',settings_path=p/'settings.json')
 @classmethod
 def tearDownClass(cls):cls.g.music.stop();pygame.quit();cls.tmp.cleanup()
 def test_exact_native_bank_and_unchanged_gameplay_contract(self):
  a=self.g.venn_visit.family['father'];bank=RosterArt(self.g.venn_visit.home,'venn_father',named=True);self.assertEqual(bank.draw_anchor,(12,30));self.assertEqual(bank.foot_anchor,(12,34));self.assertFalse(hasattr(a,'moving'));self.assertEqual(a.blocker.size,(12,8))
  for dr in ('front','back','left','right'):
   png=ROOT/f'assets/characters/named_hd/venn_father/idle_{dr}.png';self.assertEqual(pygame.image.tobytes(snapshot(bank.idles[dr]),'RGBA'),pygame.image.tobytes(pygame.image.load(str(png)),'RGBA'));self.assertEqual(len(bank.walks[dr]),8)
   for i,(im,duration) in enumerate(bank.walks[dr]):
    self.assertEqual(duration,70);self.assertIs(bank.sprite(dr,True,i*70),im);canvas=WorldCanvas((24,36),pygame.SRCALPHA);canvas.blit(im,(0,0));png=ROOT/f'assets/characters/named_hd/venn_father/walk_{dr}/frame_{i+1:02}.png';self.assertEqual(pygame.image.tobytes(snapshot(canvas),'RGBA'),pygame.image.tobytes(pygame.image.load(str(png)),'RGBA'))
