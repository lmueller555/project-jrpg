"""Capture the first real MQ02 Bolt Shot, normal and Reduced Motion.

Uses the existing unseeded New Game input driver through MQ01 and MQ02. No
combatant, ATB, damage, camera, pose, or effect is replaced. Audio is reconstructed
from actual event-triggered cached cue buffers, not claimed SDL loopback.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import wave
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/'tests')]
import numpy as np
import pygame
from PIL import Image,ImageDraw
import test_opening_dialogue_pass as opening
from test_mill_battle_gameplay import finish_mill_battle

OUT = ROOT/'docs/reviews/mira_bolt_firing'
FPS = 100
KEYS = (0,180,240,279,280,320,370,400,430,500,580,680,799)


class Captured(Exception):pass


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest = json.loads((ROOT/'assets/combat/mira/animation.json').read_text())
    native = Image.new('RGB',(6*256,2*280),'#14232c');labels=ImageDraw.Draw(native);clock=0
    for index,record in enumerate(manifest['animations']['attack']['frames']):
        sprite=Image.open(ROOT/'assets/combat/mira'/record['file']).convert('RGBA')
        sprite=sprite.resize((256,256),Image.Resampling.NEAREST)
        x,y=index%6*256,index//6*280
        native.paste(sprite,(x,y+24),sprite)
        labels.text((x+5,y+5),f'{index+1} {clock}ms '+record.get('phase','aim'),fill='white')
        clock+=record['duration_ms']
    native.save(OUT/'native_frames.png')
    evidence = {'fps':FPS,'scope':'PR1 firing only; projectile/contact unchanged until PR2',
        'entry':'Unseeded New Game through production MQ01 and MQ02 inputs',
        'fixture_changes':['Music muted; effects volume1 for cue capture','Disposable save/settings files'],
        'audio':'Actual event cue buffers reconstructed on the action clock, not SDL loopback',
        'modes':{}}
    for reduced in (False,True):
        driver = opening.OpeningDialogueDriver();game = driver.g
        game.audio.reduced_motion = reduced
        name = 'reduced_motion' if reduced else 'normal'

        def on_step(scene):
            action = scene.model.current_action
            if action is None or action.actor != 'mira' or action.action != 'bolt_shot':return
            assert action.elapsed == 0
            assert game.combat.kind == 'mill' and scene.model.enemy_id == 'ridgeback_tusker'
            game.audio.set_effects(1.)
            start_hp = scene.model.enemy.hp
            home = tuple(scene._home_positions()['mira'])
            rows,images,cues,buffers = [],[],[],[]
            original_play = scene.action_audio.play

            def play(cue):
                original_play(cue)
                sound = scene.action_audio._sounds.get(cue)
                cues.append({'elapsed':action.elapsed,'cue':cue,
                    'raw_bytes':len(sound.get_raw()) if sound is not None else 0,
                    'decoded_peak':int(np.max(np.abs(pygame.sndarray.array(sound).astype(np.int32))))
                        if sound is not None and sound.get_raw() else 0})
                if sound is not None:
                    samples = pygame.sndarray.array(sound).astype(np.float64)*sound.get_volume()
                    buffers.append((round(action.elapsed*pygame.mixer.get_init()[0]),samples))

            # Include exact preboundary snapshots in addition to uniform100fps
            # video frames. They do not replace the clock or select a pose.
            times = sorted(set([i/FPS for i in range(101)]+[.279,.799]))
            with tempfile.TemporaryDirectory(prefix='bolt-firing-capture-') as temp, \
                    patch.object(scene.action_audio,'play',side_effect=play):
                video = Path(temp)/'silent.mp4'
                encoder = subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo',
                    '-pix_fmt','rgb24','-s','960x640','-r',str(FPS),'-i','-','-an',
                    '-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-threads','2',str(video)],stdin=subprocess.PIPE)
                try:
                    for time in times:
                        game.update(max(0,time-action.elapsed) if scene.model.current_action is action
                                    else .01,(0,0),False)
                        game.draw()
                        image = Image.frombytes('RGB',game.ui_surface.get_size(),
                            pygame.image.tobytes(game.ui_surface,'RGB')).resize((960,640),Image.Resampling.NEAREST)
                        ImageDraw.Draw(image).text((8,8),f'{name} {time:.3f}s',fill='white',stroke_width=2,stroke_fill='black')
                        if round(time*1000) in KEYS:image.save(OUT/f'{name}_{round(time*1000):03}.png')
                        if abs(round(time*FPS)-time*FPS) < 1e-8:
                            encoder.stdin.write(image.tobytes());images.append(image)
                        rows.append(dict(requested=time,elapsed=action.elapsed,resolved=action.resolved,
                            hp=scene.model.enemy.hp,pose=scene._pose('mira'),shot=scene._mira_shot(),
                            mira_floor=list(scene._positions()['mira'])))
                finally:
                    encoder.stdin.close()
                    if encoder.wait():raise RuntimeError('Capture encoding failed')
                rate,format_,channels = pygame.mixer.get_init();assert format_ == -16
                mix = np.zeros((round(1.01*rate),channels),dtype=np.float64)
                for start,samples in buffers:
                    if samples.ndim == 1:samples=samples[:,None]
                    end = min(len(mix),start+len(samples))
                    mix[start:end] += samples[:end-start]
                assert np.max(np.abs(mix)) < 32767
                with wave.open(str(Path(temp)/'cues.wav'),'wb') as audio:
                    audio.setparams((channels,2,rate,0,'NONE','not compressed'))
                    audio.writeframes(np.round(mix).astype('<i2').tobytes())
                subprocess.run(['ffmpeg','-y','-v','error','-i',str(video),'-i',str(Path(temp)/'cues.wav'),
                    '-c:v','copy','-c:a','aac','-movflags','+faststart',str(OUT/f'{name}.mp4')],check=True)
            # Native-size GIFs use one palette and changed rectangles; the
            # full-size PNG/MP4 remain the exact-color review references.
            gif_frames = [im.resize((480,320),Image.Resampling.NEAREST) for im in images[::4]]
            palette = gif_frames[0].quantize(colors=256,dither=Image.Dither.NONE)
            gif_frames = [im.quantize(palette=palette,dither=Image.Dither.NONE) for im in gif_frames]
            for slow in (False,True):
                gif_frames[0].save(OUT/f'{name}{"_slow" if slow else ""}.gif',save_all=True,
                    append_images=gif_frames[1:],duration=160 if slow else 40,loop=0,optimize=True,disposal=1)
            sheet = Image.new('RGB',(960*3,640*2))
            for index,milliseconds in enumerate((240,280,320,370,500,680)):
                sheet.paste(Image.open(OUT/f'{name}_{milliseconds:03}.png'),((index%3)*960,index//3*640))
            sheet.save(OUT/f'{name}_sheet.png')
            for milliseconds in KEYS:
                (OUT/f'{name}_{milliseconds:03}.png').unlink()
            assert [row['cue'] for row in cues].count('mira_clack') == 1
            clack=next(row for row in cues if row['cue']=='mira_clack')
            assert clack['raw_bytes']>1000 and clack['decoded_peak']>0
            assert all(tuple(row['mira_floor']) == home for row in rows if row['requested'] < .8)
            before = next(row for row in rows if row['requested'] == .279)
            release = next(row for row in rows if row['requested'] == .28)
            impact = next(row for row in rows if row['requested'] == .4)
            assert before['shot']['projectile'] is None and before['hp'] == start_hp
            assert release['shot']['projectile'] == release['shot']['origin']
            assert impact['resolved'] and impact['hp'] < start_hp and impact['shot']['projectile'] is None
            evidence['modes'][name] = dict(home=list(home),start_hp=start_hp,cues=cues,timeline=rows,
                audio_peak=float(np.max(np.abs(mix))/32768),mixer=[rate,format_,channels],frames=len(images),
                sources={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in
                    ('battle_scene.py','mira_combat_art.py','battle_action_audio.py',
                     'assets/audio/sfx/mira/bolt_clack.wav','assets/combat/mira/animation.json')})
            raise Captured()

        def battle(game,*args,**kwargs):
            return finish_mill_battle(game,read_aftermath=False,on_step=on_step)
        try:
            with patch.object(opening,'finish_mill_battle',battle):driver.run()
            raise AssertionError('No production Mira Bolt Shot observed')
        except Captured:print('Captured '+name,flush=True)
        finally:driver.close()
    (OUT/'verification.json').write_text(json.dumps(evidence,indent=2,default=str)+'\n')


if __name__ == '__main__':main()
