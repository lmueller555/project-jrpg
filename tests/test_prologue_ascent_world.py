"""Actual transparent-railing regression rays through the painted world."""
import json
import math
from pathlib import Path
import unittest

import numpy as np

from cinematic_bridge_ascent import camera_at
from tools.build_prologue_bridge_ascent import WorldRenderer
from tools.build_prologue_face_environment import _surface_samples


class AscentWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = WorldRenderer()
        path = (Path(__file__).resolve().parents[1]/'docs/reviews/'
                'veinhold_bridge_ascent/render_regressions/witnesses.json')
        cls.witnesses = json.loads(path.read_text())['witnesses']

    def test_transparent_brace_gaps_reach_the_actual_world_surface(self):
        for witness in self.witnesses:
            with self.subTest(frame=witness['index']):
                x,y = witness['pixel']
                camera = camera_at(witness['index']/60)
                focal = camera['focal_pixels']
                horizontal, vertical = (480.-x)/focal, (320.-y)/focal
                pitch = camera['pitch_radians']
                along = -math.cos(pitch)+vertical*math.sin(pitch)
                down = math.sin(pitch)+vertical*math.cos(pitch)

                # Independently intersect this pixel ray with the physical
                # rail plane, then establish that the authored brace is absent.
                rail_depth = 7./abs(horizontal)
                rail_y = camera['position'][1]+along*rail_depth
                rail_z = camera['position'][2]+down*rail_depth
                self.assertTrue(0 < rail_y < 299.0819285747636)
                self.assertTrue(0 < rail_z < 1.2)
                height,width = self.renderer.rail[0].shape[:2]
                texel = _surface_samples(self.renderer.rail,
                    np.array([(rail_y/4.%1.)*width]),
                    np.array([(1.-rail_z/1.2)*(height-1)]),
                    np.array([rail_depth/focal*width/4.]))
                self.assertEqual(float(texel[0,3]),0.)

                # A transparent panel cannot terminate the ray. The recorded
                # mainland/sea elevation supplies an independent intersection.
                surface_z = 0. if witness['index']==24 else -12.65
                expected = (surface_z-camera['position'][2])/down
                self.assertGreater(expected,rail_depth+10.)
                self.renderer.render(witness['index'])
                self.assertAlmostEqual(float(self.renderer.depth[y,x]),expected,delta=.001)
                self.assertTrue(math.isinf(float(self.renderer.raised_depth[y,x])))


if __name__ == '__main__':
    unittest.main()
