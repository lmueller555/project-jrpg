"""Select current complete authored drawings from immutable generation records."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent

def main():
    records=json.loads((P/'generation_records_initial.json').read_text())
    parts=[P/'repair_generation_records_second_half.json',P/'repairs/repair_generation_records_07_17.json',P/'repair_generation_records_outliers.json']
    for path in parts:
      if not path.exists():continue
      for key,entry in json.loads(path.read_text()).items():
        row=dict(entry)
        if 'source_master' not in row:row['source_master']=f'repairs/frame_{int(key):02d}.png'
        if path.parent.name=='repairs' and row.get('prompt_file') and not row['prompt_file'].startswith('repairs/'):
          row['prompt_file']='repairs/'+row['prompt_file']
        if not (P/row['source_master']).is_file():raise ValueError('Selected master missing: '+row['source_master'])
        records[str(int(key))]=row
    records={str(i):records[str(i)] for i in range(48)}
    (P/'generation_records.json').write_text(json.dumps(records,indent=2)+'\n')
    print('Selected',len(records),'complete drawings;',sum(v['source_master'].startswith('repairs/') for v in records.values()),'corrected sources')
if __name__=='__main__':main()
