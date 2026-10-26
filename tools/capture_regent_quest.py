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
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image,ImageDraw,ImageFont
from main import Game
from npc_routines import find_path
from quests import OPENING_QUEST,MILL_QUEST,REGENT_QUEST
from capture_mill_quest import save_gif

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/reviews/regent_quest'


class Capture:
    def __init__(self):
        OUT.mkdir(parents=True,exist_ok=True)
        self.g=Game(fullscreen=False,start_on_title=False,save_path=None)
        self.g.audio.set_music(0);self.g.audio.set_effects(0)
        self.c=self.g.regent_quest
        self.frames=[];self.durations=[];self.cart=[];self.cart_durations=[]
        self.tick_index=0;self.label='Prepare to welcome Aldric'
        self.font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
        self.seen_pages=[];self.seen_contexts=[];self.saved_stills=set()
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
        g.world=g.town;g.player.position.update(self.c.points['preparations'])
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
        if record and self.tick_index%30==0:self.frame(120)
        if before=='releasing' or self.c.stage=='releasing':
            if self.tick_index%3==0:self.cart_frame(100)

    def wait(self,predicate,seconds=120):
        for _ in range(round(seconds*30)):
            if predicate():return
            self.tick()
        raise AssertionError(('Timeout',self.c.stage,self.g.social.script_identifier,
                              tuple(self.g.player.position),[(a.data['id'],tuple(a.position),self.c._world(a).data['id'],self.c.paths.get(a)) for a in self.c.party]))

    def walk(self,goal,seconds=120):
        goal=pygame.Vector2(goal);route=[];stalled=0
        for _ in range(round(seconds*30)):
            if self.g.player.position.distance_to(goal)<1.5:return
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
        self.label='Bring the visitors to the sanctuary courtyard'
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
        assert 'CH01_MQ04' not in self.g.quests.definitions
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
        (OUT/'capture.json').write_text(json.dumps({'quest_completed':True,'stage':self.c.stage,
            'quest_id':REGENT_QUEST,'dialogue_pages':len(self.seen_pages),'overview_frames':len(frames),
            'cart_frames':len(self.cart),'optional_dialogue':sorted(optional),'seeded':'completed MQ01/MQ02 prerequisites and starting station only',
            'excavation_authorized':False,'role':'guide and host; adults settle the dispute'},indent=2)+'\n')
        print('Captured complete MQ03:',len(frames),'overview frames;',len(self.cart),'cart frames;',len(self.seen_pages),'dialogue pages')
        for name in ['quest.gif','cart_release.gif']:print(name,(OUT/name).stat().st_size,'bytes')
        pygame.quit()


def capture():Capture().run()
if __name__=='__main__':capture()
