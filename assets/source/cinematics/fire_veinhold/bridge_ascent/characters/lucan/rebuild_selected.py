"""Rebuild the selected whole-image recipes, preserving exact declared PNG bytes."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json
from check_source_provenance import Snapshot,registration_records,render_recipe
S=Path(__file__).resolve().parent;ROOT=S.parents[6]
PROFILE=ROOT/'assets/story/fire_veinhold_opening/shot08/characters/lucan/actorperformance.json'


def main():
    profile=json.loads(PROFILE.read_text());snapshot=Snapshot();recipes=registration_records(snapshot);rebuilt=0
    for name,expected in profile['source_sha256'].items():
        path=(PROFILE.parent/name).resolve()
        if name.startswith('../'):
            assert sha256(path.read_bytes()).hexdigest()==expected;continue
        candidates=[record for _,_,record in recipes[path] if record.get('output_sha256')==expected]
        assert candidates,f'No selected hash-bound recipe for {name}'
        record=candidates[-1];source=ROOT/record['source']
        assert sha256(source.read_bytes()).hexdigest()==record['source_sha256']
        image=render_recipe(source,record,profile['canvas'],record.get('alpha_floor',0));buffer=BytesIO();image.save(buffer,format='PNG');result=buffer.getvalue()
        assert sha256(result).hexdigest()==expected,f'PNG encoding or selected recipe changed: {name}'
        path.write_bytes(result);rebuilt+=1
    print(json.dumps({'actor':'lucan','rebuilt_selected_pngs':rebuilt,'direct_upstream_reuse':16,'profile_sha256':sha256(PROFILE.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
