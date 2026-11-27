"""Reproduce Veinhold machinery, warning, rush, ice and running Foley.

Original deterministic synthesis: no downloaded samples or external plugins.
The two warning loops share their exact two-second phase so perspective changes
crossfade without retriggering the siren. Run with --check to compare exports.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import wave

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT/'assets/story/fire_veinhold_opening/continuation/audio'
SOURCE = ROOT/'assets/source/cinematics/fire_veinhold/continuation/audio'
RATE = 48000
SEED = 824613
STEP_DURATION = .22


def _band_noise(count, rng, low, high):
    """Periodic, softly bandlimited air; no abrupt sample-window boundaries."""
    spectrum = np.fft.rfft(rng.standard_normal(count))
    frequency = np.fft.rfftfreq(count, 1/RATE)
    spectrum *= (1-np.exp(-(frequency/max(1, low))**4))*np.exp(-(frequency/high)**4)
    value = np.fft.irfft(spectrum, n=count)
    return value/max(1e-9, np.std(value))


def _normalise(stereo, peak):
    return stereo*(peak/max(1e-9, np.max(np.abs(stereo))))


def _encode(value):
    data = np.rint(np.clip(value, -.999, .999)*32767).astype('<i2')
    stream = BytesIO()
    with wave.open(stream, 'wb') as writer:
        writer.setnchannels(2);writer.setsampwidth(2);writer.setframerate(RATE)
        writer.writeframes(data.tobytes())
    return stream.getvalue()


def sounds():
    rng = np.random.default_rng(SEED)
    t = np.arange(2*RATE)/RATE
    # A motor-driven rotating horn, not a gated electronic beep. Integer mean
    # cycles over the two-second interval make every harmonic loop seamlessly.
    phase = 2*np.pi*560*t-340*np.sin(np.pi*t)
    horn = (np.sin(phase)+.31*np.sin(2*phase+.12)
            +.11*np.sin(3*phase+.45)+.035*np.sin(5*phase))
    rotary = .76+.17*np.cos(np.pi*t-.25)+.07*np.sin(2*np.pi*27*t)
    motor = .11*np.sin(2*np.pi*95*t)+.055*np.sin(2*np.pi*168*t)
    air = _band_noise(len(t),rng,170,2400)
    body = horn*rotary+motor+.065*air
    opposite_air = _band_noise(len(t),rng,170,2000)
    near = _normalise(np.column_stack((body+.018*opposite_air,
                                      body-.018*opposite_air)), .81)
    # Same source and timing, heard beyond the facility walls after the rush.
    spectrum = np.fft.rfft(near, axis=0)
    frequency = np.fft.rfftfreq(len(t),1/RATE)
    spectrum *= (1/(1+(frequency/1050)**4))[:,None]
    distant = np.fft.irfft(spectrum,n=len(t),axis=0)
    distant += .14*np.roll(distant,round(.115*RATE),axis=0)
    distant = _normalise(distant, .73)

    t = np.arange(RATE)/RATE
    envelope = np.sin(np.pi*t)**1.35
    low = _band_noise(len(t),rng,55,1350)
    high = _band_noise(len(t),rng,1300,6800)
    # Wind peaks during mid-flight; short metal resonances imply passing spans.
    rush = envelope*(.58*low+.22*high)
    for at, tone in ((.24,360),(.43,425),(.61,510),(.77,590)):
        age = np.maximum(0,t-at)
        rush += (t>=at)*.075*np.exp(-age*37)*np.sin(2*np.pi*tone*age)
    rush = _normalise(np.column_stack((rush, .91*rush+.09*np.roll(rush,111))), .73)
    rush[:240] *= np.linspace(0,1,240)[:,None]
    rush[-720:] *= np.linspace(1,0,720)[:,None]

    t = np.arange(round(1.4*RATE))/RATE
    air = _band_noise(len(t),rng,800,6600)
    creak = np.zeros(len(t))
    for at,tone,gain in ((.10,1700,.23),(.31,2130,.16),(.72,1250,.10)):
        age = np.maximum(0,t-at)
        creak += (t>=at)*gain*np.exp(-age*10)*(
            np.sin(2*np.pi*(tone*age-190*age*age))+.18*air)
    creak *= np.minimum(1,t/.04)*np.minimum(1,(1.4-t)/.15)
    ice = _normalise(np.column_stack((creak,.88*creak+.12*np.roll(creak,89))),.48)
    # A separate seed leaves approved warning/rush exports unchanged. This is
    # steady turbine air and steel resonance, with no alarm-like pulse or beep.
    machinery_rng = np.random.default_rng(SEED+1)
    t = np.arange(2*RATE)/RATE
    low = _band_noise(len(t),machinery_rng,18,420)
    high = _band_noise(len(t),machinery_rng,450,1650)
    turbine = (.53*low+.075*high+.24*np.sin(2*np.pi*44*t)
               +.11*np.sin(2*np.pi*89*t+.25)+.045*np.sin(2*np.pi*178*t))
    turbine *= .94+.06*np.cos(np.pi*t)
    machinery = _normalise(np.column_stack((turbine,
        .92*turbine+.08*np.roll(turbine,109))),.64)
    result = {'industrial_siren.wav':near,'distant_siren.wav':distant,
              'bridge_rush.wav':rush,'ice_settle.wav':ice,'machinery_bed.wav':machinery}
    # Independent seeds preserve all five existing exports. Each contact has
    # one compact boot/deck impulse plus the softer equipment response after
    # impact; there is no running rhythm baked into these single-step sources.
    t = np.arange(round(STEP_DURATION*RATE))/RATE
    for actor_index,(actor,mass,metal,cloth) in enumerate((
            ('lucan',1.0,1.0,.12),('iselin',.60,.30,.45),
            ('crown_soldier',.78,.62,.20))):
        for side,variation in (('near',0),('far',1)):
            step_rng = np.random.default_rng(SEED+20+actor_index*2+variation)
            noise = _band_noise(len(t),step_rng,110,4200)
            soft = _band_noise(len(t),step_rng,180,1500)
            attack = np.minimum(1,t/.0017)
            pitch = (67+actor_index*12)*(1+.035*variation)
            boot = mass*(.54*np.exp(-t*40)*np.sin(2*np.pi*pitch*t)
                         +.24*np.exp(-t*94)*noise)*attack
            # Short, inharmonic deck resonances avoid a tuned electronic beep.
            deck = sum(weight*np.sin(2*np.pi*frequency*t)*np.exp(-t*decay)
                       for frequency,weight,decay in ((174,.18,35),(389,.10,49),(913,.045,62)))
            age = np.maximum(0,t-.032)
            gear = (t>=.032)*metal*.065*np.exp(-age*39)*(
                np.sin(2*np.pi*(1380+variation*73)*age)+.5*noise)
            cloth_age = np.maximum(0,t-.018)
            rustle = (t>=.018)*cloth*.065*soft*np.exp(-cloth_age*22)
            mono = boot+mass*deck*attack+gear+rustle
            mono *= np.minimum(1,(STEP_DURATION-t)/.028)
            stereo = np.column_stack((mono,.96*mono+.04*np.roll(mono,31)))
            result[f'{actor}_step_{side}.wav'] = _normalise(stereo,.68)
    return result


def products():
    result = {}
    records = {}
    for name,value in sounds().items():
        raw = _encode(value)
        result[TARGET/name] = raw
        records[name] = {'duration':len(value)/RATE,'sha256':sha256(raw).hexdigest(),
                         'peak':round(float(np.max(np.abs(value))),6),
                         'rms':round(float(np.sqrt(np.mean(value*value))),6),
                         'loop':name.endswith('siren.wav') or name=='machinery_bed.wav',
                         'clipped_samples':0}
    recipe = {'version':1,'generator':'tools/build_prologue_alert_audio.py',
              'seed':SEED,'sample_rate':RATE,'channels':2,'sample_width':2,
              'source':'Original deterministic synthesis; no third-party samples.',
              'sounds':records,
              'timeline':{'machinery_start':25,'alarm_start':30,'alarm_lead_seconds':4,'rush_start':34,
                          'bridge_arrival':35,'running_start':39,'sequence_end':42,'siren_period':2},
              'running_foley':{'duration':STEP_DURATION,
                  'contact_source':'assets/story/fire_veinhold_opening/shot06/scene.json and referenced character animation contacts',
                  'scheduling':'One source per actor and near/far contact; no rhythm or guessed footstep loop is baked into the sources.'}}
    result[TARGET/'manifest.json'] = (json.dumps(recipe,indent=2)+'\n').encode()
    result[SOURCE/'recipe.json'] = (json.dumps({key:value for key,value in recipe.items()
        if key != 'sounds'},indent=2)+'\n').encode()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    mismatches = []
    for path,raw in products().items():
        if args.check:
            if not path.exists() or path.read_bytes() != raw:mismatches.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    if mismatches:raise SystemExit('Outdated prologue alert audio: '+', '.join(mismatches))
    print('Prologue alert audio '+('reproduces exactly' if args.check else 'exported'))


if __name__ == '__main__':main()
