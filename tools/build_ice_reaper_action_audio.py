"""Build the rescue scene's layered 48 kHz effects from retained MIT sources.

Offline and deterministic. Requires numpy and ffmpeg; no network access.
Recorded/game-library transients provide the tactile attacks. Filtered noise,
modal resonances and short stereo reflections add snow, ice, weight and scale.
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

TARGET = ROOT/'assets/audio/sfx/ice_reaper_rescue'
SOURCE = TARGET/'source'
RATE = 48000
RNG = np.random.default_rng(307451)


def read(name):
    data = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(SOURCE/name),
                                   '-f', 'f32le', '-ac', '1', '-ar', str(RATE), '-'])
    return np.frombuffer(data, dtype='<f4').astype(np.float64)


def fit(value, seconds):
    output = np.zeros(round(seconds*RATE))
    output[:min(len(value), len(output))] = value[:len(output)]
    return output


def pitch(value, ratio):
    return np.interp(np.arange(0, len(value), ratio), np.arange(len(value)), value)


def band(value, low, high):
    spectrum = np.fft.rfft(value)
    frequency = np.fft.rfftfreq(len(value), 1/RATE)
    lo = np.minimum(1, np.maximum(0, (frequency-low)/max(20, low*.5))) if low else 1
    hi = np.minimum(1, np.maximum(0, (high-frequency)/max(100, high*.25)))
    return np.fft.irfft(spectrum*lo*hi, n=len(value))


def noise(seconds, low=0, high=15000):
    data = band(RNG.normal(0, 1, round(seconds*RATE)), low, high)
    return data / max(.01, np.std(data))


def at(value, seconds, total):
    output = np.zeros(round(total*RATE)); i = round(seconds*RATE)
    length = min(len(value), len(output)-i)
    output[i:i+length] += value[:length]
    return output


def hit(seconds, weight=1):
    t=np.arange(round(seconds*RATE))/RATE
    body=np.sin(2*np.pi*(60*t-18*t*t))*np.exp(-8*t)
    attack=noise(seconds, 60, 7000)*np.exp(-35*t)
    return weight*(body*.22+attack*.2)*(1-np.exp(-t*1300))


def glass(seconds):
    t=np.arange(round(seconds*RATE))/RATE
    out=fit(pitch(read('platform_break.ogg'), 1.15), seconds)*.65
    # Nonharmonic short resonances, randomized grains; no pitched UI beeps.
    for _ in range(32):
        start=float(RNG.uniform(0, seconds*.7)); length=min(float(RNG.uniform(.025,.16)),seconds-start)
        x=np.arange(round(length*RATE))/RATE
        grain=noise(length, float(RNG.uniform(1200,3500)), 15000)*np.exp(-x*float(RNG.uniform(30,70)))
        out+=at(grain*.055,start,seconds)
    return out+noise(seconds,1800,10000)*np.exp(-t*4)*.025


def write(name, mono):
    mono=np.asarray(mono); duration=len(mono)/RATE
    # Early reflections and a soft outdoor tail retain impact clarity.
    left=mono.copy();right=mono.copy()
    for delay,gain in ((.019,.10),(.043,.07),(.083,.035),(.149,.02)):
        shift=round(delay*RATE)
        if shift < len(mono):
            left[shift:]+=mono[:-shift]*gain
            right[shift+int(RATE*.003):]+=mono[:len(mono)-shift-int(RATE*.003)]*gain*.9
    stereo=np.stack((left,right),axis=1)
    peak=np.max(np.abs(stereo));stereo=np.tanh(stereo/max(peak,.01)*1.15)*.86
    ramp=min(round(.006*RATE),len(stereo)//2)
    stereo[:ramp]*=np.linspace(0,1,ramp)[:,None]
    fade=min(round(.12*RATE),len(stereo)//2)
    stereo[-fade:]*=np.linspace(1,0,fade)[:,None]
    pcm=np.round(np.clip(stereo,-1,1)*32767).astype('<i2')
    temporary=TARGET/(name+'.wav')
    with wave.open(str(temporary),'wb') as stream:
        stream.setnchannels(2);stream.setsampwidth(2);stream.setframerate(RATE);stream.writeframes(pcm.tobytes())
    output=TARGET/(name+'.ogg')
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(temporary),'-map_metadata','-1',
                    '-c:a','libvorbis','-q:a','6',str(output)],check=True)
    temporary.unlink()
    return {'file':str(output.relative_to(ROOT)), 'duration':round(duration,5),
            'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'rate':RATE,'channels':2}


def main():
    TARGET.mkdir(parents=True,exist_ok=True)
    sounds={}
    t=np.arange(round(.75*RATE))/RATE
    snow=fit(pitch(read('fps_walking.ogg'),.8),.75)*.7
    snow+=noise(.75,500,9000)*np.exp(-t*5)*(1-np.exp(-t*80))*.11
    snow+=fit(pitch(read('platform_land.ogg'),.8),.75)*.25
    sounds['snow_dash']=write('snow_dash',snow)
    t=np.arange(round(.85*RATE))/RATE
    slash=noise(.85,150,14000)*(np.sin(np.pi*np.minimum(1,t/.48))**2)*np.exp(-t*2)*.24
    slash+=at(hit(.38,.35),.27,.85)
    sounds['flame_slash']=write('flame_slash',slash)
    sounds['prison_crack']=write('prison_crack',glass(.82))
    impact=glass(1.7)*.38+fit(pitch(read('fps_enemy_destroy.ogg'),.65),1.7)*.35+hit(1.7,1.2)
    t=np.arange(round(1.7*RATE))/RATE
    for frequency,gain in ((376,.1),(733,.06),(1189,.045),(2061,.025)):
        impact+=gain*np.sin(2*np.pi*frequency*t)*np.exp(-t*9)*(1-np.exp(-t*400))
    sounds['shield_impact']=write('shield_impact',impact)
    load=fit(pitch(read('fps_weapon_change.ogg'),.85),.55)
    sounds['load_shell']=write('load_shell',load*.7+hit(.55,.12))
    breech=fit(pitch(read('fps_weapon_change.ogg'),1.45),.48)*.7+at(hit(.18,.55),.1,.48)
    sounds['close_breech']=write('close_breech',breech)
    fire=fit(pitch(read('fps_blaster.ogg'),.68),1.3)*.6+hit(1.3,1.0)
    t=np.arange(round(1.3*RATE))/RATE
    fire+=noise(1.3,90,5500)*np.exp(-t*7)*.16
    sounds['launcher_fire']=write('launcher_fire',fire)
    explosion=glass(1.65)*.75+fit(pitch(read('fps_enemy_destroy.ogg'),.9),1.65)*.5+hit(1.65,.8)
    sounds['shard_explosion']=write('shard_explosion',explosion)
    # Breathy, wide, granular magic rather than a discrete electronic note.
    def magic(seconds, big=False):
        t=np.arange(round(seconds*RATE))/RATE
        env=(1-np.exp(-t*(4 if big else 6)))*np.exp(-t/(seconds*.6))
        out=noise(seconds,180,5500)*env*.065
        for index in range(25):
            f=float(RNG.uniform(130 if big else 500,3500)); phase=float(RNG.uniform(0,6.28))
            grain=np.sin(2*np.pi*f*t+np.sin(t*(.8+index*.05))*2+phase)
            grain*=np.sin(np.pi*np.minimum(1,t/(seconds*.5)))**2
            out+=grain*env*(.004+index*.00015)
        if big:out+=hit(seconds,.4)
        return out
    sounds['awakening']=write('awakening',magic(1.7))
    sounds['prison_burst']=write('prison_burst',glass(2.25)*.8+hit(2.25,1.0))
    sounds['rune_bloom']=write('rune_bloom',magic(3.45,True))
    manifest={'version':1,'description':'Layered action foley and designed ice/magic effects',
              'sources':[{'repository':'https://github.com/kenneyNL/Starter-Kit-FPS','commit':'185fd2326d74a5cf858cffc616f87cf9696f9cc0','license':'MIT'},
                         {'repository':'https://github.com/kenneyNL/Starter-Kit-3D-Platformer','commit':'3fa8a04b1c01ab23db43123d4ce814a34c3fc7f0','license':'MIT'}],
              'sounds':sounds,'cues':list(CUES)}
    (TARGET/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'effects':len(sounds),'cues':len(CUES)}))


if __name__=='__main__':main()
