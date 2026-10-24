"""Real runtime capture: new well draw, complete dry route, all six targets."""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import json
import random
import sys
from pathlib import Path
from PIL import Image
import pygame

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import main
from capture_gardener import gif, panel, render

OUTPUT=ROOT/'docs/reviews/gardener_well'
CAPTIONS={
    'rest':'Resting / next trip in 3-5 minutes',
    'pickup':'Pick up the empty pail',
    'to_well':'Follow the village lane to the well',
    'well_setdown':'Set the empty pail beside the well',
    'well_to_crank':'Step up to the crank',
    'well_grip':'Take hold of the crank',
    'well_lower':'Turn the crank / lower the well bucket',
    'well_fill':'Dip and fill the well bucket',
    'well_raise':'Reverse the crank / lift the full bucket',
    'well_lock':'Secure the windlass',
    'well_to_pour':'Step around to the waiting pail',
    'well_guide':'Guide the bucket clear of the rim',
    'well_pour':'Pour into the portable pail',
    'well_back_to_crank':'Return to the windlass',
    'well_reset':'Guide back and park the empty bucket',
    'well_back_to_pail':'Return to the full pail',
    'well_pickup':'Lift the full pail',
    'return_to_sanctuary':'Carry water up the sanctuary stairs',
    'return_to_rest':'Return with the empty pail',
    'setdown':'Set down the empty pail and rest'
}


def caption(actor):
    if actor.state in CAPTIONS:return CAPTIONS[actor.state]
    step=actor.steps[actor.step_index];bed=step.get('bed',{})
    name=bed.get('label',bed.get('id','flowers').replace('_',' '))
    if actor.state.startswith('water_'):return f'Water {name}'
    if actor.state.startswith('inspect_'):return f'Inspect {name}'
    return 'Walk to the next watering spot'


def overview(game):
    image=Image.new('RGB',(384,696))
    for y in (0,320,640):
        frame=render(game,(240,240+y))
        image.paste(frame.crop((0,0,384,min(320,696-y))),(0,y))
    return image


def capture():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    game=main.Game();game.player.position.update(480,924)
    actor=main.Gardener(game.town.npcs[1].data,game.town,random.Random(2026))
    game.town.npcs[1]=actor
    initial_rest=actor.rest_duration_ms
    game.update((initial_rest-1000)/1000,(0,0),False)
    route=[];well=[];watering=[];events=[];previous=None;finished=None;well_still=None
    for i in range(1400):
        state=actor.state
        if state!=previous:
            events.append({'time_ms':round(game.elapsed_ms),'state':state,'position':list(actor.position),'water_units':actor.water_units})
            previous=state
        text=caption(actor)
        if i%2==0:
            route.append(panel(overview(game),1,'Gardener / full watering trip',
                               'Real-time trip | long rests omitted',text))
        if state.startswith('well_'):
            scene=render(game,(474,786)).crop((0,0,120,120))
            well.append(panel(scene,6,'Sanctuary gardener / drawing water',
                              '6x native pixels | actual game animation',text))
            if state=='well_pour' and .4<=game.town.well.progress<=.6:well_still=well[-1]
        if state.startswith(('inspect_','water_')):
            camera=(round(actor.position.x)-60,round(actor.position.y)-54)
            scene=render(game,camera).crop((0,0,120,80))
            watering.append(panel(scene,6,'Sanctuary gardener / watering',
                                  '6x native pixels | four flower patches and both window troughs',text))
        if actor.completed_cycles and finished is None:finished=game.elapsed_ms
        if finished is not None and game.elapsed_ms-finished>=1000:break
        game.update(.1,(0,0),False)
        if i%150==0:print(f'Captured {i/10:.0f}s: {state}',flush=True)
    if not actor.completed_cycles:raise RuntimeError(f'Trip stalled at {state}')
    well_still.save(OUTPUT/'well_drawing.png')
    watering[-20].save(OUTPUT/'watering.png')
    route[-8].save(OUTPUT/'full_routine.png')
    gif(OUTPUT/'well_drawing.gif',well)
    gif(OUTPUT/'watering.gif',watering)
    gif(OUTPUT/'full_routine.gif',route,200)
    metadata={
        'status':actor.behavior['status'],'initial_rest_duration_ms':initial_rest,
        'next_rest_duration_ms':actor.rest_duration_ms,
        'rest_range_ms':actor.behavior['rest_range_ms'],
        'active_trip_ms':round(finished-initial_rest),
        'well_excerpt_ms':len(well)*100,
        'watered_beds':actor.watered_beds,'remaining_water_units':actor.water_units,
        'events':events,'well_interval_ms':100,'route_interval_ms':200,
        'notes':'Travel and actions use real game timing. Most initial rest is omitted. Watering montage cuts only between stops.'
    }
    (OUTPUT/'capture.json').write_text(json.dumps(metadata,indent=2)+'\n')
    pygame.quit()


if __name__=='__main__':capture()
