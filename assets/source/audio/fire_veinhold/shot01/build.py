"""Offline, deterministic 48 kHz PCM flight effects; numpy is the only dependency.

The retained wing recording is CC0. Wind is original seeded filtered noise.
Generation holds at most one six-second stereo effect and its FFT work buffers;
the runtime only decodes these finite exports and performs no synthesis.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import wave

import numpy as np


SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[4]
OUTPUT = ROOT/'assets/audio/sfx/fire_veinhold/shot01'
RATE = 48000
SEED = 741915


def filtered(value,low=160.,high=12000.):
    frequency = np.fft.rfftfreq(len(value),1/RATE)
    spectrum = np.fft.rfft(value)
    low_weight = np.minimum(1.,np.maximum(0.,(frequency-low)/(low*.8)))
    high_weight = np.minimum(1.,np.maximum(0.,(high-frequency)/(high*.3)))
    # A smooth pinkward tilt avoids brittle white-noise hiss and bass rumble.
    spectrum *= low_weight*high_weight/np.sqrt(np.maximum(frequency,150.)/1000.)
    result = np.fft.irfft(spectrum,n=len(value))
    return result/max(float(np.std(result)),.001)


def wind(seconds,rng,*,periodic=False):
    length = round(seconds*RATE)
    t = np.arange(length)/RATE
    shared = filtered(rng.normal(size=length))
    sides = []
    for index in range(2):
        independent = filtered(rng.normal(size=length),low=220.+index*30.,high=11000.)
        if periodic:
            # Integer harmonics retain matching value/derivative at each loop.
            envelope = .76+.15*np.sin(2*np.pi*t/seconds+index*.4)+.07*np.sin(6*np.pi*t/seconds)
        else:
            envelope = np.sin(np.pi*np.minimum(1.,t/seconds))**1.4
        sides.append((shared*.60+independent*.40)*envelope)
    stereo = np.stack(sides,axis=1)
    return stereo/max(float(np.max(np.abs(stereo))),.001)*.38


def read_wing():
    with wave.open(str(SOURCE/'wing_flap_source.wav'),'rb') as stream:
        assert stream.getframerate() == RATE and stream.getsampwidth() == 3
        raw = np.frombuffer(stream.readframes(stream.getnframes()),dtype=np.uint8).reshape(-1,3)
        samples = raw[:,0].astype(np.int32)|(raw[:,1].astype(np.int32)<<8)|(raw[:,2].astype(np.int32)<<16)
        samples = ((samples<<8)>>8).reshape(-1,stream.getnchannels()).mean(axis=1)/8388608.
    value = samples[round(.13*RATE):round(.43*RATE)]
    # Retain the recorded cloth transient rather than replacing it with a bird cry.
    value = filtered(value,180.,7000.)
    value /= max(float(np.max(np.abs(value))),.001)
    attack = round(.012*RATE);release = round(.045*RATE)
    value[:attack] *= np.linspace(0.,1.,attack)
    value[-release:] *= np.linspace(1.,0.,release)
    return np.stack((value,value*.96),axis=1)*.24


def encode(value):
    assert value.ndim == 2 and value.shape[1] == 2 and np.isfinite(value).all()
    pcm = np.round(np.clip(value,-1.,1.)*32767).astype('<i2')
    buffer = BytesIO()
    with wave.open(buffer,'wb') as stream:
        stream.setnchannels(2);stream.setsampwidth(2);stream.setframerate(RATE)
        stream.writeframes(pcm.tobytes())
    return buffer.getvalue(),pcm


def build(check=False):
    rng = np.random.default_rng(SEED)
    sounds = {}
    definitions = (('wind_loop',6.,True),('air_pass',1.25,False),
                   ('bank_gust',1.8,False),('climb_rush',2.,False),('crest_gust',1.55,False))
    products = {}
    for name,seconds,periodic in definitions:
        value = wind(seconds,rng,periodic=periodic)
        content,pcm = encode(value)
        products[OUTPUT/(name+'.wav')] = content
        sounds[name] = stats(content,pcm,periodic)
    content,pcm = encode(read_wing())
    products[OUTPUT/'wing_feather.wav'] = content
    sounds['wing_feather'] = stats(content,pcm,False)
    manifest = {'version':1,'sample_rate':RATE,'channels':2,'sample_width':2,
        'seed':SEED,'generator':str(Path(__file__).relative_to(ROOT)),
        'source':{'file':str((SOURCE/'wing_flap_source.wav').relative_to(ROOT)),
                  'sha256':hashlib.sha256((SOURCE/'wing_flap_source.wav').read_bytes()).hexdigest(),
                  'title':'Wing Flap 1.wav','creator':'_stubb','license':'CC0-1.0',
                  'original_url':'https://freesound.org/people/_stubb/sounds/389634/'},
        'sounds':sounds,
        'handoff':{'shot_duration':10.,'wind_loop_seconds':6.,'automatic_end_fade':False,
                   'stop_owner':'cinematic controller'},
        'wing_sync':{'period':.75,'downstroke_phase':.25,'flap_windows':[[0,2],[5,8]],
                     'first_phase_offset_seconds':.391,'second_phase_offset_seconds':.141,
                     'bank_hold_phase':3.188,'crest_hold_phase':7.188}}
    products[OUTPUT/'manifest.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
    for path,content in products.items():
        if check:
            if not path.exists() or path.read_bytes() != content:
                raise ValueError(f'Stale audio export: {path.relative_to(ROOT)}')
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
    print(f'{"Verified" if check else "Built"} six stereo flight effects; no music or vocal bird call.')


def stats(content,pcm,loop):
    value = pcm.astype(np.float64)/32767.
    return {'duration':len(pcm)/RATE,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest(),
            'peak':round(float(np.max(np.abs(value))),6),
            'rms':round(float(np.sqrt(np.mean(value**2))),6),
            'clipped_samples':int(np.sum(np.abs(value)>=1.)), 'loop':loop}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    build(check=parser.parse_args().check)
