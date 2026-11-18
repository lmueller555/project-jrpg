"""Scoped firing authoring, planted registration and exact release handoff."""
import hashlib
import json
import os
from pathlib import Path
import unittest
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')

from PIL import Image
from mira_combat_art import MiraCombatArt
import pygame
from battle_action_audio import BattleActionAudio, SOURCES, LIMITS

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT/'assets/combat/mira'
SOURCE = ROOT/'assets/source/combat/mira_bolt_firing'


class MiraBoltFiringTests(unittest.TestCase):
    def setUp(self):
        self.art = MiraCombatArt()
        self.attack = self.art.animations['attack']

    def test_original_aim_pixels_and_every_other_skill_are_preserved(self):
        # Snapshot hashes are recorded before the scoped repair, not generated
        # from the new outputs. No git history is needed to run this check.
        protected = json.loads((SOURCE/'recipe.json').read_text())['protected_outputs']
        for name, expected in protected.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected,name)

    def test_firing_drawings_keep_both_boots_and_head_exactly_registered(self):
        reference = Image.open(SOURCE/'protected_aim.png').convert('RGBA')
        for frame in self.attack['frames'][3:]:
            image = Image.open(ART/frame['file']).convert('RGBA')
            for region in ((0,0,64,26),(0,36,64,64)):
                self.assertEqual(image.crop(region).tobytes(),reference.crop(region).tobytes())
            self.assertEqual(frame['anchors']['floor'],[32,54])
            self.assertEqual(set(image.getchannel('A').getdata()),{0,255})

    def test_mechanism_recoil_and_settle_are_distinct_authored_drawings(self):
        frames = self.attack['frames'][3:]
        self.assertEqual([f['phase'] for f in frames],
            ['compression','snap','recoil','recoil_peak','settle','followthrough','lower','rest'])
        pixels = [Image.open(ART/f['file']).crop((0,26,64,36)).tobytes() for f in frames]
        self.assertEqual(len(set(pixels)),8)
        self.assertNotEqual(frames[1]['anchors']['muzzle'],frames[3]['anchors']['muzzle'])

    def test_release_frame_owns_the_frozen_origin_not_the_recoiling_cuff(self):
        self.assertEqual((self.art.release_at,self.art.contact_at,self.art.duration),(.28,.4,.8))
        self.assertEqual(self.art.frame_record('attack',279.999)['phase'],'compression')
        snap = self.art.frame_record('attack',280)
        self.assertEqual(snap['phase'],'snap')
        self.assertEqual(snap['anchors']['muzzle'],[14,28])
        shot = self.art.shot(.28,.4,(400,150),(150,150))
        self.assertEqual(shot['origin'],(364,98))
        self.assertEqual(shot['projectile'],shot['origin'])
        later = self.art.shot(.38,.4,(400,150),(150,150))
        self.assertEqual(later['origin'],shot['origin'])
        self.assertNotEqual(later['muzzle'],shot['muzzle'])
        self.assertTrue(self.art.shot(.319,.4,(400,150),(150,150))['flash'])
        self.assertFalse(self.art.shot(.32,.4,(400,150),(150,150))['flash'])
        self.assertIsNone(self.art.shot(.4,.4,(400,150),(150,150))['projectile'])

    def test_dry_clack_has_its_own_short_cue_without_changing_other_skills(self):
        self.assertEqual(SOURCES['mira_clack'][0],'mira/bolt_clack.wav')
        self.assertEqual(LIMITS['mira_clack'],.065)
        self.assertEqual(LIMITS['focus'],.1)
        self.assertEqual(LIMITS['release'],.25)

    def test_production_default_mixers_decode_a_real_nonzero_clack(self):
        for rate in (44100,48000):
            with self.subTest(mixer_rate=rate):
                pygame.mixer.quit();pygame.mixer.init(frequency=rate,size=-16,channels=2)
                player=BattleActionAudio(SimpleNamespace(audio=SimpleNamespace(effects_volume=1)))
                player.play('mira_clack')
                sound=player._sounds['mira_clack']
                self.assertGreater(sound.get_length(),.06)
                self.assertGreater(len(sound.get_raw()),1000)
                self.assertTrue(any(pygame.sndarray.array(sound).flat))
                player.stop();self.assertFalse(player._channels)
        pygame.mixer.quit()


if __name__ == '__main__':unittest.main()
