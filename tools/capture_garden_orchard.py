"""Record actual Game.update/draw, 30 Hz simulation and normal 15 fps playback.

Fixtures seed completed predecessor quests and place only Caelan/camera near a
site. Worker steps, props, contact events, dialogue and Continue use production
code. A second fixture places Caelan in a worker lane to demonstrate yielding.
Audio is the production accepted start/gain/stop stream rendered with identical
synthesis PCM (see capture_regional_audio); no editorial effects or music.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import sys, tempfile, json, hashlib
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from main import Game
from garden_orchard import SCENE_ID
from tools.capture_lantern_quest import seed_previous_quests
from tools import capture_regional_audio as audio_capture
OUT=ROOT/'docs/reviews/garden_orchard'
audio_capture.OUT=OUT
KEEP_STILLS={
    'garden_work_and_care_fill','garden_work_and_care_water',
    'garden_work_and_care_weed_turnip_0','garden_work_and_care_sort_turnip_0',
    'garden_work_and_care_weed_plant','garden_work_and_care_sort_plant',
    'garden_work_complete','garden_scene_complete',
    'garden_work_and_care_dialogue_garden_quiet_care_0',
    'garden_work_and_care_dialogue_garden_quiet_care_3',
    'orchard_harvest_and_rest_reach_apple_0','orchard_harvest_and_rest_admire',
    'orchard_harvest_and_rest_sort_apple_1','orchard_harvest_and_rest_rest',
    'orchard_work_complete',
    'orchard_harvest_and_rest_dialogue_garden_orchard_greeting_1',
    'blocked_carry','carry_before_continue','carry_after_continue',
    'plant_before_continue','plant_after_continue',
}


def still(g,name):
    if name not in KEEP_STILLS:return
    g.draw()
    pygame.image.save(g.window,str(OUT/(name+'.png')))
    pygame.image.save(g.canvas,str(OUT/(name+'_native.png')))


class Recorder(audio_capture.Recorder):
    def __init__(self,g,name,role):
        super().__init__(g)
        self.name=name;self.role=role;self.seen=set()
    def run(self,seconds,direction=(0,0)):
        super().run(seconds,direction)
        c=self.g.world.garden_orchard
        s=c.state[self.role];a=c.action(self.role)
        if a and 'pose' in a and s['elapsed']>.9:
            label=a['pose']+('_'+a.get('item','') if a.get('item') else '')
            if label not in self.seen:
                self.seen.add(label);still(self.g,self.name+'_'+label)
    def close(self):
        super().close()
        (OUT/'regional_audio.mp4').rename(OUT/(self.name+'.mp4'))
        report=json.loads((OUT/'capture_report.json').read_text())
        report['source_sha256']={str(path):hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in (Path('garden_orchard.py'),Path('regional_audio.py'),Path('assets/characters/garden_workers/art.json'))}
        report['state']=self.g.world.garden_orchard.to_dict()
        report['cache_stats']=self.g.world.cache_stats
        (OUT/(self.name+'_report.json')).write_text(json.dumps(report,indent=2)+'\n')
        (OUT/'capture_report.json').unlink()
        (OUT/'review.wav').unlink()
        return report


def game_at(root,role):
    g=Game(window_size=(960,640),fullscreen=False,start_on_title=False,
           save_path=root/'save.json',settings_path=root/'settings.json')
    g.audio.set_music(0);g.audio.set_effects(1)
    seed_previous_quests(g)
    g.world=g.overworld_world
    g.opening_fade=g.transfer_cooldown=0;g.location_seconds=0
    position=(-526,1214) if role=='gardener' else (-115,-238)
    g.player.position.update(position)
    assert g.world.can_stand(position), ('invalid capture watcher',position)
    focus=(-530,1164) if role=='gardener' else (-167,-278)
    g.camera.reset();g.camera.focus(focus,duration=0)
    return g


def dialogue(g,r):
    assert g.overworld_travel.interact(), 'interaction failed'
    while g.social.active:
        r.run(3.5)
        still(g,r.name+'_dialogue_'+str(g.social.script_identifier)+'_'+str(g.social.page_index))
        g.social.advance()


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    reports={}
    with tempfile.TemporaryDirectory() as tmp,patch('pygame.mixer.find_channel',side_effect=audio_capture.Channel):
        root=Path(tmp)
        g=game_at(root,'gardener');c=g.world.garden_orchard
        r=Recorder(g,'garden_work_and_care','gardener')
        r.mark('Southern garden: finite watering, weeding and two turnips')
        r.until(lambda:c.state['gardener']['phase']=='ready',limit=180)
        still(g,'garden_work_complete');r.mark('Optional conversation initiated by E')
        # Approach only after delivery has cleared the southern end.
        r.run(.15,(0,-1))
        dialogue(g,r)
        assert c.state['gardener']['read']
        r.mark('Gardener moves the struggling plant into hedge shade')
        r.until(lambda:c.state['gardener']['phase']=='rest',limit=60)
        r.run(5);still(g,'garden_scene_complete')
        r.mark('Review fixture: Caelan positioned beside shade for short repeat')
        g.player.position.update(-526,1160)
        dialogue(g,r)
        reports[r.name]=r.close()

        g=game_at(root,'picker');c=g.world.garden_orchard
        r=Recorder(g,'orchard_harvest_and_rest','picker')
        r.mark('Village orchard: three fruit, one bruised, finite sorting')
        r.until(lambda:c.state['picker']['phase']=='rest',limit=180)
        still(g,'orchard_work_complete');r.run(5)
        r.mark('Picker greeting after settling in the existing rest nook')
        dialogue(g,r);r.run(4)
        reports[r.name]=r.close()

        g=game_at(root,'gardener');c=g.world.garden_orchard
        r=Recorder(g,'blocked_and_continue','gardener')
        r.until(lambda:bool(c.action('gardener') and c.action('gardener').get('carry')=='can'),limit=30)
        # Deliberate blocked-lane fixture. All recovery uses actual player motion.
        g.player.position.update(-526,1172)
        r.mark('Caelan obstructs the watering lane; worker waits with vessel')
        r.run(3);before=tuple(c.actors[0].position)
        r.run(2);assert tuple(c.actors[0].position)==before
        still(g,'blocked_carry')
        r.mark('Caelan steps aside; carrying resumes')
        r.run(.32,(1,0));r.run(.15,(0,1))
        r.until(lambda:bool(c.action('gardener') and c.action('gardener').get('carry')=='can' and c.actors[0].moving),limit=20)
        r.run(.15)
        before=c.to_dict();assert g.world.can_stand(g.player.position);assert g.save_progress()
        still(g,'carry_before_continue');r.mark('Save and Continue during carried water')
        g.on_title=True;assert g.begin_journey(True)
        c=g.world.garden_orchard
        assert c.to_dict()==before
        g.opening_fade=g.transfer_cooldown=0;g.location_seconds=0
        g.camera.focus((-530,1164),duration=0)
        still(g,'carry_after_continue');r.run(1)
        # Restore Caelan to the documented clear watching station, outside lane.
        g.player.position.update(-526,1214)
        r.until(lambda:c.state['gardener']['phase']=='ready',limit=180)
        r.run(.15,(0,-1))
        dialogue(g,r)
        assert c.state['gardener']['read']
        r.until(lambda:bool(c.action('gardener') and c.action('gardener').get('carry')=='plant'),limit=30)
        r.run(.3);before=c.to_dict();assert g.world.can_stand(g.player.position);assert g.save_progress()
        still(g,'plant_before_continue');r.mark('Save and Continue while moving the plant after dialogue read')
        g.on_title=True;assert g.begin_journey(True)
        c=g.world.garden_orchard;assert c.to_dict()==before
        assert c.state['gardener']['read']
        g.opening_fade=g.transfer_cooldown=0;g.location_seconds=0
        g.camera.focus((-530,1164),duration=0)
        still(g,'plant_after_continue')
        r.until(lambda:c.state['gardener']['phase']=='rest',limit=30)
        r.run(3);reports[r.name]=r.close()
    (OUT/'capture_report.json').write_text(json.dumps({'method':__doc__,'clips':{name:{'seconds':r['seconds'],'peak_dbfs':r['peak_dbfs'],'events':len(r['events'])} for name,r in reports.items()}},indent=2)+'\n')
    pygame.quit()
if __name__=='__main__':main()
