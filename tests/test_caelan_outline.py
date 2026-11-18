"""Caelan contour readability without silhouette, shading or registration drift."""
import json
from pathlib import Path
import unittest
from PIL import Image

from tools.caelan_outline import apply_outline, INK, STYLE
from tools.build_caelan_overworld import drawing
from tools.build_mira_combat import _main_component

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/characters/caelan/overworld_refresh'
CARDINAL=((1,0),(-1,0),(0,1),(0,-1))


def read(path):return json.loads((ROOT/path).read_text())


def colors(image):
    return {image.getpixel((x,y)) for y in range(image.height) for x in range(image.width)}


def edges(image):
    return [(x,y) for y in range(image.height) for x in range(image.width)
            if image.getpixel((x,y))[3] and any(
                not (0<=x+dx<image.width and 0<=y+dy<image.height)
                or not image.getpixel((x+dx,y+dy))[3] for dx,dy in CARDINAL)]


def raw_travel(record):
    cell,bounds,_=drawing(record['index'])
    crop=cell.crop(bounds)
    scale=record['scale']
    body=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.NEAREST)
    raw=Image.new('RGBA',tuple(record['canvas']))
    raw.alpha_composite(body,tuple(record['destination']))
    return raw


class CaelanOutlineTests(unittest.TestCase):
    def assert_preserved_silhouette_and_interior(self,raw,outlined):
        self.assertEqual(outlined.size,raw.size)
        self.assertEqual(outlined.getchannel('A').tobytes(),raw.getchannel('A').tobytes())
        boundary=set(edges(raw))
        for y in range(raw.height):
            for x in range(raw.width):
                if (x,y) not in boundary:
                    self.assertEqual(outlined.getpixel((x,y)),raw.getpixel((x,y)),(x,y))

    def test_all_travel_contours_keep_alpha_and_interior_and_improve_readability(self):
        registration=read('assets/source/characters/caelan/overworld_refresh/registration.json')
        self.assertEqual(registration['outline'],STYLE)
        for record in registration['source_cells']:
            with self.subTest(file=record['file']):
                raw=raw_travel(record)
                image=Image.open(ROOT/record['file']).convert('RGBA')
                self.assert_preserved_silhouette_and_interior(raw,image)
                boundary=edges(image)
                dark=sum(max(image.getpixel(point)[:3])<60 for point in boundary)
                # Mira's reference idles have ~79–89% dark cardinal edges.
                # Permit bright facial/hand edge highlights in moving poses.
                self.assertGreaterEqual(dark/len(boundary),.7)
                old_dark=sum(max(raw.getpixel(point)[:3])<60 for point in boundary)
                self.assertGreater(dark,old_dark)

    def test_contour_does_not_mutate_input_or_fill_clear_limb_gaps(self):
        raw=Image.new('RGBA',(12,12))
        for x,y in ((3,3),(4,3),(5,3),(3,4),(4,4),(5,4),
                    (3,5),(5,5),(3,6),(5,6)):
            raw.putpixel((x,y),(130,85,60,255))
        before=raw.tobytes();outlined=apply_outline(raw)
        self.assertEqual(raw.tobytes(),before)
        self.assert_preserved_silhouette_and_interior(raw,outlined)
        self.assertEqual(outlined.getpixel((4,5)),(0,0,0,0))
        self.assertEqual(outlined.getpixel((4,6)),(0,0,0,0))
        self.assertEqual(apply_outline(outlined).tobytes(),outlined.tobytes())
        self.assertIn(INK,colors(outlined))

    def test_rescue_uses_same_contour_for_caelan_and_preserves_other_actors(self):
        folder=ROOT/'assets/source/story/sanctuary_rescue'
        registration=read('assets/source/story/sanctuary_rescue/registration.json')
        manifest=read('assets/story/sanctuary_rescue/art.json')
        self.assertEqual(manifest['caelan_outline'],STYLE)
        count=0
        for record in registration['frames']:
            with self.subTest(file=record['file']):
                sheet=Image.open(folder/record['source']).convert('RGBA')
                cell=_main_component(sheet.crop(tuple(record['source_rect'])))
                crop=cell.crop(record['source_bounds']);scale=record['scale']
                body=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.NEAREST)
                raw=Image.new('RGBA',tuple(record['canvas']))
                raw.alpha_composite(body,tuple(record['destination']))
                image=Image.open(ROOT/record['file']).convert('RGBA')
                if '/actions/row_5_' in record['file']:
                    count+=1
                    self.assert_preserved_silhouette_and_interior(raw,image)
                    self.assertNotEqual(raw.tobytes(),image.tobytes())
                    self.assertIn(INK,colors(image))
                else:self.assertEqual(raw.tobytes(),image.tobytes())
        self.assertEqual(count,4)

    def test_shared_policy_is_recorded_for_dependent_body_exports(self):
        manifest=read('assets/source/characters/caelan/overworld_refresh/dependents.json')
        self.assertEqual(manifest['outline'],STYLE)
        paths={record['file'] for record in manifest['outputs']}
        for name in ('assets/story/halden/caelan/hold_front.png',
                     'assets/story/elira/hold_left.png',
                     'assets/story/venn/caelan/give_right.png',
                     'assets/story/sanctuary_opening/poses/caelan_seated.png',
                     'assets/story/mill/poses/body.png',
                     'assets/story/lantern/poses/caelan_body.png'):
            with self.subTest(file=name):
                self.assertIn(name,paths)
                self.assertIn(INK,colors(Image.open(ROOT/name).convert('RGBA')))


if __name__=='__main__':unittest.main()
