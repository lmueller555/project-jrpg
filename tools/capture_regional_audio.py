"""Game.update/draw plus offline PCM from the production accepted voice stream.

The dummy device cannot be recorded. Fake channel leases preserve the mixer
API; RegionalAudio owns cue expiry using game seconds. Its observer feeds the
same generated PCM, gains and stop events into a 48kHz mono offline mixer.
No unrelated soundtrack, normalization or compression is added.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import sys, tempfile, subprocess, json, wave
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from main import Game
from grain_farm import MILL_FLAG
from regional_audio import Source,samples
from tools.capture_lantern_quest import seed_previous_quests
OUT=ROOT/'docs/reviews/regional_audio'
RATE=48000

class Channel:
    def __init__(self):self.sound=None
    def get_sound(self):return self.sound
    def set_volume(self,v):pass
    def play(self,sound,**kw):self.sound=sound
    def stop(self):self.sound=None

class Recorder:
    def __init__(self,g):
        self.g=g;self.voices={};self.pcm={};self.blocks=[];self.events=[];self.count=0;self.markers=[];self.snapshots=[]
        g.regional_audio.observer=self.event
        self.process=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24','-video_size','960x640','-framerate','15','-i','-','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',str(OUT/'silent.mp4')],stdin=subprocess.PIPE)
    def event(self,action,key,**data):
        if action=='start':self.voices[key]={**data,'offset':0}
        elif action=='stop':self.voices.pop(key,None)
        elif key in self.voices:self.voices[key]['gain']=data['gain']
        if action!='gain':self.events.append({'time':self.count/30,'action':action,'key':key,**data})
    def mark(self,label):
        self.markers.append({'time':self.count/30,'label':label})
        self.snapshots.append({'time':self.count/30,'label':label,'listener':list(self.g.player.position),'voices':{k:{'gain':self.g.regional_audio._gain(v[0]),'source':list(v[0].point())} for k,v in self.g.regional_audio.voices.items()}})
    def run(self,seconds,direction=(0,0)):
        for _ in range(round(seconds*30)):
            self.g.update(1/30,direction,False)
            block=np.zeros(RATE//30,dtype=np.float64)
            for v in self.voices.values():
                name=v['sound']
                if name not in self.pcm:self.pcm[name]=np.array(samples(name,RATE,1),dtype=np.float64)
                pcm=self.pcm[name];idx=np.arange(len(block))+v['offset']
                valid=np.ones(len(block),dtype=bool) if v['ambient'] else idx<len(pcm)
                block[valid]+=pcm[idx[valid]%len(pcm)]*v['gain'];v['offset']+=len(block)
            self.blocks.append(block)
            if self.count%2==0:
                self.g.draw();self.process.stdin.write(pygame.image.tobytes(self.g.window,'RGB'))
            self.count+=1
    def until(self,predicate,limit=90):
        for _ in range(limit*15):
            if predicate():return
            self.run(2/30)
        raise AssertionError('capture timeout')
    def close(self):
        self.g.regional_audio.stop();self.process.stdin.close();assert self.process.wait()==0
        data=np.concatenate(self.blocks);peak=float(np.max(np.abs(data)))/32768
        assert peak<1
        with wave.open(str(OUT/'review.wav'),'wb') as w:
            w.setparams((1,2,RATE,0,'NONE','not compressed'));w.writeframes(np.rint(data).astype('<i2').tobytes())
        subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(OUT/'silent.mp4'),'-i',str(OUT/'review.wav'),'-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart',str(OUT/'regional_audio.mp4')],check=True)
        (OUT/'silent.mp4').unlink()
        (OUT/'capture_report.json').write_text(json.dumps({'method':__doc__,'seconds':self.count/30,'sample_rate':RATE,'peak':peak,'peak_dbfs':float(20*np.log10(peak)),'rms_dbfs':float(20*np.log10(np.sqrt(np.mean(data**2))/32768)),'markers':self.markers,'snapshots':self.snapshots,'events':self.events},indent=2)+'\n')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp,patch('pygame.mixer.find_channel',side_effect=Channel):
        g=Game(window_size=(960,640),fullscreen=False,start_on_title=False,save_path=Path(tmp)/'save.json',settings_path=Path(tmp)/'settings.json')
        g.audio.set_music(0);seed_previous_quests(g);g.social.flags.add(MILL_FLAG)
        g.world=g.overworld_world;g.opening_fade=g.transfer_cooldown=0;g.location_seconds=0
        def position(p):g.player.position.update(p);g.camera.reset()
        position((-876,232));r=Recorder(g);r.mark('Farm: finite placements, rustles and lashing')
        r.until(lambda:g.world.grain_farm.stage=='ready');r.run(2)
        r.mark('Bridge: tool contact and tea');position((-2376,642));c=g.world.bridge_crew
        r.until(lambda:c.stage=='ready');g.overworld_travel.interact()
        r.until(lambda:c.stage=='request');g.overworld_travel.interact()
        while g.social.active:r.run(2);g.social.advance()
        r.until(lambda:c.stage=='exchange');g.overworld_travel.interact()
        while g.social.active:r.run(2);g.social.advance()
        r.until(lambda:c.state['tea_beat']==5);r.run(2)
        r.mark('River approach: far, mid, near (walk west)');position((-2180,1000));r.run(5.4,(-1,0))
        r.mark('River departure: near to hard cutoff');r.run(6,(1,0))
        r.mark('Return to hearing range');r.run(6,(-1,0))
        r.mark('Effects mute');g.audio.set_effects(0);r.run(2)
        r.mark('Unmute');g.audio.set_effects(1);r.run(2)
        r.mark('Regional map pauses audio');g.map_open=True;r.run(2);g.map_open=False;r.run(2)
        r.mark('Town transfer releases voices');g.world=g.town;position((120,120));r.run(2)
        r.mark('Return to region');g.world=g.overworld_world;position((-2550,1000));r.run(2)
        # Explicit stress fixture at listener: production scheduler, synthetic
        # colocated families. Labelled here, never claimed as authored scenery.
        r.mark('Budget fixture: six candidates; two beds plus two incidental voices')
        for i,name in enumerate(('river','wind')):
            g.regional_audio.play(Source('bed_fixture'+str(i),name,'bed_fixture'+str(i),lambda:g.player.position,priority=5,ambient=True))
        for i in range(6):
            g.regional_audio.play(Source('budget'+str(i),'creak' if i%2 else 'cup','fixture'+str(i),lambda:g.player.position,priority=3+i))
        assert len(g.regional_audio.voices)==4
        r.run(2);g.regional_audio.stop();r.mark('Wind within an authored grain patch');position((-1400,720));r.run(4);r.mark('Title releases voices');g.on_title=True;r.run(2);r.close()
    pygame.quit()
if __name__=='__main__':main()
