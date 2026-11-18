"""Native Serene body drawings with retained compatibility prop art only."""
from pathlib import Path
from PIL import Image,ImageDraw
import json,importlib.util,argparse,hashlib
S=Path(__file__).resolve().parent

def render(f,refs,size):
 idle=Image.open(refs/f"idle_{f['face']}.png").convert('RGBA');im=Image.new('RGBA',size);ox,oy=f.get('offset',[0,0]);d=ImageDraw.Draw(im)
 for sh in f['shapes']:d.polygon([(x+ox,y+oy)for x,y in sh['points']],fill=sh['fill'],outline=sh.get('outline'))
 mask=Image.new('L',(48,72));ImageDraw.Draw(mask).polygon(list(map(tuple,f['core_polygon'])),fill=255);body=Image.new('RGBA',(48,72));body.paste(idle,(0,0),mask);dx,dy=f.get('core_shift',[0,0]);im.alpha_composite(body,(ox+dx,oy+dy))
 dx,dy=f.get('head_shift',[0,0]);im.alpha_composite(idle.crop((0,0,48,f['head_cut'])),(ox+dx,oy+dy))
 return im

def export(root,legacy=None,base=None):
 legacy=legacy or root;base=base or root;refs=base/'assets/characters/named_hd/serene';out=root/'assets/characters/serene/activity_hd';plans=json.loads((S/'drawings.json').read_text());hashes={}
 spec=importlib.util.spec_from_file_location('serene_legacy_props',legacy/'tools/build_serene_routines.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 recipe=json.loads((legacy/'assets/source/characters/serene/routines/recipe.json').read_text());materials=json.loads((legacy/'assets/characters/serene/palette.json').read_text())['materials']
 def save(im,p):
  p.parent.mkdir(parents=True,exist_ok=True);im.save(p);hashes[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
 for name,frames in plans.items():
  for i,f in enumerate(frames):
   body=render(f,refs,(96,96) if name in recipe['actions'] else (48,72));im=Image.new('RGBA',body.size)
   if name in recipe['actions'] and f['prop_owner']=='actor':
    # The original prop is not redesigned by an actor migration. It is behind
    # the back-facing body, including when legitimately fully occluded.
    prop=Image.new('RGBA',(48,48));kind=f['legacy_prop']['kind'];mod.PROP_DRAWERS[kind](prop,f['legacy_prop'],recipe['prop_palette'],materials);im.alpha_composite(prop.resize((96,96),Image.Resampling.NEAREST))
   im.alpha_composite(body);save(im,out/'routines'/name/f'frame_{i+1:02}.png' if name in recipe['actions'] else out/'story'/f'{name}.png')
 m=json.loads((legacy/'assets/characters/serene/routines/animations.json').read_text());m.update(artwork_pixels_per_world_pixel=2,status='candidate',legacy_surface_prop_bank='assets/characters/serene/routines',source_drawings='assets/source/characters/serene/activity_hd/drawings.json')
 for key in ('approved_inputs','review','source_recipe'):m.pop(key,None)
 (out/'routines/animations.json').write_text(json.dumps(m,indent=2)+'\n')
 story=dict(artwork_pixels_per_world_pixel=2,logical_size=[24,36],poses={'seated':'assets/characters/serene/activity_hd/story/seated.png','aid_left':'assets/characters/serene/activity_hd/story/aid_left.png'},retained_cinematic_bank='assets/story/regent_arrival/actors/serene/animation.json')
 (out/'story/poses.json').write_text(json.dumps(story,indent=2)+'\n');(out/'sha256.json').write_text(json.dumps(hashes,indent=2)+'\n');return hashes
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--legacy-input-root',type=Path);p.add_argument('--base-root',type=Path);a=p.parse_args();print('Exported',len(export(a.repo_root.resolve(),a.legacy_input_root.resolve()if a.legacy_input_root else None,a.base_root.resolve()if a.base_root else None)),'native actor PNGs')
