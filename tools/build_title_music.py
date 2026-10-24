"""New sampled piano/cello title score, quantized to one 72-BPM quarter grid.

Build dependencies: NumPy, libfluidsynth, FFmpeg, GeneralUser GS 2.0.3.
The game only plays the exported Ogg and does not require these dependencies.
"""
import argparse
import ctypes as c
import ctypes.util
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import wave
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
RATE=44100
TEMPO=72
BEAT_FRAMES=RATE*60//TEMPO # exactly 36,750 samples per quarter note
BARS=28
COUNT=BARS*4*BEAT_FRAMES
SOUNDFONT_SHA='9575028c7a1f589f5770fccc8cff2734566af40cd26ed836944e9a5152688cfe'
PROGRAMS={'piano':0,'cello':42,'strings':48,'bell':14}
CHANNELS={name:index for index,name in enumerate(PROGRAMS)}
G=(43,50,55,59);DF=(42,50,57);EM=(40,47,55,59)
CMAJ=(48,55,59);CMIN=(48,51,55,57);GD=(38,50,55,59);DSUS=(50,57,60)
CHORDS=(G,DF,EM,DSUS,CMAJ,CMIN,GD,DSUS)
PIANO=(
 ((0,1,62),(1,2,67),(3,1,69)),
 ((0,2,71),(2,1,69),(3,1,67)),
 ((0,2,66),(2,1,64),(3,1,62)),
 ((0,2,69),(2,2,67)),
 ((0,1,64),(1,1,67),(2,2,71)),
 ((0,2,69),(2,1,67),(3,1,63)),
 ((0,2,67),(2,1,66),(3,1,64)),
 ((0,3,62),),
)
CELLO=(
 ((0,2,55),(2,1,57),(3,1,59)),
 ((0,2,62),(2,2,59)),
 ((0,2,64),(2,1,62),(3,1,59)),
 ((0,3,57),),
 ((0,2,55),(2,2,60)),
 ((0,2,63),(2,1,62),(3,1,60)),
 ((0,2,59),(2,1,57),(3,1,55)),
 ((0,3,54),),
)


class SampleRenderer:
    def __init__(self,soundfont):
        name=ctypes.util.find_library('fluidsynth')
        if not name:raise RuntimeError('libfluidsynth is required to render the source score')
        self.lib=c.CDLL(name)
        def bind(name,args,result):
            f=getattr(self.lib,name);f.argtypes=args;f.restype=result;return f
        P=c.c_void_p;I=c.c_int;S=c.c_char_p
        self.new_settings=bind('new_fluid_settings',[],P)
        self.num=bind('fluid_settings_setnum',[P,S,c.c_double],I)
        self.integer=bind('fluid_settings_setint',[P,S,I],I)
        self.new_synth=bind('new_fluid_synth',[P],P)
        self.load=bind('fluid_synth_sfload',[P,S,I],I)
        self.program=bind('fluid_synth_program_select',[P,I,I,I,I],I)
        self.on=bind('fluid_synth_noteon',[P,I,I,I],I)
        self.off=bind('fluid_synth_noteoff',[P,I,I],I)
        self.silence=bind('fluid_synth_all_sounds_off',[P,I],I)
        self.cc=bind('fluid_synth_cc',[P,I,I,I],I)
        self.write=bind('fluid_synth_write_float',[P,I,P,I,I,P,I,I],I)
        self.delete=bind('delete_fluid_synth',[P],None)
        self.delete_settings=bind('delete_fluid_settings',[P],None)
        self.settings=self.new_settings()
        self.num(self.settings,b'synth.sample-rate',RATE)
        self.num(self.settings,b'synth.gain',.6)
        self.integer(self.settings,b'synth.reverb.active',0)
        self.integer(self.settings,b'synth.chorus.active',0)
        self.integer(self.settings,b'synth.min-note-length',0)
        self.synth=self.new_synth(self.settings)
        sf=self.load(self.synth,str(soundfont).encode(),0)
        if sf<0:raise RuntimeError('Could not load the licensed SoundFont')
        for name,preset in PROGRAMS.items():
            channel=CHANNELS[name]
            self.program(self.synth,channel,sf,0,preset)
            self.cc(self.synth,channel,10,{'piano':52,'cello':76,'strings':64,'bell':40}[name])
            self.cc(self.synth,channel,7,{'piano':100,'cello':90,'strings':48,'bell':35}[name])
            self.cc(self.synth,channel,74,60 if name=='piano' else 80)

    def render(self,count):
        left=np.empty(count,'float32');right=np.empty(count,'float32')
        self.write(self.synth,count,left.ctypes.data,0,1,right.ctypes.data,0,1)
        return np.stack((left,right),axis=1)

    def clear(self):
        for channel in CHANNELS.values():self.silence(self.synth,channel)
        # FluidSynth retains a short output block after a voice is stopped.
        self.render(256)

    def close(self):
        self.delete(self.synth);self.delete_settings(self.settings)

    def attack_frames(self,name,pitch,velocity):
        self.clear();channel=CHANNELS[name]
        self.on(self.synth,channel,pitch,velocity)
        audio=self.render(RATE//2)
        energy=np.mean(audio.astype('float64')**2,axis=1)
        window=220 # 5 ms RMS window, consistently used for calibration/checks
        rms=np.sqrt(np.convolve(energy,np.ones(window)/window,mode='full')[:len(energy)])
        peak=float(np.max(rms))
        if peak<1e-7:raise RuntimeError(f'Inaudible sample: {name} {pitch}')
        onset=int(np.argmax(rms>=peak*.12))
        self.clear()
        return onset

    def verify_alignment(self,calibration):
        results=[]
        for name,pitch,velocity in (('piano',67,65),('cello',55,64),('strings',55,44),('bell',67,31)):
            self.clear()
            key=(name,pitch,velocity)
            advance=calibration.get(key)
            if advance is None:advance=self.attack_frames(*key)
            expected=BEAT_FRAMES*2
            prefix=self.render(expected-advance)
            self.on(self.synth,CHANNELS[name],pitch,velocity)
            probe=np.concatenate((prefix,self.render(RATE//2)))
            energy=np.mean(probe.astype('float64')**2,axis=1)
            rms=np.sqrt(np.convolve(energy,np.ones(220)/220,mode='full')[:len(energy)])
            actual=int(np.argmax(rms>=np.max(rms)*.12))
            error=actual-expected
            results.append({'instrument':name,'midi':pitch,'expected_sample':expected,
                            'audible_onset_sample':actual,'error_samples':error,
                            'error_ms':error/RATE*1000,'attack_advance_samples':advance})
            if abs(error)>round(RATE*.004):raise AssertionError(f'{name}: audible onset error {error/RATE*1000:.2f}ms')
        self.clear()
        return results


def compose():
    events=[]
    def add(bar,beat,length,pitch,instrument,velocity,role):
        start=bar*4+beat
        assert isinstance(start,int) and isinstance(length,int)
        events.append({'beat':start,'duration_beats':length,'midi':pitch,
                       'instrument':instrument,'velocity':velocity,'role':role,
                       'start_sample':start*BEAT_FRAMES,'duration_samples':length*BEAT_FRAMES})
    for bar in range(BARS):
        local=bar%8
        chord=CHORDS[local] if bar<24 else (G,CMIN,GD,DSUS)[bar-24]
        quiet=bar>=24
        accompaniment=37 if quiet else (40 if bar<8 else 43)
        # Whole-note bass and half-note block chords, all on beats one/three.
        add(bar,0,4,chord[0]-12,'piano',accompaniment+3,'bass')
        for beat in (0,2):
            for pitch in chord[1:]:add(bar,beat,2,pitch,'piano',accompaniment,'harmony')
        if bar<8 or 16<=bar<24:
            for beat,length,pitch in PIANO[local]:
                add(bar,beat,length,pitch,'piano',65 if bar<8 else 69,'melody')
        elif 8<=bar<16:
            for beat,length,pitch in CELLO[local]:add(bar,beat,length,pitch,'cello',64,'melody')
        else:
            phrase=(((0,2,67),(2,2,69)),((0,2,67),(2,2,63)),
                    ((0,2,67),(2,2,64)),((0,2,66),(2,1,62)))[bar-24]
            for beat,length,pitch in phrase:add(bar,beat,length,pitch,'piano',57,'melody')
        if 16<=bar<24:
            # Cello supplies a complementary sustained answer beneath the piano.
            for beat,length,pitch in CELLO[local][:2]:
                add(bar,beat,length,pitch,'cello',58,'answer')
            for pitch in chord[1:]:add(bar,0,4,pitch,'strings',44,'support')
        if bar in (0,18,24):add(bar,0,4,67 if bar!=18 else 74,'bell',31,'accent')
    return events


def render(events,soundfont):
    engine=SampleRenderer(soundfont)
    try:
        calibration={}
        for e in events:
            key=(e['instrument'],e['midi'],e['velocity'])
            if key not in calibration:calibration[key]=engine.attack_frames(*key)
            e['attack_advance_samples']=calibration[key]
        audit=engine.verify_alignment(calibration)
        engine.clear()
        schedule=[]
        for e in events:
            channel=CHANNELS[e['instrument']]
            start=(e['start_sample']-e['attack_advance_samples'])%COUNT
            end=(e['start_sample']+e['duration_samples']-e['attack_advance_samples'])%COUNT
            schedule.extend(((start,1,channel,e['midi'],e['velocity']),
                             (end,0,channel,e['midi'],0)))
        schedule.sort()
        # Warm up one complete cycle so the exported seam includes release tails.
        output=None
        for cycle in range(2):
            audio=np.zeros((COUNT,2),'float32');cursor=0
            for sample,on,channel,pitch,velocity in schedule:
                if sample>cursor:audio[cursor:sample]=engine.render(sample-cursor);cursor=sample
                if on:engine.on(engine.synth,channel,pitch,velocity)
                else:engine.off(engine.synth,channel,pitch)
            if cursor<COUNT:audio[cursor:]=engine.render(COUNT-cursor)
            output=audio
        # Short diffuse stereo room; no separate rhythmic delay echoes.
        rng=np.random.default_rng(72)
        for channel in (0,1):
            t=np.arange(round(.7*RATE))/RATE
            impulse=rng.normal(0,1,len(t))*np.exp(-t*8)
            impulse=np.convolve(impulse,np.ones(21)/21,mode='same')
            impulse[:round(.012*RATE)]=0
            impulse/=np.linalg.norm(impulse)
            wet=np.fft.irfft(np.fft.rfft(output[:,channel])*np.fft.rfft(impulse,n=COUNT),n=COUNT)
            audio[:,channel]=output[:,channel]+.12*wet
        audio-=np.mean(audio,axis=0)
        audio*=.68/float(np.max(np.abs(audio)))
        # Remove the sample discontinuity at the loop splice without moving
        # notes or inserting silence; only the final 10 ms receive correction.
        seam=audio[0]-audio[-1]
        amount=RATE//100
        audio[-amount:]+=(np.linspace(0,1,amount)**3)[:,None]*seam
        return audio,calibration,audit
    finally:engine.close()


def write_wav(path,audio):
    with wave.open(str(path),'wb') as output:
        output.setparams((2,2,RATE,0,'NONE','not compressed'))
        output.writeframes(np.round(np.clip(audio,-1,1)*32767).astype('<i2').tobytes())


def ogg(source,target):
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(source),'-c:a','libvorbis','-q:a','5',str(target)],check=True)


def build(soundfont):
    if hashlib.sha256(soundfont.read_bytes()).hexdigest()!=SOUNDFONT_SHA:
        raise ValueError('Use the documented GeneralUser GS 2.0.3 SoundFont for reproducible rendering')
    events=compose();audio,calibration,audit=render(events,soundfont)
    folder=ROOT/'assets/ui/title';review=ROOT/'docs/reviews/title_piano_cello'
    review.mkdir(parents=True,exist_ok=True)
    write_wav(folder/'eldenmere_theme.wav',audio);ogg(folder/'eldenmere_theme.wav',folder/'eldenmere_theme.ogg')
    excerpt=audio[:48*BEAT_FRAMES].copy() # 12 bars / 40 seconds, includes cello answer
    excerpt[-RATE//4:]*=np.linspace(1,0,RATE//4)[:,None]
    write_wav(review/'sketch.wav',excerpt);ogg(review/'sketch.wav',review/'sketch.ogg')
    (review/'sketch.wav').unlink()
    reference=excerpt.copy()
    for beat in range(48):
        t=np.arange(round(.035*RATE))/RATE
        click=np.sin(math.tau*(1500 if beat%4==0 else 1050)*t)*np.exp(-t*160)
        start=beat*BEAT_FRAMES
        reference[start:start+len(click)]+=click[:,None]*(.11 if beat%4==0 else .075)
    write_wav(review/'sketch_with_click.wav',reference)
    ogg(review/'sketch_with_click.wav',review/'sketch_with_click.ogg')
    (review/'sketch_with_click.wav').unlink()
    (review/'timing_audit.json').write_text(json.dumps({
        'method':'Causal 5 ms RMS window at 12% of each isolated note peak',
        'audio_sha256':hashlib.sha256((folder/'eldenmere_theme.wav').read_bytes()).hexdigest(),
        'tempo_bpm':TEMPO,'beat_samples':BEAT_FRAMES,'tolerance_ms':4,
        'all_score_starts_and_durations_are_integer_beats':True,'measured_instruments':audit},indent=2)+'\n')
    score={'title':'Eldenmere — A Place to Return To','status':'replacement_for_discarded_score',
           'meter':'4/4','quarter_bpm':TEMPO,'tonal_center':'G major, E-minor shading and borrowed C minor',
           'duration_seconds':COUNT/RATE,'sample_rate':RATE,'channels':2,'beat_samples':BEAT_FRAMES,
           'motif_midi':[62,67,69,71,67],'instruments':list(PROGRAMS),'programs':PROGRAMS,
           'timing':'Integer quarter-note beats only; no timing jitter or syncopated note starts',
           'rendering':'Sampled GeneralUser GS 2.0.3 via FluidSynth; per-note attack compensation',
           'soundfont_sha256':SOUNDFONT_SHA,'loop':'One-cycle preroll and circular room tail',
           'sections':[{'name':name,'start_beat':bar*4,'start_seconds':bar*4*60/TEMPO}
                       for name,bar in (('Piano',0),('Cello answer',8),('Together',16),('Quiet return',24))],
           'attack_calibration':[{'instrument':key[0],'midi':key[1],'velocity':key[2],
                                  'advance_samples':value,'advance_ms':value/RATE*1000}
                                 for key,value in calibration.items()], 'events':events}
    (folder/'music_score.json').write_text(json.dumps(score,indent=2)+'\n')
    print(f'Replaced title score: {COUNT/RATE:.2f}s, 4/4, {TEMPO} BPM; {len(events)} beat-locked sampled notes.')
    print('Clean and click-reference excerpts: docs/reviews/title_piano_cello/')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--soundfont',type=Path,required=True,help='GeneralUser GS 2.0.3 .sf2 file')
    build(parser.parse_args().soundfont)
