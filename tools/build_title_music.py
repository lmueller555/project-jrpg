"""Synthesize an original, quiet harp/flute title loop without sample libraries."""
import math
from pathlib import Path
import struct
import wave

ROOT=Path(__file__).resolve().parents[1]


def build():
    rate=22050
    seconds=24
    samples=[0.0]*(rate*seconds)

    def note(start,length,midi,gain,kind):
        frequency=440*2**((midi-69)/12)
        for i in range(round(length*rate)):
            t=i/rate
            if kind=='plucked':
                envelope=(1-math.exp(-t*90))*math.exp(-t*2.3)
                value=sum(math.sin(math.tau*frequency*h*t)/(h*h) for h in (1,2,3,4))
            else:
                envelope=min(1,t/.14)*min(1,max(0,(length-t)/.3))
                value=math.sin(math.tau*frequency*t+.008*math.sin(math.tau*4*t))
                value+=.13*math.sin(math.tau*2*frequency*t)
            index=round(start*rate)+i
            if index<len(samples):samples[index]+=value*envelope*gain

    # Six unhurried measures in D major, resolving before the loop returns.
    chords=((50,57,62),(47,54,59),(43,50,55),(45,52,57),(43,50,55),(45,54,62))
    for bar,chord in enumerate(chords):
        for beat in range(8):note(bar*4+beat*.5,1.6,chord[beat%3]+12,.035,'plucked')
    melody=((.5,2,74),(3,1,78),(4.5,2,76),(7,1,74),(8.5,2,71),
            (11,1,69),(12.5,2,73),(15,1,76),(16.5,2,74),(19,1,71),(20.5,2.5,74))
    for start,length,pitch in melody:note(start,length,pitch,.055,'flute')
    path=ROOT/'assets/ui/title/eldenmere_theme.wav'
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as output:
        output.setparams((1,2,rate,0,'NONE','not compressed'))
        pcm=bytearray()
        for i,value in enumerate(samples):
            fade=min(1,i/rate/.15,(seconds-i/rate)/.5)
            pcm.extend(struct.pack('<h',round(max(-1,min(1,value*fade))*32767)))
        output.writeframes(pcm)
    print('Built original 24-second title theme:',path.relative_to(ROOT))


if __name__=='__main__':build()
