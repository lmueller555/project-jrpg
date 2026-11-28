"""Register whole continuity drawings at the matching source-cell density.

ImageGen minimally redraws the complete figures. This helper preserves the
original registered composition through the declared full-cell resolution
ratio; it never fits occupied bounds or changes limbs.
"""
from pathlib import Path
import json,math,hashlib,importlib.util
import cv2,numpy as np
from PIL import Image
P=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('registration',P/'authoring/extract_register_atlases.py')
reg=importlib.util.module_from_spec(spec);spec.loader.exec_module(reg)
tasks=json.loads((P/'repairs/minimal_tasks.json').read_text())
reportpath=P/'registered_atlases/registration_report.json'
report=json.loads(reportpath.read_text());mapping={(r['kind'],r.get('index',r['phase'])):r for r in report}
high=json.loads((P/'authoring/actual_high_helmet_centres.json').read_text())
for ti,task in enumerate(tasks):
 oldname=f'transition_{ti+1:02d}';old=Image.open(P/f'atlases/{oldname}.png').convert('RGBA');newpath=P/'repairs'/Path(task['output']).name;new=Image.open(newpath).convert('RGBA');ow,oh=old.width/4,old.height/2;nw,nh=new.width/4,new.height
 obs=reg.SHEET_OBSERVATIONS[oldname];nominal=round(ow)/1024;uniform=math.dist(*obs['reference_dome_chord'])*nominal/math.dist(*obs['cell0_dome_chord'])
 for k,sample in enumerate(task['samples']):
  j=5+k;oldbox=[round(j%4*ow),round(j//4*oh),round((j%4+1)*ow),round((j//4+1)*oh)];cell=old.crop(oldbox);anchor=np.array([cell.width/2,cell.width*.9375])
  if sample['elevation']<55:
   measured,planned,_=reg.observed_cap_top(cell,sample,nominal,anchor);kind='actual opaque helmet-crown upper silhouette'
  else:
   measured=np.array(high[oldname]['points'][j]);r,u=reg.basis(sample['elevation'],sample['azimuth']);bob=-.025*math.cos(4*math.pi*sample['phase']/48);world=np.array([0,.22,1.65+bob]);planned=anchor+np.array([500*np.dot(r,world),-500*np.dot(u,world)])*nominal;kind='actual geometric steel crown center'
  oldorigin=planned-uniform*measured;box=[round(k*nw),0,round((k+1)*nw),round(nh)];complete=new.crop(box);ratio=complete.width/cell.width
  rigid_box=[(113,100,165,151),(107,130,159,180),(120,225,171,270)][ti];patch=reg.matte(cell.crop(rigid_box));patch=cv2.resize(patch,(round(patch.shape[1]*ratio),round(patch.shape[0]*ratio)),interpolation=cv2.INTER_CUBIC);expected=np.array(rigid_box[:2])*ratio;left=np.maximum(0,np.floor(expected-35)).astype(int);right=np.minimum(complete.size,np.ceil(expected+np.array(patch.shape[::-1])+35)).astype(int);gray=reg.matte(complete);roi=gray[left[1]:right[1],left[0]:right[0]];scores=cv2.matchTemplate(roi,patch,cv2.TM_CCOEFF_NORMED);_,score,_,loc=cv2.minMaxLoc(scores);actual=left+loc;offset=actual-expected;origin=oldorigin*ratio-uniform*offset;applied=np.round(origin).astype(int);
  rigid_observation={'article':'matching rigid anatomical-right pauldron patch','original_source_window':list(rigid_box),'new_source_match_top_left':actual.tolist(),'declared_cell_resolution_ratio':ratio,'correlation_score':score,'whole_pose_translation_correction':(-uniform*offset).tolist()}
  complete.putalpha(complete.getchannel('A').point(lambda a:0 if a<=16 else a));sampled=complete.convert('RGBa').resize((round(complete.width*uniform),round(complete.height*uniform)),Image.Resampling.LANCZOS).convert('RGBA');bounds=sampled.getchannel('A').point(lambda a:255 if a>16 else 0).getbbox();placed=[bounds[q]+applied[q%2] for q in range(4)];size=[complete.width,round(complete.width*1.5)];padding=[int(max(0,-placed[0]+4)),int(max(0,-placed[1]+4)),int(max(0,placed[2]-size[0]+4)),int(max(0,placed[3]-size[1]+4))];canvas=Image.new('RGBA',(size[0]+padding[0]+padding[2],size[1]+padding[1]+padding[3]));canvas.alpha_composite(sampled,tuple(applied+padding[:2]));dest=P/f'registered_atlases/transition/frame_{sample["index"]:03d}.png';canvas.save(dest)
  row={**sample,'file':str(dest.relative_to(P)),'canvas':list(canvas.size),'anchor':(anchor*ratio+padding[:2]).tolist(),'art_pixels_per_metre':500*nominal*ratio,'source_atlas':str(newpath.relative_to(P)),'source_sha256':reg.digest(newpath),'source_cell':box,'source_cell_rgba_sha256':hashlib.sha256(new.crop(box).tobytes()).hexdigest(),'uniform_whole_cell_scale':uniform,'whole_cell_origin':origin.tolist(),'padding_for_containment_only':padding,'matching_original_atlas':f'atlases/{oldname}.png','matching_original_atlas_sha256':reg.digest(P/f'atlases/{oldname}.png'),'matching_original_cell':oldbox,'source_cell_resolution_ratio':ratio,'rigid_pauldron_registration':rigid_observation,'rigid_sheet_calibration':{'method':'Inherited matching-phase actual rigid steel-brim density; reviewed new complete-source body/armor composition preserves original reference at declared full-cell resolution ratio. No body/foot bounds fit.','observations':obs,'uniform_scale':uniform},'observed_original_landmark':{'type':kind,'source':measured.tolist(),'physical_projection_plan':planned.tolist()},'sha256':reg.digest(dest),'construction':'Complete minimal ImageGen continuity drawing; uniform whole-cell sampling and original matching-phase composition carried across declared full-cell resolution only. No limbs/parts restored, warped or interpolated.'};mapping[('transition',sample['index'])]=row
reportpath.write_text(json.dumps(list(mapping.values()),indent=2)+'\n')
print('Registered9 complete minimal continuity drawings; earlier entry/far banks unchanged.')

