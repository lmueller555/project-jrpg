"""Offline native performance review driven by the actual staged well model.

This does not select the new gardener in Game. Station travel is an explicit
authoring fixture with retained compatibility gait, not a navigation playtest.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import gardener_well_presentation as actor_art
from well_mechanism import WellMechanism
from well_mechanism_presentation import WellMechanismPresentation

DEFAULT=ROOT/'docs/reviews/gardener_well_hd'


def digest(raw):return sha256(raw).hexdigest()
def document(value):return (json.dumps(value,indent=2)+'\n').encode()


def board(image,title,subtitle=''):
    out=Image.new('RGB',(max(520,image.width),image.height+60),'#213c35')
    out.paste(image,(0,60),image if image.mode=='RGBA' else None)
    draw=ImageDraw.Draw(out);draw.text((10,10),title,fill='#f1e6c8');draw.text((10,31),subtitle,fill='#b9cfbd')
    return out


def scene(renderer,state,selection,position,elapsed):
    canvas=Image.new('RGBA',(320,256),'#213c35')
    canvas.alpha_composite(renderer.render(state,ambient_ms=elapsed),(24,40))
    body=actor_art.render_pose(selection)
    xy=(round(2*(position[0]-24-480)),round(2*(position[1]-36-780)))
    canvas.alpha_composite(body,xy)
    return canvas.convert('RGB')


def capture(folder=DEFAULT):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    old=json.loads((ROOT/'docs/reviews/eldenmere_well_pack/production_before.json').read_text())
    # Rebase the read-only proof on this checkout, rather than freezing runtime
    # bytes to PR1 forever. The historical pack supplies the protected path set.
    from tools.capture_eldenmere_settlement_framework import production_snapshot
    baseline_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    production_before=production_snapshot()
    protected_before={path:digest((ROOT/path).read_bytes()) for path in sorted(old['protected_files'])}
    contract_path=ROOT/'assets/source/terrain/eldenmere/well_hd/mechanism/contract.json'
    reference=ROOT/'assets/source/characters/npcs/female_02/gardener_well_hd/mechanism_reference.json'
    assert reference.read_bytes()==contract_path.read_bytes()
    town=json.loads((ROOT/'assets/maps/eldenmere/playable/map.json').read_text())
    with Image.open(ROOT/town['collision']) as raw:collision=raw.convert('L')
    routine=json.loads((ROOT/'assets/maps/eldenmere/routines/gardener.json').read_text())
    def clear_probe(position,size):
        x,y=round(position[0])-size[0]//2,round(position[1])-size[1]//2
        return collision.crop((x,y,x+size[0],y+size[1])).getbbox() is None
    renderer=WellMechanismPresentation(root=ROOT);model=WellMechanism(contract_path)
    token=model.reserve('offline.gardener','canonical.gardener.pail')
    loading=[528.,894.];operator=[564.,866.];position=loading.copy();route=[];travel_phase=None;walk_ms=0.;samples=[];frames=[]
    complete_at=None
    for tick in range(900):
        elapsed=tick*50;state=model.snapshot().to_dict();phase=state['phase_id']
        if phase=='await_loading' and elapsed>=250:model.signal_ready(token,'loading')
        if phase in ('await_operator','await_retrieval'):
            if travel_phase!=phase:
                route=[[564.,894.],operator.copy()] if phase=='await_operator' else [[564.,894.],loading.copy()]
                travel_phase=phase
            budget=3.
            while route and budget>1e-9:
                target=route[0];distance=math.dist(position,target);step=min(distance,budget)
                if distance:position=[position[i]+(target[i]-position[i])*step/distance for i in (0,1)]
                budget-=step;walk_ms+=step/60*1000
                if distance<=step+1e-9:position=route.pop(0)
            if not route:model.signal_ready(token,'operator' if phase=='await_operator' else 'loading')
        state=model.snapshot().to_dict();phase=state['phase_id']
        for size in (routine['probe_size'],town['player_probe_size']):
            assert clear_probe(position,size),('Offline route intersects static collision',position,size)
        if phase in ('await_operator','await_retrieval') and route:
            target=route[0];dx,dy=target[0]-position[0],target[1]-position[1]
            facing=('right' if dx>0 else 'left') if abs(dx)>abs(dy) else ('front' if dy>0 else 'back')
            # The well still owns the bucket. Choose unladen compatibility
            # body art while preserving the authoritative water metadata.
            selection=actor_art.carry_pose(facing,(walk_ms%560)/560,0);selection['pail_visible']=False
            selection['water_units']=state['water_units']
            selection['pail_owner']=state['pail_owner']
        else:selection=actor_art.select_pose(state)
        rendered=scene(renderer,state,selection,position,elapsed)
        picture=board(rendered,'OFFLINE MODEL-DRIVEN GARDENER PERFORMANCE',f'{phase} | owner: {state["pail_owner"]} | water: {state["water_units"]}/6')
        frames.append(picture)
        samples.append({'preview_ms':elapsed,'state':state,'actor_position_world':position.copy(),
                        'pose_id':selection['pose_id'],'events':[event.to_dict() for event in model.drain_events()]})
        if phase=='complete':
            if complete_at is None:complete_at=elapsed
            if elapsed-complete_at>=750:break
        model.update(.05)
    if complete_at is None:raise AssertionError('Offline operation did not complete')
    frames[0].save(folder/'joint_operation.gif',save_all=True,append_images=frames[1:],duration=50,loop=0,disposal=2,optimize=False)
    frames[0].save(folder/'joint_operation_slow.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,disposal=2,optimize=False)
    # Numbered motion and contact sheets use the actual controller trace.
    contact_metrics=[]
    for family in ('lower','raise'):
        sheet=Image.new('RGB',(4*320,4*290),'#213c35')
        for k in range(16):
            item=next(s for s in samples if s['state']['phase_id']==family and s['state']['crank_sample']==k)
            selected=actor_art.select_pose(item['state']);im=scene(renderer,item['state'],selected,operator,item['preview_ms'])
            at=((k%4)*320,(k//4)*290);sheet.paste(im,(at[0],at[1]+30));ImageDraw.Draw(sheet).text((at[0]+5,at[1]+6),f'{k}: {selected["pose_id"]}',fill='white')
            pose=actor_art.bank()['poses'][selected['pose_id']]
            contact_metrics.append({'family':family,'sample':k,'pose_id':selected['pose_id'],
                                    'actual_hand_grip_logical':pose['hand_grip_logical'],
                                    'target':pose['contact_target_logical'],'gap_logical':pose['contact_gap_logical']})
        sheet.save(folder/(family+'_numbered.png'))
        # A whole actual phase in trace order preserves direction and timing.
        # Numbered sheets are index references, not chronological animation.
        phase_items=[s for s in samples if s['state']['phase_id']==family]
        loop=[board(scene(renderer,s['state'],actor_art.select_pose(s['state']),operator,s['preview_ms']),
                    f'{family}: actual model sample {s["state"]["crank_sample"]}',
                    'Chronological phase; repeats the operation phase at loop boundary.') for s in phase_items]
        loop[0].save(folder/(family+'_loop.gif'),save_all=True,append_images=loop[1:],duration=50,loop=0,disposal=2,optimize=False)
        loop[0].save(folder/(family+'_loop_slow.gif'),save_all=True,append_images=loop[1:],duration=100,loop=0,disposal=2,optimize=False)
    cue_panels=[]
    for phase,cue in (('attach',.7),('detach',.65)):
        items=[s for s in samples if s['state']['phase_id']==phase]
        for label,item in (('before',max((s for s in items if s['state']['phase_progress']<cue),key=lambda s:s['state']['phase_progress'])),
                           ('after',min((s for s in items if s['state']['phase_progress']>=cue),key=lambda s:s['state']['phase_progress']))):
            selected=actor_art.select_pose(item['state']);im=scene(renderer,item['state'],selected,loading,item['preview_ms'])
            cue_panels.append(board(im,phase+' '+label+' ownership cue',f'owner:{item["state"]["pail_owner"]}, grip:{selected["hand_grip_logical"]}'))
    cue_sheet=Image.new('RGB',(1040,632),'#213c35')
    for k,im in enumerate(cue_panels):cue_sheet.paste(im,((k%2)*520,(k//2)*316))
    cue_sheet.save(folder/'handoff_cues.png')
    # Whole-task bindings remain visible independently of future live routing.
    carry=Image.new('RGB',(8*144,228),'#213c35')
    for n,(facing,units) in enumerate((f,u) for f in ('front','back','left','right') for u in (0,6)):
        selected=actor_art.carry_pose(facing,0,units);im=actor_art.render_pose(selected).resize((144,144),Image.Resampling.NEAREST);carry.paste(im,(n*144,40),im);ImageDraw.Draw(carry).text((n*144+5,10),f'{facing} {units}/6',fill='white')
    carry.save(folder/'directional_carry.png')
    pour=Image.new('RGB',(8*144,4*174),'#213c35')
    for row,(facing,raised) in enumerate((f,r) for r in (False,True) for f in ('left','right')):
        for k in range(8):
            selected=actor_art.pour_pose(facing,raised,(k+.1)/8,6);im=actor_art.render_pose(selected).resize((144,144),Image.Resampling.NEAREST);pour.paste(im,(k*144,row*174+28),im)
        ImageDraw.Draw(pour).text((8,row*174+7),f'{facing} '+('raised trough' if raised else 'ground bed'),fill='white')
    pour.save(folder/'pour_bindings.png')
    pickup=Image.new('RGB',(8*144,2*174),'#213c35')
    for row,deposit in enumerate((False,True)):
        for k in range(8):
            selected=actor_art.pickup_pose((k+.1)/8,0,deposit);im=actor_art.render_pose(selected).resize((144,144),Image.Resampling.NEAREST);pickup.paste(im,(k*144,row*174+28),im)
        ImageDraw.Draw(pickup).text((8,row*174+7),'setdown' if deposit else 'pickup',fill='white')
    pickup.save(folder/'pickup_setdown.png')
    manifest=ROOT/actor_art.MANIFEST
    production_after=production_snapshot()
    protected_after={path:digest((ROOT/path).read_bytes()) for path in protected_before}
    assert production_after==production_before,'Capture changed active production files'
    assert protected_after==protected_before,'Capture changed protected source/runtime files'
    historical_changed=[path for path,value in old['protected_files'].items()
                        if protected_before[path]!=(value['sha256'] if isinstance(value,dict) else value)]
    report={'scope':'Offline actual-model-driven native 2x character performance; not live Game selection/navigation or gameplay acceptance.',
            'revision':baseline_revision,
            'contract_sha256':digest(contract_path.read_bytes()),'manifest_sha256':digest(manifest.read_bytes()),
            'adapter_sha256':digest((ROOT/'gardener_well_presentation.py').read_bytes()),
            'runtime_activation':False,'capture_active_and_protected_files_unchanged':True,
            'preservation':{
                'baseline_revision':baseline_revision,
                'active_file_count':production_before['active_file_count'],
                'protected_file_count':len(protected_before),
                'unique_file_count':len(set(production_before['active_files'])|set(protected_before)),
                'production_before_sha256':digest(document(production_before)),
                'production_after_sha256':digest(document(production_after)),
                'protected_before_sha256':digest(document(protected_before)),
                'protected_after_sha256':digest(document(protected_after)),
                'baseline_production':production_before,'baseline_protected_files':protected_before,
                'historical_reference':{
                    'revision':old['revision'],
                    'production_matches':production_before==old['production'],
                    'protected_paths_changed_since_reference':sorted(historical_changed),
                    'scope':'Historical comparison only; legitimate later main changes are not capture mutations.'}},
            'positions':{'loading':loading,'operator':operator},'step_ms':50,'operation_duration_ms':complete_at,
            'offline_route':{'waypoints_world':[loading,[564.,894.],operator],
                             'reverse_for_retrieval':True,'speed':60,
                             'static_collision_sha256':digest((ROOT/town['collision']).read_bytes()),
                             'probe_sizes_checked':[routine['probe_size'],town['player_probe_size']],
                             'all_sample_probes_clear':True,
                             'scope':'Synthetic offline route; unchanged static collision only, not live NPC navigation.'},
            'contact_measurement':'Distance from actual distal hand/finger contact pixels to the projected knob; not an exact palm-center claim.',
            'visual_review':{
                'status':'Staged review; user approval pending and live integration deferred.',
                'identity':'Chestnut bob, sage clothing, dark belt/boots retained. Raising uses a wider three-quarter head and exertion silhouette than profile lowering/support; accepted for staged review, not an exact silhouette match.',
                'support':'Stationary support varies by at most one artwork pixel in lowering; raising support is fixed. Distinct brace holds the actual nonzero fill sample14; brake uses the near-rest quadrant during secure return.',
                'contact':'All32 operating contact gaps are below4logical units. Small gaps remain visible; no anatomy stretching or exact-contact claim.',
                'handoff':'Back pail is mostly torso-occluded; both cue sides use the same[24,16]logical grip without a location jump.',
                'layers':'Offline whole-well then actor composition only. PR4 must validate actual runtime split layers, dynamic blockers, interruption and save restoration.'},
            'contacts':contact_metrics,'compatibility_travel':'Existing four-frame complete travel bodies; 560ms cycle unchanged.',
            'samples':samples,'review_sha256':{p.name:digest(p.read_bytes()) for p in sorted(folder.iterdir()) if p.suffix in ('.png','.gif')}}
    (folder/'observations.json').write_bytes(document(report))
    print('Gardener performance review:',len(samples),'actual model samples;',len(contact_metrics),'working contacts.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',nargs='?',type=Path,default=DEFAULT);args=parser.parse_args();capture(args.output)
