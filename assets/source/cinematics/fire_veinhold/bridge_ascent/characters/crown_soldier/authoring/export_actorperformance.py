"""Build Crown actor inputs from complete approved-entry and atlas drawings.

No anatomy is synthesized here. Whole-figure registration has already happened.
Every published bitmap's exact hash is bound into the portable manifest.
"""
from pathlib import Path
import argparse,json,shutil,hashlib
P=Path(__file__).resolve().parent.parent
R=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').exists())
OUT=R/'assets/story/fire_veinhold_opening/shot08/characters/crown_soldier'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
 rows=json.loads((P/'registered_atlases/registration_report.json').read_text())
 transitions={r['index']:r for r in rows if r['kind']=='transition'}
 overhead={r['phase']:r for r in rows if r['kind']=='overhead'}
 transitions.update({r['index']:r for r in json.loads((P/'entry/selection.json').read_text())})
 transitions[26]=json.loads((P/'registered_samples/entry_026_close_model_registration.json').read_text())
 assert len(overhead)==48 and set(overhead)==set(range(48))
 hashes={};selected=[];cycle=[];provenance=[]
 def publish(row,rel):
  src=P/row['file'];dst=OUT/rel
  if args.check:
   if not dst.is_file() or dst.read_bytes()!=src.read_bytes():raise ValueError('Published actor PNG differs:'+rel)
  else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
  h=digest(dst);hashes[rel]=h
  return {'file':rel,'canvas':row['canvas'],'anchor':row['anchor'],'art_pixels_per_metre':row['art_pixels_per_metre']},h
 for phase in range(48):
  row=overhead[phase];rec,h=publish(row,f'overhead/phase_{phase:02d}.png');cycle.append({**rec,'phase':phase});provenance.append({'kind':'overhead','phase':phase,'source_record':row,'export_sha256':h})
 for index in range(133):
  logical=(18+index)%48
  if index==132:
   row=overhead[logical];rec={k:cycle[logical][k] for k in ['file','canvas','anchor','art_pixels_per_metre']};authored=logical;time=index/60;held=False
  else:
   authored_tick=index if index<=26 or index%2==0 else index-1
   row=transitions[authored_tick];authored=(18+authored_tick)%48
   rel=f'entry/frame_{authored_tick:03d}.png' if authored_tick<=25 else f'transition/frame_{authored_tick:03d}.png'
   if rel in hashes:rec={'file':rel,'canvas':row['canvas'],'anchor':row['anchor'],'art_pixels_per_metre':row['art_pixels_per_metre']}
   else:rec,h=publish(row,rel);provenance.append({'kind':'transition','authored_tick':authored_tick,'source_record':row,'export_sha256':h})
   time=authored_tick/60;held=index!=authored_tick
  selected.append({'index':index,**rec,'logical_phase':logical,'authored_phase':authored,'authored_time_seconds':time,'held_reviewed_exposure':held})
 assert selected[0]['file']=='entry/frame_000.png' and selected[25]['authored_phase']==43 and selected[26]['authored_phase']==44
 assert selected[132]['file']==cycle[6]['file']
 manifest={'version':1,'actor':'crown_soldier','canvas':[1024,1536],'anchor':[512,960],'art_pixels_per_metre':500,'cycle_ms':800,'cycle_phase_count':48,'approval_state':'prepared_for_ingame_review','source_review':'Independent source/native entry, later-angle continuity and tiny-cycle gates provisionally passed; final full-scene chronological bank review remains separate.','review_pointer':'docs/reviews/veinhold_bridge_ascent/independent_review/crown_current_full_gate_corrected.json','construction':'Exact approved entry0–25, matching-phase continuity drawing26, complete camera-specific ImageGen atlas drawings exposed at30Hz thereafter, and48 complete painted high-angle cycle drawings. No warped or interpolated anatomy. Runtime timing remains60Hz.','entry_handoff':'Entry0–25 retain exact approved shot07 phase18–43 PNG bytes and original canvas/anchor/density. Tick26 is phase44; tick28 is46; tick30 is0. Odd ticks after26 hold the preceding reviewed whole drawing. Logical phase/audio timing is independent of drawing exposure.','transition_frames':selected,'overhead_cycle':{'view_elevation_degrees':81.53851392632384,'frames':cycle},'source_sha256':dict(sorted(hashes.items()))}
 payload=(json.dumps(manifest,indent=2)+'\n').encode();provenance_payload=(json.dumps(provenance,indent=2)+'\n').encode()
 if args.check:
  if (OUT/'actorperformance.json').read_bytes()!=payload:raise ValueError('Actor manifest does not reproduce')
  if (P/'selection_provenance.json').read_bytes()!=provenance_payload:raise ValueError('Selected source provenance does not reproduce')
 else:
  OUT.mkdir(parents=True,exist_ok=True);(OUT/'actorperformance.json').write_bytes(payload);(P/'selection_provenance.json').write_bytes(provenance_payload)
 print('Verified deterministic Crown export.' if args.check else 'Wrote prepared Crown export.')
 print(json.dumps({'transitions':len(selected),'overhead':len(cycle),'used_unique_pngs':len(hashes),'manifest':str(OUT/'actorperformance.json')}))
if __name__=='__main__':main()

