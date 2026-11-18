"""Complete refinement sources are explicit, scoped and immutable at export."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import tempfile,unittest
from PIL import Image
from tools.build_regional_worker_activity_hd import refined_body
class RefinedCompleteMasters(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  im=Image.new('RGBA',(96,104));im.putpixel((48,92),(2,3,4,255));b=BytesIO();im.save(b,format='PNG');self.data=b.getvalue()
  (self.root/'master.png').write_bytes(self.data);self.recipe={'refined_masters':{'poses/old.png':{'file':'master.png','sha256':sha256(self.data).hexdigest()}}}
 def select(self):return refined_body(self.recipe,'poses/old.png',self.root,b'legacy',{'original':True})
 def test_absent_override_retains_original_complete_body(self):self.assertEqual(refined_body({},'poses/old.png',self.root,b'old',{'sample':True}),(b'old',{'sample':True}))
 def test_complete_master_is_copied_exactly_with_historical_provenance(self):
  data,trace=self.select();self.assertEqual(data,self.data);self.assertEqual(trace['original_registration'],{'original':True});self.assertEqual(trace['refined_complete_master'],'master.png')
 def test_changed_source_requires_review(self):
  (self.root/'master.png').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'changed'):self.select()
 def test_refinement_cannot_escape_actor_source(self):
  for path in ('../foreign.png','/tmp/foreign.png'):
   self.recipe['refined_masters']['poses/old.png']['file']=path
   with self.assertRaisesRegex(ValueError,'leaves actor'):self.select()
 def test_invalid_density_or_soft_alpha_are_rejected(self):
  for size,alpha in (((80,88),255),((96,104),128),((96,104),0)):
   im=Image.new('RGBA',size,(3,4,5,alpha));b=BytesIO();im.save(b,format='PNG');data=b.getvalue();(self.root/'master.png').write_bytes(data);self.recipe['refined_masters']['poses/old.png']['sha256']=sha256(data).hexdigest()
   with self.assertRaisesRegex(ValueError,'Invalid complete'):self.select()
