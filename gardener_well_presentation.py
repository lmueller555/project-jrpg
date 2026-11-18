"""Read-only phase adapter for the staged gardener performance.

It samples an external immutable mechanism snapshot. It never advances time,
changes ownership, decrements water, emits gameplay cues or alters a live actor.
"""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent
MANIFEST='assets/characters/npcs/female_02/gardener_well_hd/animations.json'


@lru_cache(maxsize=1)
def _bank():return json.loads((ROOT/MANIFEST).read_text())


def bank():
    """Return a defensive manifest copy; callers cannot change the shared bank."""
    return deepcopy(_bank())


@lru_cache(maxsize=192)
def _native_image(relative):
    with Image.open(ROOT/Path(MANIFEST).parent/relative) as raw:
        return raw.convert('RGBA')


def _image(relative):
    # Compositors receive copies so cached source pixels stay immutable.
    return _native_image(relative).copy()


def _read(state,key,default=None):
    return state.get(key,default) if isinstance(state,dict) else getattr(state,key,default)


def _selection(clip_name,index,water_units=0,pail_visible=False,angle=0,owner='actor'):
    data=_bank();clip=data['clips'][clip_name];index=max(0,min(len(clip['frames'])-1,index));name=clip['frames'][index];pose=data['poses'][name]
    pail=next(record for record in data['pails']['variants'] if record['angle']==angle and record['units']==water_units)
    return {'pose_id':name,'clip':clip_name,'frame_index':index,'body_file':pose['file'],
            'draw_anchor_logical':deepcopy(data['draw_anchor_logical']),'foot_anchor_logical':deepcopy(data['foot_anchor_logical']),
            'hand_grip_logical':deepcopy(pose['hand_grip_logical']),'pail_order':pose['pail_order'],
            'pail_visible':bool(pail_visible),'pail_owner':owner,'water_units':water_units,
            'pail':deepcopy(pail),'facing':pose['facing'],'crank_sample':index if clip_name in ('lower','raise') else None}


def select_pose(snapshot,facing=None):
    """Sample the external mechanism; phase owns facing at its fixed station.

    An optional facing is an assertion by the caller, not a direction override.
    Travel and lifecycle positioning belong to the future live actor adapter.
    """
    phase=_read(snapshot,'phase_id','await_loading');progress=max(0,min(1,float(_read(snapshot,'phase_progress',0))))
    crank_phase=float(_read(snapshot,'crank_phase',0))%1
    # Prefer the authoritative crank sample, including a stopped nonzero phase.
    sample=_read(snapshot,'crank_sample',None)
    sample=int(math.floor(crank_phase*16+1e-9))%16 if sample is None else int(sample)%16
    owner=_read(snapshot,'pail_owner','actor');units=max(0,min(6,int(_read(snapshot,'water_units',0))))
    if phase=='fill' and sample==14:
        result=_selection('brace',0,units,False,owner=owner)
    elif phase=='secure' and sample in (14,15,0):
        # Authored short brake grip fits the knob around this rest quadrant.
        # Other angles retain their matching whole-body operating drawing.
        result=_selection('brake',0,units,False,owner=owner)
    elif phase in ('guide_into_shaft','lower','fill','secure'):
        result=_selection('lower',sample,units,False,owner=owner)
    elif phase=='raise':result=_selection('raise',sample,units,False,owner=owner)
    elif phase=='engage':result=_selection('engage',min(2,int(progress*3)),units,False,owner=owner)
    elif phase in ('attach','detach'):
        cue=.7 if phase=='attach' else .65
        # Reach the real loading grip before transfer, hold it through the cue,
        # then recover. Reversing all keys would lower the hands before grasp.
        if progress < cue:
            index=min(3,int(progress/max(cue*.75,1e-9)*4))
        else:index=min(7,4+int((progress-cue)/max(1-cue,1e-9)*4))
        result=_selection('attach_back' if phase=='attach' else 'detach_back',index,units,owner=='actor',owner=owner)
    elif phase=='await_retrieval':result=_selection('attach_back',7,units,False,owner=owner)
    elif phase in ('await_loading','complete'):result=_selection('attach_back',0,units,owner=='actor',owner=owner)
    else:result=_selection('disengage',2,units,owner=='actor',owner=owner)
    if phase=='idle' or _read(snapshot,'pail_id',True) is None:
        # An unreserved mechanism has no personal prop to present. A cancelled
        # operation with its retained pail identity still follows its owner.
        result['pail_visible']=False
    if facing is not None and facing!=result['facing']:
        raise ValueError('Mechanism phase requires '+result['facing']+' facing')
    result.update(phase_id=phase,phase_progress=progress,crank_sample=sample,crank_phase=crank_phase)
    return result


def carry_pose(facing,walk_phase,water_units):
    """Sample normalized 0..1 walk phase; the retained full cycle is 560 ms."""
    if facing not in ('front','back','left','right'):raise ValueError('Unknown carrying direction')
    units=max(0,min(6,int(water_units)));mode='full' if units else 'empty'
    return _selection(f'carry_{mode}_{facing}',int((float(walk_phase)%1)*4),units,True)


def pour_pose(facing,raised,progress,water_units):
    if facing not in ('left','right'):raise ValueError('Pouring needs an authored side')
    progress=max(0,min(1,float(progress)));index=min(7,int(progress*8));clip=f'pour_{"trough" if raised else "ground"}_{facing}'
    # Pour direction follows the mouth normal, not the hanging mass. Positive
    # PIL rotation faces the upward opening left and lowers its left lip.
    tilt=(0,0,25,50,50,25,0,0)[index]*(1 if facing=='left' else -1)
    result=_selection(clip,index,max(0,min(6,int(water_units))),True,tilt)
    result.update(stream_visible=index in (3,4) and result['water_units']>0,pour_progress=progress,raised=bool(raised))
    return result


def pickup_pose(progress,water_units=0,depositing=False):
    progress=max(0,min(1,float(progress)));clip='setdown_left' if depositing else 'pickup_left'
    index=min(7,int(progress*8));held=(progress<.5) if depositing else (progress>=.5)
    result=_selection(clip,index,max(0,min(6,int(water_units))),held)
    ground_pose=_bank()['poses'][_bank()['clips']['pickup_left']['frames'][3]]
    result.update(station_pail_visible=not held,station_grip_logical=deepcopy(ground_pose['hand_grip_logical']),
                  depositing=bool(depositing),pickup_progress=progress)
    return result


def render_pose(selection,pour_target_logical=None):
    """Offline/native body and held pail composition; no world state mutation."""
    body=_image(selection['body_file'])
    canvas=Image.new('RGBA',body.size)
    pail=None;xy=None
    if selection['pail_visible']:
        pail=_image(selection['pail']['file'])
        grip=selection['hand_grip_logical'];anchor=selection['pail']['grip_logical']
        xy=tuple(round(2*(grip[i]-anchor[i])) for i in (0,1))
    if pail is not None and selection['pail_order']=='before':canvas.alpha_composite(pail,xy)
    canvas.alpha_composite(body)
    if pail is not None and selection['pail_order']=='after':canvas.alpha_composite(pail,xy)
    if selection.get('station_pail_visible'):
        station=_image(selection['pail']['file'])
        anchor=selection['pail']['grip_logical'];grip=selection['station_grip_logical']
        canvas.alpha_composite(station,tuple(round(2*(grip[i]-anchor[i])) for i in (0,1)))
    if selection.get('stream_visible') and xy is not None:
        origin=selection['pail']['stream_origin_logical']
        start=(xy[0]+round(origin[0]*2),xy[1]+round(origin[1]*2))
        side=-1 if selection['facing']=='left' else 1
        target=pour_target_logical or [selection['hand_grip_logical'][0]+side*9,31 if selection['raised'] else 42]
        end=tuple(round(v*2) for v in target);middle=((start[0]+end[0])//2,(start[1]+end[1])//2-2)
        draw=ImageDraw.Draw(canvas);draw.line([start,middle,end],fill='#598e9f',width=2)
        draw.line([(start[0]+1,start[1]),(middle[0]+1,middle[1]),(end[0]+1,end[1])],fill='#b9d9d2',width=1)
    return canvas
