"""Read-only actualsource diagnostic; never edits production inputs."""
from pathlib import Path
from PIL import Image,ImageDraw
from hashlib import sha256
from statistics import median
import numpy as np,json
B=Path(__file__).resolve().parents[3];P=B/'batches/overhead_000_015_validated_chain/outer_measurement_audit';bindings=json.loads((P/'input_binding.json').read_text())['rows'];additional=json.loads((P/'additional_input_binding.json').read_text());records={str(r['index']):r for r in bindings};records.update({r['name']:r for r in additional})
# Visible convex attached cranial-cap boundaries, excluding detached upstream
# waves, braid and jewelry. Bony skull edges are hidden under hair. These are
# manually observed source features with explicit uncertainty, never NCC boxes.
manual={
 '71':([101,195],[190,195],6,'Left cap boundary blends into attached upwind hair, right boundary partly abuts jewel attachment; width is approximate.'),
 '72':([94,213],[179,213],5,'Visible rounded attached cap; right boundary partly hidden by jewel/forward braid root.'),
 '87':([93,214],[177,214],5,'Rounded cap edges, excluding separate left hair loops and imageRIGHT braid.'),
 '88':([83,209],[178,209],4,'Convex cap outer edges are clearer than the internal whorl; braid/jewel excluded.'),
 '103':([82,209],[179,209],4,'Same convex cap family as88; excludes stray loops and star/pearl clasp.'),
 '104':([91,207],[165,207],4,'Smaller source cap than88/103; excludes imageRIGHT braid and star clasp.'),
 '117':([95,209],[168,209],4,'Rounded white cap outer contour; right contour partly meets braid/clasp.'),
 '118':([642,700],[1044,700],15,'Large single drawing. Convex attached cap contour has fine loose fringe; exclude far upstream hair and star clasp.'),
 'frozen55':([247,115],[342,115],8,'Approved oblique/front head reference: left parietal boundary merges into windblown bangs, so much less precise than overhead. Face/skin width is not used.'),
 'overhead32':([111,180],[207,180],4,'Frozen overhead calibration: clear convex attached cap, excluding separate left loops and imageRIGHT braid/jewel.'),
 'alternate72':([104,167],[179,167],5,'Alternate unselected view: attached convex cap is narrower in sourcepixels; excludes left loose loops and imageRIGHT braid/jewel.')}
result=[]
for key,(left,right,uncertainty,note) in manual.items():
 record=records[key];source=B/record['source'];digest=sha256(source.read_bytes()).hexdigest()
 if digest!=record['source_sha256']:raise ValueError('Changed bound source '+key)
 sample=Image.open(source).crop(tuple(record['cell'])).convert('RGBA');width=right[0]-left[0];density=record['current_density_scale'];a=np.asarray(sample.getchannel('A'));yy,xx=np.nonzero(a>128);bounds=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)];mid=[(left[0]+right[0])/2,(left[1]+right[1])/2]
 row={**record,'label':key,'observed_feature':'Horizontal width of convex attached hair-covered cranial cap; estimated skull-envelope proxy. Actual bony skull is occluded; loose trailing hair, braid and jewelry excluded.','left_cap_boundary_source_cell':left,'right_cap_boundary_source_cell':right,'observed_width_source_cell_pixels':width,'width_uncertainty_source_cell_pixels':uncertainty,'boundary_note':note,'current_width_art_pixels':None if density is None else width*density,'current_width_uncertainty_art_pixels':None if density is None else uncertainty*density,'collar':{'state':'occluded or no anatomically comparable rigid collar width exposed; not measured'},'clasp':{'state':'Not used as density ruler: cluster versus star designs and subpixel small pearl boundaries differ across paintings; no reliable matching rigid diameter.'},'silhouette_alpha128_bounds':bounds,'silhouette_width_in_cap_units':(bounds[2]-bounds[0])/width,'silhouette_height_in_cap_units':(bounds[3]-bounds[1])/width,'upstream_top_reach_in_cap_units':(mid[1]-bounds[1])/width,'downstream_bottom_reach_in_cap_units':(bounds[3]-mid[1])/width,'measurement_method':'Manual actual-source pixel ruler; no NCC location, correlation scale, occupiedheightfit or desired target substituted as observation.'}
 if key=='frozen55':row['collar']={'state':'Only partial V-opening visible below chin; not equivalent to top-view fullcollar diameter, not density calibration.','partial_opening_points_source_cell':[[280,192],[317,192]],'partial_opening_width_source_cell_pixels':37,'uncertainty_source_cell_pixels':6}
 result.append(row)
 vis=Image.new('RGB',sample.size,'#25374b');vis.paste(sample,(0,0),sample);pen=ImageDraw.Draw(vis);pen.line([tuple(left),tuple(right)],fill='#ffcf33',width=2)
 for x,y in [left,right]:pen.ellipse((x-3,y-3,x+3,y+3),outline='#ff3333',width=2);pen.line((x-uncertainty/2,y+5,x+uncertainty/2,y+5),fill='#ff3333',width=1)
 if key=='118':box=[450,350,1250,1000];factor=1
 elif key=='frozen55':box=[150,20,440,270];factor=2
 elif key=='overhead32':box=[65,90,260,260];factor=3
 else:box=[55,115,225,280];factor=3
 v=vis.crop(tuple(box));v=v.resize((round(v.width*factor),round(v.height*factor)),Image.Resampling.NEAREST);d=ImageDraw.Draw(v);d.rectangle((0,0,v.width,31),fill='#152131');d.text((5,3),f'{key}: OUTER CAP width{width}±{uncertainty} sourcepx',fill='white');d.text((5,16),f'points {left} → {right}; current artwidth '+('unselected' if density is None else f'{width*density:.1f}px'),fill='white');v.save(P/f'outer_cap_{key}.png')
cal=next(r for r in result if r['label']=='overhead32');canonical=cal['current_width_art_pixels'];canonical_uncertainty=cal['current_width_uncertainty_art_pixels'];frozen55=next(r for r in result if r['label']=='frozen55')
for r in result:r['proposed_uniform_scale_from_frozen_overhead32_outer_cap']=canonical/r['observed_width_source_cell_pixels']
groups=[('transition_056_071_linked_view_bridge',['71']),('transition_072_087_linked_occlusion_alpha',['72','87']),('transition_088_103_matched_phase',['88','103']),('transition_104_119_matched_phase',['104','117']),('transition_118_passing',['118']),('unselected_alternate72',['alternate72'])];proposals=[]
for name,keys in groups:
 rr=[r for r in result if r['label'] in keys];w=median(r['observed_width_source_cell_pixels']for r in rr);proposals.append({'source_bank':name,'observed_indices':keys,'median_outer_cap_width_source_cell_pixels':w,'proposed_whole_drawing_scale':canonical/w,'status':'Sparse sampled endpoints only; verify first/mid/last before locking one master density. Perpose uniformwholeimage correction may be needed if actual head size drifts inside sheet.'})
report={'version':1,'status':'Independent actual-source outercap audit; no production edits','calibration':{'frozen_overhead32_visible_outer_cap_art_pixels':canonical,'uncertainty_art_pixels':canonical_uncertainty,'frozen55_oblique_visible_outer_cap_art_pixels':frozen55['current_width_art_pixels'],'frozen55_uncertainty_art_pixels':frozen55['current_width_uncertainty_art_pixels'],'interpretation':'Frozen overhead32 outercap96±4rawpx at existing1.3702239789 gives131.54±5.48artpx. Frozen55 visiblecap95±8rawpx gives123.44±10.40artpx, compatible within hair/angle uncertainty. Thus nominal~130 is independently supported by actual approved outercap; not by an internalNCCwhorl box.'},'observations':result,'sampled_bank_scale_proposals':proposals,'limitations':'Visible attached hair-covered cap is a skull-envelope proxy, not exposed bone. Hair merger/clasp occlusion create explicit boundary uncertainty. Collars mostly hidden; clasp designs differ. Density changes are proposed only, not applied; no runtime/native review inferred.'}
(P/'outer_cranium_observations.json').write_text(json.dumps(report,indent=2)+'\n')
(P/'README.md').write_text('''# Independent outer-cranium audit

This directory contains read-only source crops, pixel rulers and manual outer-cap
boundary overlays. `outer_cranium_observations.json` binds every measurement to
the exact selected source SHA, source cell and current production scale.

The ruler follows the rounded attached hair-covered cranium rather than an
internal bright hair-whorl correlation window. Skull bone is covered, so these
are explicitly approximate visible cap boundaries with uncertainty. Loose wind
loops, braid and jewelry are excluded. No NCC scale is used here.

Frozen overhead32 supplies the actual outer-cap calibration. Frozen55 is a
less precise oblique cross-check because windblown bangs merge into its contour.
Sparse first/last bank samples do not establish a single safe density for all
intermediate poses. No production assets, export registration, profile or raw
master was changed. Proposed scales require parent native/proportion review.
''')
print('canonical',canonical,'±',canonical_uncertainty)
for r in result:print(r['label'],r['observed_width_source_cell_pixels'],'current',r['current_width_art_pixels'],'proposed',r['proposed_uniform_scale_from_frozen_overhead32_outer_cap'])
for key in ['71','72','alternate72']:
 r=next(r for r in result if r['label']==key);print('RATIOS',key,{k:r[k]for k in ['silhouette_width_in_cap_units','silhouette_height_in_cap_units','upstream_top_reach_in_cap_units','downstream_bottom_reach_in_cap_units']})
