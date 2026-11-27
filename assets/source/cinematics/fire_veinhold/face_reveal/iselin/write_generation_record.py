"""Retain Iselin's complete-drawing source and reference provenance."""
from pathlib import Path
from hashlib import sha256
import json

FOLDER=Path(__file__).resolve().parent
ROOT=FOLDER.parents[5]
KEY_ID='exec-375aa0aa-ae81-4299-a39b-5ca22c452d37'
BATCHES={0:'exec-8d341d18-10d9-4c41-9947-4c672656244f',
         4:'exec-0401f566-057c-4aba-bdfb-611491a650e7',
         8:'exec-01e707fb-6f7c-4917-b2d3-3f8c1abb679d',
         12:'exec-3835f26c-3999-4237-9367-e9a24f7739fc',
         16:'exec-940745be-d301-4217-884c-e478ff9b81b9',
         20:'exec-34bc19d8-30e6-436b-8a91-727f0f62afb2'}
REPAIRS={1:'exec-cc5068fb-d64b-48fa-8aec-1806706d6db7',
         2:'exec-26f19d9a-df15-423f-8bb6-eba18c2d571d',
         3:'exec-a51ba1f8-2f19-47d9-a2e1-355d333a9888',
         13:'exec-2487786f-313c-45dc-8a9e-76291e564e74',
         14:'exec-9c1b3549-9633-4ee4-a760-1929fa1117fb',
         15:'exec-46014ca3-c915-4dab-94e2-63c35615e456'}


def digest(path):return sha256(path.read_bytes()).hexdigest()


def main():
    records=[]
    key_refs=['assets/source/cinematics/fire_veinhold/continuation/materials/frozen_bridge_final.png',
              'assets/source/portraits/eldenmere/iselin_master.png',
              'assets/story/fire_veinhold_opening/shot06/characters/iselin/frame_00.png']
    for phase,generation in [('keys',KEY_ID),*BATCHES.items(),*[(f'repair{key}',value)for key,value in REPAIRS.items()]]:
        if phase=='keys':
            filename='keys_00_06_12_18.png';prompt='keys_prompt.txt';refs=key_refs
        elif isinstance(phase,int):
            filename=f'batch_{phase:02d}_{phase+3:02d}.png';prompt=filename.replace('.png','_prompt.txt')
            ref={0:'00',4:'06',8:'07',12:'12',16:'18',20:'19'}[phase]
            refs=[f'key_{ref}_reference.png']
            if phase in (0,12):refs+=['keys_00_06_12_18.png']
            if phase in (8,20):refs+=[f'key_{12 if phase==8 else 0:02d}_reference.png']
        else:
            index=int(phase[6:]);filename=f'repairs/frame_{index:02d}.png';prompt=filename.replace('.png','_prompt.txt')
            if index in (3,15):refs=[f'repairs/frame_{index-1:02d}.png',f'production_{index+1:02d}_reference.png']
            else:
                first=0 if index<12 else 12
                refs=[f'production_{first:02d}_reference.png',f'production_{first+3:02d}_reference.png']
        records.append({'generator':'image_gen','generation_id':generation,
            'generated_original':f'/workspace/generated_images/{generation}.png',
            'source':filename,'source_sha256':digest(FOLDER/filename),'prompt':prompt,
            'prompt_sha256':digest(FOLDER/prompt),'references':refs})
    record={'version':1,'actor':'iselin','facing':'front',
        'purpose':'Full-body painted cinematic frontal run; the selected source bank has 24 complete drawings in a 400ms cycle.',
        'style':'Natural human proportions and detailed painted materials matching frozen guards, translated from Iselin identity references.',
        'near':'anatomical_right','far':'anatomical_left',
        'costume_sides':{'mantle':'anatomical_right / viewer_left','braid':'anatomical_left / viewer_right'},
        'active_selection':'source_art_24.json',
        'generated_masters':records,
        'technical_alpha_export':{'source':'repairs/frame_02.png','output':'repairs/frame_02_alpha_clean.png',
            'method':'Set alpha<16 to zero; retain every RGB byte and alpha>=16 unchanged. Removes nearly transparent generator fringe; no shape, anatomy, color or face paint.',
            'source_sha256':digest(FOLDER/'repairs/frame_02.png'),
            'output_sha256':digest(FOLDER/'repairs/frame_02_alpha_clean.png')},
        'history':'Original atlas cells1/2/3/13/14/15 remain retained but active profiles select the individual complete-pose repairs.'}
    (FOLDER/'production_generation_24.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':main()
