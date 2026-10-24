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

OUTPUT=ROOT/'docs/reviews/gardener_top_winch_bucket'
CAPTIONS={
    'rest':'Resting / next trip in 3-5 minutes',
    'pickup':'Pick up the empty pail',
    'to_well':'Follow the village lane to the well',
    'well_attach':'Raise her pail behind her torso / rope remains retracted',
    'well_hook':'Fasten her pail / only the short center hook is visible',
    'well_settle':'Pail snaps beneath the winch / one-pixel settling bounce',
    'well_to_crank':'Step to the crank / pail remains visible at the top',
    'well_grip':'Take hold of the crank',
    'well_lower':'Turn the crank / pail descends and rope lengthens',
    'well_fill':'Her pail fills in the shaft',
    'well_raise':'Reverse the crank / pail rises back into view',
    'well_lock':'Secure the visibly parked pail beneath the winch',
    'well_to_loading':'Return to the near side of the well',
    'well_catch':'Reach up / pail snaps from the winch behind her',
    'well_unhook':'Secure the concealed pail in both hands',
    'well_take':'Lower her pail into its carrying pose',
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
    game=main.Game(fullscreen=False,start_on_title=False);game.player.position.update(420,1100)
    actor=main.Gardener(game.town.npcs[1].data,game.town,random.Random(2026))
    game.town.npcs[1]=actor
    initial_rest=actor.rest_duration_ms
    game.update((initial_rest-1000)/1000,(0,0),False)
    route=[];well=[];watering=[];events=[];previous=None;finished=None;well_still=None;parked_still=None
    for i in range(1400):
        state=actor.state
        if state!=previous:
            events.append({'time_ms':round(game.elapsed_ms),'state':state,'position':list(actor.position),'water_units':actor.water_units})
            previous=state
        text=caption(actor)
        if i%2==0:
            route.append(panel(overview(game),1,'Gardener / full watering trip',
                               'Real-time trip | long rests omitted',text))
        near_loading=actor.position.distance_to(game.town.well.data['loading_position'])<44
        if state.startswith('well_') or (near_loading and state in ('to_well','return_to_sanctuary')):
            scene=render(game,(474,786)).crop((0,0,120,120))
            well.append(panel(scene,6,'Sanctuary gardener / drawing water',
                              '6x native pixels | actual game animation',text))
            if state=='well_unhook' and .35<=game.town.well.progress<=.55:well_still=well[-1]
            if state=='well_lock' and game.town.well.progress>=.5:parked_still=well[-1]
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
    parked_still.save(OUTPUT/'parked_bucket.png')
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
        'notes':'Travel and actions use real game timing. Most initial rest is omitted. Actor-owned phases show only a three-pixel hook beneath the windlass. On attachment the concealed pail snaps to a fully visible parked position below the winch, settles by one pixel, and then descends with the rope. It returns visibly to the same position before snapping behind her torso during retrieval. Watering montage cuts only between stops.'
    }
    (OUTPUT/'capture.json').write_text(json.dumps(metadata,indent=2)+'\n')
    pygame.quit()


if __name__=='__main__':capture()
