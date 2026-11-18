"""Rebuild Mira's dry bolt-contact cue from original synthesis, no inputs."""
from array import array
from math import cos, exp, pi
from pathlib import Path
from random import Random
from sys import byteorder
import wave

RATE = 44100
DURATION = .096


def build(destination=Path(__file__).with_name('bolt_impact.wav')):
    rng = Random(841)
    smoothed = grain = 0.
    signal = []
    for index in range(round(RATE*DURATION)):
        t = index/RATE
        # Short, damped low resonance, with a little upper-mid collision grain.
        # No reverb, delayed layers or sustained steel ring.
        body = (.78*cos(2*pi*(153*t+1.3*(1-exp(-43*t))))
                + .26*cos(2*pi*292*t)) * exp(-68*t)
        smoothed += .04*(rng.uniform(-1, 1)-smoothed)
        grain += .20*(smoothed-grain)
        contact = 2.5*(smoothed-grain)*exp(-205*t)
        attack = min(1., t/.0015)
        tail = min(1., (DURATION-t)/.011)
        signal.append((body+contact)*attack*tail)
    gain = .69*32767/max(map(abs, signal))
    pcm = array('h', (round(value*gain) for value in signal))
    if byteorder != 'little':pcm.byteswap()
    with wave.open(str(destination), 'wb') as wav:
        wav.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        wav.writeframes(pcm.tobytes())


if __name__ == '__main__':
    build()
