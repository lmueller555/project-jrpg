"""Capture PR4 rooms and real inn stair traversal through the production Game.

Static room/initial-town placements are explicitly disclosed review fixtures.
Every stair/exterior doorway transfer uses ordinary Game.update movement. No
replacement artwork, temporary collision, fake controller or test world is used.
Journeys/settings are temporary. Native 960x640 PNGs are authoritative; GIFs are
labelled 480x320 indexed-color movement previews. This is not an uninterrupted story playthrough.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

import pygame
from PIL import Image
from main import Game
from tools.eldenmere_interior_architecture import recipe


def capture(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    report={'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'working_tree_modified':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
        'method':'Production Game.draw/Game.update, live generated maps, native WorldCanvas 960x640.',
        'fixtures':['Static room views begin at their established safe arrival positions.',
                    'Traversal starts at the inn exterior approach; Rhea is a disclosed recruited-party fixture.',
                    'HP/MP are lowered only to observe the real existing ground-bed recovery; service prices/stock are untouched.',
                    'No source art, blockers, doors, NPC stations or quest milestones are injected.'],
        'limitations':['Not an uninterrupted story playthrough.','GIFs are 480x320 indexed-color previews; native 960x640 PNGs preserve exact pixels.'],
        'views':{},'transfers':[],'movement':{},'saves':{},'sources':{},'companion_scenes':[],
        'same_session':{},'fresh_disk_continue':{}}
    for name in ('main.py','opening_conclusion.py','lantern_rest.py',
                 'tools/capture_eldenmere_interior_architecture.py',
                 'tools/eldenmere_interior_architecture.py',
                 'assets/maps/eldenmere/town_hd/interior_architecture.json',
                 'assets/maps/eldenmere/playable/map.json','assets/services/eldenmere.json'):
        report['sources'][name]=sha256((ROOT/name).read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='eldenmere-interior-review-') as temporary:
        temporary=Path(temporary)
        g=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
               save_path=temporary/'journey.json',settings_path=temporary/'settings.json')
        try:
            g.on_title=False;g.opening.restore({'version':1,'stage':'disabled'})
            g.opening_fade=g.transfer_cooldown=0;g.audio.set_music(0);g.audio.set_effects(0)
            frames=[];tick_count=0;tracing=False
            def movement_preview(path,source):
                from tools.capture_mill_quest import save_gif
                previews=[frame.resize((480,320),Image.Resampling.NEAREST) for frame in source]
                save_gif(path,previews,[100]*len(previews),colors=96)
            def save(name):
                g.location_seconds=0;g.draw();path=output/(name+'.png');pygame.image.save(g.window,path)
                report['views'][name]={'file':path.name,'scene':g.world.data['id'],
                    'position':list(g.player.position),'facing':g.player.facing,
                    'cooldown':g.transfer_cooldown,'reduced_motion':g.audio.reduced_motion,'clock_ms':g.elapsed_ms,
                    'sha256':sha256(path.read_bytes()).hexdigest()}
            def tick(direction=(0,0),running=False):
                nonlocal tick_count
                origin=g.world.data['id'];g.update(1/60,direction,running);tick_count+=1
                if g.world.data['id']!=origin:
                    door=next((d for d in g.world.doors if d.data.get('rearm_after_exit')),None)
                    report['transfers'].append({'from':origin,'to':g.world.data['id'],
                        'position':list(g.player.position),'facing':g.player.facing,
                        'cooldown':g.transfer_cooldown,'stair_armed':door.entry_armed if door else None})
                    save('transfer_'+str(len(report['transfers']))+'_'+g.world.data['id'])
                for actor in g.party_travel.actors():
                    assert g.world.can_stand(actor.position)
                    assert not any(actor in s.npcs for s in g.scenes.values())
                    if g.world.data['id'] not in report['companion_scenes']:
                        report['companion_scenes'].append(g.world.data['id'])
                if tracing and tick_count%6==0:
                    g.location_seconds=0;g.draw()
                    frames.append(Image.frombytes('RGB',g.window.get_size(),pygame.image.tobytes(g.window,'RGB')))
            def move(point,running=False,expected=None):
                point=pygame.Vector2(point)
                for _ in range(1200):
                    if expected and g.world.data['id']==expected:return
                    delta=point-g.player.position
                    if delta.length()<=1.2:return
                    direction=delta.normalize()
                    # Cardinal approaches avoid rounding ambiguity at the sensor.
                    if abs(delta.x)<.7:direction=(0,1 if delta.y>0 else -1)
                    elif abs(delta.y)<.7:direction=(1 if delta.x>0 else -1,0)
                    tick(direction,running)
                raise AssertionError(('Blocked review route',g.world.data['id'],list(g.player.position),list(point)))
            def key(value):
                g.handle_events([pygame.event.Event(pygame.KEYDOWN,key=value,repeat=False),
                                 pygame.event.Event(pygame.KEYUP,key=value)])
            def fresh_continue(label):
                nonlocal g
                before=g.journey_snapshot();assert g.save_progress()
                old=g
                resumed=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
                    save_path=temporary/'journey.json',settings_path=temporary/'settings.json')
                assert resumed.has_saved_journey
                assert resumed.begin_journey(True),resumed.save_error
                resumed.audio.set_music(0);resumed.audio.set_effects(0);pygame.event.clear()
                old.music.stop();g=resumed
                assert g.world.data['id']==before['player']['scene']
                assert list(g.player.position)==before['player']['position']
                for field,value in (('inventory',g.inventory.to_dict()),('party',g.party.to_dict()),
                                    ('quests',g.quests.to_dict()),('gold',g.wallet.gold)):
                    assert value==before[field],field
                stair=next(d for d in g.world.doors if d.data.get('rearm_after_exit'))
                assert not stair.entry_armed
                report['fresh_disk_continue'][label]={'new_game_instance':True,
                    'scene':g.world.data['id'],'position':list(g.player.position),
                    'state_unchanged':['inventory','party','quests','gold'],'stair_disarmed':True}
                # Let the ordinary Continue fade finish through real updates,
                # without moving the arrival or bypassing the presentation.
                for _ in range(36):tick()
                save(label+'_fresh_continue')
            for name in (*recipe()['rooms'],'inn_guest_floor'):
                g.world=g._scene_by_id(name);point=g.world.data['spawn']
                assert g.world.can_stand(point),(name,point)
                g.player.position.update(point);g.player.facing='back';g.elapsed_ms=400;g.camera.reset()
                for reduced in (False,True):
                    g.audio.set_reduced_motion(reduced);g.world.update_grass(0,reduced_motion=reduced)
                    save('room_'+name+('_reduced' if reduced else '_normal'))
                if name=='school':
                    g.player.position.update(216,180);g.camera.reset();save('room_school_purpose')
            # Actual exterior entry, then walk/run both reciprocal stair directions.
            g.audio.set_reduced_motion(False);g.world=g.town;g.player.position.update(288,1488)
            g.player.facing='back';g.opening_fade=g.transfer_cooldown=0;g.camera.reset()
            assert g.party.recruit('rhea');owners={a.data['id']:sum(a in s.npcs for s in g.scenes.values()) for a in g.persistent_npcs}
            tracing=True
            for _ in range(30):tick()
            move((288,1468),expected='inn')
            assert g.world.data['id']=='inn'
            # One continuous real-movement sequence closes the recovery/stair
            # integration gap. Only depleted resources are fixture prerequisites.
            move((108,294));move((108,180));move((60,180))
            assert g.bed_rest.nearby() and g.bed_rest._profile()['entity']=='guest_bed'
            for attributes in (g.attributes,g.party.characters['rhea']):attributes.set_current(hp=1,mp=0)
            gold=g.wallet.gold;price=g.services.data['inn']['price']
            report['same_session']['recovery_fixture']={'caelan_hp_mp':[1,0],'rhea_hp_mp':[1,0],
                'price_definition_unchanged':price,'entity':'guest_bed','scene':'inn'}
            key(pygame.K_e)
            for _ in range(24):
                if g.social.choosing:break
                key(pygame.K_SPACE)
            assert g.social.choosing
            for _ in range(30):tick()
            save('same_session_existing_guest_bed_offer')
            g.draw();index=next(i for i,r in enumerate(g.social.choice_options) if r['action']=='rest')
            rect=g.social.choice_rects[index];point=(round(rect.centerx*2),round(rect.centery*2))
            g.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=point),
                             pygame.event.Event(pygame.MOUSEBUTTONUP,button=1,pos=point)])
            for attributes in (g.attributes,g.party.characters['rhea']):
                assert attributes.current_hp==attributes.value('hp')
                assert attributes.current_mp==attributes.value('mp')
            assert g.wallet.gold==gold-price
            save('same_session_existing_guest_bed_recovered')
            for _ in range(24):
                if not g.social.active:break
                key(pygame.K_SPACE)
            assert not g.social.active
            for _ in range(60):tick()
            report['same_session']['confirmed_existing_rest']={'caelan_recovered':True,'rhea_recovered':True,
                'price':price,'gold_spent':gold-g.wallet.gold,'rest_entity':'guest_bed'}
            move((108,180));move((108,294));move((242,294))
            approach_and_rest_frames=list(frames)
            for running in (False,True):
                kind='run' if running else 'walk'
                frames.clear()
                # Clear the courtyard sensor first, then use the southern aisle.
                move((242,294));move((320,300));move((366,300))
                move((366,270),running,expected='inn_guest_floor')
                assert g.world.data['id']=='inn_guest_floor'
                if not running:fresh_continue('same_session_upstairs')
                for _ in range(100):tick((0,-1),running)
                assert g.world.data['id']=='inn_guest_floor','Held north bounced upstairs'
                save(kind+'_upper_held_north')
                # Leaving the reserve rearms. Deliberate re-approach descends.
                move((366,300));move((320,300));move((366,300))
                move((366,270),running,expected='inn')
                assert g.world.data['id']=='inn'
                for _ in range(100):tick((0,-1),running)
                assert g.world.data['id']=='inn','Held north bounced downstairs'
                save(kind+'_lower_held_north')
                move((366,300));move((320,300))
                if not running:
                    move((242,294));move((216,294));move((216,318),expected=g.town.data['id'])
                    assert g.world is g.town
                    save('same_session_rest_upstairs_continue_downstairs_out')
                    report['same_session']['sequence']=['town entry','existing guest_bed confirmed rest',
                        'stairs upstairs','fresh Game disk Continue upstairs','stairs downstairs','existing exterior return']
                    report['same_session']['completed_with_real_movement']=True
                    sequence=approach_and_rest_frames+frames
                    path=output/'town_bed_rest_upper_continue_return.gif'
                    movement_preview(path,sequence)
                    report['same_session']['movement_file']=path.name
                if frames:
                    path=output/(kind+'_stairs.gif')
                    movement_preview(path,frames)
                    report['movement'][kind]={'file':path.name,'frames':len(frames),'frame_ms':100,'preview_pixels':[480,320],
                        'reciprocal':True,'held_input_no_bounce':True,'sha256':sha256(path.read_bytes()).hexdigest()}
                if not running:
                    # Re-enter normally for the separately identified run pass.
                    for _ in range(30):tick()
                    move((288,1468),expected='inn')
                    assert g.world.data['id']=='inn'
            tracing=False
            for actor in g.persistent_npcs:
                assert sum(actor in s.npcs for s in g.scenes.values())==owners[actor.data['id']]
            assert {'inn','inn_guest_floor'}<=set(report['companion_scenes'])
            report['persistent_ownership_unchanged']=True
            report['companion_positions_clear_and_never_world_npcs']=True
            # Actual disk Save/Continue on each floor, with landing disarmed.
            for name in ('inn','inn_guest_floor'):
                g.world=g._scene_by_id(name);g.player.position.update(366,300)
                g.player.facing='front';g.opening_fade=g.transfer_cooldown=0
                before=g.journey_snapshot();assert g.saves.eligible(manual=True)
                assert g.saves.manual(1)
                row=next(row for row in g.saves.entries() if row[2]==('manual',1))
                assert g.saves.load(row)
                assert g.save_progress()
                g.saved_journey=g._read_saved_journey();assert g.begin_journey(True)
                assert g.world.data['id']==name and g.world.can_stand(g.player.position)
                assert not next(d for d in g.world.doors if d.data.get('rearm_after_exit')).entry_armed
                for field,value in (('inventory',g.inventory.to_dict()),('party',g.party.to_dict()),('quests',g.quests.to_dict()),('gold',g.wallet.gold)):
                    assert value==before[field],(name,field)
                report['saves'][name]={'disk_continue':True,'manual_slot_continue':True,'position':list(g.player.position),
                    'state_unchanged':['inventory','party','quests','gold'],'stair_disarmed':True}
                for _ in range(36):tick()
                g.camera.reset();save('continue_'+name)
            # Exterior exit remains a real existing portal after the new stairs.
            g.world=g._scene_by_id('inn');g.player.position.update(320,300)
            g.opening_fade=g.transfer_cooldown=0;move((242,294));move((216,294));move((216,318),expected=g.town.data['id'])
            assert g.world is g.town;save('inn_actual_exterior_return')
            report['exterior_portal_preserved']=True
        finally:g.music.stop();pygame.quit()
    (output/'gameplay_evidence.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'views':len(report['views']),'transfers':len(report['transfers']),
                      'movement':list(report['movement']),'saves':report['saves']},indent=2))
    return report


def capture_lantern_regression(output):
    """Run the shipped real-action driver separately, never overwrite history."""
    from time import perf_counter
    import tools.capture_lantern_rest as legacy
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    previous_output=legacy.OUT;legacy.OUT=output
    class TimedCapture(legacy.Capture):
        def __init__(self):
            self.lifecycle=[];self.previous_state=None
            super().__init__()
        def tick(self,seconds=1/30,direction=(0,0),record=True):
            def state():return {'stage':self.c.stage,'action':self.c.action,
                                'frame_owner':self.c.rest.frame_location}
            before=state()
            if before!=self.previous_state:
                self.lifecycle.append({'elapsed_game_ms':self.g.elapsed_ms,'state':before})
            super().tick(seconds,direction,record)
            after=state()
            if after!=before:self.lifecycle.append({'elapsed_game_ms':self.g.elapsed_ms,'state':after})
            self.previous_state=after
    start=perf_counter();driver=None
    try:
        driver=TimedCapture();driver.run()
        evidence={'base_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'method':'Existing production lantern-rest driver; ordinary movement, real doors/dialogue/action callbacks.',
            'separate_from_inn_capture':True,'wall_seconds':round(perf_counter()-start,3),
            'fixture_prerequisites':'Existing shipped MQ04 elira_visited checkpoint and completed MQ01–MQ03 only. Historical Lantern PR2 labels are not the architecture PR numbers.',
            'new_lantern_progress_injected':False,'lifecycle':driver.lifecycle,
            'frame_ownership_changes':driver.ownership_changes,
            'sources':{name:sha256((ROOT/name).read_bytes()).hexdigest() for name in
                ('lantern_quest.py','lantern_rest.py','tools/capture_lantern_rest.py',
                 'tools/eldenmere_interior_architecture.py')},
            'native_pngs':{p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob('*.png'))}}
        (output/'regression_metadata.json').write_text(json.dumps(evidence,indent=2)+'\n')
        print('Separate lantern regression seconds:',evidence['wall_seconds'])
        return evidence
    finally:
        legacy.OUT=previous_output
        if pygame.get_init():
            if driver is not None:driver.g.music.stop()
            pygame.quit()
        if driver is not None:driver.temp.cleanup()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    p.add_argument('--lantern',action='store_true',help='Run only the separately timed existing Lantern rest driver')
    a=p.parse_args()
    (capture_lantern_regression if a.lantern else capture)(a.output)
