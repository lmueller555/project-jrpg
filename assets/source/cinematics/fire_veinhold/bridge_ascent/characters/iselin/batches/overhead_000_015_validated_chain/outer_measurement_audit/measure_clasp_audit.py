"""Read-only actualsource diagnostic; never edits production inputs."""
from pathlib import Path
from PIL import Image,ImageDraw
from hashlib import sha256
import json
B=Path(__file__).resolve().parents[3];P=B/'batches/overhead_000_015_validated_chain/outer_measurement_audit';bindings={r['index']:r for r in json.loads((P/'clasp_input_binding.json').read_text())}
# Whole motif bounds use visible metal/pearl graphic, excluding braid/hair.
# The beaded clusters have no consistently resolvable single central sphere.
# Star-family inner boxes follow the gray pearl surface, excluding silver rim
# and white specular highlight; coarse source pixels imply large uncertainty.
measure={
 55:('beaded_cluster',[333,85,363,134],None,3,4),
 56:('beaded_cluster',[192,54,210,86],None,2,3),
 60:('beaded_cluster',[190,72,209,107],None,2,3),
 64:('beaded_cluster',[189,98,208,133],None,2,3),
 68:('beaded_cluster',[187,134,208,171],None,2,3),
 71:('beaded_cluster',[187,164,207,205],None,2,3),
 72:('beaded_cluster',[171,187,192,220],None,2,3),
 87:('beaded_cluster',[172,190,190,215],None,2,3),
 88:('flower_star',[167,188,190,213],[175,196,182,203],2,2),
 103:('flower_star',[168,186,192,211],[176,194,183,201],2,2),
 104:('flower_star',[160,196,185,221],[168,203,176,211],2,2),
 117:('flower_star',[159,196,184,222],[167,204,175,211],2,2),
 118:('flower_star',[968,601,1064,698],[1003,636,1033,666],5,5)}
rows=[]
for index,(family,outer,pearl,wunc,hunc) in measure.items():
 bound=bindings[index];path=B/bound['source'];assert sha256(path.read_bytes()).hexdigest()==bound['source_sha256'];sample=Image.open(path).crop(tuple(bound['cell'])).convert('RGBA');scale=bound['current_density_scale'];width,height=outer[2]-outer[0],outer[3]-outer[1]
 record={**bound,'motif_family':family,'whole_motif_source_cell_bounds':outer,'whole_motif_width_source_pixels':width,'whole_motif_height_source_pixels':height,'whole_motif_width_uncertainty_source_pixels':wunc,'whole_motif_height_uncertainty_source_pixels':hunc,'whole_motif_current_art_width':width*scale,'whole_motif_current_art_height':height*scale,'central_pearl':{'status':'No unambiguous single central sphere boundary at this coarse painting; metal/beads overlap. Whole cluster measured instead; not interchangeable with later flower/star.'},'method':'Manual actualsource pixel ruler. Same visible whole beaded motif within55–87; same gray central pearl surface excluding metal rim/specularglint within88+. No NCC scale or target measurements.'}
 if pearl:
  pw,ph=pearl[2]-pearl[0],pearl[3]-pearl[1];record['central_pearl']={'status':'Gray inner pearl surface visible; coarse boundary, excluding silver outer rim and glint.','source_cell_bounds':pearl,'horizontal_diameter_source_pixels':pw,'vertical_diameter_source_pixels':ph,'diameter_uncertainty_source_pixels':1.5 if index!=118 else 3,'current_art_mean_diameter':(pw+ph)/2*scale,'warning':'Painted diameter is6–8pixels in sheet cells; ±1.5px is20–25% uncertainty. Local jewelry/head proportion can drift independently; not sole density calibration.'}
 rows.append(record)
 pad=8 if index!=118 else 15;box=[max(0,outer[0]-pad),max(0,outer[1]-pad),min(sample.width,outer[2]+pad),min(sample.height,outer[3]+pad)];vis=Image.new('RGB',sample.size,'#25374b');vis.paste(sample,(0,0),sample);d=ImageDraw.Draw(vis);d.rectangle(outer,outline='#ffcf33',width=1)
 if pearl:d.rectangle(pearl,outline='#00ffff',width=1)
 vis=vis.crop(tuple(box));factor=8 if index!=118 else 3;vis=vis.resize((vis.width*factor,vis.height*factor),Image.Resampling.NEAREST);banner=Image.new('RGB',(max(vis.width,500),vis.height+48),'#152131');banner.paste(vis,(0,48));d=ImageDraw.Draw(banner);d.text((5,4),f'{index} {family}: outer{width}x{height} sourcepx, current{width*scale:.1f}x{height*scale:.1f}artpx',fill='white');d.text((5,20),'yellow=whole motif; cyan=inner pearl if resolvable',fill='white');banner.save(P/f'clasp_measurement_{index:03d}.png')
# Frozen trueoverhead32 is a useful same-star inner-pearl comparison.
cal=json.loads((P/'additional_input_binding.json').read_text())[1];path=B/cal['source'];assert sha256(path.read_bytes()).hexdigest()==cal['source_sha256'];scale=cal['current_density_scale'];calibration={'label':'frozen_overhead32','source':cal['source'],'source_sha256':cal['source_sha256'],'cell':cal['cell'],'current_density_scale':scale,'central_pearl_source_bounds':[209,170,218,179],'central_pearl_diameter_source_pixels':9,'diameter_uncertainty_source_pixels':1.5,'current_art_diameter':9*scale,'note':'Sameflower/star pearl family; approximategray sphere boundary at9sourcepx. Actualcap observation remains separate.'}
base55=next(r for r in rows if r['index']==55)
for r in rows:
 if r['motif_family']=='beaded_cluster':r['current_art_whole_motif_width_ratio_to_frozen55']=r['whole_motif_current_art_width']/base55['whole_motif_current_art_width']
report={'version':1,'status':'Manual visible rigidappearance crosscheck; no production edits','observations':rows,'frozen_overhead32_pearl_crosscheck':calibration,'findings':['Visible beaded motif rawwidth grows18px at56 to20px at71 while current density stays2.407. Currentart motifwidth is43.3→48.1px versus frozen55about39.0px. This supports some sourceframing/appearance drift, but coarsebounds and camera foreshortening prevent treating the wholemotif as exact isotropic ruler.','Selected72 beadedmotif current43.2x67.8artpx is close to frozen55~39.0x63.7 within sourceboundary/projection uncertainty; this does not support blindly shrinking72by25% solely to make a windmerged hairenvelope constant.','Flower/star central pearl currentdiameters are about10.6 at88/103,14.9 at104,14.0 at117,10.9 at118 versus frozenoverhead32~12.3artpx. Because smallcell pearl diameter has±20–25% uncertainty and jewelry/head ratio visiblyvaries bypainting, accessory alone cannot prove wholebody density or justify anatomy-distorting rescale.','Outerhaircap measurements and clasp crosschecks do not supply one unambiguous physical skull width across every painting. Distinguish volume, visible capdefinition, camera projection and actual source framing. Use actualneck/collar/head model continuity with native proofs; do not replace NCC ruler error with a different unqualified hairenvelope ruler.'],'limitations':'Whole beaded motif is not the same geometric object outline as the flower/star. Pearl circles are only measured where resolved; no invented hidden circle diameters. Angled jewelry plane may foreshorten; spherical pearl surface is a better but coarse crosscheck.'}
(P/'clasp_observations.json').write_text(json.dumps(report,indent=2)+'\n')
old=P/'outer_cranium_observations.json';d=json.loads(old.read_text());d['density_proposal_status']='EXPLORATORY ONLY / superseded by rigidappearance crosscheck. Windmerged hair cap is not proven rigid skull. Do notapply the listed cap-normalization scales as recommendations without independent model/native review.';d['critical_feature_definition_caution']='In selected72 the left outercap envelope includes a wrapping loose/windblown hair band. An inner anatomicallyrigid cap estimate around68rawpx versus85px outerhairwidth is plausible. These are different features, not conflicting exact bone measurements. The skull remains occluded; cap-only scales can overcorrect.'
for x in d['sampled_bank_scale_proposals']:x['status']='Exploratory arithmetic from visiblehairenvelope only; NOT production recommendation. Rigidclasp crosscheck may contradict large rescale; see clasp_observations.json.'
old.write_text(json.dumps(d,indent=2)+'\n')
print('Saved',len(rows),'clasp measurements')
