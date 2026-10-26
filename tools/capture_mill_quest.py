"""Review MQ02 using the production Game, interactions, walking and scene links.

Only completed MQ01 prerequisites and the starting station are seeded. MQ02
progress comes from dialogue callbacks and the real action/controller clocks.
Walking is sampled sparsely in the overview; the spell close-up is sampled at
15 fps. Review captions are outside the rendered game scene.
"""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from pathlib import Path
import bisect
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from PIL import Image, ImageDraw, ImageFont
from main import Game
from npc_routines import find_path
from quests import OPENING_QUEST, MILL_QUEST

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/reviews/mill_quest'


def save_gif(path,frames,durations,colors=128):
    """Use one palette, then verify every decoded image and cumulative duration."""
    assert frames and len(frames)==len(durations)
    # Downsample only the palette contact sheet, never the published frames.
    thumb=(max(1,frames[0].width//3),max(1,frames[0].height//3))
    contact=Image.new('RGB',(thumb[0]*len(frames),thumb[1]))
    for i,frame in enumerate(frames):
        contact.paste(frame.resize(thumb,Image.Resampling.NEAREST),(i*thumb[0],0))
    palette=contact.quantize(colors=colors)
    indexed=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(path,save_all=True,append_images=indexed[1:],duration=durations,
                    loop=0,disposal=1,optimize=False)
    starts=[];elapsed=0
    for duration in durations:starts.append(elapsed);elapsed+=duration
    with Image.open(path) as gif:
        decoded=0
        for i in range(gif.n_frames):
            gif.seek(i);source=bisect.bisect_right(starts,decoded)-1
            assert gif.convert('RGB').tobytes()==indexed[source].convert('RGB').tobytes(),(path,i,source)
            decoded+=gif.info['duration']
        assert decoded==elapsed,(decoded,elapsed)


class Capture:
    def __init__(self):
        OUT.mkdir(parents=True,exist_ok=True)
        self.g=Game(fullscreen=False,start_on_title=False,save_path=None)
        self.g.audio.set_music(0);self.g.audio.set_effects(0)
        self.c=self.g.mill_quest
        self.frames=[];self.durations=[];self.close=[];self.close_durations=[]
        self.tick_index=0;self.label='Mira at her workbench';self.repair_still=False
        self.font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
        self._seed_handoff()

    def _seed_handoff(self):
        g=self.g
        assert g.accept_quest(OPENING_QUEST)
        for key in ('halden','elira','venn'):assert g.quests.complete_objective(OPENING_QUEST,key)
        g._sync_inventory();g.halden_visit.restore();g.elira_visit.restore();g.venn_visit.restore()
        # The earlier optional failure has already happened in this review run.
        g.venn_visit.method='magicks';g.venn_visit.magicks_failed=True
        g.social.flags.add('CH01_MQ01_VENN_MAGICKS_FAILED')
        assert g.quests.turn_in(OPENING_QUEST,'mother_serene')
        assert g.quests.unlock(MILL_QUEST)
        g.opening_conclusion.restore({'version':1,'stage':'done'})
        g.opening.restore({'version':1,'stage':'disabled'})
        g.opening_fade=0;g.transfer_cooldown=0;g.social.blocked.clear()
        g.world=g.town;g.player.position.update(610,480);g.player.facing='back'
        g.quests.drain_events();g.quest_ui.reset();g.camera.reset()

    def game_image(self):
        self.g.draw()
        size=self.g.ui_surface.get_size()
        image=Image.frombytes('RGB',size,pygame.image.tobytes(self.g.ui_surface,'RGB'))
        return image.resize((480,320),Image.Resampling.NEAREST)

    def frame(self,duration=120):
        scene=self.game_image()
        frame=Image.new('RGB',(480,344),'#e8edf2');frame.paste(scene,(0,24))
        d=ImageDraw.Draw(frame);d.text((9,4),self.label,font=self.font,fill='#243529')
        self.frames.append(frame);self.durations.append(duration)

    def close_frame(self,duration=70):
        if self.g.world.data['id']!='upstream':return
        # Same runtime world renderer and actor/prop ownership as Game.draw.
        camera=(420,284);size=(144,128)
        canvas=pygame.Surface(size)
        self.g.world.draw(canvas,camera,self.g.player,self.g.elapsed_ms,include_ui=False)
        for visit in self.g.household_visits:visit.draw_world(canvas,camera)
        scene=Image.frombytes('RGB',size,pygame.image.tobytes(canvas,'RGB'))
        frame=Image.new('RGB',(576,556),'#e8edf2')
        frame.paste(scene.resize((576,512),Image.Resampling.NEAREST),(0,44))
        d=ImageDraw.Draw(frame);d.text((10,5),'CAELAN / A SMALLER MAGICAL SUCCESS',font=self.font,fill='#243529')
        caption='Move the trapped still water into the drain'
        if self.c.spell_done:caption='The recess is clear; the small spell worked'
        d.text((10,24),caption,font=self.font,fill='#243529')
        self.close.append(frame);self.close_durations.append(duration)

    def tick(self,seconds=1/30,direction=(0,0),record=True):
        self.g.update(seconds,direction,False);self.tick_index+=1
        if record:
            action=self.c.action
            cadence=3 if action else 24
            if self.tick_index%cadence==0:self.frame(100 if action else 120)
        if self.c.action=='spell' and self.tick_index%2==0:self.close_frame()
        if self.c.action=='repair' and self.c.action_time>.9 and not self.repair_still:
            self.save_still('cooperative_repair.png');self.repair_still=True

    def wait(self,predicate,seconds=40):
        for _ in range(round(seconds*30)):
            if predicate():return
            self.tick()
        raise AssertionError(('Timeout',self.c.stage,self.c.action,self.g.world.data['id']))

    def read(self):
        count=0
        while self.g.social.active:
            count+=1;assert count<120,'Unfinished dialogue'
            identifier=self.g.social.script_identifier
            if identifier=='mill_resolution' and self.g.social.page_index==0:self.save_still('resolution.png')
            # Let facings settle without moving the player or accepting prose.
            for _ in range(4):self.tick(record=False)
            self.frame(650)
            if identifier and identifier.startswith('mill_encouragement'):
                page=self.g.social.page_index
                if page>=2:
                    self.g.draw();pygame.image.save(self.g.ui_surface,OUT/'encouragement.png')
            self.g.social.advance()

    def walk(self,goal,seconds=100):
        goal=pygame.Vector2(goal)
        # A* is the same collision-aware route search used by the NPCs. Replan
        # when a resident crosses the player's route rather than crossing walls.
        deadline=round(seconds*30);route=[];retry=0
        for tick in range(deadline):
            if self.g.player.position.distance_to(goal)<1.5:return
            if self.g.social.active:self.read()
            if not route or retry>=20:
                found=find_path(self.g.world,self.g.player.position,goal,self.g.world.probe_size,None)
                if found is None:raise AssertionError(('No walking route',self.g.world.data['id'],tuple(self.g.player.position),tuple(goal)))
                route=list(found);retry=0
            if not route:return
            target=pygame.Vector2(route[0]);delta=target-self.g.player.position
            if delta.length()<1.5:route.pop(0);continue
            before=self.g.player.position.copy()
            dt=min(1/30,delta.length()/72)
            self.tick(dt,delta)
            retry=retry+1 if before==self.g.player.position else 0
        raise AssertionError(('Walk timeout',tuple(self.g.player.position),tuple(goal)))

    def companion(self):
        self.wait(lambda:self.c.mira in self.g.world.npcs and self.c.mira.position.distance_to(self.g.player.position)<=76)

    def at(self,key):
        self.walk(self.c.points[key]);self.companion()

    def interact(self,script=None):
        if self.g.social.active:self.read()
        assert self.c.interact(),('No interaction',self.c.stage,tuple(self.g.player.position))
        if script:assert self.g.social.script_identifier==script,(self.g.social.script_identifier,script)
        self.read()

    def link(self,destination):
        link=next(link for link in self.g.world.data['world_links']
                  if json.loads((ROOT/link['destination']).read_text())['id']==destination)
        self.walk(link['position']);self.companion()
        self.wait(lambda:self.g.transfer_cooldown==0)
        assert self.g.travel_link(link)
        self.companion();self.g.camera.reset();self.frame(300)

    def save_still(self,name):
        self.g.draw();pygame.image.save(self.g.ui_surface,OUT/name)

    def run(self):
        self.frame(800)
        self.walk((610,476))
        assert self.g.social.start(self.c.mira);self.read()
        assert self.g.quests.status(MILL_QUEST)=='active'
        self.label='Mira and Caelan inspect the stopped mill'
        for p in [(720,476),(960,476)]:self.walk(p)
        self.at('mechanism');self.interact('mill_mechanism')
        self.save_still('mill_stopped.png')
        self.at('race');self.interact('mill_race')
        assert self.g.quests.objective_status(MILL_QUEST,'diagnose_mill')=='completed'
        self.label='Follow the millrace upstream'
        for p in [(1080,476),(960,476),(720,476)]:self.walk(p)
        self.link('upstream')
        self.label='The upstream intake is obstructed'
        self.at('intake');self.interact('mill_intake');self.save_still('upstream.png')
        self.label='Mira relieves the pressure at the bypass'
        self.at('bypass');self.interact('mill_prepare');self.wait(lambda:self.c.action is None)
        assert self.c.prepared and not self.c.mill_restored
        self.label='Caelan tries a smaller, controlled spell'
        self.at('spell');self.interact('mill_spell_intro')
        self.close_frame(200)
        self.wait(lambda:self.c.spell_done)
        props={prop['id']:prop for prop in self.c.surface_props}
        for identifier in ('intake_screen','lever','millrace_flow'):
            prop=props[identifier]
            assert pygame.image.tobytes(prop['surface'],'RGBA')==pygame.image.tobytes(prop['states']['prepared'],'RGBA'),identifier+' changed before physical repair'
        pool=props['inspection_pool']
        assert pygame.image.tobytes(pool['surface'],'RGBA')==pygame.image.tobytes(pool['states']['cleared'],'RGBA')
        self.close_frame(400);self.save_still('small_success.png')
        assert self.g.social.script_identifier=='mill_encouragement_failed'
        self.label='A small success, and encouragement from Mira'
        self.read();assert self.c.encouraged
        self.label='Together they free the intake screen'
        self.at('lever');self.interact('mill_repair');self.wait(lambda:self.c.action is None)
        assert self.c.mill_restored;self.save_still('intake_restored.png')
        self.label='Return to the mill'
        self.link(self.g.town.data['id'])
        for p in [(720,476),(960,476)]:self.walk(p)
        self.at('mill_station');self.interact('mill_verify')
        assert self.c.verified;self.save_still('mill_running.png')
        self.label="Halden's mill is working again"
        halden=self.g.halden_visit.halden
        self.walk(halden.position+(0,28))
        if not self.c.resolved:
            self.companion()
            if not self.g.social.active:assert self.g.social.start(halden)
            self.save_still('resolution.png');self.read()
        assert self.c.resolved and self.g.quests.status(MILL_QUEST)=='completed'
        for _ in range(15):self.tick()
        self.frame(1200)
        assert not self.g.opening_conclusion.mill_stopped
        # The overview is intentionally compact: retain every dialogue page
        # and scene cut, with sparse walking/action samples. Detailed motion is
        # preserved separately in the full-size spell loops and PNG stills.
        overview=[];overview_durations=[];walking=action=0
        for frame,duration in zip(self.frames,self.durations):
            keep=duration>=300
            if duration==120:walking+=1;keep=walking%3==1
            if duration==100:action+=1;keep=action%4==1
            if keep:
                overview.append(frame.resize((320,229),Image.Resampling.NEAREST))
                overview_durations.append(duration)
        save_gif(OUT/'quest.gif',overview,overview_durations,64)
        save_gif(OUT/'small_spell.gif',self.close,self.close_durations,128)
        save_gif(OUT/'small_spell_slow.gif',self.close,[duration*2 for duration in self.close_durations],128)
        print('Captured complete MQ02:',len(self.frames),'overview frames;',len(self.close),'spell frames')
        for name in ['quest.gif','small_spell.gif','small_spell_slow.gif']:
            print(name,(OUT/name).stat().st_size,'bytes')
        pygame.quit()


def capture():Capture().run()
if __name__=='__main__':capture()
