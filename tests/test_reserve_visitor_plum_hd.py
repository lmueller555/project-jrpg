"""Faithful reserve visitor art opt-in preserves the stationary social contract."""
import json
import os
from pathlib import Path
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from sanctuary_reserve import ReserveVisitor
ROOT=Path(__file__).resolve().parents[1]
class World:
    def image(self,path):return pygame.image.load(str(ROOT/path)).convert_alpha()
class PlumArtTests(unittest.TestCase):
    def test_native_bank_and_unchanged_behavior(self):
        pygame.init();pygame.display.set_mode((1,1))
        try:
            records=json.loads((ROOT/'assets/story/sanctuary_reserve/layout.json').read_text())['actors']
            record=next(r for r in records if r['id']=='reserve_visitor_plum')
            actor=ReserveVisitor(record,World())
            self.assertEqual(actor.roster_art.design_id,'adult_woman_03')
            self.assertEqual(actor.data['variant'],'female_03')
            self.assertEqual(tuple(actor.position),(300,306))
            self.assertEqual(actor.blocker.size,(10,6))
            self.assertEqual(actor.draw_anchor,(12,30))
            for facing in ('front','back','left','right'):
                actor.request_conversation(facing)
                sprite=actor.sprite(999)
                self.assertEqual(sprite.get_size(),(24,36))
                self.assertEqual(sprite.native.get_size(),(48,72))
                self.assertIs(sprite,actor.idles[facing])
            actor.end_conversation()
            self.assertEqual(actor.facing,'left')
            self.assertFalse(actor.conversation_ready)
            self.assertFalse(actor.moving)
            self.assertFalse(next(r for r in records if r['id']=='reserve_caretaker').get('roster_design'))
        finally:pygame.quit()
if __name__=='__main__':unittest.main()
