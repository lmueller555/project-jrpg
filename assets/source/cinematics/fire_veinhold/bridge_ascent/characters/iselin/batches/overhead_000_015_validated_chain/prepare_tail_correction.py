"""Prepare guide-only12–15repair inputs; finalfigures areImageGen authored."""
from pathlib import Path
from PIL import Image
import importlib.util,json,shutil
B=Path(__file__).resolve().parents[2];P=B/'batches/overhead_000_015_validated_chain';Q=P/'tail_012_015_correction';Q.mkdir(exist_ok=True)
if (Q/'master.png').exists():raise ValueError('Refuse to overwrite retained authoring inputs')
path=B/'batches/overhead_016_031_pose_retry/prepare_annotated_batches.py';spec=importlib.util.spec_from_file_location('annotated_guide',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
sheet=Image.new('RGB',(1024,1536));rows=[]
for n,phase in enumerate(range(12,16)):
 im,raw=module.guide_cell(phase);x=n%2*512;y=n//2*768;sheet.paste(im,(x,y));rows.append({'sample_index':phase,'gait_frame':phase,'cell':[x,y,x+512,y+768],'view_elevation':90.,'view_azimuth':0.})
sheet.save(Q/'camera_pose_guide.png')
for f in ['approved_phase_reference.png','angle_model_reference.png']:shutil.copyfile(P/f,Q/f)
Image.open(P/'master.png').crop((256,1152,512,1536)).save(Q/'adjacent_passing_model.png')
(Q/'reference_manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
(Q/'prompt.txt').write_text('''Draw FOUR COMPLETE Iselin running drawings, strict2COLUMNS2ROWS, transparent alphaZERO background/gutters. All TRUE90DEGREE straight-down OVERHEAD, running toward IMAGE BOTTOM. Exact fixed adult head/shoulder/body size, no occupied-height fit. No face or frontal body.
REFERENCE1 is primary exact3D linked pose/camera guide. Red=anatomicalRIGHT/imageLEFT, cyan=LEFT/imageRIGHT; KNEE and BOOT labels explain the different positions. These construction colors/text must NOT appear in finalart. Ref2 ONLY approved head/braid appearance; ref3ONLYcoatmaterial. Ref4 is an adjacent valid compact passing figure at phase13, for model/view/cloth continuity—not a complete cycle or contactpose. Fresh complete figures in all4cells, not pasted bodyparts.
Readingorder TOPLEFTphase12, TOPRIGHT13, BOTTOMLEFT14, BOTTOMRIGHT15. These are FOUR consecutive60Hz instants, the MIDDLE OF PASSING/RECOVERY and still NINE frames before the next LEFTcontact24. DO NOT finish this sheet by extending a foot toward contact. All FOUR remain compact folded-leg passing silhouettes.
CRITICAL: in ALL FOUR cells BOTH BOOT endpoints are on the IMAGE TOP side of HEAD CENTER. The LEFT/imageRIGHT KNEE protrudes DOWN in front of crown, but its CALF folds BACK UP to its BOOT hidden behind/above the head. The RIGHT/imageLEFT leg also recovers/folds behind. Never mistake that projecting knee for a straight shin and boot hanging down below the head. There is NO extended front shin/boot below the crown anywhere in this four-frame segment. A thigh/knee may protrude naturally below crown but returns UP via a folded calf to the occluded boot. Follow the labeled hip→KNEE→BOOT chain even where head/coat hide it. Do not amputate body or draw ghostoldfeet. Exactly2arms2legs; hands continue a small neutral-to-rightarm-forward passing movement, connected to shoulders/elbows. Tiny sequential motion, not four widely spaced gaitkeys.
White/silver long loose hair streams behind/up-image and imageLEFT in stable wind. ONE FORWARD thick braid roots anatomicalLEFT/imageRIGHT pearl/silver templeclasp; mantle anatomicalRIGHT/imageLEFT. Royalblue/navy coat with silver fasteners/lining/embroidery, graytrousers and plain grayboots/simplebands. Match accepted head/material references exactly, no violetregrade, rearponytail, mirroring, bootembroidery or redesign. Same lively material-specific hair/clothlag, no volumechange. Painterly cinematic detail and thin darkedge. Entire separateflowingfigures within cells. Completely TRANSPARENTalphaZERO background, no cloudyhalo/checkerboard/box/shadow.''')
print(Q)
