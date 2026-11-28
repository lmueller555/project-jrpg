"""Rigid-helmet density calibration and whole-figure registration only.

Never fits occupied height/foot bounds, edits limbs or builds anatomy. Raw
ImageGen masters stay intact. Observed helmet endpoints are actual artwork
measurements; Blender world points are explicit source-registration plans.
"""
from pathlib import Path
from hashlib import sha256
import math,json,shutil
import numpy as np
from PIL import Image,ImageDraw
import sys
REPO=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').exists());sys.path.insert(0,str(REPO))
from cinematic_bridge_ascent import actor_states_at
P=Path(__file__).resolve().parent.parent
REF=REPO/'assets/story/fire_veinhold_opening/shot07/characters/crown_soldier/frame_18.png'
REFERENCE_BRIM_POINTS=[[298,192],[466,180]]
REFERENCE_DIAMETER=math.dist(*REFERENCE_BRIM_POINTS)
# Manually observed opposing steel-brim extrema, excluding hair and shoulders.
# These measure one rigid article; they never prescribe body or boot size.
MEASURED={48:('first_batch/physical_048.png',[[490,315],[653,315]]),72:('first_batch/corrected_072.png',[[482,607],[684,609]]),96:('first_batch/time_096.png',[[427,907],[580,909]]),132:('first_batch/compact_132.png',[[450,962],[634,974]])}

def digest(p):return sha256(p.read_bytes()).hexdigest()
def basis(elevation,azimuth):
 e,a=map(math.radians,(elevation,azimuth));ray=np.array([math.sin(a)*math.cos(e),math.cos(a)*math.cos(e),math.sin(e)]);view=-ray;right=np.array([-1.,0,0]);right-=view*np.dot(right,view);right/=np.linalg.norm(right);up=np.cross(right,view);return right,up

def main():
 records=[];dest=P/'registered_samples/time_000.png';shutil.copyfile(REF,dest);records.append({'index':0,'file':str(dest.relative_to(P)),'canvas':[768,1024],'anchor':[384,960],'art_pixels_per_metre':500,'retained_approved_exact_bytes':True,'sha256':digest(dest),'source':str(REF),'source_sha256':digest(REF)})
 approved42=REPO/'assets/story/fire_veinhold_opening/shot07/characters/crown_soldier/frame_42.png';target42=P/'registered_samples/time_024.png';shutil.copyfile(approved42,target42);records.append({'index':24,'file':str(target42.relative_to(P)),'canvas':[768,1024],'anchor':[384,960],'art_pixels_per_metre':500,'retained_approved_exact_bytes':True,'sha256':digest(target42),'source':str(approved42),'source_sha256':digest(approved42)})
 for i,(relative,endpoints) in MEASURED.items():
  source=P/relative;im=Image.open(source).convert('RGBA');a=next(a for a in actor_states_at(i/60)['runners'] if a['id']=='crown_soldier');r,u=basis(a['view_elevation_degrees'],a['view_azimuth_degrees']);phi=2*math.pi*a['frame_index']/48;bob=-.025*math.cos(2*phi);world=np.array([0,.23,1.575+bob]);planned=[512+500*np.dot(r,world),960-500*np.dot(u,world)];center=np.mean(endpoints,axis=0);diam=math.dist(*endpoints);scale=REFERENCE_DIAMETER/diam;origin=np.asarray(planned)-scale*center;applied=tuple(round(v) for v in origin)
  im.putalpha(im.getchannel('A').point(lambda x:0 if x<=16 else x));sampled=im.convert('RGBa').resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS).convert('RGBA');canvas=Image.new('RGBA',(1024,1536));canvas.alpha_composite(sampled,applied);out=P/f'registered_samples/time_{i:03d}.png';canvas.save(out);bounds=sampled.getchannel('A').point(lambda x:255 if x>128 else 0).getbbox();placed=[bounds[j]+applied[j%2] for j in range(4)]
  records.append({'index':i,'phase':a['frame_index'],'local_time':i/60,'file':str(out.relative_to(P)),'canvas':[1024,1536],'anchor':[512,960],'art_pixels_per_metre':500,'sha256':digest(out),'source':relative,'source_sha256':digest(source),'observed_steel_brim_endpoints_source':endpoints,'observed_steel_brim_diameter_source':diam,'uniform_whole_master_scale':scale,'whole_master_origin':origin.tolist(),'applied_origin':list(applied),'planned_brim_center_exported':planned,'physical_brim_point_world':[float(x) for x in world],'opaque_bounds_diagnostic_only':placed,'method':'Uniform whole-source calibration from approved steel-brim size, followed by entire-figure placement using camera-projected physical brim anchor. No occupied-height/foot fitting, limb edits, warps or part composites.'})
 report={'reference':{'file':str(REF),'sha256':digest(REF),'observed_steel_brim_endpoints_exported':REFERENCE_BRIM_POINTS,'observed_steel_brim_diameter':REFERENCE_DIAMETER,'declared_art_pixels_per_metre':500},'records':records};(P/'registered_samples/calibration_report.json').write_text(json.dumps(report,indent=2)+'\n')
 grid=Image.new('RGB',(3*480,2*340),'#152335');draw=ImageDraw.Draw(grid)
 for n,rec in enumerate(records):
  i=rec['index'];a=next(a for a in actor_states_at(i/60)['runners'] if a['id']=='crown_soldier');im=Image.open(P/rec['file']).convert('RGBA');s=a['pixels_per_metre']/500;image=im.convert('RGBa').resize((round(im.width*s),round(im.height*s)),Image.Resampling.LANCZOS).convert('RGBA');frame=Image.new('RGBA',(960,640),'#283a49');origin=[round(a['ground_anchor'][j]-rec['anchor'][j]*s) for j in range(2)];frame.alpha_composite(image,origin);frame.convert('RGB').save(f'/tmp/crown_ascent_registered_native_{i:03d}.png');x=n%3*480;y=n//3*340;grid.paste(frame.convert('RGB').resize((480,320),Image.Resampling.NEAREST),(x,y));draw.text((x+10,y+321),f'{i}/60, phase{a["frame_index"]}',fill='white')
 grid.save('/tmp/crown_ascent_registered_first_batch_native.jpg');print(json.dumps({'reference_brim':REFERENCE_DIAMETER,'scales':{r['index']:r.get('uniform_whole_master_scale',1) for r in records},'clipped':[r['index'] for r in records if 'opaque_bounds_diagnostic_only' in r and (min(r['opaque_bounds_diagnostic_only'][:2])<0 or r['opaque_bounds_diagnostic_only'][2]>1024 or r['opaque_bounds_diagnostic_only'][3]>1536)]}))
if __name__=='__main__':main()
