from pathlib import Path
import hashlib,json,unittest,subprocess,sys,tempfile,shutil
from PIL import Image
R=Path(__file__).resolve().parents[1];S=R/'assets/source/characters/regional_npc_hd/regional_picker/actions_hd';O=R/'assets/characters/regional_npc_hd/regional_picker/actions_hd'
class PickerNative(unittest.TestCase):
 def setUp(self):self.m=json.loads((O/'animation.json').read_text())
 def test_dormant_scale(self):
  self.assertIs(self.m['runtime_activation'],False);self.assertEqual(self.m['artwork_pixels_per_world_pixel'],2);self.assertEqual(self.m['logical_canvas'],[40,44]);self.assertEqual(self.m['draw_anchor_logical'],[20,38])
 def test_export_is_exact_native_source(self):
  for seq in self.m['sequences'].values():
   for f in seq['frames']:
    self.assertEqual((S/'masters'/f['file']).read_bytes(),(O/f['file']).read_bytes());im=Image.open(O/f['file']);im.load();self.assertEqual(im.size,(80,88));self.assertGreater(f['duration_ms'],0)
 def test_two_step_and_cadence(self):
  for dr in ['front','back','right','left']:
   seq=self.m['sequences']['carry_'+dr];self.assertEqual(len(seq['frames']),8);self.assertEqual(sum(x['duration_ms'] for x in seq['frames']),680)
   a=Image.open(O/seq['frames'][0]['file']).crop((16,55,64,80));b=Image.open(O/seq['frames'][4]['file']).crop((16,55,64,80));self.assertNotEqual(a.tobytes(),b.tobytes())
 def test_profile_identity_symmetry(self):self.assertEqual(Image.open(S/'references/idle_left.png').tobytes(),Image.open(S/'references/idle_right.png').transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes())
 def test_actions_and_rest_anchor(self):
  self.assertEqual(set(self.m['sequences']),{'carry_'+d for d in ['front','back','right','left']}|{'reach_front','admire_front','lower_front','sort_right','rest_front'});self.assertEqual(self.m['sequences']['rest_front']['draw_anchor_logical'],[20,44]);self.assertEqual(len(self.m['sequences']['rest_front']['frames']),1)
 def test_ground_continuity(self):
  for key,seq in self.m['sequences'].items():
   if key=='rest_front':continue
   for i,f in enumerate(seq['frames']):
    bottom=77
    if key.startswith('carry_'):
     dr=key.split('_')[1];j=(i+4)%8 if dr=='left' else i;dr='right' if dr=='left' else dr
     q=json.loads((S/f'carry_{dr}_contours.json').read_text())[j];boots=['fb','nb'] if dr=='right' else ['lb','rb'];bottom=max(y for b in boots for x,y in q[b])+8
    with Image.open(O/f['file']) as im:self.assertEqual(im.getbbox()[3],bottom, f['file'])
 def test_nonwriting_check_and_author_reproducibility(self):
  def snapshot():
   folders=(S,O,R/'docs/qa/regional_picker_actions');files=[p for folder in folders for p in folder.rglob('*') if p.is_file()]+[R/'tools/build_regional_picker_actions_hd.py']
   return {str(p.relative_to(R)):(p.stat().st_mtime_ns,hashlib.sha256(p.read_bytes()).hexdigest()) for p in files}
  before=snapshot();subprocess.run([sys.executable,str(R/'tools/build_regional_picker_actions_hd.py'),'--check'],check=True,capture_output=True);self.assertEqual(before,snapshot())
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'source';shutil.copytree(S,source);shutil.rmtree(source/'masters');subprocess.run([sys.executable,str(source/'author.py')],check=True)
   for p in (S/'masters').glob('*.png'):self.assertEqual(p.read_bytes(),(source/'masters'/p.name).read_bytes())
   # Missing output must fail rather than silently repair; stage only tiny exporter inputs.
   stage=Path(tmp)/'check';(stage/'tools').mkdir(parents=True);shutil.copyfile(R/'tools/build_regional_picker_actions_hd.py',stage/'tools/build_regional_picker_actions_hd.py')
   for folder in (S,O,R/'docs/qa/regional_picker_actions'):shutil.copytree(folder,stage/folder.relative_to(R))
   victim=stage/'assets/characters/regional_npc_hd/regional_picker/actions_hd/carry_front_00.png';victim.unlink()
   result=subprocess.run([sys.executable,str(stage/'tools/build_regional_picker_actions_hd.py'),'--check'],capture_output=True)
   self.assertNotEqual(result.returncode,0);self.assertFalse(victim.exists())
if __name__=='__main__':unittest.main()
