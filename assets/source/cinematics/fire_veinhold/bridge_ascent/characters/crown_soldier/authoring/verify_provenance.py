"""Read/verify retained ImageGen raw provenance and selected actor inputs."""
from pathlib import Path
from hashlib import sha256
import json
P=Path(__file__).resolve().parent.parent
R=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').exists())
O=R/'assets/story/fire_veinhold_opening/shot08/characters/crown_soldier'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def local(path):
 q=Path(path)
 if q.exists():return q
 if '/project-jrpg/' in str(path):return R/str(path).split('/project-jrpg/',1)[1]
 marker='/bridge_ascent/characters/crown_soldier/'
 if marker in str(path):return P/str(path).split(marker,1)[1]
 return q
count=0;errors=[]
for path in sorted(P.rglob('*_generation.json')):
 record=json.loads(path.read_text());before=dict(record)
 if 'source_path' not in record or 'output' not in record:continue
 out=local(record['output']);source=local(record['source_path'])
 if path.name=='overhead_00_initial_generation.json':out=path.with_name('overhead_00_initial.png')
 if not out.exists():errors.append(str(path)+': missing retained output');continue
 h=digest(out)
 if source.exists() and digest(source)!=h:errors.append(str(path)+': retained PNG differs from raw source')
 for field,value in [('source_sha256',h),('output_sha256',h)]:
  if field in record and record[field]!=value:errors.append(str(path)+': mismatched '+field)
  record.setdefault(field,value)
 refs={}
 for ref in record.get('referenced_image_paths',[]):
  if not local(ref).exists():errors.append(str(path)+': missing reference '+ref)
  else:refs[ref]=digest(local(ref))
 if 'reference_sha256' in record and record['reference_sha256']!=refs:errors.append(str(path)+': reference bytes changed')
 record.setdefault('reference_sha256',refs)
 if 'prompt' in record and 'prompt_sha256' not in record:record.setdefault('prompt_text_sha256',sha256(record['prompt'].encode()).hexdigest())
 prompt=local(record.get('prompt_file',''))
 if prompt.is_file() and 'prompt_sha256' not in record:record.setdefault('prompt_file_sha256',digest(prompt))
 # Existing complete metadata remains byte-for-byte stable, including child
 # records that have their own historical metadata hash chains.
 if before!=record:path.write_text(json.dumps(record,indent=2)+'\n')
 count+=1
m=json.loads((O/'actorperformance.json').read_text())
for rel,expected in m['source_sha256'].items():
 p=O/rel
 if not p.is_file() or digest(p)!=expected:errors.append('Published PNG hash mismatch:'+rel)
for i,row in enumerate(m['transition_frames']):
 if row['index']!=i or row['logical_phase']!=(18+i)%48:errors.append('Incorrect logical phase:'+str(i))
 if i<=25:
  approved=R/f'assets/story/fire_veinhold_opening/shot07/characters/crown_soldier/frame_{(18+i)%48:02d}.png'
  if digest(O/row['file'])!=digest(approved):errors.append('Entry handoff bytes changed:'+str(i))
assert len(m['transition_frames'])==133 and len(m['overhead_cycle']['frames'])==48
assert m['transition_frames'][132]['file']==m['overhead_cycle']['frames'][6]['file']
report={'generation_records_verified':count,'published_unique_pngs_verified':len(m['source_sha256']),'transition_records':133,'cycle_phases':48,'exact_approved_entry_frames':26,'logical_phase_offset':18,'cycle_ms':800,'errors':errors}
(P/'provenance_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
if errors:raise SystemExit(1)

