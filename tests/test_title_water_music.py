"""Water registration/coverage and the shipped title theme's audio contract."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
from array import array
import hashlib
import json
from pathlib import Path
import unittest
import wave

import pygame
from PIL import Image, ImageChops
import main

ROOT=Path(__file__).resolve().parents[1]
WATER=ROOT/'assets/ui/title/water'


class TitleWaterArt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((WATER/'animation.json').read_text())
        cls.mask=Image.open(WATER/'mask.png').convert('L')
        cls.base=Image.open(ROOT/'assets/ui/title/eldenmere_dawn.png').convert('RGB')

    def test_registered_frames_change_only_water_and_cover_every_region(self):
        self.assertEqual(self.data['source_sha256'],hashlib.sha256((ROOT/'assets/ui/title/eldenmere_dawn.png').read_bytes()).hexdigest())
        self.assertEqual(sum(f['duration_ms'] for f in self.data['frames']),2400)
        x,y=self.data['position']
        variation=Image.new('L',self.base.size)
        first=None
        for record in self.data['frames']:
            overlay=Image.open(WATER/record['file']).convert('RGBA')
            self.assertLessEqual(set(overlay.getchannel('A').tobytes()),{0,255})
            full=Image.new('RGBA',self.base.size)
            full.paste(overlay,(x,y))
            self.assertEqual(full.getchannel('A').tobytes(),self.mask.tobytes())
            result=self.base.copy();result.paste(overlay,(x,y),overlay)
            delta=ImageChops.difference(result,self.base).convert('L')
            self.assertIsNone(ImageChops.multiply(delta,ImageChops.invert(self.mask)).getbbox())
            if first is None:first=result
            variation=ImageChops.lighter(variation,ImageChops.difference(result,first).convert('L'))
        for region in self.data['regions']:
            mask=Image.open(WATER/(region['id']+'_mask.png')).convert('L')
            pixels=sum(v>0 for v in mask.tobytes())
            changed=sum(v>0 for v in ImageChops.multiply(variation,mask).tobytes())
            self.assertGreater(pixels,0,region['id'])
            self.assertGreater(changed/pixels,.98,region['id'])

    def test_rocks_people_bridge_and_buildings_never_enter_water_mask(self):
        for point in ((84,192),(108,202),(140,238),(565,99),(290,211),
                      (151,314),(190,348),(297,259),(320,265)):
            self.assertEqual(self.mask.getpixel(point),0,point)

    def test_falls_are_faster_and_flows_point_downstream(self):
        regions={r['id']:r for r in self.data['regions']}
        for name in ('upper_fall','bridge_fall','foreground_cascade','mill_discharge'):
            self.assertGreater(regions[name]['cycles'],regions['main_stream']['cycles'])
            self.assertGreater(regions[name]['flow'][1],0)
        self.assertGreater(regions['main_stream']['flow'][0],0)


class TitleMusic(unittest.TestCase):
    def test_theme_is_full_length_stereo_unclipped_and_continuous(self):
        score=json.loads((ROOT/'assets/ui/title/music_score.json').read_text())
        self.assertEqual(score['meter'],'4/4')
        self.assertEqual(score['quarter_bpm'],72)
        self.assertEqual([s['name'] for s in score['sections']],['Piano','Cello answer','Together','Quiet return'])
        self.assertEqual(score['motif_midi'],[62,67,69,71,67])
        self.assertEqual(set(score['instruments']),{'piano','cello','strings','bell'})
        with wave.open(str(ROOT/'assets/ui/title/eldenmere_theme.wav')) as audio:
            self.assertEqual((audio.getnchannels(),audio.getsampwidth(),audio.getframerate()),(2,2,44100))
            duration=audio.getnframes()/audio.getframerate()
            self.assertTrue(90<duration<110)
            self.assertAlmostEqual(duration,score['duration_seconds'])
            pcm=array('h',audio.readframes(audio.getnframes()))
        self.assertLess(max(abs(v) for v in pcm),30000)
        self.assertGreater(max(abs(v) for v in pcm),20000)
        self.assertLess(abs(pcm[-2]-pcm[0]),1000)
        self.assertLess(abs(pcm[-1]-pcm[1]),1000)
        self.assertTrue(any(pcm[i]!=pcm[i+1] for i in range(0,len(pcm),2000)))

    def test_runtime_ogg_decodes_and_music_toggle_uses_it(self):
        pygame.display.init();pygame.display.set_mode((1,1));pygame.mixer.init()
        try:
            sound=pygame.mixer.Sound(str(ROOT/'assets/ui/title/eldenmere_theme.ogg'))
            self.assertTrue(90<sound.get_length()<110)
            game=main.Game(fullscreen=False)
            game.title.start_music()
            self.assertTrue(game.title.music_started)
            self.assertTrue(pygame.mixer.music.get_busy())
            game.title.settings=True;game.title.selected=1
            game.title.activate()
            self.assertFalse(pygame.mixer.music.get_busy())
        finally:pygame.quit()

    def test_every_written_entrance_and_release_is_on_the_same_beat_grid(self):
        score=json.loads((ROOT/'assets/ui/title/music_score.json').read_text())
        samples=score['sample_rate']*60//score['quarter_bpm']
        self.assertEqual(samples,score['beat_samples'])
        for event in score['events']:
            self.assertIsInstance(event['beat'],int)
            self.assertIn(event['duration_beats'],(1,2,3,4))
            self.assertEqual(event['start_sample'],event['beat']*samples)
            self.assertEqual(event['duration_samples'],event['duration_beats']*samples)
            self.assertGreaterEqual(event['attack_advance_samples'],0)
            self.assertLess(event['attack_advance_samples'],int(.2*score['sample_rate']))

    def test_rendered_instrument_entrances_match_click_reference(self):
        report=json.loads((ROOT/'docs/reviews/title_piano_cello/timing_audit.json').read_text())
        master=ROOT/'assets/ui/title/eldenmere_theme.wav'
        self.assertEqual(report['audio_sha256'],hashlib.sha256(master.read_bytes()).hexdigest())
        self.assertEqual({r['instrument'] for r in report['measured_instruments']},{'piano','cello','strings','bell'})
        for probe in report['measured_instruments']:
            self.assertLessEqual(abs(probe['error_ms']),report['tolerance_ms'])
            self.assertEqual(probe['expected_sample']%report['beat_samples'],0)
        for name in ('sketch.ogg','sketch_with_click.ogg'):
            self.assertTrue((ROOT/'docs/reviews/title_piano_cello'/name).is_file())


if __name__=='__main__':unittest.main()
