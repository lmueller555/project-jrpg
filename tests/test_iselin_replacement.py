"""The live regent is consistently Iselin; predecessor data is archival only."""
import json
from pathlib import Path
import tempfile
import unittest
import pygame
from tools.capture_sanctuary_rescue import make_game
from tools.build_regent_iselin import products
from party_state import PartyState
from sanctuary_arrival import CastActor

ROOT=Path(__file__).resolve().parents[1]


class ReplacementTests(unittest.TestCase):
    def test_active_manifests_and_dialogue_use_one_registered_identity(self):
        for name in ('assets/story/regent/art.json','assets/story/regent/layout.json',
                     'assets/story/regent/scene.json','assets/story/regent/resolution.json',
                     'assets/story/regent_arrival/scene.json','assets/story/regent_arrival/scenery/scenery.json',
                     'assets/story/regent_arrival/crossroads/manifest.json',
                     'assets/story/regent_aerial/actors/manifest.json','assets/story/regent_aerial/landscape/manifest.json',
                     'assets/story/sanctuary_arrival/scene.json','assets/story/sanctuary_rescue/scene.json',
                     'assets/dialogue/eldenmere.json','assets/quests/eldenmere.json','assets/portraits/eldenmere/portraits.json'):
            with self.subTest(file=name):self.assertNotIn('aldric',(ROOT/name).read_text().lower())
        art=json.loads((ROOT/'assets/story/regent/art.json').read_text())
        actor=next(a for a in art['actors'] if a['id']=='iselin')
        self.assertEqual(actor['art'],'assets/characters/iselin/animation.json')
        self.assertEqual(actor['draw_anchor'],[12,30])
        self.assertEqual(actor['probe_size'],[8,4])
        manifest=json.loads((ROOT/'assets/story/regent_arrival/actors/iselin/animation.json').read_text())
        for direction in ('left','left_back','back'):
            self.assertEqual(len(manifest['loops']['walk_'+direction]),16)
        for path,data in products().items():
            with self.subTest(export=str(path)):
                self.assertEqual(path.read_bytes(),data)

    def test_native_seating_releases_its_override(self):
        with tempfile.TemporaryDirectory() as directory:
            g=make_game(directory,seed=False,embedded=False)
            try:
                c=g.regent_quest;a=c.iselin;c.stage='welcome';c._meal_ready=True
                c._place(a,c.dining,c.points['meal_seats']['iselin']['approach'])
                action=c.scene_actions;action._meal_clock=.1;action._apply_seating()
                self.assertEqual(a.facing,'left')
                self.assertIs(a.story_sprite,a.walks['left'][2])
                self.assertIsNone(getattr(a,'detailed_sprite',None))
                action._meal_clock=1;action._apply_seating()
                self.assertEqual(a.story_sprite.get_size(),(24,36))
                self.assertEqual(a.story_draw_anchor,(12,30))
                self.assertFalse(hasattr(a,'story_detail'))
                action.release()
                self.assertFalse(hasattr(a,'story_detail'))
                self.assertFalse(hasattr(a,'story_sprite'))
            finally:g.music.stop();pygame.quit()

    def test_sanctuary_cast_and_old_saved_guard_reason_keep_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            g=make_game(directory,seed=False,embedded=False)
            try:
                source=g.regent_quest.iselin
                actor=CastActor('iselin',g.world,source=source)
                actor.moving=True;actor.facing='back';actor.walk_ms=70
                self.assertEqual(actor.sprite(0).get_size(),(24,36))
                self.assertIsNone(getattr(actor,'detailed_sprite',None))
                self.assertEqual(actor.draw_anchor,(12,30))
                self.assertEqual(actor.walk_durations['back'],(35,)*16)
                party=PartyState(g.party.characters['caelan'])
                self.assertTrue(party.recruit('lucan',temporary=True))
                for old in ('Returned to Aldric.','Returned to Aldric after the cave rescue.'):
                    party.set_available('lucan',False,old)
                    snapshot=party.to_dict()
                    self.assertTrue(party.restore(snapshot))
                    self.assertNotIn('Aldric',party.to_dict()['members']['lucan']['reason'])
                    self.assertEqual(snapshot['members']['lucan']['reason'],old)
            finally:g.music.stop();pygame.quit()
