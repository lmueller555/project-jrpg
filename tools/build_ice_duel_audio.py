"""Build finite stereo duel effects from retained MIT foley and designed layers.

No network or music processing. The existing rescue effects and Wintermute 2
are read-only inputs. Outputs are deterministic 48 kHz stereo Vorbis files.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ice_reaper_audio import CUES

BASE = ROOT/'assets/audio/sfx/ice_reaper_rescue'
TARGET = ROOT/'assets/audio/sfx/ice_reaper_duel'
RATE = 48000
RNG = np.random.default_rng(452106)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(relative):
    raw = subprocess.check_output(['ffmpeg','-v','error','-i',str(BASE/relative),
                                   '-f','f32le','-ac','1','-ar',str(RATE),'-'])
    return np.frombuffer(raw,dtype='<f4').astype(np.float64)


def fit(value, seconds):
    result = np.zeros(round(seconds*RATE))
    result[:min(len(value),len(result))] = value[:len(result)]
    return result


def pitch(value, ratio):
    return np.interp(np.arange(0,len(value),ratio),np.arange(len(value)),value)


def band(value, low, high):
    frequency = np.fft.rfftfreq(len(value),1/RATE)
    lower = np.clip((frequency-low)/max(35,low*.5),0,1) if low else 1
    upper = np.clip((high-frequency)/max(150,high*.22),0,1)
    return np.fft.irfft(np.fft.rfft(value)*lower*upper,n=len(value))


def noise(seconds, low, high):
    value=band(RNG.normal(0,1,round(seconds*RATE)),low,high)
    return value/max(.01,np.std(value))


def at(value, start, seconds):
    result=np.zeros(round(seconds*RATE));offset=round(start*RATE)
    count=min(len(value),len(result)-offset)
    if count>0:result[offset:offset+count]+=value[:count]
    return result


def hit(seconds, gain):
    time=np.arange(round(seconds*RATE))/RATE
    body=np.sin(2*np.pi*(58*time-12*time*time))*np.exp(-time*10)
    grit=noise(seconds,90,4500)*np.exp(-time*36)
    return gain*(body*.45+grit*.25)*(1-np.exp(-time*900))


def write(name, value, *, spread=.15):
    value=np.asarray(value,dtype=np.float64)
    duration=len(value)/RATE
    left=value.copy();right=value.copy()
    # Sparse outdoor reflections retain direction and impact clarity.
    for delay,gain in ((.013,.07),(.031,.045),(.071,.025)):
        offset=round(delay*RATE)
        if offset<len(value):
            left[offset:]+=value[:-offset]*gain
            offset+=round(.002*RATE)
            right[offset:]+=value[:-offset]*gain*.9
    time=np.arange(len(value))/RATE
    pan=np.sin(time*1.4)*spread
    stereo=np.stack((left*(1-pan*.35),right*(1+pan*.35)),axis=1)
    stereo=stereo/max(.01,float(np.max(np.abs(stereo))))*.76
    ramp=min(round(.008*RATE),len(stereo)//2)
    stereo[:ramp]*=np.linspace(0,1,ramp)[:,None]
    fade=min(round(.14*RATE),len(stereo)//2)
    stereo[-fade:]*=np.linspace(1,0,fade)[:,None]
    temporary=TARGET/f'{name}.wav'
    with wave.open(str(temporary),'wb') as stream:
        stream.setnchannels(2);stream.setsampwidth(2);stream.setframerate(RATE)
        stream.writeframes(np.round(stereo*32767).astype('<i2').tobytes())
    output=TARGET/f'{name}.ogg'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(temporary),'-map_metadata','-1',
                    '-fflags','+bitexact','-flags:a','+bitexact',
                    '-c:a','libvorbis','-q:a','6',str(output)],check=True)
    temporary.unlink()
    return dict(file=output.relative_to(ROOT).as_posix(),duration=duration,
                rate=RATE,channels=2,sha256=sha(output),designed_peak=.76)


def main():
    TARGET.mkdir(parents=True,exist_ok=True)
    source_names=('flame_slash.ogg','snow_dash.ogg','prison_crack.ogg','shield_impact.ogg',
                  'source/fps_land.ogg','source/platform_land.ogg','source/platform_break.ogg')
    sources={name:read(name) for name in source_names}
    sounds={}
    duration=.5;time=np.arange(round(duration*RATE))/RATE
    envelope=np.sin(np.pi*np.minimum(1,time/.36))**2*np.exp(-time*2)
    staff=noise(duration,160,11500)*envelope*.23
    staff+=fit(pitch(sources['flame_slash.ogg'],1.35),duration)*.16
    sounds['staff_sweep']=write('staff_sweep',staff,spread=.8)

    duration=1.5;time=np.arange(round(duration*RATE))/RATE
    envelope=(1-np.exp(-time*22))*np.exp(-time*2.2)
    gust=noise(duration,80,8500)*envelope*.18
    gust+=noise(duration,25,650)*envelope*.065
    gust+=fit(pitch(sources['snow_dash.ogg'],.52),duration)*.18
    for birth in (.22,.53,.89,1.17):
        gust+=at(fit(pitch(sources['source/platform_land.ogg'],1.1),.2)*.07,birth,duration)
    sounds['wind_burst']=write('wind_burst',gust,spread=.9)

    duration=.9
    landing=fit(pitch(sources['source/fps_land.ogg'],.8),duration)*.5
    landing+=fit(pitch(sources['source/platform_land.ogg'],.75),duration)*.28+hit(duration,.22)
    sounds['caelan_lands']=write('caelan_lands',landing,spread=.3)
    shield=landing+fit(pitch(sources['shield_impact.ogg'],1.25),duration)*.12
    sounds['lucan_lands']=write('lucan_lands',shield,spread=.3)

    duration=1.05;time=np.arange(round(duration*RATE))/RATE
    frost=fit(pitch(sources['prison_crack.ogg'][::-1],.8),duration)
    frost*=np.minimum(1,time/.2)*np.exp(-np.maximum(0,time-.55)*3)
    frost+=noise(duration,1800,13500)*(1-np.exp(-time*4))*np.exp(-time*1.6)*.025
    for birth,ratio in ((.25,1.6),(.48,1.9),(.72,1.3)):
        frost+=at(pitch(sources['source/platform_break.ogg'],ratio)*.09,birth,duration)
    sounds['ice_sword_forms']=write('ice_sword_forms',frost,spread=.65)

    duration=.5;time=np.arange(round(duration*RATE))/RATE
    fire=fit(pitch(sources['flame_slash.ogg'],.8),duration)*.28
    fire+=noise(duration,120,7500)*(1-np.exp(-time*80))*np.exp(-time*6)*.14
    fire+=hit(duration,.16)
    sounds['fireball_ignite']=write('fireball_ignite',fire,spread=.6)

    duration=4.5;time=np.arange(round(duration*RATE))/RATE
    envelope=np.minimum(1,time/.35)*np.clip((duration-time)/.7,0,1)
    bed=noise(duration,100,6200)*(.075+.015*np.sin(time*2.6))*envelope
    bed+=noise(duration,30,380)*.024*envelope
    for birth in np.arange(.2,duration-.6,.43):
        grain=noise(.12,1600,10000)*np.exp(-np.arange(round(.12*RATE))/RATE*42)*.035
        bed+=at(grain,float(birth),duration)*envelope
    sounds['fire_presence']=write('fire_presence',bed,spread=.8)

    duration=.85;time=np.arange(round(duration*RATE))/RATE
    windup=noise(duration,250,11000)*np.sin(np.pi*np.minimum(1,time/.65))**2*.15
    windup+=fit(pitch(sources['prison_crack.ogg'],.8),duration)*.09
    sounds['sword_windup']=write('sword_windup',windup,spread=.6)

    duration=1.65;time=np.arange(round(duration*RATE))/RATE
    envelope=(1-np.exp(-time*40))*np.exp(-time*.8)
    charge=noise(duration,90,11500)*envelope*.2+hit(duration,.48)
    charge+=noise(duration,25,480)*envelope*.055
    for birth,ratio in ((.28,1.3),(.72,1.6),(1.14,1.9)):
        charge+=at(pitch(sources['prison_crack.ogg'],ratio)*.16,birth,duration)
    sounds['charge_launch']=write('charge_launch',charge,spread=.95)

    manifest=dict(version=1,description='Finite duel foley and designed wind, fire and ice effects',
        sources=[dict(file=(BASE/name).relative_to(ROOT).as_posix(),sha256=sha(BASE/name)) for name in source_names],
        upstream=[dict(repository='https://github.com/kenneyNL/Starter-Kit-FPS',
                       commit='185fd2326d74a5cf858cffc616f87cf9696f9cc0',license='MIT',
                       retained_license='assets/audio/sfx/ice_reaper_rescue/source/fps_LICENSE.md'),
                  dict(repository='https://github.com/kenneyNL/Starter-Kit-3D-Platformer',
                       commit='3fa8a04b1c01ab23db43123d4ce814a34c3fc7f0',license='MIT',
                       retained_license='assets/audio/sfx/ice_reaper_rescue/source/platform_LICENSE.md')],
        operation='Decode retained foley, pitch/filter, deterministic seeded noise, gain envelopes, sparse stereo reflections; no score modification.',
        sounds=sounds,cues=[cue for cue in CUES if cue['time']>=21])
    (TARGET/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(sounds=len(sounds),new_cues=len(manifest['cues']))))


if __name__=='__main__':main()
