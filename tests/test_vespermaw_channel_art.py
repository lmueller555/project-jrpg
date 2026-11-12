"""Registered elemental materials and channel performance asset boundaries."""
import json
import os
from pathlib import Path
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import pygame

from vespermaw_channel_art import VespermawChannelArt

ROOT=Path(__file__).resolve().parents[1]


class VespermawChannelArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.display.set_mode((1,1))
        cls.art=VespermawChannelArt()

    @classmethod
    def tearDownClass(cls):pygame.display.quit()

    def test_full_performance_has_registered_anatomy_and_precise_timing(self):
        data=self.art.data
        self.assertEqual(len(data['frames']),72)
        self.assertEqual(sum(f['duration_ms'] for f in data['frames']),2500)
        self.assertEqual(data['commit_ms'],1650)
        self.assertEqual(data['anchor'],[64,128])
        self.assertEqual([data['frames'][i]['phase'] for i in (0,24,42,64)],
                         ['brace','rise','release','settle'])
        outputs=[]
        for frame in data['frames']:
            image,anchor=self.art.channel_frame(frame['start_ms'],'fire','ice')
            self.assertEqual(image.get_size(),(160,144))
            self.assertEqual(anchor,(64,128))
            self.assertEqual(frame['anchors']['floor'],[64,128])
            outputs.append(pygame.image.tobytes(image,'RGBA'))
        self.assertEqual(len(set(outputs)),72)

    def test_element_material_retains_every_pose_silhouette_and_caches_stably(self):
        bank=json.loads((ROOT/'assets/combat/vespermaw/animation.json').read_text())
        for name,animation in bank['animations'].items():
            # Every state includes attacks, hit, recovery and defeat; sample
            # first/middle/last to protect their materially different outlines.
            for frame in [animation['frames'][i] for i in (0,len(animation['frames'])//2,-1)]:
                base=pygame.image.load(str(ROOT/'assets/combat/vespermaw'/frame['file'])).convert_alpha()
                original=pygame.image.tobytes(base,'RGBA')
                forms=[]
                for element in ('fire','ice','water'):
                    tinted=self.art.tint(base,element)
                    self.assertIs(tinted,self.art.tint(base,element))
                    self.assertEqual(pygame.surfarray.array_alpha(tinted).tolist(),
                                     pygame.surfarray.array_alpha(base).tolist(),(name,element))
                    forms.append(pygame.image.tobytes(tinted,'RGBA'))
                self.assertEqual(len(set(forms)),3,name)
                self.assertEqual(pygame.image.tobytes(base,'RGBA'),original)

    def test_channel_lights_do_not_leak_into_transparent_sprite_padding(self):
        for elapsed in (0,550,1000,1649,1650,2000,2499):
            index=self.art._index(elapsed)
            image,_=self.art.channel_frame(elapsed,'water','fire')
            self.assertEqual(pygame.surfarray.array_alpha(image).tolist(),
                             pygame.surfarray.array_alpha(self.art.frames[index]).tolist())
            self.assertIn('spine',self.art.anchors(elapsed))

    def test_final_fur_reveal_completes_at_the_authoritative_commit_cue(self):
        cue=self.art.data['commit_ms']
        index=self.art._index(cue)
        record=self.art.data['frames'][index]
        self.assertEqual(index,self.art._index(cue-1))
        expected=self.art.tint(self.art.frames[index],'ice').copy()
        self.art._channel_highlights(expected,record,'ice',record['start_ms'],False)
        before,_=self.art.channel_frame(cue-1,'fire','ice')
        committed,_=self.art.channel_frame(cue,'fire','ice')
        self.assertNotEqual(pygame.image.tobytes(before,'RGBA'),
                            pygame.image.tobytes(expected,'RGBA'))
        self.assertEqual(pygame.image.tobytes(committed,'RGBA'),
                         pygame.image.tobytes(expected,'RGBA'))


if __name__=='__main__':unittest.main()
