"""Original 6/8 title theme: Home, Curiosity, Fragility, Return.

Offline NumPy synthesis of breath-shaped flute, voiced harp, slow strings,
pizzicato replies and sparse bells. FFmpeg creates the runtime Ogg file.
"""
import json
import math
from pathlib import Path
import subprocess
import wave
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
RATE=44100
TEMPO=54 # dotted-quarter beats/minute; two per 6/8 bar
BAR=120/TEMPO
EIGHTH=BAR/6
SECTIONS=('Home','Curiosity','Fragility','Return')
D=(50,54,57,62);G=(43,50,57,59);EM=(52,55,59,62)
A=(45,52,57,61);ASUS=(45,52,57,62);BM=(47,54,59,62)
PROGRESSIONS=(
    (D,G,EM,ASUS,(42,50,57,62),BM,G,A,EM,(45,52,57,59)),
    (D,G,(42,50,57,62),BM,EM,ASUS,A,D,EM,(45,52,57,59)),
    (BM,G,EM,(42,49,54,59),(42,49,54,58),BM,(43,50,58,62),EM,ASUS,A),
    (D,G,(42,50,57,62),BM,EM,ASUS,D,G,EM,(45,52,57,59)),
)
PHRASES=(
    ((0,1.35,74),(1.5,.45,76),(2,.9,78),(3,2.6,81)),
    ((.5,1.7,78),(2.5,.8,76),(4,1.6,74)),
    ((0,1.35,76),(1.5,.45,78),(2,.9,79),(3,2.6,83)),
    ((0,1.7,81),(2,.8,79),(3,1,78),(4.5,1,76)),
    ((.5,1.35,78),(2,.8,81),(3,1.3,83),(4.5,1,81)),
    ((0,1.7,78),(2.5,.8,76),(4,1.6,74)),
    ((.5,.8,76),(1.5,.8,78),(3,1.3,81),(4.5,1,79)),
    ((0,1.7,78),(2.5,.8,76),(4,1.6,74)),
    ((.5,1.3,76),(2,1.3,79),(3.5,.8,78),(4.5,1,76)),
    ((0,1.3,76),(2,.8,73),(3,1.3,76),(4.5,1,81)),
)


def compose():
    events=[]
    rng=np.random.default_rng(2255)
    def add(bar,eighth,length,pitch,instrument,gain,pan):
        events.append({'start':bar*BAR+eighth*EIGHTH,'length':length*EIGHTH,
                       'midi':pitch,'instrument':instrument,'gain':gain,'pan':pan})
    for section,progression in enumerate(PROGRESSIONS):
        for local,chord in enumerate(progression):
            bar=section*10+local
            strength=(.66,.83,.65,.94)[section]
            add(bar,0,6.8,chord[0]-12,'bass',.11*strength,-.08)
            for beat in range(6):
                pitch=chord[(0,2,1,3,2,1)[beat]]+12
                add(bar,beat+float(rng.uniform(-.015,.015)),4.1,pitch,'harp',
                    (.095 if beat in (0,3) else .065)*strength,float(rng.uniform(-.52,.1)))
            if section or local>=4:
                for index,pitch in enumerate(chord[1:]):
                    add(bar,.15,7.5,pitch,'strings',(.028 if section==2 else .022)*strength,
                        (-.52,0,.5)[index])
            for note_index,(eighth,length,pitch) in enumerate(PHRASES[local]):
                if section==2:
                    pitch={74:71,76:73,78:74,79:76,81:78,83:79,73:70}[pitch]
                    if local==4:pitch=(73,78,82,78)[note_index]
                    if local==6:pitch=(74,72,70,69)[note_index]
                add(bar,eighth,length,pitch,'flute',.14*strength,.18)
            if section in (1,3) and local%2:
                for beat,pitch in zip((1,2.5,4,5),(chord[1]+12,chord[2]+12,chord[3]+12,chord[2]+12)):
                    add(bar,beat,2.2,pitch,'pizzicato',.043*strength,.48)
            if local in (0,7) and section!=2:
                add(bar,0,9,74 if local==0 else 81,'bell',.018,-.45)
    return events


def instrument(event,rng):
    length=event['length'];t=np.arange(round((length+.08)*RATE))/RATE
    frequency=440*2**((event['midi']-69)/12);kind=event['instrument']
    release=np.minimum(1,np.maximum(0,(length-t)/(.25 if kind=='flute' else .4)))
    if kind=='flute':
        depth=.0018*np.minimum(1,t/.7)
        phase=np.cumsum(frequency*(1+depth*np.sin(math.tau*4.7*t)))*math.tau/RATE
        value=np.sin(phase)+.12*np.sin(2*phase+.2)+.035*np.sin(3*phase)
        breath=np.convolve(rng.normal(0,1,len(t)),np.ones(11)/11,mode='same')
        value+=.055*breath
        value*=np.minimum(1,t/.16)**.8*release*(.97+.03*np.sin(math.tau*.8*t))
    elif kind=='strings':
        value=np.zeros(len(t))
        for detune in (-.002,0,.0022):
            phase=math.tau*frequency*(1+detune)*t+float(rng.uniform(0,math.tau))
            for harmonic in range(1,6):value+=np.sin(harmonic*phase)/(3*harmonic**1.7)
        value*=np.minimum(1,t/.65)*np.minimum(1,np.maximum(0,(length-t)/.8))
    elif kind=='bass':
        phase=math.tau*frequency*t
        value=(np.sin(phase)+.13*np.sin(2*phase))*(1-np.exp(-t*28))*np.exp(-t*.8)*release
    elif kind=='bell':
        value=np.zeros(len(t))
        for ratio,gain in ((1,1),(2.76,.3),(5.4,.08)):
            value+=gain*np.sin(math.tau*frequency*ratio*t)*np.exp(-t*(1.2+ratio*.3))
        value*=(1-np.exp(-t*120))*release
    else:
        value=np.zeros(len(t))
        for harmonic in range(1,9):
            phase=math.tau*frequency*harmonic*(1+.00008*harmonic**2)*t
            value+=np.sin(phase+float(rng.uniform(-.05,.05)))*np.exp(-t*(1.1+harmonic*.25))/harmonic**1.6
        value*=(1-np.exp(-t*150))*release
        if kind=='pizzicato':value*=np.exp(-t*2)
    return (value*event['gain']).astype('float32')


def build():
    duration=40*BAR;count=round(duration*RATE)
    audio=np.zeros((count,2),dtype='float32')
    rng=np.random.default_rng(555);events=compose()
    for event in events:
        note=instrument(event,rng);first=round(event['start']*RATE)%count
        positions=(np.arange(len(note))+first)%count
        pan=event['pan']
        audio[positions,0]+=note*math.cos((pan+1)*math.pi/4)
        audio[positions,1]+=note*math.sin((pan+1)*math.pi/4)
    # Circular delay tails wrap across the seam, preserving the final resonance.
    dry=audio.copy()
    for delay,gain in ((.071,.13),(.113,.11),(.181,.095),(.293,.065),(.431,.04)):
        audio[:,0]+=np.roll(dry[:,1],round(delay*RATE))*gain
        audio[:,1]+=np.roll(dry[:,0],round((delay+.017)*RATE))*gain
    audio-=np.mean(audio,axis=0)
    audio=np.tanh(audio);audio*=.7/float(np.max(np.abs(audio)))
    pcm=np.round(audio*32767).astype('<i2');folder=ROOT/'assets/ui/title'
    with wave.open(str(folder/'eldenmere_theme.wav'),'wb') as output:
        output.setparams((2,2,RATE,0,'NONE','not compressed'));output.writeframes(pcm.tobytes())
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(folder/'eldenmere_theme.wav'),
                    '-c:a','libvorbis','-q:a','5',str(folder/'eldenmere_theme.ogg')],check=True)
    score={'title':'Eldenmere — Home and the Road Beyond','meter':'6/8',
           'dotted_quarter_bpm':TEMPO,'tonal_center':'D major / relative B minor',
           'motif_midi':[74,76,78,81],'duration_seconds':count/RATE,'sample_rate':RATE,
           'channels':2,'loop':'Circular instrument/reverb tails; no inserted silence',
           'sections':[{'name':name,'start_seconds':i*10*BAR,'bars':10} for i,name in enumerate(SECTIONS)],
           'instruments':['harp','flute','strings','pizzicato','bass','bell'],'events':events}
    (folder/'music_score.json').write_text(json.dumps(score,indent=2)+'\n')
    print(f'Built {duration:.2f}s stereo title theme; {len(events)} notes; four connected passages.',flush=True)


if __name__=='__main__':build()
