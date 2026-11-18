"""Original quiet material sounds for the hand-operated well.

Deterministic signed-16-bit PCM, generated only when its mixer format is needed.
There are no recordings, asset-tool dependencies or changes to mixer settings.
"""
from array import array
import math
import random


DURATIONS = {'well_winding': 1.6, 'well_fill': 1.6, 'well_pour': .6,
             'well_hook': .22, 'well_splash': .45, 'well_drip': .5}
LOOPS = frozenset(('well_winding', 'well_fill'))


def samples(name, rate, channels):
    """Return soft wood/rope, iron contact and small-water material cues."""
    duration = DURATIONS[name]
    count = round(rate*duration)
    fade = min(count, round(rate*.06)) if name in LOOPS else 0
    rng = random.Random(41501+tuple(DURATIONS).index(name))
    values = []
    low = 0.
    for i in range(count+fade):
        t = i/rate
        white = rng.uniform(-1, 1)
        low += .12*(white-low)
        if name == 'well_winding':
            # Gentle, uneven wood resonance beneath rope friction. No ratchet
            # beat implies an extra crank turn or a second simulation clock.
            rub = .55+.25*math.sin(2*math.pi*1.875*t)**2
            resonance = .028*math.sin(2*math.pi*83*t+.22*math.sin(2*math.pi*3.1*t))
            resonance += .013*math.sin(2*math.pi*139*t+.32*math.sin(2*math.pi*2.3*t))
            value = rub*(resonance+low*.18+white*.008)
        elif name == 'well_fill':
            swell = .72+.28*math.sin(math.pi*t/duration)**2
            value = swell*(low*.24+white*.024)
            value += .013*math.sin(2*math.pi*217*t)*math.sin(2*math.pi*3.75*t)**4
        elif name == 'well_pour':
            envelope = math.sin(math.pi*min(1, t/duration))**.65
            value = envelope*(low*.27+white*.065)
        elif name == 'well_hook':
            envelope = min(1, t/.004)*math.exp(-32*t)
            value = envelope*(.13*math.sin(2*math.pi*875*t)
                              +.06*math.sin(2*math.pi*2057*t)+white*.014)
        elif name == 'well_splash':
            envelope = min(1, t/.008)*math.exp(-9*t)
            value = envelope*(low*.55+white*.105)
            value += .048*math.exp(-16*t)*math.sin(2*math.pi*(145*t+32*t*t))
        else:
            # Three restrained droplets, not a sustained rain bed.
            value = 0.
            for start, pitch, volume in ((.015, 1100, .075), (.17, 1430, .055), (.34, 970, .04)):
                local = t-start
                if local >= 0:
                    envelope = min(1, local/.002)*math.exp(-65*local)
                    value += volume*envelope*math.sin(2*math.pi*(pitch*local-460*local*local))
        if name not in LOOPS:
            value *= min(1, max(0, (duration-t)/.018))
        values.append(value)
    if fade:
        for i in range(fade):
            blend = i/fade
            values[i] = values[count+i]*(1-blend)+values[i]*blend
        values = values[:count]
    pcm = array('h')
    for value in values:
        pcm.extend([round(value*24000)]*channels)
    return pcm
