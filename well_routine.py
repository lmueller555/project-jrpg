"""A hand-operated well whose animation follows its reserved operator's clock."""
import json
from pathlib import Path
import pygame

ROOT=Path(__file__).resolve().parent


def mix(a,b,t):return pygame.Vector2(a).lerp(b,max(0,min(1,t)))


class DrawingWell:
    def __init__(self,world):
        folder=Path('assets/terrain/eldenmere/well/drawing')
        self.data=json.loads((ROOT/folder/'animation.json').read_text())
        self.fixed=world.image((folder/self.data['fixed']).as_posix())
        self.rim=world.image((folder/self.data['front_rim']).as_posix())
        self.owner=None
        self.pails={}
        anim=json.loads((ROOT/'assets/characters/npcs/female_02/gardener/animations.json').read_text())
        self.bucket_data=anim['buckets']
        for key,record in anim['buckets'].items():
            self.pails[key]=world.image('assets/characters/npcs/female_02/gardener/'+record['file'])

    def reserve(self,actor):
        if self.owner is not None and self.owner is not actor:return False
        self.owner=actor;return True

    def release(self,actor):
        if self.owner is actor:self.owner=None

    @property
    def state(self):return self.owner.state if self.owner else 'idle'

    @property
    def time(self):return self.owner.state_ms if self.owner else 0

    @property
    def progress(self):
        return min(1,self.time/self.data['phases_ms'].get(self.state,1))

    @property
    def crank_index(self):
        tick=int((self.time+1e-6)//100)
        if self.state=='well_lower':return tick%8
        if self.state=='well_raise':return -tick%8
        if self.state=='well_reset' and self.time>=1200:return (tick-12)%8
        return 0

    @property
    def bucket_grip(self):
        d=self.data;s=self.state;t=self.progress
        idle=d['idle_bucket_grip'];low=d['lowered_bucket_grip'];high=d['raised_bucket_grip'];out=d['pour_bucket_grip']
        if s=='well_lower':return mix(idle,low,t)
        if s=='well_fill':return pygame.Vector2(low)
        if s=='well_raise':return mix(low,high,t)
        if s in ('well_lock','well_to_pour'):return pygame.Vector2(high)
        if s=='well_guide':
            # Bring it over the FRONT opening before moving right. Going
            # directly toward the crank would pass through the timber post.
            if t<.3:return mix(high,(40,56),t/.3)
            if t<.5:return mix((40,56),(40,64),(t-.3)/.2)
            return mix((40,64),out,(t-.5)*2)
        if s=='well_pour':return pygame.Vector2(out)
        if s=='well_back_to_crank':return pygame.Vector2(out)
        if s=='well_reset':
            if t<.25:return mix(out,(40,64),t/.25)
            if t<.4:return mix((40,64),(40,56),(t-.25)/.15)
            if t<.6:return mix((40,56),high,(t-.4)/.2)
            return mix(high,idle,(t-.6)/.4)
        return pygame.Vector2(idle)

    @property
    def draw_level(self):
        if self.state=='well_fill':return min(6,int(self.progress*7))
        if self.state in ('well_raise','well_lock','well_to_pour','well_guide'):return 6
        if self.state=='well_pour':return 6-self.owner.water_units
        return 0

    @property
    def portable_visible(self):
        return self.owner is not None and self.state not in ('well_setdown','well_pickup')

    def portable_sprite(self):return self.pails[f'bucket_0_{self.owner.water_units}']

    @property
    def pail_blocker(self):
        x,y=self.data['pail_grip_world']
        return pygame.Rect(x-5,y+6,10,6)

    def sprite(self,elapsed_ms):
        image=pygame.Surface(self.data['canvas_size'],pygame.SRCALPHA)
        image.blit(self.fixed,(0,0))
        i=self.crank_index
        # Grain bands rotate around the spindle's face with the crank. Reverse
        # crank phases reverse these bands as well; idle/filling holds them.
        for x in (28,47):
            pygame.draw.line(image,'#735136',(x,41+i%4),(x+5,41+i%4))
            pygame.draw.line(image,'#c69d66',(x+1,41+(i+2)%4),(x+4,41+(i+2)%4))
        phase=int(elapsed_ms//100)%4
        # Restrained water glint remains independent of the operated mechanism.
        for x in (29+phase,48-phase):image.set_at((x,69),pygame.Color('#598e9f'))
        grip=self.bucket_grip
        angle=0
        if self.state=='well_pour':
            angle=25 if self.progress<.12 or self.progress>.88 else 50
        key=f'bucket_{angle}_{self.draw_level}'
        pygame.draw.line(image,'#735136',self.data['rope_origin'],tuple(round(v) for v in grip),2)
        pygame.draw.line(image,'#c69d66',self.data['rope_origin'],tuple(round(v) for v in grip),1)
        # Bucket and rope are inside the shaft except during the guided transfer.
        xy=grip-pygame.Vector2(self.bucket_data[key]['grip'])
        image.blit(self.pails[key],xy)
        outside=self.state in ('well_pour','well_back_to_crank') or (self.state=='well_guide' and self.progress>=.3) or (self.state=='well_reset' and self.progress<=.4)
        if not outside:image.blit(self.rim,(0,0))
        if self.state=='well_fill':
            radius=4+phase
            pygame.draw.line(image,'#b9d9d2',(40-radius,70),(36,69))
            pygame.draw.line(image,'#598e9f',(44,69),(40+radius,70))
        if self.state=='well_raise' and grip.y<61:
            for n in range(2):
                image.set_at((round(grip.x)+n*3,round(grip.y)+14+(phase+n)%4),pygame.Color('#b9d9d2'))
        if self.state=='well_pour' and .12<=self.progress<=.88:
            start=xy+pygame.Vector2(self.bucket_data[key]['spout'])
            end=pygame.Vector2(self.data['pail_grip_world'])-self.data['position']+pygame.Vector2(1,5)
            pygame.draw.line(image,'#598e9f',start,end,2)
            pygame.draw.line(image,'#b9d9d2',start,end,1)
            drop=mix(start,end,(phase+1)/5)
            image.set_at(tuple(round(v) for v in drop),pygame.Color('#598e9f'))
        # Shaft wrap and the crank share the very same phase as her hand.
        pygame.draw.line(image,'#a37b4c',(39+i%2,40),(39+i%2,46),1)
        pivot=self.data['crank_pivot'];hand=self.data['crank_handles'][i]
        pygame.draw.line(image,'#45382d',pivot,hand,3)
        pygame.draw.line(image,'#a37b4c',pivot,hand,1)
        pygame.draw.line(image,'#c69d66',hand,(hand[0]+2,hand[1]),2)
        return image
