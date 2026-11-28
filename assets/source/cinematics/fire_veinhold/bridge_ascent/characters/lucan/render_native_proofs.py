"""Capture Lucan through the exact offline production whole-figure compositor."""
from pathlib import Path
from hashlib import sha256
import json,sys
import numpy as np
from PIL import Image,ImageDraw
S=Path(__file__).resolve().parent;ROOT=S.parents[6];sys.path.insert(0,str(ROOT))
from cinematic_bridge_ascent import actor_states_at,camera_signature
from tools.build_prologue_bridge_ascent import FigureCompositor,_figure_record


def main():
    profile=ROOT/'assets/story/fire_veinhold_opening/shot08/characters/lucan/actorperformance.json'
    source=profile.read_bytes();data=json.loads(source);out=Path('/tmp/lucan_production_native_review');out.mkdir(exist_ok=True)
    compositor=FigureCompositor();records=[]
    for index in range(181):
        state=actor_states_at(index/60);actor=state['runners'][0]
        row=data['transition_frames'][index] if index<len(data['transition_frames']) else data['overhead_cycle']['frames'][actor['frame_index']]
        record=_figure_record(profile,data,row,'lucan')
        picture=compositor.compose(Image.new('RGB',(960,640),'#203040'),np.full((640,960),np.inf),state,[record],shadows=False)
        picture.save(out/f'native_{index:03d}.png')
        records.append({'index':index,'local_time':index/60,'gait_frame':actor['frame_index'],'source':row['file'],
                        'source_sha256':sha256(record['path'].read_bytes()).hexdigest(),'state':state,
                        'output_sha256':sha256((out/f'native_{index:03d}.png').read_bytes()).hexdigest()})
    binding={'profile_sha256':sha256(source).hexdigest(),'camera_signature':camera_signature(),
             'renderer':'tools.build_prologue_bridge_ascent.FigureCompositor.compose(shadows=False)','records':records}
    (out/'binding.json').write_text(json.dumps(binding,indent=2)+'\n')
    samples=[0,15,16,23,24,27,28,31,32,*range(35,53),59,60,67,68,75,76,83,84,99,100,107,108,132,133]
    cols=4;rows=(len(samples)+cols-1)//cols;sheet=Image.new('RGB',(cols*480,rows*340),'#203040');draw=ImageDraw.Draw(sheet)
    for cell,index in enumerate(samples):
        picture=Image.open(out/f'native_{index:03d}.png');picture.thumbnail((480,320));x,y=cell%cols*480,cell//cols*340;sheet.paste(picture,(x,y));draw.text((x+6,y+321),f'{index:03d} /{index/60:.3f}s',fill='white')
    sheet.save(out/'contact.jpg',quality=95)
    assert profile.read_bytes()==source,'Source changed during actual production native capture'
    print(json.dumps({'profile_sha256':binding['profile_sha256'],'output':str(out),'frames':len(records)}))

if __name__=='__main__':main()
