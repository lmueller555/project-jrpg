"""Native architecture authoring checks, separate from real gameplay evidence."""
from hashlib import sha256
from pathlib import Path
import json
import unittest

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from tools import eldenmere_architecture_art as art


class ArchitectureArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.drawings={name:art.generate_architecture(name) for name in art.IDENTITIES}

    def test_thirteen_live_consumers_and_independent_return_values(self):
        self.assertEqual(len(self.drawings),13)
        for name,result in self.drawings.items():
            with self.subTest(name=name):
                self.assertEqual(result.structure.size,tuple(v*2 for v in result.metadata['logical_size']))
                self.assertEqual(result.structure.mode,'RGBA')
                self.assertEqual(set(result.structure.getchannel('A').getdata()),{0,255})
                self.assertEqual(result.structure.tobytes(),art.generate_architecture(name).structure.tobytes())
        a=art.generate_architecture('mill');a.structure.putpixel((0,0),(1,2,3,255))
        self.assertNotEqual(a.structure.tobytes(),art.generate_architecture('mill').structure.tobytes())

    def test_no_geometry_or_portal_migration(self):
        for name,result in self.drawings.items():
            r=art.records()[name];m=result.metadata
            for key in ('logical_size','ground_rect_logical','door_rect_logical'):
                self.assertEqual(m[key],r[key])
            x,y,w,h=m['door_rect_logical']
            self.assertIsNone(result.structure.crop((x*2,y*2,(x+w)*2,(y+h)*2)).getbbox(),name)
            self.assertEqual(m['depth_baseline_logical'],sum(r['ground_rect_logical'][i] for i in (1,3)))
            self.assertIn('no source facade registration',m['export_transform'])

    def test_changed_registration_requires_explicit_review(self):
        r=dict(art.records()['school']);r['ground_rect_logical']=[20,96,148,96]
        with self.assertRaisesRegex(ValueError,'Review changed school ground_rect_logical'):
            art.generate_architecture('school',r)

    def test_explicit_glass_panes_exclude_roof_stone_and_structural_timber(self):
        for name,result in self.drawings.items():
            self.assertEqual(result.pane_mask.mode,'L')
            self.assertIn(set(result.pane_mask.getdata()),({0,255},{0}))
            for material in ('roof','masonry','timber'):
                self.assertIsNone(ImageChops.multiply(result.pane_mask,result.material_masks[material]).getbbox(),(name,material))
            materials=list(result.material_masks)
            for index,one in enumerate(materials):
                for two in materials[index+1:]:
                    self.assertIsNone(ImageChops.multiply(result.material_masks[one],result.material_masks[two]).getbbox(),(name,one,two))
            declared=Image.new('L',result.structure.size);draw=ImageDraw.Draw(declared)
            for pane in result.metadata['pane_regions']:
                draw.rectangle(art.Drawing.coords(pane['rect_logical']),fill=255)
            self.assertIsNone(ImageChops.subtract(result.pane_mask,declared).getbbox(),name)
            if name!='item_shop':self.assertIsNotNone(result.pane_mask.getbbox(),name)

    def test_normal_and_reduced_differ_only_by_declared_effect_ownership(self):
        for name,result in self.drawings.items():
            pristine=result.structure.tobytes()
            reduced=result.ambient(7,True)
            self.assertEqual(reduced.tobytes(),pristine,name)
            for phase in (0,5,17):
                normal=result.ambient(phase)
                # Architecture is always identical below any smoke and outside
                # actual glass. Roof pixels cannot be recolored as window light.
                protected=ImageChops.subtract(result.material_masks['roof'],result.pane_mask)
                roofbox=protected.getbbox()
                if roofbox:
                    delta=ImageChops.difference(normal.convert('RGB'),reduced.convert('RGB')).convert('L')
                    # Smoke may pass over roof near its own cap, never diffuse
                    # over the slate field. Clear only the authored smoke region.
                    emitter=result.metadata['smoke_emitter_logical']
                    if emitter:
                        x,y=emitter;ImageDraw.Draw(delta).rectangle((int(x*2)-5,0,int(x*2)+9,int(y*2)+1),fill=0)
                    self.assertIsNone(ImageChops.multiply(delta,protected).getbbox(),(name,phase))
            self.assertEqual(result.structure.tobytes(),pristine,name)

    def test_mill_left_foundation_and_school_feet_fit_occupied_ground(self):
        for name,left,right,foot in (('mill',24,120,132),('school',24,168,192)):
            result=self.drawings[name]
            # Actual bottom masonry row, not just a metadata assertion. Mill's
            # small entrance stair projects south of the wall and is not a wall.
            row=result.structure.crop((0,(foot-2)*2,result.structure.width,foot*2)).getchannel('A')
            box=row.getbbox();self.assertIsNotNone(box)
            self.assertGreaterEqual(box[0],left*2,name)
            self.assertLessEqual(box[2],right*2,name)
        mill=self.drawings['mill']
        self.assertEqual(mill.metadata['mill_wheel_position_logical'],[88,94])
        self.assertEqual(mill.metadata['mill_axle_center_logical'],[112,118])
        self.assertIsNone(mill.structure.crop((0,276,44,312)).getbbox(),'old service fence resurrected')

    def test_right_rear_hearth_flue_correspondence(self):
        for name,x in (('mira',116),('mill',102),('school',146)):
            result=self.drawings[name];emitter=result.metadata['smoke_emitter_logical']
            self.assertEqual(emitter[0],x)
            cap=result.metadata['chimney_cap_rect_logical'];cx,cy,cw,ch=cap
            self.assertTrue(cx<=emitter[0]<cx+cw and cy<=emitter[1]<cy+ch)
            self.assertIsNotNone(result.material_masks['masonry'].crop(tuple(round(v*2) for v in (cx,cy,cx+cw,cy+ch))).getbbox())
        self.assertIsNone(self.drawings['item_shop'].metadata['smoke_emitter_logical'])
        self.assertEqual(self.drawings['sanctuary'].metadata['bell_mount_logical'],[42,54])

    def test_shop_merchandise_pixels_never_animate_or_receive_pane_light(self):
        result=self.drawings['item_shop'];box=(140,272,296,368)
        expected=result.structure.crop(box).tobytes()
        self.assertIsNone(result.pane_mask.crop(box).getbbox())
        for phase in range(18):
            self.assertEqual(result.ambient(phase).crop(box).tobytes(),expected)
            self.assertEqual(result.ambient(phase,True).crop(box).tobytes(),expected)
        # Existing stock remains exactly source-native, not a newly invented
        # catalogue or a set of recolored anonymous rectangles.
        with Image.open(art.ROOT/'assets/terrain/eldenmere/business_exteriors_hd/displays/maintained.png') as source:
            source=source.convert('RGBA')
            delta=ImageChops.difference(result.structure.crop(box).convert('RGB'),source.convert('RGB')).convert('L')
            self.assertIsNone(ImageChops.multiply(delta,source.getchannel('A')).getbbox())

    def test_households_have_different_structural_bay_rhythms(self):
        names=('halden','elira','venn','home_a','home_b','home_c','liam_house')
        pane_arrangements=[str(self.drawings[n].metadata['pane_regions']) for n in names]
        self.assertEqual(len(set(pane_arrangements)),7)
        # Comparing facade pixels prevents a roof-color-only pass from passing.
        facades=[self.drawings[n].structure.crop((24,214,216,282)).tobytes() for n in names if n!='elira']
        self.assertEqual(len(set(facades)),6)
        inn=self.drawings['inn'];self.assertEqual(inn.metadata['occupied_floors'],2)
        for name in ('inn','item_shop'):
            sign=self.drawings[name].metadata['business_sign']
            self.assertIn('not baked',sign['owner'])
            self.assertEqual(sign['position_logical'],art.records()[name]['sign_position_logical'])
            with Image.open(art.ROOT/f"assets/terrain/eldenmere/business_exteriors_hd/props/{sign['prop']}/idle.png") as prop:
                alpha=prop.convert('RGBA').getchannel('A').filter(ImageFilter.MaxFilter(3))
            occupied=Image.new('L',self.drawings[name].pane_mask.size)
            occupied.paste(alpha,tuple(v*2 for v in sign['position_logical']))
            self.assertIsNone(ImageChops.multiply(occupied,self.drawings[name].pane_mask).getbbox(),name+' sign must not sweep over panes')
        self.assertEqual(len([p for p in inn.metadata['pane_regions'] if p['rect_logical'][1]<180]),16)

    def test_roof_volumes_cover_ground_depth_without_converging_or_stretching_walls(self):
        for name,drawing in self.drawings.items():
            for volume in drawing.metadata['roof_volumes']:
                gx,gy,gw,gh=volume['ground_rect_logical'];rx,ry,rw,rh=volume['roof_rect_logical']
                self.assertGreaterEqual(rh,gh,(name,volume['role']))
                self.assertLessEqual(rh-gh,6,(name,'roof depth must reflect occupied ground, not a tall frontal panel'))
                self.assertGreaterEqual(rw,gw,(name,volume['role']))
                self.assertGreater(gy+gh-(ry+rh),0,(name,'eave height must rise above its ground'))
                self.assertLessEqual(rx,gx);self.assertGreaterEqual(rx+rw,gx+gw)

    def test_schedule_uses_reviewed_roof_planes_wall_contacts_and_cap_emitters(self):
        schedule=json.loads((art.ROOT/'assets/source/maps/eldenmere/town_hd/architecture_schedule.json').read_text())
        for record in schedule['buildings']:
            metadata=self.drawings[record['id']].metadata
            self.assertEqual(record['roof_planes_local_logical'],metadata['roof_planes_logical'])
            self.assertEqual(record['wall_contact_bounds_local_logical'],metadata['wall_ground_bounds_logical'])
            if record['chimney']:
                self.assertEqual(record['chimney']['position_logical'],metadata['smoke_emitter_logical'])
            self.assertTrue((art.ROOT/record['architecture_source']).is_file())

    def test_drop_in_adapter_uses_native_drawing_not_split_registration(self):
        for design,name in art.DESIGN_IDS.items():
            r=art.records()[name];structure,mask=art.building_structure(r)
            self.assertEqual(structure.tobytes(),self.drawings[name].structure.tobytes())
            self.assertEqual(mask.tobytes(),self.drawings[name].pane_mask.tobytes())


if __name__=='__main__':unittest.main()
