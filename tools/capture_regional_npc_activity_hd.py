"""Capture real controller activity joins at native gameplay scale.

Only prerequisite flags and player review positions are fixtures. NPC feet,
pose, facing, frame selection, transfers and props remain production-controlled.
--extended follows the blue gardener through genuine care dialogue, physical
plant relocation, borrowed sheep-care work and automatic return. No NPC state
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
STATIONS={'grain_loader':(-776,250),'grain_coworker':(-776,250),
          'bridge_mason':(-2340,644),'bridge_tender':(-2340,644),
          'regional_gardener':(-508,1206),'regional_picker':(-135,-230)}
CORE=('regional_npc_art.py','regional_npc_activity.py','grain_farm.py','garden_orchard.py','npc_roster_art.py')
def fingerprint():return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in CORE}
def capture(actor_id,output,extended=False,reduced=False):
    if extended and actor_id!='regional_gardener':raise ValueError('Extended route is the blue gardener only')
    output.mkdir(parents=True,exist_ok=True)
    rows=[];crops=[];seen=set();draw_times=[];source=fingerprint();mode='work';done_ticks=0
    with tempfile.TemporaryDirectory(prefix='regional-native-activity-') as temp:
        p=Path(temp)
        g=Game(fullscreen=False,window_size=(960,640),start_on_title=True,
               save_path=p/'journey.json',settings_path=p/'settings.json')
        try:
            g.on_title=False;g.opening.restore({'version':1,'stage':'disabled'})
            g.opening_fade=g.transfer_cooldown=0
            seed_previous_quests(g);g.social.flags.add('CH01_MQ02_MILL_RESTORED')
            g.audio.set_reduced_motion(reduced)
            g.world=g.overworld_world;g.player.position.update(STATIONS[actor_id]);g.camera.reset()
            controllers=(g.world.grain_farm,g.world.bridge_crew,g.world.garden_orchard)
            actor=next(a for c in controllers for a in c.actors if a.data['id']==actor_id)
            binding=actor_binding(actor_id)
            if not binding or not binding['activation']['activity']:raise ValueError('Native activity not explicitly active')
            for tick in range(20000 if extended else 6600):
                if mode=='wildlife':
                    if actor.position.y>1360:g.player.position.update(-280,1458)
                    else:
                        for offset in ((60,40),(-60,40),(60,-40),(-60,-40),(0,60),(0,-60)):
                            if g.world.can_stand(actor.position+offset):
                                g.player.position.update(actor.position+offset);break
                        else:raise AssertionError('No safe player review landing')
                g.update(1/30,(0,0),False)
                garden=g.world.garden_orchard;wildlife=g.world.wildlife
                key=actor.animation_key if hasattr(actor,'clips') else ((actor.native_action_key if not getattr(actor,'wildlife_owned',False) else None) or actor.pose)+'_'+actor.facing
                index=actor.frame_index if hasattr(actor,'clips') else None
                stage=(g.world.grain_farm.stage if actor_id.startswith('grain_') else
                       g.world.bridge_crew.stage if actor_id.startswith('bridge_') else
                       str(wildlife.vignette['step']) if mode=='wildlife' else str(garden.state[actor.role]['step']))
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
                                 'legacy_attachment':actor.attachment if hasattr(actor,'clips') else None,
                                 'portable_positions':{k:[list(point),z] for k,(point,z) in garden.portable_positions().items()} if actor_id.startswith('regional_') else None,
                                 'wildlife_basket':list(wildlife.basket_position()),'wildlife_owned':getattr(actor,'wildlife_owned',False),
                                 'controller_stage':stage})
                finished=(g.world.grain_farm.stage=='ready' and tick>600 if actor_id.startswith('grain_') else
                          g.world.bridge_crew.stage=='ready' and tick>600 if actor_id.startswith('bridge_') else
                          garden.state[actor.role]['phase']!='work')
                if extended:
                    if mode=='work' and garden.state['gardener']['phase']=='ready':
                        g.player.position.update(-526,1204)
                        if not g.overworld_travel.interact():raise AssertionError('Care dialogue did not start')
                        if g.social.script_identifier!='garden_quiet_care':raise AssertionError('Wrong dialogue')
                        while g.social.active:g.social.advance()
                        mode='care'
                    elif mode=='care' and garden.state['gardener']['phase']=='rest':
                        mode='wildlife';g.player.position.update(-570,1206)
                    finished=mode=='wildlife' and wildlife.vignette['phase']=='done'
                done_ticks=done_ticks+1 if finished else 0
                if done_ticks>=20:break
            else:raise AssertionError('Production activity did not complete')
            if not rows:raise AssertionError('No real rendered activity')
            board=Image.new('RGB',(640,36+((len(crops)+4)//5)*144),'#dfe5da');draw=ImageDraw.Draw(board)
            draw.text((8,8),'ACTUAL GAME CROPS / NATIVE2x / FEET ALIGNED FOR SCALE COMPARISON',fill='#20382b')
            for i,(label,im) in enumerate(crops):
                x=i%5*128;y=i//5*144+32;board.paste(im,(x,y));draw.text((x+2,y+114),label[:22],fill='#20382b')
            board.save(output/'actual_transition_board.png')
            if fingerprint()!=source:raise AssertionError('Runtime changed during capture')
            if hashlib.sha256((ROOT/binding['activity_manifest']).read_bytes()).hexdigest()!=binding['activity_manifest_sha256']:raise AssertionError('Manifest changed during capture')
            report={'actor_id':actor_id,'binding':binding,'method':'Game.update30Hz + real Game.draw native960x640; no NPC state overrides. Board crops align feet but preserve native pixels.',
                    'fixtures':['completed predecessor quests','mill restored','player review station / safe following positions' if extended else 'player review station'],
                    'extended':extended,'reduced_motion':reduced,'runtime_sha256':source,'frames':rows,
                    'final_garden':garden.to_dict(),'final_wildlife':wildlife.to_dict(),
                    'final_grain':g.world.grain_farm.to_dict(),'final_bridge':g.world.bridge_crew.to_dict(),
                    'draw_ms':{'samples':len(draw_times),'median':sorted(draw_times)[len(draw_times)//2],'max':max(draw_times)},
                    'source_manifest_sha256':binding['activity_manifest_sha256']}
            (output/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
        finally:g.music.stop();pygame.quit()
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('actor',choices=STATIONS);parser.add_argument('output',type=Path)
    parser.add_argument('--extended',action='store_true');parser.add_argument('--reduced-motion',action='store_true')
    args=parser.parse_args();capture(args.actor,args.output,args.extended,args.reduced_motion)
