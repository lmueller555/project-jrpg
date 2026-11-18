"""Dormant Tomas action art preserves metadata, identity and native density."""
import hashlib,json,unittest
from pathlib import Path
from PIL import Image,ImageSequence
ROOT=Path(__file__).resolve().parents[1]
BANK=ROOT/'assets/characters/tomas/activity_hd'
SOURCE=ROOT/'assets/source/characters/tomas/activity_hd'
def read(p):return json.loads(p.read_text())
class TomasActivityArtTests(unittest.TestCase):
 def test_complete_native_drawings_and_hard_alpha(self):
  plans=read(SOURCE/'drawings.json');self.assertEqual(len(plans),133)
  counts={}
  for name,plan in plans.items():
   counts[name.split('/')[0]]=counts.get(name.split('/')[0],0)+1
   with Image.open(BANK/name) as im:
    self.assertEqual(im.size,tuple(plan['size']));self.assertEqual(im.mode,'RGBA')
    self.assertEqual(set(im.getchannel('A').tobytes()),{0,255})
  self.assertEqual(counts,{'routines':74,'breakfast':23,'sack':36})
 def test_routine_timing_and_single_owner_custody_are_unchanged(self):
  old=read(ROOT/'assets/characters/tomas/routines/animations.json');new=read(BANK/'routines/animations.json')
  for key in ('animations','walk_sets','draw_anchor','body_offset'):self.assertEqual(old[key],new[key])
  self.assertEqual(new['logical_size'],old['frame_size']);self.assertEqual(new['artwork_pixels_per_world_pixel'],2)
  for record in new['animations'].values():
   self.assertEqual(sum(f['duration_ms'] for f in record['frames']),record['duration_ms'])
 def test_breakfast_cues_and_wrist_registration_retained(self):
  for name in ('tomas_eat','tomas_sit','tomas_stand'):
   old=read(ROOT/f'assets/story/sanctuary_opening/poses/{name}/animation.json');new=read(BANK/f'breakfast/{name}/animation.json')
   for key in ('frames','duration_ms','draw_anchor','loop','registration'):self.assertEqual(old[key],new[key])
  meta=read(BANK/'breakfast/art.json');self.assertEqual(meta['logical_size'],[24,36]);self.assertEqual(meta['draw_anchor'],[12,30])
 def test_sack_contacts_and_native_prop_footprint(self):
  old=read(ROOT/'assets/story/halden/art.json');new=read(BANK/'sack/art.json')
  for key in ('carry_canvas','carry_anchor','lift_duration_ms','contact_frame','directions'):self.assertEqual(old[key],new[key])
  with Image.open(BANK/'sack/sack.png') as im:self.assertEqual(im.size,(32,36))
 def test_canonical_faces_source_hashes_and_cinematic_retention(self):
  meta=read(BANK/'provenance.json')
  for name,expected in meta['canonical_idles'].items():self.assertEqual(hashlib.sha256((ROOT/'assets/characters/named_hd/tomas'/name).read_bytes()).hexdigest(),expected)
  for name,expected in meta['exports'].items():self.assertEqual(hashlib.sha256((BANK/name).read_bytes()).hexdigest(),expected)
  audit=read(BANK/'cinematic_audit.json');self.assertEqual(audit['decision'],'retain_originals_in_place')
  for path,expected in audit['files'].items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),expected)
 def test_preview_timing(self):
  routine=read(BANK/'routines/animations.json')
  durations={'routines_'+name:clip['duration_ms'] for name,clip in routine['animations'].items()}
  durations.update({'routines_carry_'+face:sum(f['duration_ms'] for f in frames) for face,frames in routine['walk_sets']['bundle'].items()})
  for name,total in durations.items():
   for label,multiplier in [('normal',1),('half',2)]:
    with Image.open(BANK/f'reviews/{name}_{label}.gif') as gif:self.assertEqual(sum(f.info['duration'] for f in ImageSequence.Iterator(gif)),total*multiplier)
if __name__=='__main__':unittest.main()
