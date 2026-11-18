"""Activation is explicit per canonical actor and requires both complete scopes."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import regent_native_activity as native
class RoyalNativeActivationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.patcher=patch.object(native,'ROOT',self.root);self.patcher.start();self.addCleanup(self.patcher.stop)
 def write(self,rel,data):
  p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data))
 def bank(self,who):
  self.write(f'assets/characters/named_hd/{who}/design.json',{'id':who})
  self.write(f'assets/story/royal_activity_hd/{who}/animation.json',{'id':who,'artwork_pixels_per_world_pixel':2,'draw_anchor':[24,60],'poses':{}})
 def test_asset_only_is_dormant(self):
  self.bank('regent_clerk');self.assertFalse(native.enabled('regent_clerk'));self.assertIsNone(native.bank('regent_clerk'))
 def test_activation_needs_both_scopes(self):
  who='regent_clerk';self.write(f'assets/characters/named_hd/{who}/activation.json',{'id':who,'enabled':True})
  self.assertFalse(native.enabled(who));self.write(f'assets/characters/named_hd/{who}/design.json',{'id':who});self.assertFalse(native.enabled(who));self.bank(who);self.assertTrue(native.enabled(who))
 def test_actor_activation_does_not_activate_siblings(self):
  for who in ('regent_clerk','regent_driver','regent_survivor'):self.bank(who)
  self.write('assets/characters/named_hd/regent_clerk/activation.json',{'id':'regent_clerk','enabled':True})
  self.assertTrue(native.enabled('regent_clerk'));self.assertFalse(native.enabled('regent_driver'));self.assertFalse(native.enabled('regent_survivor'));self.assertFalse(native.enabled('lucan'))
 def test_identity_mismatch_is_not_activation(self):
  self.bank('regent_clerk');self.write('assets/characters/named_hd/regent_clerk/activation.json',{'id':'regent_driver','enabled':True});self.assertFalse(native.enabled('regent_clerk'))
if __name__=='__main__':unittest.main()
