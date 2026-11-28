"""Register complete generated figures by inspected rigid armor width and crown location.

No limb/part edits, silhouettes resized to height, or procedural body art.  The
only final-pixel operations are whole-cell crop, alpha floor<=16, uniform sampling
and translation.  NCC locates the dark crown texture; it NEVER determines scale.
"""
from pathlib import Path
from hashlib import sha256
import json,math,sys
import cv2,numpy as np
from PIL import Image,ImageDraw
S=Path(__file__).resolve().parent;ROOT=S.parents[6];sys.path.insert(0,str(ROOT))
OUT=ROOT/'assets/story/fire_veinhold_opening/shot08/characters/lucan'
CANVAS=(1024,1536);ANCHOR=(512,960)
# Manual source observations: exposed rigid cap pair, excluding upper arms/shield.
# Values are approximate reviewed physical-size registration references, not gait
# targets.  Final native review still controls adoption.
SELECTION={
 'transition':[(36,'transition_036_043.png',198),(44,'transition_044_051.png',185),
 (52,'transition_052_059_alpha.png',220),(60,'transition_060_067.png',222),
 (68,'transition_068_075.png',220),(76,'transition_076_083b.png',210),
 (84,'transition_084_091b.png',210),(92,'transition_092_099b.png',210),
 (100,'transition_100_107b.png',210)],
 'overhead':[(0,'overhead_000_007b.png',184),(8,'overhead_008_015.png',215),
 (16,'overhead_016_023.png',220),(24,'overhead_024_031.png',190),
 (32,'overhead_032_039_alpha.png',210),(40,'overhead_040_047.png',210)]}

def crown_match(image):
    template=Image.open(S/'model_key_90_geometry.png').convert('RGB').crop((540,595,725,785))
    template=cv2.cvtColor(np.array(template),cv2.COLOR_RGB2GRAY)
    gray=cv2.cvtColor(np.array(image.convert('RGB')),cv2.COLOR_RGB2GRAY)
    h,w=gray.shape;left,right=int(w*.22),int(w*.80)
    best=None
    for scale in np.linspace(.22,.9,70):
        sample=cv2.resize(template,None,fx=scale,fy=scale)
        if sample.shape[1]>=right-left or sample.shape[0]>=h:continue
        response=cv2.matchTemplate(gray[:,left:right],sample,cv2.TM_CCOEFF_NORMED)
        _,score,_,point=cv2.minMaxLoc(response)
        if best is None or score>best['score']:
            best={'point':[left+point[0]+sample.shape[1]/2,point[1]+sample.shape[0]/2],
                  'score':score,'matched_core_size':[sample.shape[1],sample.shape[0]]}
    return best

def export(record):
    source=ROOT/record['source'];image=Image.open(source).convert('RGBA').crop(record['cell'])
    image.putalpha(image.getchannel('A').point(lambda a:0 if a<=16 else a))
    scale=record['scale'];image=image.convert('RGBa').resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.LANCZOS).convert('RGBA')
    result=Image.new('RGBA',CANVAS);result.alpha_composite(image,tuple(round(v) for v in record['origin']));return result

def main():
    if (S/'selected_performance.json').is_file():
        from rebuild_selected import main as rebuild_selected
        rebuild_selected()
        return
    from cinematic_bridge_ascent import actor_states_at
    guides={r['index']:r for r in json.loads((S/'guide_frames/transition_guide_targets.json').read_text())}
    records=[]
    for kind,masters in SELECTION.items():
        for start,name,shoulder_span in masters:
            source=S/name;master=Image.open(source).convert('RGBA');w,h=master.width//4,master.height//2
            scale=270/shoulder_span
            for cell,index in enumerate(range(start,start+8)):
                box=[cell%4*w,cell//4*h,(cell%4+1)*w,(cell//4+1)*h];image=master.crop(box)
                match=crown_match(image)
                target=[512,1040] if kind=='overhead' else [v*2 for v in guides[index]['guide_landmark_targets']['head_centre']]
                origin=[target[a]-match['point'][a]*scale for a in(0,1)]
                record={'kind':kind,'index':index,'gait_frame':index%48,'source':source.relative_to(ROOT).as_posix(),
                    'source_sha256':sha256(source.read_bytes()).hexdigest(),'cell':box,'scale':scale,'origin':origin,
                    'alpha_floor':16,'rigid_registration':{'observed_main_pauldron_pair_span':shoulder_span,'target_main_pauldron_pair_span':270,'main_cranium_reference_band':[120,135]},
                    'crown_location_match':match,'guide_head_centre':target,
                    'method':'Uniform completefigure scale from inspected rigid pauldron pair; crown texture NCC locates complete image only, never determines density.'}
                result=export(record);path=OUT/f'{kind}_{index:03d}.png';result.save(path);record['output_sha256']=sha256(path.read_bytes()).hexdigest();records.append(record)
    from register_special import apply as apply_special
    repaired=apply_special()
    replaced={r['index'] for r in repaired}
    records=[r for r in records if r['kind']!='transition' or r['index'] not in replaced]+repaired
    (S/'bank_registration.json').write_text(json.dumps(records,indent=2)+'\n')
    early=json.loads((S/'early_registration.json').read_text());transition=[]
    for i in range(133):
        if i<16:
            transition.append({'index':i,'file':f'../../../shot07/characters/lucan/frame_{i:02d}.png','canvas':[768,1024],'anchor':[384,960],'gait_frame':i})
        elif i<108:
            transition.append({'index':i,'file':f'transition_{i:03d}.png','gait_frame':i%48})
        else:
            transition.append({'index':i,'file':f'overhead_{i%48:03d}.png','gait_frame':i%48,'source_view_degrees':90,'reuse':'matching phase from view-equivalent overhead interval; actual native overlap reviewed separately'})
    cycle=[{'file':f'overhead_{i:03d}.png','gait_frame':i} for i in range(48)]
    files=set(r['file'] for r in transition+cycle)
    profile={'version':1,'actor':'lucan','canvas':list(CANVAS),'anchor':list(ANCHOR),'art_pixels_per_metre':500,
        'source_state':'whole_figure_image_authored','transition_frames':transition,'overhead_cycle':{'frames':cycle},
        'source_sha256':{f:sha256((OUT/f).resolve().read_bytes()).hexdigest() for f in sorted(files)}}
    (OUT/'actorperformance.json').write_text(json.dumps(profile,indent=2)+'\n')
    # Final early frames reference approved PNGs directly; padded trial exports
    # and partial review manifests are not production inputs.
    for index in range(16):
        (OUT/f'transition_{index:03d}.png').unlink(missing_ok=True)
    (OUT/'actorperformance.partial.json').unlink(missing_ok=True)
    # Separate actual native frames; no cinematic backdrop or fitted thumbnails.
    proof=Path('/tmp/lucan_ascent_native_review');proof.mkdir(exist_ok=True)
    for index in(23,24,27,28,30,31,32,33,34,35,36,37,39,40,43,44,47,48,51,52,59,60,67,68,75,76,83,84,91,92,99,100,107,108,109,120,132,133,144,168,180):
        state=actor_states_at(index/60)['runners'][0];phase=state['frame_index'];row=transition[index] if index<133 else cycle[phase]
        figure=Image.open((OUT/row['file']).resolve()).convert('RGBA');factor=state['scale'];anchor=row.get('anchor',ANCHOR)
        figure=figure.convert('RGBa').resize((max(1,round(figure.width*factor)),max(1,round(figure.height*factor))),Image.Resampling.LANCZOS).convert('RGBA')
        result=Image.new('RGBA',(960,640),'#203040');root=state['ground_anchor'];result.alpha_composite(figure,(round(root[0]-anchor[0]*factor),round(root[1]-anchor[1]*factor)));result.convert('RGB').save(proof/f'native_{index:03d}.png')
    sheet=Image.new('RGB',(1600,320*7),'#203040');d=ImageDraw.Draw(sheet)
    samples=[23,24,27,28,30,31,32,35,36,39,43,44,47,48,51,52,59,60,67,68,75,76,83,84,99,100,107,108]
    for c,index in enumerate(samples):
        im=Image.open(proof/f'native_{index:03d}.png');im=im.resize((400,267),Image.Resampling.LANCZOS);x,y=c%4*400,c//4*320;sheet.paste(im,(x,y));d.text((x+5,y+270),f'{index} /{index/60:.3f}s',fill='white')
    sheet.save('/tmp/lucan_full_native_contact.jpg',quality=95)
    print('Exported complete133transition and48overhead profile; actual native proof /tmp/lucan_full_native_contact.jpg')

if __name__=='__main__':main()
