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
        tick=int((self.time+1e-6)//(125 if self.state=='well_raise' else 100))
        if self.state=='well_lower':return tick%8
        if self.state=='well_raise':return -tick%8
        return 0

    @property
    def bucket_grip(self):
        d=self.data;s=self.state;t=self.progress
        loading=d['loading_grip'];shaft=d['shaft_grip'];low=d['lowered_bucket_grip']
        if s=='well_settle':return pygame.Vector2(shaft)
        if s=='well_lower':return mix(shaft,low,t)
        if s=='well_fill':return pygame.Vector2(low)
        if s=='well_raise':return mix(low,shaft,t)
        if s=='well_catch':return pygame.Vector2(shaft if t<.55 else loading)
        if s in ('well_to_crank','well_grip','well_lock','well_to_loading'):
            return pygame.Vector2(shaft)
        return pygame.Vector2(loading)

    @property
    def draw_level(self):
        return self.owner.water_units if self.owner else 0

    @property
    def bucket_on_rope(self):
        return self.owner is not None and self.state in (
            'well_settle','well_to_crank','well_grip','well_lower','well_fill',
            'well_raise','well_lock','well_to_loading','well_catch')

    @property
    def bucket_at_handoff(self):
        return self.state=='well_catch' and self.progress>=.55

    @property
    def rope_deployed(self):
        # The long line exists only between bucket attachment and the retrieval
        # transfer. Actor-owned handoff phases show the retracted hook instead.
        return self.bucket_on_rope and not self.bucket_at_handoff

    @property
    def rope_end(self):
        d=self.data
        if self.state=='well_settle':
            return mix(d['hook_tip'],d['shaft_grip'],self.progress)
        if self.state=='well_catch':
            return mix(d['shaft_grip'],d['hook_tip'],self.progress/.55)
        return pygame.Vector2(self.bucket_grip)

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
        # Use the same six 200ms ambient phases as the terrain exports.
        phase=int(elapsed_ms//200)%6
        for x in (29+phase,48-phase):image.set_at((x,69),pygame.Color('#598e9f'))
        grip=self.bucket_grip
        key=f'bucket_0_{self.draw_level}'
        if self.rope_deployed:
            rope_end=tuple(round(v) for v in self.rope_end)
            pygame.draw.line(image,'#735136',self.data['rope_origin'],rope_end,2)
            pygame.draw.line(image,'#c69d66',self.data['rope_origin'],rope_end,1)
        xy=grip-pygame.Vector2(self.bucket_data[key]['grip'])
        # Inside the shaft, the pail is composited before the near rim. At the
        # retrieval transfer it moves forward behind the gardener's body.
        if self.bucket_on_rope and not self.bucket_at_handoff:
            image.set_clip(pygame.Rect(0,0,self.data['canvas_size'][0],72))
            image.blit(self.pails[key],xy)
            image.set_clip(None)
        if self.state=='well_fill':
            radius=4+phase
            pygame.draw.line(image,'#b9d9d2',(40-radius,70),(36,69))
            pygame.draw.line(image,'#598e9f',(44,69),(40+radius,70))
        image.blit(self.rim,(0,0))
        if self.bucket_on_rope and self.bucket_at_handoff:
            image.blit(self.pails[key],xy)
        x,y=self.data['hook_tip'];mount_y=self.data['hook_mount'][1]
        hook=[(x,mount_y),(x,y-1),(x+2,y),(x+2,y-1)]
        # With no attached pail, only this three-pixel hook hangs beneath the
        # windlass. No line reaches the rim or the gardener.
        if not self.rope_deployed:
            pygame.draw.lines(image,'#a2b4a7',False,hook)
        if self.state=='well_raise' and grip.y<61:
            for n in range(2):
                image.set_at((round(grip.x)+n*3,round(grip.y)+14+(phase+n)%4),pygame.Color('#b9d9d2'))
        # Shaft wrap and the crank share the very same phase as her hand.
        pygame.draw.line(image,'#c69d66',(40+i%2,40),(40+i%2,46),1)
        pivot=self.data['crank_pivot'];hand=self.data['crank_handles'][i]
        pygame.draw.line(image,'#45382d',pivot,hand,3)
        pygame.draw.line(image,'#a37b4c',pivot,hand,1)
        pygame.draw.line(image,'#c69d66',hand,(hand[0]+2,hand[1]),2)
        return image
