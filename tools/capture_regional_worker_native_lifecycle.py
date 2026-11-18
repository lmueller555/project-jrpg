"""Capture real controller activity joins at native gameplay scale.

Only prerequisite flags and player review positions are fixtures. NPC feet,
pose, facing, frame selection, transfers and props remain production-controlled.
The four grain/bridge workers run their actual finite work plus optional
physical exchange/tea scenes. Grain includes unrepaired cover and repaired
uncover, seeded by a disclosed change of the existing mill-restored fixture. No NPC state
is seeded to skip those programs. Saved crops are clearly marked actual Game
pixels; full960x640 scenes and world/camera registrations remain authoritative.
"""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
import sys,tempfile,time
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image,ImageDraw
from main import Game
from tools.capture_lantern_quest import seed_previous_quests
from regional_npc_art import actor_binding
STATIONS={'grain_loader':(-876,232),'grain_coworker':(-876,232),
          'bridge_mason':(-2340,644),'bridge_tender':(-2340,644),
          'regional_gardener':(-508,1206),'regional_picker':(-135,-230)}
CORE=('regional_npc_art.py','regional_npc_activity.py','grain_farm.py','garden_orchard.py','npc_roster_art.py','bridge_crew.py','main.py','dense_art.py','rendering.py')
def fingerprint():return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in CORE}
def capture(actor_id,output,reduced=False):
    if not actor_id.startswith(('grain_','bridge_')):raise ValueError('Grain/bridge roles only')
    output.mkdir(parents=True,exist_ok=True)
    rows=[];crops=[];seen=set();draw_times=[];source=fingerprint();mode='unrepaired' if actor_id.startswith('grain_') else 'work';done_ticks=0;dialogue_timer=0.;barrier_seen=False
    with tempfile.TemporaryDirectory(prefix='regional-native-activity-') as temp:
        p=Path(temp)
        g=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
               save_path=p/'journey.json',settings_path=p/'settings.json')
        try:
            g.on_title=False;g.opening.restore({'version':1,'stage':'disabled'})
            g.opening_fade=g.transfer_cooldown=0
            seed_previous_quests(g);g.social.flags.add('CH01_MQ02_MILL_RESTORED')
            g.audio.set_reduced_motion(reduced)
            if actor_id.startswith('grain_'):g.social.flags.discard('CH01_MQ02_MILL_RESTORED')
            g.world=g.overworld_world;g.player.position.update(STATIONS[actor_id]);g.camera.reset()
            controllers=(g.world.grain_farm,g.world.bridge_crew,g.world.garden_orchard)
            actor=next(a for c in controllers for a in c.actors if a.data['id']==actor_id)
            binding=actor_binding(actor_id)
            if not binding or not binding['activation']['activity']:raise ValueError('Native activity not explicitly active')
            for tick in range(20000):
                g.update(1/30,(0,0),False)
                garden=g.world.garden_orchard;wildlife=g.world.wildlife
                key=actor.animation_key;index=actor.frame_index
                controller=g.world.grain_farm if actor_id.startswith('grain_') else g.world.bridge_crew
                stage=controller.stage
                stage=mode+'_'+stage
                detail=actor.detailed_sprite(g.elapsed_ms)
                native_key=hashlib.sha256(pygame.image.tobytes(detail[0],'RGBA')).hexdigest() if detail else None
                identity=(stage,key,index,actor.moving,native_key)
                if identity not in seen:
                    seen.add(identity);start=time.perf_counter();g.draw();draw_times.append((time.perf_counter()-start)*1000)
                    file=f'{len(rows):03}_{stage}_{key}_{index}.png'
                    pygame.image.save(g.canvas.native,str(output/file))
                    cam=g.camera.position();px=round((actor.position.x-cam[0])*2);py=round((actor.position.y-cam[1])*2)
                    raw=Image.frombytes('RGB',g.canvas.native.get_size(),pygame.image.tobytes(g.canvas.native,'RGB'))
                    crops.append((stage+'/'+key,raw.crop((px-64,py-96,px+64,py+16))))
                    safe=g.world.can_stand(actor.position,actor.probe_size,actor)
                    if not safe:raise AssertionError(('Unsafe actor feet',list(actor.position)))
                    rows.append({'file':file,'tick':tick,'scene':g.world.data['id'],'camera':list(cam),
                                 'player_review_position':list(g.player.position),'feet':list(actor.position),
                                 'facing':actor.facing,'pose':actor.pose,'moving':actor.moving,'clock':actor.clock,
                                 'animation_key':key,'frame_index':index,'native_activity':detail is not None,
                                 'native_artwork_size':list(detail[0].get_size()) if detail else None,
                                 'native_anchor':list(detail[1]) if detail else None,'safe_feet':safe,
                                 'legacy_attachment':actor.attachment,'physical_state':controller.to_dict(),
                                 'prop_records':[{'sort_y':z,'layer':layer,'image_logical_size':list(im.get_size()),'world_top_left':list(point)} for z,layer,im,point in controller.props()],
                                 'cup_owner':controller.cup_owner.data['id'] if actor_id.startswith('bridge_') and controller.cup_owner else None,
                                 'portable_positions':{k:[list(point),z] for k,(point,z) in garden.portable_positions().items()} if actor_id.startswith('regional_') else None,
                                 'wildlife_basket':list(wildlife.basket_position()),'wildlife_owned':getattr(actor,'wildlife_owned',False),
                                 'controller_stage':stage})
                farm=g.world.grain_farm;bridge=g.world.bridge_crew
                if actor_id.startswith('grain_'):
                    if mode=='unrepaired' and farm.covered and farm.stage=='rest' and farm.timer>=2.2:
                        g.social.flags.add('CH01_MQ02_MILL_RESTORED');mode='work'
                    if mode=='work' and farm.stage=='ready' and farm.coworker_stop==6:
                        g.player.position.update(-870,203)
                        if not g.overworld_travel.interact() or g.social.script_identifier!='grain_farm_extra_sack':raise AssertionError('Grain exchange dialogue did not start')
                        mode='exchange'
                    finished=mode=='exchange' and farm.state['scene_done'] and farm.stage=='rest' and farm.timer>=2.5
                else:
                    barrier_seen=barrier_seen or bridge.stage=='barrier_look'
                    if mode=='work' and barrier_seen and bridge.stage=='ready' and bridge.timer>=2.5:
                        g.player.position.update(-2376,642)
                        if not g.overworld_travel.interact() or bridge.state['tea_beat']!=1:raise AssertionError('Tea work did not begin')
                        mode='tea'
                    if mode=='tea' and bridge.stage in ('request','exchange') and not g.social.active:
                        if not g.overworld_travel.interact() or g.social.script_identifier!='bridge_crew_tea':raise AssertionError('Tea dialogue did not start')
                    finished=mode=='tea' and bridge.state['tea_beat']==5 and bridge.stage=='ready' and bridge.timer>=2.5
                if g.social.active:
                    dialogue_timer+=1/30
                    if dialogue_timer>=1.4:g.social.advance();dialogue_timer=0.
                else:dialogue_timer=0.
                done_ticks=done_ticks+1 if finished else 0
                if done_ticks>=20:break
            else:
                (output/'failure_state.json').write_text(json.dumps({'mode':mode,'player':list(g.player.position),'farm':g.world.grain_farm.to_dict(),'farm_stage':g.world.grain_farm.stage,'coworker_stop':g.world.grain_farm.coworker_stop,'bridge':g.world.bridge_crew.to_dict(),'bridge_stage':g.world.bridge_crew.stage,'actors':{a.data['id']:{'feet':list(a.position),'pose':a.pose,'moving':a.moving} for c in controllers for a in c.actors}},indent=2)+'\n')
                raise AssertionError('Production activity did not complete; see failure_state.json')
            if not rows:raise AssertionError('No real rendered activity')
            board=Image.new('RGB',(640,36+((len(crops)+4)//5)*144),'#dfe5da');draw=ImageDraw.Draw(board)
            draw.text((8,8),'ACTUAL GAME CROPS / NATIVE2x / FEET ALIGNED FOR SCALE COMPARISON',fill='#20382b')
            for i,(label,im) in enumerate(crops):
                x=i%5*128;y=i//5*144+32;board.paste(im,(x,y));draw.text((x+2,y+114),label[:22],fill='#20382b')
            board.save(output/'actual_transition_board.png')
            if fingerprint()!=source:raise AssertionError('Runtime changed during capture')
            if hashlib.sha256((ROOT/binding['activity_manifest']).read_bytes()).hexdigest()!=binding['activity_manifest_sha256']:raise AssertionError('Manifest changed during capture')
            report={'actor_id':actor_id,'binding':binding,'method':'Game.update30Hz + real Game.draw native960x640; no NPC state overrides. Board crops align feet but preserve native pixels.',
                    'fixtures':['completed predecessor quests','player review stations','mill-restored flag added after genuine cover/rest' if actor_id.startswith('grain_') else 'mill restored'],
                    'extended':True,'reduced_motion':reduced,'runtime_sha256':source,'frames':rows,
                    'final_garden':garden.to_dict(),'final_wildlife':wildlife.to_dict(),
                    'final_grain':g.world.grain_farm.to_dict(),'final_bridge':g.world.bridge_crew.to_dict(),
                    'draw_ms':{'samples':len(draw_times),'median':sorted(draw_times)[len(draw_times)//2],'max':max(draw_times)},
                    'source_manifest_sha256':binding['activity_manifest_sha256']}
            (output/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
        finally:g.music.stop();pygame.quit()
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('actor',choices=[r for r in STATIONS if r.startswith(('grain_','bridge_'))]);parser.add_argument('output',type=Path)
    parser.add_argument('--reduced-motion',action='store_true')
    args=parser.parse_args();capture(args.actor,args.output,args.reduced_motion)
