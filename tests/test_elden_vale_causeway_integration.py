"""Physical causeway contacts are authored separately from native overhead art."""
import copy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from PIL import Image
from overworld_world import OverworldWorld
from tools.build_elden_vale_overworld import validate_signature_props,_rect_segment_distance
ROOT=Path(__file__).resolve().parents[1]

def read(path):return json.loads((ROOT/path).read_text())
def rect(prop):
    x,y=(round(v*24) for v in prop['tile_position']);w,h=prop['solid']
    return pygame.Rect(x-w//2,y-h//2,w,h)

class CausewayContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.display.set_mode((1,1))
        cls.region=read('assets/maps/overworld/elden_vale/region.json')
        cls.plan=cls.region['signature_landscape'];cls.props=cls.plan['props']
        cls.art=read(cls.region['hd_art_manifest'])
    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_complete_arch_reconstruction_and_real_aperture(self):
        source=read('assets/terrain/overworld/elden_vale/signature_landscape_hd/manifest.json')['assets']['arch_complete']
        master=Image.open(ROOT/source['image']).convert('RGBA').resize((480,360),Image.Resampling.NEAREST)
        assembled=Image.new('RGBA',master.size)
        for key in self.plan['causeway']['arch_crops']:
            r=(self.art['landmarks'] if key.endswith('lintel') else self.art['props'])[key]
            part=Image.open(ROOT/r['image']).convert('RGBA');assembled.alpha_composite(part,tuple(r['assembly_position_artwork']))
            self.assertEqual(part.size,tuple(v*2 for v in r['logical_size']))
        self.assertEqual(master.getchannel('A').tobytes(),assembled.getchannel('A').tobytes())
        for bg in ('black','white'):
            a=Image.new('RGBA',master.size,bg);a.alpha_composite(master)
            b=Image.new('RGBA',master.size,bg);b.alpha_composite(assembled)
            self.assertEqual(a.tobytes(),b.tobytes())
        self.assertIsNone(master.getchannel('A').crop((120,180,355,360)).getbbox())

    def test_source_supports_preserve_96_unit_both_route_envelopes(self):
        validate_signature_props(self.region)
        road=next(r for r in self.region['roads'] if r['id']=='south_town_road')
        minimum=min(_rect_segment_distance(tuple(rect(p)),tuple(v*24 for v in a),tuple(v*24 for v in b))
                    for p in self.props for points in (road['points'],self.region['design_layout']['causeway']['points']) for a,b in zip(points,points[1:]))
        self.assertGreaterEqual(minimum,48)
        self.assertAlmostEqual(minimum,49.049,places=2)

    def test_rejects_unsafe_nonfinite_duplicate_and_workarea_supports(self):
        for label,change in [('road',lambda p:p.update(tile_position=[10,-1])),('nonfinite',lambda p:p.update(tile_position=[float('nan'),0])),('negative',lambda p:p.update(solid=[-2,16])),('duplicate',lambda p:p.update(id=self.props[1]['id'])),('workarea',lambda p:p.update(tile_position=[-40,5]))]:
            data=copy.deepcopy(self.region);change(data['signature_landscape']['props'][0])
            with self.subTest(case=label),self.assertRaises(ValueError):validate_signature_props(data)

    def test_support_props_are_depthsorted_and_surfaces_have_no_collision(self):
        world=OverworldWorld();authored={p['id']:p for p in world.environment.authored}
        for source in self.props:
            self.assertEqual(authored[source['id']]['solid'],source['solid'])
            self.assertTrue(world.environment._signature_reserved(authored[source['id']]['position']))
        for r in self.region['landmark_layers']:
            if r['id'].startswith('causeway_'):self.assertEqual(r['collision'],'none')
        lintel=next(r for r in self.region['landmark_layers'] if r['id']=='causeway_arch_lintel')
        self.assertEqual(lintel['layer'],'overhead')
        for i in range(4):self.assertEqual(next(r for r in self.region['landmark_layers'] if r['id']==f'causeway_paving_{i}')['layer'],'ground')
        self.assertEqual(self.art['props']['causeway_arch_left']['foot_anchor'],[33,80])
        self.assertEqual(self.art['props']['causeway_arch_right']['foot_anchor'],[29,80])

    def test_every_new_support_is_present_in_all_intersected_collision_chunks(self):
        world=OverworldWorld()
        for prop in self.props:
            r=rect(prop)
            for cy in range(r.top//384,(r.bottom-1)//384+1):
                for cx in range(r.left//384,(r.right-1)//384+1):
                    chunk=pygame.Rect(cx*384,cy*384,384,384);overlap=r.clip(chunk)
                    registered={p['id'] for p in world.environment.collision_props(cx,cy)}
                    self.assertIn(prop['id'],registered)
                    mask=world._collision_chunk(cx,cy)
                    for x in range(overlap.left,overlap.right):
                        for y in range(overlap.top,overlap.bottom):self.assertTrue(mask.get_at((x-chunk.x,y-chunk.y)))
        # Rest parapet straddles y384 only through plant exclusion, arch crosses
        # x/negative-y ownership as authored; explicitly verify all touched chunks.

    def test_collision_additions_are_exact_authored_footprints(self):
        baseline=copy.deepcopy(self.region);baseline['signature_landscape']['props']=[]
        with TemporaryDirectory() as d:
            path=Path(d)/'before.json';path.write_text(json.dumps(baseline))
            before=OverworldWorld(path);after=OverworldWorld()
            chunks={(x,y) for p in self.props for x in range(rect(p).left//384,(rect(p).right-1)//384+1) for y in range(rect(p).top//384,(rect(p).bottom-1)//384+1)}
            for cx,cy in chunks:
                old=before._collision_chunk(cx,cy);new=after._collision_chunk(cx,cy)
                allowed=pygame.Mask((384,384))
                for prop in self.props:
                    r=rect(prop).move(-cx*384,-cy*384).clip(pygame.Rect(0,0,384,384))
                    if r:allowed.draw(pygame.Mask(r.size,fill=True),r.topleft)
                added=new.copy();added.erase(old,(0,0));added.erase(allowed,(0,0))
                self.assertEqual(added.count(),0,(cx,cy))
                # Local reservation may remove generated trunks only near the
                # new supports. It must not erase unrelated terrain collision.
                removed=old.copy();removed.erase(new,(0,0))
                for prop in self.props:
                    r=rect(prop).inflate(48,48).move(-cx*384,-cy*384).clip(pygame.Rect(0,0,384,384))
                    if r:removed.erase(pygame.Mask(r.size,fill=True),r.topleft)
                self.assertEqual(removed.count(),0,(cx,cy))
            for record in after.landmarks.records:after.landmarks.image(record)
            self.assertGreater(after.landmarks.sources.bytes,0)
            self.assertLessEqual(after.landmarks.sources.bytes,after.landmarks.sources.budget)

    def test_fragment_contact_covers_inspected_left_base_without_moving_art(self):
        prop=next(p for p in self.props if p['id']=='causeway_bone_fragment')
        binding=self.art['props'][prop['key']]
        self.assertEqual(list(rect(prop)),[-852,483,22,8])
        origin=[round(prop['tile_position'][i]*24)-binding['foot_anchor'][i] for i in range(2)]
        self.assertEqual(origin,[-854,457])
        with Image.open(ROOT/binding['image']) as art:
            self.assertEqual(art.convert('RGBA').getpixel((20,60))[3],255)
        self.assertTrue(rect(prop).collidepoint(-844,487))
        # Manually reviewed thick left base, not an alpha-derived footprint.
        self.assertTrue(rect(prop).contains(pygame.Rect(-851,484,19,6)))
        self.assertFalse(rect(prop).collidepoint(-814,479))  # elevated thin tail

    def test_joined_remnant_ports_register_without_rotation(self):
        sources=read('assets/terrain/overworld/elden_vale/signature_landscape_hd/manifest.json')['assets']
        results=[]
        for pid,key,port in [('causeway_deck','deck_straight','east'),('causeway_broken_end','broken_deck_end','west')]:
            prop=next(p for p in self.props if p['id']==pid);binding=self.art['props'][prop['key']]
            origin=[round(prop['tile_position'][i]*24)-binding['foot_anchor'][i] for i in range(2)]
            results.append([origin[i]+sources[key]['ports_logical'][port][i] for i in range(2)])
        self.assertEqual(results,[[-364,170],[-364,170]])
