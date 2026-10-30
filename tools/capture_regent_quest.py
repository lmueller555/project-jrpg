"""Capture MQ03 through real Game interactions, dialogue and actor staging.

Only completed MQ01/MQ02 prerequisites and the starting station are seeded.
Caelan walks the visit route, reads the adult dispute, welcomes the visitors and
hears the unresolved covenant discussion. No MQ03 facts are assigned directly.
The overview compresses travel but keeps every main dialogue page; a separate
close-up follows the released cart and its actual owner.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from pathlib import Path
import json
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image,ImageDraw,ImageFont
from main import Game
from npc_routines import find_path
from quests import OPENING_QUEST,MILL_QUEST,REGENT_QUEST
from npc_following import IDLE_RESET, TURN_INTERVAL
from tools.capture_mill_quest import save_gif
from tools.quest_capture_navigation import travel_to

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/reviews/regent_quest'


class Capture:
    def __init__(self):
        OUT.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='mq03-review-')
        self.g=Game(fullscreen=False,start_on_title=False,
                    save_path=Path(self.temp.name)/'journey.json',
                    settings_path=Path(self.temp.name)/'settings.json')
        self.g.audio.set_music(0);self.g.audio.set_effects(0)
        self.c=self.g.regent_quest
        self.frames=[];self.durations=[];self.cart=[];self.cart_durations=[]
        self.tick_index=0;self.label='Prepare to welcome Aldric'
        self.font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
        self.seen_pages=[];self.seen_contexts=[];self.saved_stills=set()
        self.room_transitions=[];self.dialogue_rooms={}
        self.simulation_seconds=0.;self.follow_frames=[];self.follow_durations=[]
        self.facing_runs={};self.facing_changes=[];self.facing_intervals=[]
        self._seed_previous_quests()

    def _seed_previous_quests(self):
        g=self.g
        assert g.accept_quest(OPENING_QUEST)
        for key in ('halden','elira','venn'):assert g.quests.complete_objective(OPENING_QUEST,key)
        g._sync_inventory();g.halden_visit.restore();g.elira_visit.restore();g.venn_visit.restore()
        assert g.quests.turn_in(OPENING_QUEST,'mother_serene')
        assert g.quests.unlock(MILL_QUEST)
        g.opening_conclusion.restore({'version':1,'stage':'done'})
        assert g.accept_quest(MILL_QUEST)
        for objective in g.quests.definitions[MILL_QUEST]['objectives']:
            assert g.quests.complete_objective(MILL_QUEST,objective['id'])
        assert g.quests.turn_in(MILL_QUEST,'mira_worker')
        g.mill_quest.restore({'version':1,'inspected':['mechanism','race','intake'],
                             'prepared':True,'spell_done':True,'encouraged':True,
                             'restored':True,'verified':True,'resolved':True})
        g.opening.restore({'version':1,'stage':'disabled'})
        if g.quests.status(REGENT_QUEST)=='locked':assert g.quests.unlock(REGENT_QUEST)
        self.c.restore(None)
        g.world=self.c.world_for_station('preparations')
        g.player.position.update(self.c.points['preparations'])
        g.player.facing='back';g.opening_fade=0;g.transfer_cooldown=0
        g.social.blocked.clear();g.quests.drain_events();g.quest_ui.reset();g.camera.reset()
        assert g.quests.status(REGENT_QUEST)=='available'
        assert self.c.stage=='idle'

    def game_image(self):
        self.g.draw();size=self.g.ui_surface.get_size()
        image=Image.frombytes('RGB',size,pygame.image.tobytes(self.g.ui_surface,'RGB'))
        return image.resize((480,320),Image.Resampling.NEAREST)

    def frame(self,duration=120):
        scene=self.game_image()
        out=Image.new('RGB',(480,344),'#e8edf2');out.paste(scene,(0,24))
        ImageDraw.Draw(out).text((9,4),self.label,font=self.font,fill='#243529')
        self.frames.append(out);self.durations.append(duration)

    def cart_frame(self,duration=100):
        actor=self.c.venn
        camera=(round(actor.position.x)-128,round(actor.position.y)-104);size=(256,184)
        canvas=pygame.Surface(size)
        self.g.town.draw(canvas,camera,self.g.player,self.g.elapsed_ms,include_ui=False)
        for visit in self.g.household_visits:visit.draw_world(canvas,camera)
        source=Image.frombytes('RGB',size,pygame.image.tobytes(canvas,'RGB'))
        out=Image.new('RGB',(512,408),'#e8edf2')
        out.paste(source.resize((512,368),Image.Resampling.NEAREST),(0,40))
        d=ImageDraw.Draw(out)
        d.text((10,4),'THE CART IS RELEASED',font=self.font,fill='#243529')
        d.text((10,22),'Mr. Venn takes back his cart; the road crew resumes',font=self.font,fill='#243529')
        self.cart.append(out);self.cart_durations.append(duration)

    def tick(self,seconds=1/30,direction=(0,0),record=True):
        before=self.c.stage
        self.g.update(seconds,direction,False);self.tick_index+=1
        self.simulation_seconds+=seconds
        if self.c.stage in ('met','escorting') and not self.g.social.locked:
            for actor in self.c.party:
                if self.c._world(actor) is not self.g.world:
                    self.facing_runs.pop(actor,None)
                    continue
                if not actor.moving:
                    run=self.facing_runs.get(actor)
                    if run is not None:
                        run['idle_seconds']+=seconds
                        if run['idle_seconds']+1e-9>=IDLE_RESET:self.facing_runs.pop(actor,None)
                    continue
                run=self.facing_runs.setdefault(actor,dict(facing=actor.facing,last_turn=None,
                    scene=self.g.world.data['id'],stage=self.c.stage,idle_seconds=0.))
                run['idle_seconds']=0.
                if (run['scene']!=self.g.world.data['id'] or run['stage']!=self.c.stage):
                    self.facing_runs.pop(actor,None)
                    continue
                if actor.facing!=run['facing']:
                    if run['last_turn'] is not None:
                        interval=self.simulation_seconds-run['last_turn']
                        self.facing_intervals.append(interval)
                        assert interval+1e-7>=TURN_INTERVAL,('Rapid follower facing',actor.data['id'],interval)
                    self.facing_changes.append(dict(actor=actor.data['id'],
                        time=round(self.simulation_seconds,6),previous=run['facing'],
                        facing=actor.facing,scene=self.g.world.data['id']))
                    run['facing']=actor.facing;run['last_turn']=self.simulation_seconds
            if (len(self.follow_frames)<200 and self.tick_index%3==0 and
                    any(actor.moving and self.c._world(actor) is self.g.world for actor in self.c.party)):
                image=self.game_image()
                out=Image.new('RGB',(480,344),'#e8edf2');out.paste(image,(0,24))
                ImageDraw.Draw(out).text((9,4),'Actual NPC following · stable facing at path corners',
                                        font=self.font,fill='#243529')
                self.follow_frames.append(out);self.follow_durations.append(100)
        else:self.facing_runs.clear()
        if record and self.tick_index%30==0:self.frame(120)
        if before=='releasing' or self.c.stage=='releasing':
            if self.tick_index%3==0:self.cart_frame(100)

    def wait(self,predicate,seconds=120):
        for _ in range(round(seconds*30)):
            if predicate():return
            self.tick()
        raise AssertionError(('Timeout',self.c.stage,self.g.social.script_identifier,
                              tuple(self.g.player.position),[(a.data['id'],tuple(a.position),self.c._world(a).data['id'],self.c.paths.get(a)) for a in self.c.party]))

    def walk(self,goal,seconds=180,next_scene=None):
        origin=self.g.world
        goal=pygame.Vector2(*(round(value/2)*2 for value in goal));route=[];stalled=0
        for _ in range(round(seconds*30)):
            if self.g.world is not origin:
                assert self.g.world.data['id']==next_scene
                return
            if self.g.player.position.distance_to(goal)<1.5:
                if next_scene is None:return
                door=next(d for d in origin.doors
                          if pygame.Vector2(d.data['anchor']).distance_to(goal)<3)
                self.tick(direction=(0,-1 if door.data['entry_side']=='north' else 1))
                continue
            # Auto-started scripted conversation is read in place before moving
            # on, preserving the controller's public stage callbacks.
            if self.g.social.active:
                if self.g.social.script_identifier in {'regent_'+kind for kind in ('preparations','arrival','dispute','welcome','discussion','aftermath')}:return
                self.read()
            if not route or stalled>=20:
                found=find_path(self.g.world,self.g.player.position,goal,self.g.world.probe_size,None)
                if found is None:raise AssertionError(('No route',tuple(self.g.player.position),tuple(goal),self.c.stage))
                route=list(found);stalled=0
            if not route:return
            delta=pygame.Vector2(route[0])-self.g.player.position
            if delta.length()<1.5:route.pop(0);continue
            before=self.g.player.position.copy()
            self.tick(min(1/30,delta.length()/72),delta)
            stalled=stalled+1 if self.g.player.position==before else 0
        raise AssertionError(('Walking stalled',tuple(self.g.player.position),tuple(goal),self.c.stage))

    def at(self,key):
        travel_to(self,self.c.world_for_station(key))
        point=pygame.Vector2(self.c.points[key])
        if key=='road':point+=(-20,52)  # Caelan observes beside the gathered adults.
        target=None
        for radius in (0,8,16,24):
            for offset in ((0,radius),(-radius,0),(radius,0),(0,-radius)):
                p=point+offset
                if self.g.world.can_stand(p):target=p;break
            if target is not None:break
        assert target is not None,('No clear station',key)
        self.walk(target);self.g.transfer_cooldown=0

    def save_still(self,name):
        self.g.draw();pygame.image.save(self.g.ui_surface,OUT/name)
        self.saved_stills.add(name)

    def read(self):
        count=0
        while self.g.social.active:
            count+=1;assert count<220,'Unfinished dialogue'
            identifier=self.g.social.script_identifier
            self.dialogue_rooms.setdefault(identifier,set()).add(self.g.world.data['id'])
            page=self.g.social.page
            speaker=page.get('speaker')
            text=page.get('text','') or ' '.join(page.get('lines',[]))
            # Settle ordinary facing and the camera without accepting prose.
            for _ in range(4):self.tick(record=False)
            self.frame(750)
            self.seen_pages.append((identifier,self.g.social.page_index,speaker))
            self.seen_contexts.append((identifier,self.c.stage))
            if identifier=='regent_preparations' and 'preparations.png' not in self.saved_stills:
                self.save_still('preparations.png')
            if identifier=='regent_arrival' and speaker=='aldric' and 'arrival.png' not in self.saved_stills:
                self.save_still('arrival.png')
            if identifier=='regent_dispute':
                if speaker=='venn_father' and 'dispute.png' not in self.saved_stills:self.save_still('dispute.png')
                if speaker=='aldric' and ('road account' in text or 'Return the cart' in text):self.save_still('ruling.png')
            if identifier=='regent_welcome' and ('welcome.png' not in self.saved_stills or 'laugh' in text.lower()):
                self.save_still('welcome.png')
            if identifier=='regent_discussion' and ('discussion.png' not in self.saved_stills or 'wearily' in text.lower()):
                self.save_still('discussion.png')
            if identifier=='regent_aftermath' and ('aftermath.png' not in self.saved_stills or 'So do I' in text):
                self.save_still('aftermath.png')
            self.g.social.advance()

    def interact(self,kind):
        if not self.g.social.active:assert self.c.interact(),('No interaction',kind,self.c.stage)
        assert self.g.social.script_identifier=='regent_'+kind,(self.g.social.script_identifier,kind,self.c.stage)
        self.read()

    def capture_handoff(self):
        """Read the next invitation from MQ03's actual completed state."""
        lantern=self.g.lantern_quest
        travel_to(self,lantern.invitation_world)
        self.walk(lantern.points['invitation'])
        self.wait(lambda:lantern._target()=='invitation')
        assert lantern.interact()
        pages=0;room=self.g.world.data['id']
        while self.g.social.active and self.g.social.script_identifier=='lantern_invitation':
            pages+=1;assert pages<100
            assert self.g.world is lantern.invitation_world
            assert lantern._world(lantern.tomas) is self.g.world
            assert lantern._world(lantern.serene) is self.g.world
            if self.g.social.page['speaker']=='serene' and 'lantern_handoff.png' not in self.saved_stills:
                self.save_still('lantern_handoff.png')
            self.g.social.advance()
            for _ in range(4):self.tick(record=False)
        assert lantern.stage=='invited'
        assert 'lantern_handoff.png' in self.saved_stills
        return dict(room=room,dialogue_pages=pages,stage=lantern.stage,
                    tomas_and_serene_present=True,prior_quest_still_complete=self.c.stage=='done')

    def run(self):
        self.frame(1000)
        self.wait(lambda:self.c._preps_ready)
        self.at('preparations');self.interact('preparations')
        assert self.c.stage=='assigned' and self.g.quests.status(REGENT_QUEST)=='active'
        self.label='Meet Aldric and his traveling party by the brook'
        self.at('arrival');self.interact('arrival')
        assert self.c.stage=='met'
        self.label='Accompany the visitors through the village'
        self.at('road');self.wait(lambda:self.c.stage=='dispute')
        self.label='Aldric hears the cart dispute; Caelan witnesses'
        self.wait(lambda:self.c._group_ready)
        self.interact('dispute')
        assert self.c.stage=='releasing'
        self.cart_frame(200)
        self.label='The agreement is honored and the cart is released'
        self.wait(lambda:self.c.stage=='escorting')
        self.cart_frame(700)
        assert self.cart,'No cart movement captured'
        self.label='Bring the visitors inside to the sanctuary dining room'
        self.at('courtyard');self.wait(lambda:self.c.stage=='welcome')
        self.label='A warm welcome and time to talk'
        self.wait(lambda:self.c._group_ready)
        self.interact('welcome');assert self.c.stage=='hosted'
        self.label='Aldric and Serene disagree about protected ground'
        self.wait(lambda:self.c._group_ready)
        self.interact('discussion');assert self.c.stage=='discussion'
        self.label='Caelan speaks with Serene after the visit'
        self.wait(lambda:getattr(self.c,'_aside_ready',True))
        self.at('aftermath');self.interact('aftermath')
        assert self.c.stage=='done' and self.g.quests.status(REGENT_QUEST)=='completed'
        assert self.g.mill_quest.mill_restored and not self.g.opening_conclusion.mill_stopped
        assert not any('AUTHORIZ' in flag.upper() or 'EXCAVATION_STARTED' in flag.upper() for flag in self.g.social.flags)
        assert self.g.quests.status('CH01_MQ04')=='available'
        self.wait(lambda:self.c._delivery_done)
        for _ in range(20):self.tick()
        assert pygame.Vector2(self.c.cart['position']).distance_to(self.c.points['cart_end'])<1
        assert self.g.town.can_stand(self.g.halden_visit.halden.position+(0,28))
        self.frame(1300)
        # Preserve every dialogue page and scene cut; compress only the travel
        # samples to keep this overview useful as a compact review artifact.
        frames=[];durations=[];walk_index=0
        for frame,duration in zip(self.frames,self.durations):
            if duration<300:
                walk_index+=1
                if walk_index%3!=1:continue
            frames.append(frame);durations.append(duration)
        expected={'regent_'+kind for kind in ('preparations','arrival','dispute','welcome','discussion','aftermath')}
        actual={identifier for identifier,_,_ in self.seen_pages if identifier and identifier.startswith('regent_')}
        optional=actual-expected
        assert expected<=actual,('Missing core visit dialogue',expected-actual)
        assert optional<={'regent_clerk_waiting'},('Unexpected optional visit dialogue',optional)
        assert all(stage in ('assigned','met','dispute') for identifier,stage in self.seen_contexts if identifier=='regent_clerk_waiting'),('Out-of-sequence clerk reminder',self.seen_contexts)
        for kind in ('preparations','arrival','dispute','welcome','discussion','aftermath'):
            expected_count=len(self.g.social._make_pages(self.c.lines[kind]))
            count=sum(identifier=='regent_'+kind for identifier,_,_ in self.seen_pages)
            assert count==expected_count,('Missing/repeated dialogue pages',kind,count,expected_count)
        overview=[frame.resize((320,229),Image.Resampling.NEAREST) for frame in frames]
        save_gif(OUT/'quest.gif',overview,durations,64)
        save_gif(OUT/'cart_release.gif',self.cart,self.cart_durations,128)
        assert self.follow_frames and self.facing_changes,'No actual following captured'
        assert self.facing_intervals,'No sustained turning sequence measured'
        save_gif(OUT/'following.gif',self.follow_frames,self.follow_durations,96)
        expected_interior={'regent_'+kind for kind in ('preparations','welcome','discussion','aftermath')}
        assert all(self.dialogue_rooms[key]=={'sanctuary_dining'} for key in expected_interior)
        assert any(t['origin']=='sanctuary_hall' and t['destination']=='sanctuary_dining'
                   for t in self.room_transitions)
        assert all(self.c._world(actor) is self.c.dining for actor in self.c.party)
        handoff=self.capture_handoff()
        (OUT/'capture.json').write_text(json.dumps({'quest_completed':True,'stage':self.c.stage,
            'quest_id':REGENT_QUEST,'dialogue_pages':len(self.seen_pages),'overview_frames':len(frames),
            'cart_frames':len(self.cart),'optional_dialogue':sorted(optional),'seeded':'completed MQ01/MQ02 prerequisites and starting station only',
            'excavation_authorized':False,'role':'guide and host; adults settle the dispute',
            'room_transitions':self.room_transitions,
            'dialogue_rooms':{k:sorted(v) for k,v in self.dialogue_rooms.items()},
            'mq04_available':True,'party_final_room':'sanctuary_dining',
            'mq04_handoff':handoff,
            'following':dict(frames=len(self.follow_frames),
                minimum_turn_interval=TURN_INTERVAL,
                observed_minimum_continuous_turn_interval=min(self.facing_intervals),
                measured_intervals=len(self.facing_intervals),
                facing_changes=self.facing_changes,
                measurement='Consecutive following turns including short stops, excluding idle >= 0.35s, dialogue and room transfers')},indent=2)+'\n')
        (OUT/'README.md').write_text(
            '# The Regent\'s Road — interior staging and following review\n\n'
            'The production Game is played from MQ03 availability to completion. Only completed '
            'MQ01/MQ02 prerequisites and the initial player station are seeded. All six main '
            'conversations, the cart release, player walking, NPC following and door transfers '
            'use the normal quest controllers. Temporary saves leave ordinary journeys untouched.\n\n'
            '- [Complete quest overview](quest.gif) — travel is compressed; every main dialogue page remains.\n'
            '- [Cart release](cart_release.gif) — Mr. Venn and his cart visibly depart.\n'
            '- [Actual NPC following](following.gif) — movement is sampled at ten frames per second.\n'
            '- [Preparations inside the dining room](preparations.png)\n'
            '- [Welcome and meal](welcome.png)\n'
            '- [Aldric and Serene\'s discussion](discussion.png)\n'
            '- [Private aftermath](aftermath.png)\n\n'
            '- [MQ04 invitation in the same dining room](lantern_handoff.png)\n\n'
            'The player walks from the dining room through the hall and courtyard to meet the '
            'visitors, then leads them back through the same doors. All local conversations and '
            'the visitors\' final stations are inside the sanctuary dining room. MQ04 becomes '
            'available normally; its invitation is then read with both Tomas and Serene present '
            'inside. The road dispute and unresolved excavation decision are preserved.\n\n'
            '`capture.json` records room transitions, dialogue locations and actual facing-change '
            'timestamps. Sustained follower turns respect the shared minimum turn interval; '
            'brief pauses remain in the measurement; scripted poses, dialogue, prolonged idle and '
            'room transfers are separate. '
            'The following clip uses ordinary collision-aware pathfinding, not direct actor movement.\n\n'
            'Reproduce with `python tools/capture_regent_quest.py`.\n',encoding='utf-8')
        print('Captured complete MQ03:',len(frames),'overview frames;',len(self.cart),'cart frames;',len(self.seen_pages),'dialogue pages')
        for name in ['quest.gif','cart_release.gif','following.gif']:print(name,(OUT/name).stat().st_size,'bytes')
        self.temp.cleanup()
        pygame.quit()


def capture():Capture().run()
if __name__=='__main__':capture()
