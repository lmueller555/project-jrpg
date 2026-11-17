"""Asset contracts: safe proposed ground contacts, coherent anatomy and open arch."""
import importlib.util
import json
from pathlib import Path
import unittest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets/terrain/overworld/elden_vale/signature_landscape_hd/manifest.json'

class SignatureLandscapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack=json.loads(PACK.read_text())
        spec=importlib.util.spec_from_file_location('signature_builder',ROOT/'tools/build_elden_vale_signature_landscape_hd.py')
        cls.builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.builder)

    def test_source_geometry_and_rejected_walkable_support(self):
        plan=json.loads((ROOT/self.pack['layout_plan']).read_text())
        self.builder.verify_layout(plan)
        plan['base_supports'][0]['rect']=[432,630,24,12]
        with self.assertRaisesRegex(ValueError,'walkable'):
            self.builder.verify_layout(plan)

    def test_layers_reconstruct_single_anatomy_and_arch(self):
        for assembly_id,whole in [('antlers','antlers_complete'),('arch','arch_complete')]:
            assembly=self.pack['assemblies'][assembly_id]
            image=Image.new('RGBA',assembly['canvas_artwork'])
            for key in assembly['parts']:
                part=self.pack['assets'][key]
                image.alpha_composite(Image.open(ROOT/part['image']).convert('RGBA'),part['assembly_position_artwork'])
            original=Image.open(ROOT/self.pack['assets'][whole]['image']).convert('RGBA')
            # Invisible RGB in empty cells is immaterial; compare alpha and premultiplied color.
            self.assertEqual(image.getchannel('A').tobytes(),original.getchannel('A').tobytes())
            for background in ('black','white'):
                a=Image.new('RGBA',image.size,background);a.alpha_composite(image)
                b=Image.new('RGBA',image.size,background);b.alpha_composite(original)
                self.assertEqual(a.tobytes(),b.tobytes())

    def test_open_underpass_is_real_transparency(self):
        record=self.pack['assets']['arch_complete']
        x,y,w,h=record['clear_underpass_logical']
        image=Image.open(ROOT/record['image'])
        self.assertIsNone(image.getchannel('A').crop((2*x,2*y,2*(x+w),2*(y+h))).getbbox())
        self.assertGreaterEqual(w,3*24)

    def test_density_masks_and_staged_activation(self):
        for name,record in self.pack['assets'].items():
            with self.subTest(asset=name):
                image=Image.open(ROOT/record['image']).convert('RGBA')
                self.assertEqual(image.size,tuple(2*n for n in record['logical_size']))
                self.assertLessEqual(set(image.getchannel('A').tobytes()),{0,255})
                if 'occlusion_mask' in record:
                    self.assertEqual(Image.open(ROOT/record['occlusion_mask']).tobytes(),image.getchannel('A').tobytes())
        self.assertEqual(self.pack['integration_status'],'not_integrated')
        for part in ['beam_left','beam_central','beam_right']:
            self.assertEqual(self.pack['assets'][part]['collision'],'none')
            self.assertEqual(self.pack['assets'][part]['contact_rects_logical'],[])

    def test_module_ports_meet_in_reference_runs(self):
        for key in ('ridge_run','causeway_run'):
            run=self.pack['assemblies'][key]['placements']
            for left,right in zip(run,run[1:]):
                a=self.pack['assets'][left['asset']]['ports_logical']['east']
                b=self.pack['assets'][right['asset']]['ports_logical']['west']
                self.assertEqual([a[i]+left['position_logical'][i] for i in range(2)],
                                 [b[i]+right['position_logical'][i] for i in range(2)])

    def test_skull_contact_registers_to_protected_ridge(self):
        base=self.pack['assets']['embedded_skull']
        x,y,w,h=base['contact_rects_logical'][0]
        px,py=base['placement_candidate_logical']
        ax,ay=base['draw_anchor_logical']
        plan=json.loads((ROOT/self.pack['layout_plan']).read_text())
        self.assertEqual([x+px-ax,y+py-ay,w,h],plan['base_supports'][0]['rect'])
