"""Acknowledged MQ03 closing exchanges and a collision-aware return outing."""
from copy import deepcopy
import json
from pathlib import Path

STAGES=('resolution_report','resolution_return','resolution_reunion','resolution_reckoning','resolution_relief','resolution_companions','resolution_family')
TEXT={
'resolution_report':'Join Lucan and Aldric at Elden Vale Sanctuary.',
'resolution_return':'Return to Serene’s dining room in Eldenmere.',
'resolution_reunion':'Speak with Serene in the dining room at home.',
'resolution_reckoning':'Hear Serene and Aldric’s account in the dining room.',
'resolution_relief':'Finish the relief arrangements with Serene and Aldric.',
'resolution_companions':'Speak with Mira before she returns to her workshop.',
'resolution_family':'Speak privately with Serene in the dining room.'}

class RegentResolution:
    def __init__(self,owner):
        self.owner=owner;self.game=owner.game
        owner.lines.update(json.loads((Path(__file__).parent/'assets/story/regent/resolution.json').read_text()))
        self.error=''
    def commit(self,next_stage):
        c=self.owner;g=self.game
        before=c.stage;quests=deepcopy(g.quests.to_dict());flags=set(g.social.flags)
        party=deepcopy(g.party.to_dict());levels=deepcopy(g.character_progression.to_dict())
        inventory=deepcopy(g.inventory.to_dict())
        c.stage=next_stage
        if next_stage=='resolution_family' and g.party.is_guest('mira'):
            if g.party.current_event_id=='mq03_sanctuary':g.party.end_event('mq03_sanctuary')
            g.party.set_available('mira',False,'Working in Eldenmere.')
        if next_stage=='done':
            c._complete('speak_serene')
            if not g.quests.turn_in('CH01_MQ03','mother_serene'):
                c.stage=before;g.quests.restore(quests);return False
            g.social.flags.add('CH01_MQ03_COMPLETE');g.quests.unlock('CH01_MQ04')
        if not g.save_store.enabled or g.save_progress():
            self.error='';c._setup=False;return True
        c.stage=before;g.quests.restore(quests);g.social.flags=flags
        g.party.restore(party);g.character_progression.restore(levels);g.inventory.restore(inventory)
        self.error='Progress could not be saved. Speak again to retry.'
        return False
    def update(self,seconds):
        c=self.owner;g=self.game
        if c.stage=='resolution_return':
            if getattr(g.world,'is_overworld',False):return
            c._follow_party(seconds)
            if g.world is c.dining and all(c._world(a) is c.dining for a in c.sanctuary_escorts):
                self.commit('resolution_reunion')
    def target(self):
        c=self.owner;g=self.game
        if c.stage=='resolution_report':actor=c.aldric
        elif c.stage=='resolution_companions':actor=g.mill_quest.mira
        else:actor=c.serene
        return actor if c._world(actor) is g.world and c._near(actor.position,72) else None
    def interact(self):
        c=self.owner
        if c.stage=='resolution_return' or self.target() is None:return False
        index=STAGES.index(c.stage);next_stage=STAGES[index+1] if index+1<len(STAGES) else 'done'
        return c._speak(c.stage,lambda:self.commit(next_stage))
    def text(self):return TEXT[self.owner.stage]+(' Save failed; speak again to retry.' if self.error else '')
