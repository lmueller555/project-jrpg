"""Actual-game wildlife review at 30 Hz simulation / 15 fps normal playback.

Only completed predecessor quests and initial Caelan positions are fixtures.
Garden work/dialogue, animal behavior, the gardener's entire pasture visit,
player movement, contact sounds and Continue use production code. Site changes
between clips are labelled cuts. Music is muted; accepted regional effects are
rendered from the production PCM and gain stream without normalization.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pygame
from main import Game
from garden_orchard import SCENE_ID
from tools.capture_lantern_quest import seed_previous_quests
from tools import capture_regional_audio as audio_capture

OUT=ROOT/'docs/reviews/purposeful_wildlife'
INPUT_SHA={}


def clean_json(value):
    if isinstance(value,float) and not math.isfinite(value):return None
    if isinstance(value,dict):return {key:clean_json(item) for key,item in value.items()}
    if isinstance(value,(tuple,list)):return [clean_json(item) for item in value]
    return value


def write_json(path,value):
    path.write_text(json.dumps(clean_json(value),indent=2,allow_nan=False)+'\n')


def input_hashes():
    paths=[ROOT/path for path in ('main.py','overworld_world.py','overworld_travel.py',
           'garden_orchard.py','purposeful_wildlife.py','regional_audio.py',
           'tools/capture_purposeful_wildlife.py','tools/capture_regional_audio.py',
           'tools/build_regional_wildlife.py','assets/characters/garden_workers/art.json',
           'assets/maps/overworld/elden_vale/region.json')]
    paths+=list((ROOT/'assets/characters/regional_wildlife').rglob('*'))
    return {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.is_file()}


def still(game,name):
    game.draw()
    pygame.image.save(game.canvas,str(OUT/(name+'_native.png')))
    pygame.image.save(game.window,str(OUT/(name+'.png')))


def wildlife(game):return game.overworld_world.wildlife


def species(game,name):
    return [actor for actor in wildlife(game).actors if actor.species==name]


def position(game,point):
    assert game.world.can_stand(point),('Blocked review watcher',point)
    game.player.position.update(point)
    game.camera.reset()


def make_game(root,point):
    game=Game(window_size=(960,640),fullscreen=False,start_on_title=False,
              save_path=root/'journey.json',settings_path=root/'settings.json')
    game.audio.set_music(0);game.audio.set_effects(1)
    seed_previous_quests(game)
    game.world=game.overworld_world
    game.opening_fade=game.transfer_cooldown=0;game.location_seconds=0
    position(game,point)
    return game


def off_record_until(game,predicate,limit=180):
    for _ in range(round(limit*30)):
        if predicate():return
        game.update(1/30,(0,0),False)
    raise AssertionError(('Preparation timeout',wildlife(game).to_dict()))


class Recorder(audio_capture.Recorder):
    def __init__(self,game,name,families=()):
        game.regional_audio.stop()
        assert game.canvas.get_size()==(480,320) and game.window.get_size()==(960,640)
        self.name=name;self.families=set(families);self.seen=set()
        self.trace=[];self.checks={};self.last_behavior=None
        super().__init__(game)

    def event(self,action,key,**data):
        if action=='start':
            source=self.g.regional_audio.voices[key][0]
            data.update(source=list(source.point()),listener=list(self.g.player.position),
                        distance=self.g.player.position.distance_to(source.point()),
                        family=source.family,priority=source.priority)
        super().event(action,key,**data)

    def record_state(self):
        controller=wildlife(self.g)
        assert self.g.camera._frame_height==320,'Capture must retain the normal regional zoom'
        actors=[{'id':actor.id,'species':actor.species,'pose':actor.pose,
                 'position':list(actor.position),'state':dict(actor.state)}
                for actor in controller.actors]
        key=tuple((actor['id'],actor['pose'],actor['state'].get('mode')) for actor in actors)
        if self.count%15==0 or key!=self.last_behavior:
            self.trace.append({'time':self.count/30,'listener':list(self.g.player.position),
                               'actors':actors,'vignette':dict(controller.vignette),
                               'basket':list(controller.basket_position()),
                               'voices':{key:{'gain':self.g.regional_audio._gain(voice[0]),
                                              'source':list(voice[0].point())}
                                         for key,voice in self.g.regional_audio.voices.items()}})
        self.last_behavior=key
        for actor in controller.actors:
            label=actor.species+'_'+actor.pose
            if actor.species in self.families and label not in self.seen:
                if actor.position.distance_to(self.g.player.position)<140:
                    self.seen.add(label);still(self.g,self.name+'_'+label)
            if actor.species=='cat' and actor.pose=='stretch' and actor.clock>=.8:
                label='cat_stretch_peak'
                if 'cat' in self.families and label not in self.seen:
                    self.seen.add(label);still(self.g,self.name+'_'+label)

    def run(self,seconds,direction=(0,0)):
        for _ in range(round(seconds*30)):
            super().run(1/30,direction)
            self.record_state()

    def walk(self,target,limit=30):
        target=pygame.Vector2(target)
        for _ in range(round(limit*30)):
            delta=target-self.g.player.position
            if delta.length()<=2:return
            before=self.g.player.position.copy()
            self.run(1/30,delta)
            if self.g.player.position.distance_to(before)<.01:
                raise AssertionError(('Player route blocked',tuple(before),tuple(target)))
        raise AssertionError(('Player route timeout',tuple(self.g.player.position),tuple(target)))

    def close(self):
        self.g.regional_audio.observer=self.event
        with np.errstate(divide='ignore'):
            super().close()
        (OUT/'regional_audio.mp4').replace(OUT/(self.name+'.mp4'))
        report=json.loads((OUT/'capture_report.json').read_text())
        report.update(method=__doc__,trace=self.trace,checks=self.checks,
                      native_size=[480,320],window_size=[960,640],simulation_hz=30,video_fps=15,
                      final_state=wildlife(self.g).to_dict(),
                      cache_stats=self.g.overworld_world.cache_stats)
        report['source_sha256']=INPUT_SHA or input_hashes()
        write_json(OUT/(self.name+'_report.json'),report)
        (OUT/'capture_report.json').unlink()
        (OUT/'review.wav').unlink()
        self.g.regional_audio.observer=None
        return report


def prepare_gardener(game):
    controller=game.world.garden_orchard
    off_record_until(game,lambda:controller.state['gardener']['phase']=='ready')
    position(game,(-526,1204))
    assert game.overworld_travel.interact()
    assert game.social.script_identifier==SCENE_ID
    pages=[]
    while game.social.active:
        pages.append(game.social.page_index)
        game.update(1/30,(0,0),False);game.social.advance()
    off_record_until(game,lambda:controller.state['gardener']['phase']=='rest')
    assert controller.state['gardener']['read']
    return {'garden_work_and_optional_scene':'completed through production update/interact before recording',
            'dialogue_pages':pages,'garden_state':controller.to_dict()}


def sheep_clip(root):
    game=make_game(root,(-526,1214))
    preparation=prepare_gardener(game)
    recorder=Recorder(game,'sheep_visit',('sheep',))
    recorder.checks['preparation']=preparation
    recorder.mark('Garden care is complete; gardener begins her finite pasture visit')
    still(game,'sheep_visit_departure')
    # Caelan uses a clear parallel path while the worker follows her own route.
    for point in ((-526,1214),(-492,1214),(-492,1250),(-336,1250)):
        recorder.walk(point)
    recorder.until(lambda:wildlife(game).worker.position.y>=1250,limit=60)
    recorder.walk((-336,1368))
    recorder.mark('Caelan watches from beside the pasture gate')
    recorder.until(lambda:wildlife(game).worker.position.y>=1408,limit=90)
    # Keep the gate and the worker's basket station clear during the relationship.
    recorder.walk((-336,1412));recorder.walk((-280,1412))
    recorder.mark('Sheep gather, investigate the one basket, and accept a pat')
    recorder.until(lambda:any(actor.pose=='nuzzle' for actor in species(game,'sheep')),limit=90)
    recorder.run(.4)
    before=wildlife(game).to_dict()
    feet=list(wildlife(game).worker.position);basket=list(wildlife(game).basket_position())
    assert game.world.can_stand(game.player.position)
    assert game.save_progress()
    still(game,'sheep_basket_before_continue')
    recorder.mark('Save and Continue during the sheep and basket interaction')
    game.on_title=True;recorder.run(.6)
    assert game.begin_journey(True)
    recorder.checks['continue_exact_state']=before==wildlife(game).to_dict()
    recorder.checks['continue_exact_worker_feet']=feet==list(wildlife(game).worker.position)
    recorder.checks['continue_exact_basket']=basket==list(wildlife(game).basket_position())
    assert all(recorder.checks[key] for key in ('continue_exact_state','continue_exact_worker_feet','continue_exact_basket'))
    recorder.checks['continue_snapshot']={'state':before,'worker_feet':feet,'basket':basket}
    game.opening_fade=game.transfer_cooldown=0;game.location_seconds=0
    still(game,'sheep_basket_after_continue');recorder.mark('Continue preserves feet, basket and contact progress')
    recorder.until(lambda:wildlife(game).vignette['contact'],limit=10)
    recorder.mark('Gardener hand contacts the sheep fleece; one quiet sheep cue')
    still(game,'sheep_pat_contact')
    recorder.until(lambda:wildlife(game).vignette['basket']=='hand',limit=10)
    recorder.mark('The same empty basket is lifted from the pasture')
    still(game,'sheep_basket_retrieved')
    recorder.until(lambda:wildlife(game).worker.position.y<1390,limit=90)
    recorder.mark('The gardener retrieves the basket and walks home; Caelan follows')
    for point in ((-336,1412),(-336,1368),(-336,1250),(-492,1250),(-492,1214)):
        recorder.walk(point)
    recorder.until(lambda:wildlife(game).vignette['phase']=='done',limit=180)
    recorder.run(3)
    still(game,'sheep_visit_complete')
    recorder.checks['completed']=wildlife(game).to_dict()
    return recorder.close()


def bird_clip(root):
    game=make_game(root,(-920,208))
    recorder=Recorder(game,'bird_grain_scatter_return',('bird',))
    recorder.mark('Labelled site cut: farm bird beside its spilled grain')
    recorder.run(8)
    recorder.mark('Caelan approaches on foot; bird scatters')
    recorder.walk((-880,208));recorder.run(2)
    recorder.mark('Caelan retreats; landing waits for the clear cooldown')
    # The away perch lies west of the grain: retreat south, leaving both the
    # airborne bird and its landing lane clear rather than startling it again.
    for point in ((-900,208),(-900,318),(-840,318)):
        recorder.walk(point)
    recorder.run(16)
    recorder.checks['accepted_wildlife_events']=[event for event in recorder.events
        if event['action']=='start' and event.get('family')=='wildlife']
    assert {event['sound'] for event in recorder.checks['accepted_wildlife_events']}=={'wings','bird'},'Scatter and completed landing must both be captured'
    return recorder.close()


def butterfly_clip(root):
    game=make_game(root,(-115,-238))
    recorder=Recorder(game,'butterfly_flowers',('butterfly',))
    recorder.mark('Labelled site cut: butterfly visits the authored orchard flowers')
    recorder.run(16)
    return recorder.close()


def cat_clip(root):
    game=make_game(root,(-460,1244))
    recorder=Recorder(game,'cat_sun_and_rest',('cat',))
    recorder.mark('Labelled site cut: farm cat rests, stretches, and walks to a second resting place')
    recorder.run(40)
    return recorder.close()


def river_clip(root):
    game=make_game(root,(-2180,1000))
    recorder=Recorder(game,'audible_distance',())
    recorder.mark('Labelled site cut: walk west from outside the river hearing radius')
    recorder.run(5.4,(-1,0));recorder.mark('Near bank; now walk east beyond the hard cutoff')
    recorder.checks['near_river_gain']=game.regional_audio._gain(game.regional_audio.voices['river'][0])
    recorder.run(6,(1,0));recorder.mark('Outside hearing range; walk west to return')
    recorder.checks['far_river_voice_released']='river' not in game.regional_audio.voices
    assert recorder.checks['far_river_voice_released']
    recorder.run(6,(-1,0));recorder.mark('Effects mute')
    game.audio.set_effects(0);start=len(recorder.blocks);recorder.run(2)
    recorder.checks['mute_pcm_exact_zero']=all(not np.any(block) for block in recorder.blocks[start:])
    assert recorder.checks['mute_pcm_exact_zero']
    game.audio.set_effects(1);recorder.mark('Effects restored');recorder.run(2)
    before=wildlife(game).to_dict();game.map_open=True
    recorder.mark('Map pause releases voices and freezes wildlife');start=len(recorder.blocks);recorder.run(2)
    recorder.checks['map_pcm_exact_zero']=all(not np.any(block) for block in recorder.blocks[start:])
    recorder.checks['map_wildlife_frozen']=before==wildlife(game).to_dict()
    assert recorder.checks['map_pcm_exact_zero'] and recorder.checks['map_wildlife_frozen']
    game.map_open=False;recorder.mark('Map closed; regional beds resume');recorder.run(2)
    still(game,'audible_distance_bank')
    return recorder.close()


CLIPS={'sheep':sheep_clip,'birds':bird_clip,'butterflies':butterfly_clip,'cat':cat_clip,'distance':river_clip}


def compile_review(reports):
    names=('sheep_visit','bird_grain_scatter_return','butterfly_flowers','cat_sun_and_rest','audible_distance')
    if not all((OUT/(name+'.mp4')).exists() for name in names):return None
    listing=OUT/'compilation_inputs.txt'
    listing.write_text(''.join("file '"+name+".mp4'\n" for name in names))
    try:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0',
                        '-i',str(listing),'-c','copy','-movflags','+faststart',
                        str(OUT/'purposeful_wildlife.mp4')],check=True)
    finally:listing.unlink()
    chapters=[];elapsed=0
    for name in names:
        report=json.loads((OUT/(name+'_report.json')).read_text())
        chapters.append({'clip':name,'starts_at':elapsed,'seconds':report['seconds']})
        elapsed+=report['seconds']
    return {'file':'purposeful_wildlife.mp4','seconds':elapsed,'chapters':chapters,
            'method':'Serial concatenation of the five unchanged normal-speed production captures; no time compression.'}


def main():
    global OUT,INPUT_SHA
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUT)
    parser.add_argument('--only',choices=tuple(CLIPS))
    args=parser.parse_args();OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=True)
    audio_capture.OUT=OUT
    INPUT_SHA=input_hashes()
    reports={}
    with tempfile.TemporaryDirectory() as tmp,patch('pygame.mixer.find_channel',side_effect=audio_capture.Channel):
        for key,capture in CLIPS.items():
            if args.only and key!=args.only:continue
            root=Path(tmp)/key;root.mkdir()
            report=capture(root)
            reports[key]={'seconds':report['seconds'],'peak_dbfs':report['peak_dbfs'],
                          'events':len(report['events']),'checks':report['checks']}
            print(key,reports[key]['seconds'],'seconds',flush=True)
    compilation=compile_review(reports)
    write_json(OUT/'capture_summary.json',{'method':__doc__,'clips':reports,'compilation':compilation,
        'limitations':['Offline production PCM reconstruction replaces unavailable SDL loopback.',
                       'No subjective listening approval is claimed.',
                       'Initial regional positions and predecessor quest completion are labelled fixtures.']})
    pygame.quit()


if __name__=='__main__':main()
