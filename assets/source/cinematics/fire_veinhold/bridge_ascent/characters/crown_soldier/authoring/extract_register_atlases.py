"""Extract complete atlas cells and register whole figures from painted helmets.

ImageGen owns every complete drawing. This helper only crops declared whole
cells, measures a rigid article against approved art, samples each entire
figure uniformly and pads transparent canvas to avoid clipping. No occupied
height fitting, anatomy interpolation or detached body parts.
"""
from pathlib import Path
from hashlib import sha256
import argparse,json,math,sys
import cv2,numpy as np
from PIL import Image,ImageDraw
REPO=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').exists());sys.path.insert(0,str(REPO))
from cinematic_bridge_ascent import actor_states_at
P=Path(__file__).resolve().parent.parent
REFERENCE=json.loads((P/'registered_samples/calibration_report.json').read_text())
REF_DIAMETER=REFERENCE['reference']['observed_steel_brim_diameter']

def digest(p):return sha256(p.read_bytes()).hexdigest()
def basis(elev,az):
 e,a=map(math.radians,(elev,az));ray=np.array([math.sin(a)*math.cos(e),math.cos(a)*math.cos(e),math.sin(e)]);view=-ray;right=np.array([-1.,0,0]);right-=view*np.dot(right,view);right/=np.linalg.norm(right);return right,np.cross(right,view)
def brim_plan(sample):
 r,u=basis(sample['elevation'],sample['azimuth']);phi=2*math.pi*sample['phase']/48;bob=-.025*math.cos(2*phi);w=np.array([0,.23,1.575+bob]);return np.array([512+500*np.dot(r,w),960-500*np.dot(u,w)])
def matte(image):
 im=image.copy();im.putalpha(im.getchannel('A').point(lambda x:0 if x<=16 else x));bg=Image.new('RGBA',im.size,'#1a2b40');bg.alpha_composite(im);return np.asarray(bg.convert('L'))
def template(angle):
 # These references are already rigid-calibrated to the approved steel brim.
 keys=[(0,0),(30,48),(53,72),(70,96),(82,132)];_,index=min(keys,key=lambda k:abs(k[0]-angle));index=0 if angle<25 else index;row=next(r for r in REFERENCE['records'] if r['index']==index);im=Image.open(P/row['file']).convert('RGBA')
 if index==0:
  canvas=Image.new('RGBA',(1024,1536));canvas.alpha_composite(im,(128,0));im=canvas;center=np.mean(REFERENCE['reference']['observed_steel_brim_endpoints_exported'],axis=0)+[128,0]
 else:center=np.array(row['planned_brim_center_exported'])
 # The cap/brim patch excludes hands, shield and most costume. High views
 # include the actual crown; low views retain the curved cap and full brim.
 top=110 if angle<45 else 95;bottom=18 if angle<45 else 95;box=(round(center[0]-100),round(center[1]-top),round(center[0]+100),round(center[1]+bottom));patch=matte(im.crop(box));relative=center-np.array(box[:2]);return patch,relative,index

def fit_helmet(cell,sample,nominal,anchor,fixed_factor=None):
 patch,refcenter,key=template(sample['elevation']);pixels=matte(cell);expected=anchor+(brim_plan(sample)-[512,960])*nominal;rx=cell.width*.17;ry=cell.height*.18;best=None
 for factor in ([fixed_factor] if fixed_factor is not None else np.linspace(.65,1.75,56)):
  scale=nominal*factor;size=(max(8,round(patch.shape[1]*scale)),max(8,round(patch.shape[0]*scale)));t=cv2.resize(patch,size,interpolation=cv2.INTER_AREA if scale<1 else cv2.INTER_CUBIC);x0=max(0,math.floor(expected[0]-rx-refcenter[0]*scale));y0=max(0,math.floor(expected[1]-ry-refcenter[1]*scale));x1=min(cell.width,math.ceil(expected[0]+rx+(patch.shape[1]-refcenter[0])*scale));y1=min(cell.height,math.ceil(expected[1]+ry+(patch.shape[0]-refcenter[1])*scale));roi=pixels[y0:y1,x0:x1]
  if roi.shape[0]<t.shape[0] or roi.shape[1]<t.shape[1]:continue
  scores=cv2.matchTemplate(roi,t,cv2.TM_CCOEFF_NORMED);_,score,_,loc=cv2.minMaxLoc(scores);center=np.array([x0+loc[0],y0+loc[1]])+refcenter*scale
  if best is None or score>best['score']:best={'score':float(score),'template_to_source_scale':float(scale),'observed_brim_center_source':center.tolist(),'template_key_index':key}
 if best is None:raise ValueError('No actual helmet measurement')
 return best,expected

# Reviewed rigid features, never occupied body/foot bounds. One calibration
# applies to the entire generated sheet so matching noise cannot pulse a body.
SHEET_OBSERVATIONS={'late01': {'reference_dome_chord': [[298, 192], [466, 180]],
            'cell0_dome_chord': [[196, 128], [328, 128]],
            'measurement_kind': 'rigid_steel_brim_chord',
            'measurement_uncertainty_source_pixels': 2,
            'review': 'Actual painted brim endpoints reviewed at source1:1 in '
                      '/tmp/crown_late_raw_head_grid.jpg; one entire-strip density, never '
                      'foot/body fitting.'},
 'late02_clean': {'reference_dome_chord': [[298, 192], [466, 180]],
                  'cell0_dome_chord': [[202, 151], [325, 151]],
                  'measurement_kind': 'rigid_steel_brim_chord',
                  'measurement_uncertainty_source_pixels': 2,
                  'review': 'Actual painted brim endpoints reviewed at source1:1 in '
                            '/tmp/crown_late_raw_head_grid.jpg; one entire-strip density, never '
                            'foot/body fitting.'},
 'late03': {'reference_dome_chord': [[298, 192], [466, 180]],
            'cell0_dome_chord': [[243, 255], [335, 255]],
            'measurement_kind': 'rigid_steel_brim_chord',
            'measurement_uncertainty_source_pixels': 2,
            'review': 'Actual painted brim endpoints reviewed at source1:1 in '
                      '/tmp/crown_late_raw_head_grid.jpg; one entire-strip density, never '
                      'foot/body fitting.'},
 'transition_01': {'reference_dome_chord': [[298, 192], [466, 180]],
                   'cell0_dome_chord': [[160, 90], [241, 90]],
                   'measurement_kind': 'rigid_steel_brim_chord',
                   'measurement_uncertainty_source_pixels': 2,
                   'review': 'Actual first-cell steel-brim extrema inspected in '
                             '/tmp/crown_all_atlas_helmet_measurements.jpg; a single rigid size '
                             'applies to entire sheet, no body/foot fit.'},
 'transition_02': {'reference_dome_chord': [[298, 192], [466, 180]],
                   'cell0_dome_chord': [[148, 110], [240, 110]],
                   'measurement_kind': 'rigid_steel_brim_chord',
                   'measurement_uncertainty_source_pixels': 2,
                   'review': 'Actual first-cell steel-brim extrema inspected in '
                             '/tmp/crown_all_atlas_helmet_measurements.jpg; a single rigid size '
                             'applies to entire sheet, no body/foot fit.'},
 'transition_03': {'reference_dome_chord': [[298, 192], [466, 180]],
                   'cell0_dome_chord': [[170, 205], [237, 204]],
                   'measurement_kind': 'rigid_steel_brim_chord',
                   'measurement_uncertainty_source_pixels': 2,
                   'review': 'Actual first-cell steel-brim extrema inspected in '
                             '/tmp/crown_all_atlas_helmet_measurements.jpg; a single rigid size '
                             'applies to entire sheet, no body/foot fit.'},
 'transition_04': {'reference_dome_chord': [[298, 192], [466, 180]],
                   'cell0_dome_chord': [[171, 246], [236, 243]],
                   'measurement_kind': 'rigid_steel_brim_chord',
                   'measurement_uncertainty_source_pixels': 2,
                   'review': 'Actual first-cell steel-brim extrema inspected in '
                             '/tmp/crown_all_atlas_helmet_measurements.jpg; a single rigid size '
                             'applies to entire sheet, no body/foot fit.'},
 'transition_05': {'reference_dome_chord': [[298, 192], [466, 180]],
                   'cell0_dome_chord': [[163, 292], [229, 291]],
                   'measurement_kind': 'rigid_steel_brim_chord',
                   'measurement_uncertainty_source_pixels': 2,
                   'review': 'Actual first-cell steel-brim extrema inspected in '
                             '/tmp/crown_all_atlas_helmet_measurements.jpg; a single rigid size '
                             'applies to entire sheet, no body/foot fit.'},
 'transition_06': {'reference_dome_chord': [[298, 192], [466, 180]],
                   'cell0_dome_chord': [[145, 294], [234, 298]],
                   'measurement_kind': 'rigid_steel_brim_chord',
                   'measurement_uncertainty_source_pixels': 2,
                   'review': 'Actual first-cell steel-brim extrema inspected in '
                             '/tmp/crown_all_atlas_helmet_measurements.jpg; a single rigid size '
                             'applies to entire sheet, no body/foot fit.'},
 'overhead_00': {'reference_dome_chord': [[298, 192], [466, 180]],
                 'cell0_dome_chord': [[125, 146], [203, 150]],
                 'measurement_kind': 'rigid_steel_brim_chord',
                 'measurement_uncertainty_source_pixels': 2,
                 'review': 'Actual first-cell steel-brim extrema inspected in '
                           '/tmp/crown_all_atlas_helmet_measurements.jpg; a single rigid size '
                           'applies to entire sheet, no body/foot fit.'},
 'overhead_01': {'reference_dome_chord': [[298, 192], [466, 180]],
                 'cell0_dome_chord': [[123, 157], [205, 159]],
                 'measurement_kind': 'rigid_steel_brim_chord',
                 'measurement_uncertainty_source_pixels': 2,
                 'review': 'Actual first-cell steel-brim extrema inspected in '
                           '/tmp/crown_all_atlas_helmet_measurements.jpg; a single rigid size '
                           'applies to entire sheet, no body/foot fit.'},
 'overhead_02': {'reference_dome_chord': [[298, 192], [466, 180]],
                 'cell0_dome_chord': [[117, 162], [201, 164]],
                 'measurement_kind': 'rigid_steel_brim_chord',
                 'measurement_uncertainty_source_pixels': 2,
                 'review': 'Actual first-cell steel-brim extrema inspected in '
                           '/tmp/crown_all_atlas_helmet_measurements.jpg; a single rigid size '
                           'applies to entire sheet, no body/foot fit.'},
 'transition_00_modelv2': {'reference_dome_chord': [[313, 145], [442, 142]],
                           'reference_pauldron_centres': [[245, 270], [494, 275]],
                           'cell0_dome_chord': [[150, 60], [219, 60]],
                           'cell0_pauldron_centres': [[129, 128], [250, 134]],
                           'review': 'Actual matching-phase steel dome and pauldron centres '
                                     'inspected in /tmp/crown_atlas_v2_features.jpg; one '
                                     'whole-sheet physical-density calibration.'},
 'transition_00': {'reference_dome_chord': [[313, 145], [442, 142]],
                   'reference_pauldron_centres': [[245, 270], [494, 275]],
                   'cell0_dome_chord': [[160, 55], [219, 55]],
                   'cell0_pauldron_centres': [[139, 118], [255, 118]],
                   'review': 'Actual painted steel dome and rigid shoulder centres inspected at '
                             'source resolution; source-only observation, no desired anatomy '
                             'coordinates.'}}

def top_plan(sample):
 r,u=basis(sample['elevation'],sample['azimuth']);phi=2*math.pi*sample['phase']/48;bob=-.025*math.cos(2*phi);candidates=[]
 for centre,radii in [([0,.22,1.65+bob],[.14,.16,.14]),([0,.23,1.575+bob],[.17,.18,.018])]:
  radii=np.asarray(radii);point=np.asarray(centre)+radii*radii*u/np.linalg.norm(radii*u);candidates.append(np.array([512+500*np.dot(r,point),960-500*np.dot(u,point)]))
 return min(candidates,key=lambda p:p[1])

def observed_cap_top(cell,sample,nominal,anchor):
 planned=anchor+(top_plan(sample)-[512,960])*nominal
 x0=max(0,round(planned[0]-cell.width*.13));x1=min(cell.width,round(planned[0]+cell.width*.13));y0=max(0,round(planned[1]-cell.height*.18));y1=min(cell.height,round(planned[1]+cell.height*.16));alpha=np.asarray(cell)[:,:,3];ys,xs=np.where(alpha[y0:y1,x0:x1]>128)
 if not len(ys):raise ValueError('No actual crown silhouette')
 top=int(ys.min());pick=ys<=top+1;return np.array([float(np.median(xs[pick])+x0),float(top+y0)]),planned,[x0,y0,x1,y1]

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--names',nargs='*');args=parser.parse_args();tasks=json.loads((P/'atlases/tasks.json').read_text());records=[];outfolder=P/'registered_atlases';outfolder.mkdir(exist_ok=True)
 for task in tasks:
  if args.names and task['name'] not in args.names:continue
  path=P/('repairs' if task['name'].startswith('late') else 'atlases')/Path(task['output']).name
  if not path.exists():continue
  atlas=Image.open(path).convert('RGBA');cw=atlas.width/task['columns'];ch=atlas.height/task['rows'];cells=[]
  for n,sample in enumerate(task['samples']):
   box=[round(n%4*cw),round(n//4*ch),round((n%4+1)*cw),round((n//4+1)*ch)];cell=atlas.crop(box);isover=task['kind']=='overhead';nominal=cell.width/(768 if isover else 1024);anchor=np.array([cell.width/2,cell.width/2 if isover else cell.width*.9375]);fit,_=fit_helmet(cell,sample,nominal,anchor);cells.append((sample,box,cell,nominal,anchor,fit))
  observations=SHEET_OBSERVATIONS.get(task['name'])
  if observations:
   nominal=cells[0][3];ratios=[math.dist(*observations['reference_dome_chord'])*nominal/math.dist(*observations['cell0_dome_chord'])]
   if 'cell0_pauldron_centres' in observations:ratios.append(math.dist(*observations['reference_pauldron_centres'])*nominal/math.dist(*observations['cell0_pauldron_centres']))
   uniform=float(ratios[0]);calibration={'method':'Fixed whole-sheet density from actual approved rigid steel helmet chord; no per-pose scale fitting','observations':observations,'feature_scale_estimates':ratios,'uniform_scale':uniform,'review_state':'rigid_features_measured'}
  else:
   estimates=[nominal/fit['template_to_source_scale'] for _,_,_,nominal,_,fit in cells if fit['score']>.6];uniform=float(np.median(estimates));calibration={'method':'Provisional fixed whole-sheet median of actual helmet patch measurements; requires native review','uniform_scale':uniform,'review_state':'pending_rigid_feature_review'}
  for sample,box,cell,nominal,anchor,_ in cells:
   fit,brim=fit_helmet(cell,sample,nominal,anchor,fixed_factor=1/uniform)
   if sample['elevation']<55:
    observed,planned,search=observed_cap_top(cell,sample,nominal,anchor)
    if task['kind']=='transition' and 26<=sample['index']<48:
     u=max(0,min(1,(sample['index']-26)/22));ease=u*u*(3-2*u);planned=planned-np.array([33.64166945,20.88728346])*nominal*(1-ease)
    landmark={'type':'actual opaque helmet-crown upper silhouette','source':observed.tolist(),'search_window':search,'physical_projection_plan':planned.tolist()}
   else:
    observations_high=json.loads((P/'authoring/actual_high_helmet_centres.json').read_text());row_high=observations_high.get(task['name'])
    if row_high and task['kind']=='transition':
     if row_high['source_sha256']!=digest(path):raise ValueError('High helmet observation source changed')
     observed=np.asarray(row_high['points'][task['samples'].index(sample)]);r,u=basis(sample['elevation'],sample['azimuth']);bob=-.025*math.cos(4*math.pi*sample['phase']/48);world=np.array([0,.22,1.65+bob]);planned=anchor+np.array([500*np.dot(r,world),-500*np.dot(u,world)])*nominal
    else:observed=np.asarray(fit['observed_brim_center_source']);planned=brim
    landmark={'type':'actual geometric helmet crown center' if row_high and task['kind']=='transition' else 'actual rigid helmet patch at fixed sheet density','source':observed.tolist(),'physical_projection_plan':planned.tolist()}
   origin=planned-uniform*observed;applied=np.round(origin).astype(int);alpha_cell=cell.copy();alpha_cell.putalpha(alpha_cell.getchannel('A').point(lambda a:0 if a<=16 else a));size=[max(1,round(v*uniform)) for v in cell.size];sampled=alpha_cell.convert('RGBa').resize(size,Image.Resampling.LANCZOS).convert('RGBA');bounds=sampled.getchannel('A').point(lambda a:255 if a>16 else 0).getbbox();targetsize=[cell.width,cell.width if task['kind']=='overhead' else round(cell.width*1.5)];placed=[bounds[j]+applied[j%2] for j in range(4)];padding=[int(max(0,-placed[0]+4)),int(max(0,-placed[1]+4)),int(max(0,placed[2]-targetsize[0]+4)),int(max(0,placed[3]-targetsize[1]+4))];canvas=Image.new('RGBA',(targetsize[0]+padding[0]+padding[2],targetsize[1]+padding[1]+padding[3]));canvas.alpha_composite(sampled,tuple(applied+padding[:2]));name=f'phase_{sample["phase"]:02d}' if task['kind']=='overhead' else f'frame_{sample["index"]:03d}';folder=outfolder/task['kind'];folder.mkdir(exist_ok=True);output=folder/(name+'.png');canvas.save(output)
   record={**sample,'file':output.relative_to(P).as_posix(),'canvas':list(canvas.size),'anchor':(anchor+padding[:2]).tolist(),'art_pixels_per_metre':500*nominal,'source_atlas':path.relative_to(P).as_posix(),'source_sha256':digest(path),'source_cell':box,'source_cell_rgba_sha256':sha256(cell.tobytes()).hexdigest(),'rigid_sheet_calibration':calibration,'helmet_fit':fit,'observed_landmark':landmark,'uniform_whole_cell_scale':uniform,'whole_cell_origin':origin.tolist(),'padding_for_containment_only':padding,'sha256':digest(output),'construction':'Complete whole-figure cell, one uniform rigid density for whole sheet, entire-pose translation only; no occupied-height fit or body/limb transforms.'};records.append(record)
   debug=Image.new('RGBA',cell.size,'#172436');debug.alpha_composite(alpha_cell);pen=ImageDraw.Draw(debug);x,y=observed;pen.ellipse((x-4,y-4,x+4,y+4),outline='yellow',width=2);debug.convert('RGB').save(f'/tmp/crown_{task["name"]}_{task["samples"].index(sample):02d}_rigid.jpg')
 reportpath=outfolder/'registration_report.json';existing=json.loads(reportpath.read_text()) if reportpath.exists() else[];mapping={(r['kind'],r.get('index',r['phase'])):r for r in existing}
 for r in records:mapping[(r['kind'],r.get('index',r['phase']))]=r
 reportpath.write_text(json.dumps(list(mapping.values()),indent=2)+'\n');print(json.dumps([{'kind':r['kind'],'frame':r.get('index',r['phase']),'score':round(r['helmet_fit']['score'],3),'scale':round(r['uniform_whole_cell_scale'],3),'canvas':r['canvas']} for r in records]))
if __name__=='__main__':main()
