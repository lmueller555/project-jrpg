"""Record the revised road approach and its actual music/SFX commands.

Earlier mill work is a fixture. The report, cinematic and Gallery use ordinary
Game input/update/draw. SDL dummy has no loopback: audio is reconstructed from
the runtime-decoded PCM and observed play/pause/gain/stop commands on a simulated
30 Hz mixer clock, rather than being presented as a hardware recording.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import wave

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]

import numpy as np
import pygame
from PIL import Image

from main import Game
from quests import MILL_QUEST, REGENT_QUEST
from test_regent_arrival import acknowledge_report, seed_mill_report
from tools.capture_battle_music_transition import MixerTrace, RATE
from tools.capture_regent_aerial import (AERIAL_PHASES, aerial_sample, contact_sheet,
    image_frame, json_value, smoke_checks, world_signature)
from tools.capture_regent_arrival_polish import key
from tools.capture_region_npcs import save_gif

FPS = 30
DEFAULT_OUTPUT = ROOT/'docs/reviews/regent_caravan_revision'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class SoundProxy:
    def __init__(self, trace, native, source):
        self.trace, self.native, self.source = trace, native, source
        raw = pygame.sndarray.array(native)
        spec = pygame.mixer.get_init()
        assert spec and spec[1] == -16, spec
        pcm = raw.astype('float32')/32768
        if pcm.ndim == 1:pcm = np.repeat(pcm[:,None], 2, axis=1)
        if spec[0] != RATE:
            count = round(len(pcm)*RATE/spec[0])
            points = np.arange(count)*spec[0]/RATE
            pcm = np.stack([np.interp(points,np.arange(len(pcm)),pcm[:,c])
                            for c in range(2)],axis=1).astype('float32')
        self.pcm = pcm
        self.pcm_sha256 = hashlib.sha256(pcm.tobytes()).hexdigest()

    def set_volume(self, value):self.native.set_volume(value)
    def get_volume(self):return self.native.get_volume()
    def get_length(self):return self.native.get_length()
    def get_raw(self):return self.native.get_raw()
    def play(self, loops=0, maxtime=0, fade_ms=0):
        channel = self.trace.find_channel()
        if channel is None:return None
        # Native Sound.play resets the selected channel gain; Channel.play
        # deliberately preserves a gain set before the call.
        channel.set_volume(1.)
        channel.play(self,loops,maxtime,fade_ms)
        return channel
    def stop(self):
        for channel in self.trace.channels.values():
            if channel.get_sound() is self:channel.stop()
    def fadeout(self, milliseconds):
        for channel in self.trace.channels.values():
            if channel.get_sound() is self:channel.fadeout(milliseconds)
    def get_num_channels(self):
        return sum(channel.get_sound() is self for channel in self.trace.channels.values())
    def __getattr__(self, name):return getattr(self.native,name)


class ChannelProxy:
    def __init__(self, trace, index):
        self.trace, self.index = trace, index
        self.sound = None
        self.position = 0
        self.paused = False
        self.gain = np.ones(2,dtype='float32')
        self.loops = 0
        self.limit = None
        self.fade = None

    def get_sound(self):
        if self.sound is not None:
            length = len(self.sound.pcm)
            end = self.limit if self.limit is not None else (length*(self.loops+1) if self.loops >= 0 else None)
            if end is not None and self.position >= end:self.sound = None
        return self.sound
    def get_busy(self):return self.get_sound() is not None
    def play(self, sound, loops=0, maxtime=0, fade_ms=0):
        assert isinstance(sound,SoundProxy)
        if self.get_sound() is not None:self.stop()
        self.sound, self.position, self.loops = sound, 0, loops
        self.paused = False
        self.limit = round(maxtime*RATE/1000) if maxtime else None
        self.fade = ('in',0,round(fade_ms*RATE/1000)) if fade_ms else None
        self.trace.event('play',self,source=sound.source,pcm_sha256=sound.pcm_sha256,
                         duration_seconds=len(sound.pcm)/RATE,loops=loops)
    def set_volume(self, left, right=None):
        requested = (float(left),float(left if right is None else right))
        # Sound and channel gain quantization follows SDL's 128 gain steps.
        gain = np.array([int(max(0,min(1,v))*128)/128 for v in requested],dtype='float32')
        if not np.array_equal(gain,self.gain):
            self.gain = gain
            self.trace.event('gain',self,gain=[float(v) for v in gain])
    def get_volume(self):return float(max(self.gain))
    def stop(self):
        if self.get_sound() is not None:self.trace.event('stop',self)
        self.sound = None
    def pause(self):
        if not self.paused:self.trace.event('pause',self)
        self.paused = True
    def unpause(self):
        if self.paused:self.trace.event('unpause',self)
        self.paused = False
    def fadeout(self,milliseconds):
        self.fade = ('out',self.position,round(milliseconds*RATE/1000))
        self.trace.event('fadeout',self,milliseconds=milliseconds)
    def render(self,count):
        out = np.zeros((count,2),dtype='float32')
        sound = self.get_sound()
        if sound is None or self.paused:return out
        indices = np.arange(count)+self.position
        length = len(sound.pcm)
        valid = np.ones(count,dtype=bool)
        if self.loops >= 0:valid &= indices < length*(self.loops+1)
        if self.limit is not None:valid &= indices < self.limit
        envelope = np.ones(count,dtype='float32')
        if self.fade:
            kind,start,duration = self.fade
            ratio = np.clip((indices-start)/max(1,duration),0,1)
            envelope = ratio if kind == 'in' else 1-ratio
            if kind == 'out':valid &= indices < start+duration
        out[valid] = (sound.pcm[indices[valid]%length]*self.gain*
                      sound.get_volume()*envelope[valid,None])
        self.position += count
        if self.fade and self.fade[0] == 'out' and self.position >= self.fade[1]+self.fade[2]:
            self.sound = None
        self.get_sound()
        return out


class EffectsTrace:
    def __init__(self):
        self.clock = 0.
        self.start = None
        self.channels = {}
        self.sounds = []
        self.events = []
        self.blocks = []
        self.bird_blocks = []
        self.gains = []
        self.patchers = []
        self.context = lambda:{}
    def install(self):
        native_sound = pygame.mixer.Sound
        def make_sound(*args,**kwargs):
            native = native_sound(*args,**kwargs)
            source = str(args[0]) if args and isinstance(args[0],(str,Path)) else 'generated-pcm'
            if source != 'generated-pcm':
                path = Path(source).resolve()
                source = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name
            else:
                caller = sys._getframe(1)
                if Path(caller.f_code.co_filename).name == 'regent_arrival.py':
                    name = caller.f_locals.get('name')
                    if name in ('hoof','wood','stream'):source = 'procedural/arrival/'+name
            sound = SoundProxy(self,native,source)
            self.sounds.append(sound)
            return sound
        handlers = {'Sound':make_sound,'Channel':self.channel,'find_channel':self.find_channel,
                    'stop':self.stop,'pause':self.pause,'unpause':self.unpause}
        for name,handler in handlers.items():
            p = patch.object(pygame.mixer,name,handler);p.start();self.patchers.append(p)
    def close(self):
        for p in reversed(self.patchers):p.stop()
    def channel(self,index):
        if index not in self.channels:self.channels[index] = ChannelProxy(self,index)
        return self.channels[index]
    def find_channel(self,force=False):
        for index in range(pygame.mixer.get_num_channels()):
            channel = self.channel(index)
            if not channel.get_busy():return channel
        return self.channel(0) if force else None
    def stop(self):
        for channel in self.channels.values():channel.stop()
    def pause(self):
        for channel in self.channels.values():channel.pause()
    def unpause(self):
        for channel in self.channels.values():channel.unpause()
    def event(self,event,channel,**values):
        if self.start is not None:
            source = channel.sound.source if channel.sound is not None else None
            self.events.append({'time':round(self.clock-self.start,6),'event':event,
                                'channel':channel.index,'source':source,
                                **values,**self.context()})
    def begin(self):self.start = self.clock
    def advance(self,seconds,record=True):
        count = round(seconds*RATE)
        total = np.zeros((count,2),dtype='float32')
        bird = total.copy()
        for channel in self.channels.values():
            sound = channel.get_sound()
            block = channel.render(count)
            total += block
            if sound is not None and Path(sound.source).stem in ('hawk_call','wing_flap'):
                bird += block
                gain = channel.gain*sound.get_volume()
                self.gains.append({'time':round(self.clock-(self.start or 0),6),
                    'cue':Path(sound.source).stem,'gain':float(max(gain)),
                    'rms':float(np.sqrt(np.mean(block**2)))})
        if self.start is not None and record:
            self.blocks.append(total);self.bird_blocks.append(bird)
        self.clock += seconds


def source_inputs():
    names = ('main.py','regent_arrival.py','regent_aerial.py','regent_aerial_audio.py',
        'gallery_session.py','cutscene_gallery.py','game_music.py',
        'assets/maps/overworld/elden_vale/region.json','tools/capture_regent_caravan_revision.py',
        'tools/capture_battle_music_transition.py','tools/capture_regent_aerial.py',
        'tools/capture_region_npcs.py','tests/test_regent_arrival.py')
    paths = [ROOT/name for name in names if (ROOT/name).is_file()]
    for folder in ('assets/story/regent_arrival','assets/story/regent_aerial',
                   'assets/audio/sfx/regent_aerial'):
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file())
    return {str(p.relative_to(ROOT)):digest(p) for p in sorted(set(paths))}


def make_game(directory):
    game = Game(fullscreen=False,start_on_title=False,window_size=(960,640),
        save_path=directory/'journey.json',settings_path=directory/'settings.json')
    game.audio.set_music(1.);game.audio.set_effects(1.)
    pygame.event.clear()
    return game


def encoder(path):
    return subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24',
        '-video_size','480x320','-framerate',str(FPS),'-i','-','-an','-c:v','libx264',
        '-preset','medium','-crf','26','-pix_fmt','yuv420p',str(path)],stdin=subprocess.PIPE)


def write_wav(path,pcm):
    assert float(np.max(np.abs(pcm))) <= 1., 'Audio clipped before export'
    with wave.open(str(path),'wb') as f:
        f.setparams((2,2,RATE,0,'NONE','not compressed'))
        f.writeframes(np.round(pcm*32767).astype('<i2').tobytes())


def capture(output,prototype=False):
    output.mkdir(parents=True,exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    inputs = source_inputs()
    music,effects = MixerTrace(),EffectsTrace()
    music.install();effects.install()
    media = []
    try:
        with tempfile.TemporaryDirectory(prefix='caravan-revision-capture-') as temporary:
            directory = Path(temporary)
            game = make_game(directory);game.overworld_world
            seed_mill_report(game);acknowledge_report(game)
            pending = (directory/'journey.json').read_bytes()
            # Discard only fixture/menu voices before the recorded cinematic.
            effects.stop()
            game.update(1/FPS,(0,0),False)
            scene = game.regent_arrival
            assert scene.active
            def context():
                snapshot = scene.aerial_snapshot() or {}
                return {'shot':scene.shot,'aerial_seconds':snapshot.get('seconds'),
                        'party_moving':snapshot.get('party_moving'),
                        'party_visible':snapshot.get('party_visible'),
                        'bird_visible':snapshot.get('bird',{}).get('visible'),
                        'bird_flapping':snapshot.get('bird',{}).get('flapping'),
                        'travel_mode':scene._audio_mode()}
            effects.context = context
            music.begin();effects.begin()
            video = encoder(output/'silent.mp4')
            frames = recorded = freezes = 0
            samples,phases,pages,handoffs = [],[],[],[]
            gif_frames,keyframes,approach,landing = [],[],[],[]
            last_page = None;due = 0.;last_handoff = False
            frozen = world_signature(game)
            try:
                for _ in range(20000):
                    if not scene.active:break
                    game.draw();shot = scene.shot;snapshot = aerial_sample(scene)
                    if not phases or phases[-1]['shot'] != shot:
                        phases.append({'shot':shot,'seconds':round(frames/FPS,4)})
                    if snapshot is not None and frames%6 == 0:
                        samples.append({'time':round(frames/FPS,4),'shot':shot,'aerial':snapshot})
                    if snapshot is not None:
                        swapped = bool(snapshot.get('ground_handoff'))
                        if swapped and not last_handoff:
                            assert snapshot['canopy']['full_occlusion']
                            handoffs.append({'time':round(frames/FPS,4),
                                'seconds':snapshot['seconds'],'coverage':snapshot['canopy']['coverage']})
                        last_handoff = swapped
                    if shot in AERIAL_PHASES:
                        fraction = scene.phase_time/scene.phase['min_seconds']
                        for target in (.15,.5,.85):
                            tag=f'{shot}_{target}'
                            if fraction>=target and not any(t==tag for t,_ in keyframes):
                                keyframes.append((tag,image_frame(game)))
                        if shot=='aerial_descent' and frames%9==0:
                            destination = landing if snapshot and snapshot.get('ground_handoff') else approach
                            destination.append((f'{shot} {scene.phase_time:.2f}s',image_frame(game)))
                    identity=(scene.phase_index,scene.dialogue_index,scene.page_index)
                    if scene.dialogue is not None and identity!=last_page:
                        last_page=identity;due=frames/FPS+max(1.8,len(' '.join(scene.caption_lines).split())*.18)
                        pages.append({'shot':shot,'speaker':scene.dialogue['speaker']})
                    recording = (shot in ('mill_close',*AERIAL_PHASES,'gate_approach')
                                 or shot=='gate_greeting' and scene.phase_time<2.2)
                    if recording:
                        native=image_frame(game);video.stdin.write(native.tobytes())
                        if recorded%6==0:gif_frames.append(native.resize((192,128),Image.Resampling.NEAREST))
                        recorded+=1
                    if scene.dialogue is not None and frames/FPS>=due:key(game,pygame.K_SPACE)
                    music.advance(1/FPS)
                    effects.advance(1/FPS,record=recording)
                    before=world_signature(game)
                    game.update(1/FPS,(0,0),False)
                    if scene.active:
                        assert world_signature(game)==before==frozen,'World advanced behind cinematic'
                        freezes+=1
                    frames+=1
                else:raise AssertionError('Arrival did not complete')
            finally:
                video.stdin.close();assert video.wait()==0
            assert scene.state=='seen' and scene.finished_reason=='finished'
            assert game.quests.status(MILL_QUEST)=='completed'
            assert game.quests.status(REGENT_QUEST)=='available'
            completed=(directory/'journey.json').read_bytes()
            # Music trace follows the whole scene; select the recorded prefix.
            music_pcm=np.concatenate(music.blocks)[:recorded*(RATE//FPS)]
            effects_pcm=np.concatenate(effects.blocks)
            bird_pcm=np.concatenate(effects.bird_blocks)
            assert len(music_pcm)==len(effects_pcm)==recorded*(RATE//FPS)
            mix=music_pcm+effects_pcm
            peak=float(np.max(np.abs(mix)))
            assert peak<1.,('Mixed runtime commands clip',peak)
            write_wav(output/'soundtrack.wav',mix)
            subprocess.run(['ffmpeg','-y','-v','error','-i',str(output/'silent.mp4'),
                '-i',str(output/'soundtrack.wav'),'-c:v','copy','-c:a','aac','-b:a','128k',
                '-movflags','+faststart','-shortest',str(output/'caravan_revision.mp4')],check=True)
            (output/'silent.mp4').unlink();(output/'soundtrack.wav').unlink()
            plays=[event for event in effects.events if event['event']=='play']
            bird_plays=[event for event in plays if Path(event['source']).stem in ('hawk_call','wing_flap')]
            if not prototype:
                assert any(Path(e['source']).stem=='hawk_call' for e in bird_plays),'No hawk call played'
                assert any(Path(e['source']).stem=='wing_flap' for e in bird_plays),'No wing beats played'
                assert all(e['bird_visible'] for e in bird_plays),'Bird sound after bird left view'
                assert all(e['bird_flapping'] for e in bird_plays
                           if Path(e['source']).stem=='wing_flap'),'Wing sound during glide/bank'
                travel = [e for e in plays if e['source'] in
                          ('procedural/arrival/hoof','procedural/arrival/wood')]
                assert travel and all(e['travel_mode']=='travel' for e in travel)
                assert all(e['party_visible'] and e['party_moving']
                           for e in travel if e['shot'] in AERIAL_PHASES)
                gains={cue:max(g['gain'] for g in effects.gains if g['cue']==cue)
                       for cue in ('hawk_call','wing_flap')}
                assert gains['wing_flap']<gains['hawk_call']
            else:gains={}
            if bird_plays:
                first=min(e['time'] for e in bird_plays if Path(e['source']).stem=='hawk_call') if any(
                    Path(e['source']).stem=='hawk_call' for e in bird_plays) else bird_plays[0]['time']
                lo=max(0,round((first-1.)*RATE));hi=min(len(bird_pcm),lo+10*RATE)
                write_wav(output/'bird_audition.wav',bird_pcm[lo:hi]);media.append('bird_audition.wav')
            gif=save_gif(output/'caravan_revision.gif',gif_frames,fps=5)
            contact_sheet(output/'approach_overview.jpg',keyframes)
            contact_sheet(output/'road_approach.jpg',approach)
            contact_sheet(output/'moving_ground_push.jpg',landing)
            game.music.stop();game.opening_audio.reset();game.regional_audio.reset()
            # Restore the actual mixer before independent ordinary smoke checks.
            effects.close();music.close()
            smoke=smoke_checks(directory,pending,completed,output) if not prototype else {}
            if not prototype:assert inputs==source_inputs(),'Inputs changed during final capture'
            media+=['caravan_revision.mp4','caravan_revision.gif','approach_overview.jpg',
                    'road_approach.jpg','moving_ground_push.jpg']
            if not prototype:media.append('reduced_motion.png')
            audio={'method':'Reconstructed from runtime-decoded native PCM and observed production Sound/Channel/music play, pause, gain and stop commands; no hardware loopback.',
                'settings':{'music_volume':1.,'effects_volume':1.},
                'rate':RATE,'mixed_peak':peak,'gains':gains,'events':effects.events,
                'music_initial':music.initial,'music_events':music.events,
                'pcm_sources':{sound.source:{'sha256':sound.pcm_sha256,'frames':len(sound.pcm)}
                               for sound in effects.sounds},
                'music_sources':{str(Path(p).relative_to(ROOT)):digest(p) for p in music.samples}}
            (output/'audio_events.json').write_text(json.dumps(json_value(audio),indent=2)+'\n')
            media.append('audio_events.json')
            report={'actual_renderer':True,'capture_stage':'prototype' if prototype else 'final',
                'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
                'fixture':'Earlier mill work only; ordinary MQ02 report, input/update/draw; no cinematic clocks/actors/phase assigned.',
                'frames':frames,'video_frames':recorded,'fps':FPS,'freeze_checks':freezes,
                'phases':phases,'dialogue_pages':pages,'sampled_aerial_trace':samples,
                'canopy_handoffs':handoffs,'gif_validation':gif,'smoke_checks':smoke,
                'audio':{'evidence':'audio_events.json','bird_cues':len(bird_plays),'gains':gains,'mixed_peak':peak},
                'render_input_sha256':inputs,'captures':{name:digest(output/name) for name in sorted(media)}}
            (output/'capture_report.json').write_text(json.dumps(json_value(report),indent=2)+'\n')
            (output/'README.md').write_text('''# Caravan road approach and bird audio

[Watch with runtime music and sound effects](caravan_revision.mp4) · [Animated preview](caravan_revision.gif)

This production Game recording follows the ordinary MQ02 report through the aerial approach, later foliage pass, moving ground-camera push and guard conversation. Earlier mill work is a fixture; no cinematic clocks, actor stations or phases are assigned during playback.

![Approach overview](approach_overview.jpg)

[Road approach](road_approach.jpg) · [Movement during ground push](moving_ground_push.jpg) · [Bird sound audition](bird_audition.wav)

The MP4 soundtrack is reconstructed from the exact runtime-decoded PCM and observed production music/Sound/Channel play, pause, volume and stop commands. SDL dummy has no hardware loopback; this is explicitly a command/PCM reconstruction. The bird audition contains only the observed hawk/wing voices, without music or travel effects. [Audio events and source hashes](audio_events.json) document the gains and schedule.

The [capture report](capture_report.json) records the actual camera/actor samples, full leaf coverage at the background handoff, GIF pixel/timing validation, source/media fingerprints and pause, focus, reload, skip, Reduced Motion and isolated Gallery checks.

Replay from **Title → Gallery → Aldric’s Relief Caravan**.

Reproduce with `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tools/capture_regent_caravan_revision.py`.
''')
            print(json.dumps({'frames':frames,'recorded_frames':recorded,'freeze_checks':freezes,
                'bird_cues':len(bird_plays),'gains':gains,'inputs':len(inputs),'media':len(media)},indent=2))
    finally:
        effects.close();music.close();pygame.quit()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--prototype',action='store_true')
    args=parser.parse_args();capture(args.output.resolve(),args.prototype)


if __name__=='__main__':main()
