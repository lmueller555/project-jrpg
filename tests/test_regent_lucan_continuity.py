"""Lucan travels with the arriving party before his personal introduction."""
import hashlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import numpy as np
import pygame
from PIL import Image

from regent_aerial import RegentAerial, GROUND_PARTY, ROAD_POINTS
from tools.export_regent_lucan import ROOT, GROUND, AERIAL, ground_outputs, aerial_outputs


class LucanArrivalContinuityTests(unittest.TestCase):
    def test_approved_ground_originals_are_retained_and_rebuild_without_mutation(self):
        outputs,sources = ground_outputs()
        for filename,digest in sources.items():
            self.assertEqual(hashlib.sha256((ROOT/filename).read_bytes()).hexdigest(),digest)
        for filename,data in outputs.items():
            self.assertEqual((GROUND/filename).read_bytes(),data)
        manifest=json.loads(outputs['lucan/animation.json'])
        self.assertEqual(manifest['canvas'],[80,96])
        self.assertEqual(manifest['anchor'],[40,92])
        for direction in ('left','back'):
            frames=manifest['loops']['walk_'+direction]
            self.assertEqual(len(frames),4)
            self.assertEqual(len({outputs['lucan/'+frame['file']] for frame in frames}),4)
            for frame in frames:
                image=Image.open(io.BytesIO(outputs['lucan/'+frame['file']])).convert('RGBA')
                self.assertEqual(image.size,(80,96))
                self.assertTrue(set(image.getchannel('A').tobytes()) <= {0,255})
                box=image.getbbox();self.assertGreater(box[0],0)
                self.assertLess(box[2],80);self.assertLessEqual(box[3],93)

    def test_aerial_poses_are_separate_foreshortened_camera_drawings(self):
        outputs=aerial_outputs()
        for filename,data in outputs.items():self.assertEqual((AERIAL/filename).read_bytes(),data)
        for pose in ('overhead','oblique'):
            image=Image.open(io.BytesIO(outputs['lucan/'+pose+'.png'])).convert('RGBA')
            self.assertEqual(image.size,(48,64))
            box=image.getbbox()
            self.assertLessEqual(box[3]-box[1],34)
            self.assertEqual(box[3],56)
        self.assertNotEqual(outputs['lucan/overhead.png'],outputs['lucan/oblique.png'])

    def test_personal_guard_is_present_in_each_ground_party_shot(self):
        scene=json.loads((ROOT/'assets/story/regent_arrival/scene.json').read_text())
        self.assertIn('lucan',scene['actors'])
        for phase in scene['phases']:
            if any(actor['id']=='aldric' for actor in phase['actors']):
                with self.subTest(shot=phase['id']):
                    self.assertEqual(sum(actor['id']=='lucan' for actor in phase['actors']),1)
        # The same guard and fixed offsets persist through each walking cut.
        for shot in ('gate_approach','gate_greeting','town_approach','town_parking'):
            phase=next(p for p in scene['phases'] if p['id']==shot)
            aldric=next(a for a in phase['actors'] if a['id']=='aldric')
            lucan=next(a for a in phase['actors'] if a['id']=='lucan')
            for key in ('position','to'):
                if key in aldric:
                    self.assertEqual([b-a for a,b in zip(aldric[key],lucan[key])],[30,-24])

    def test_gate_admission_uses_same_road_depth_and_back_facing(self):
        scene=json.loads((ROOT/'assets/story/regent_arrival/scene.json').read_text())
        phase=next(p for p in scene['phases'] if p['id']=='gate_admission')
        lucan=next(a for a in phase['actors'] if a['id']=='lucan')
        aldric=next(a for a in phase['actors'] if a['id']=='aldric')
        self.assertEqual(lucan['route'],aldric['route'])
        self.assertEqual(lucan['route_end']-lucan['route_start'],aldric['route_end']-aldric['route_start'])
        self.assertEqual(lucan['move_start'],aldric['move_start'])
        self.assertEqual(lucan['move_seconds'],aldric['move_seconds'])
        self.assertEqual(lucan['after_pose'],'stand_back')
        self.assertEqual(lucan['route_poses'][-1][1],'walk_back')

    def test_overhead_guard_follows_painted_road_before_ground_handoff(self):
        aerial=RegentAerial(SimpleNamespace())
        for time in np.linspace(21,26.4,20):
            snapshot=aerial.sample(float(time))
            lucan=snapshot['projected_actors']['lucan']
            aldric=snapshot['projected_actors']['aldric']
            clerk=snapshot['projected_actors']['clerk']
            self.assertTrue(lucan['moving'])
            self.assertLess(float(np.linalg.norm(ROAD_POINTS-np.asarray(lucan['world_xy']),axis=1).min()),.3)
            self.assertGreater(aldric['road_distance'],lucan['road_distance'])
            self.assertGreater(lucan['road_distance'],clerk['road_distance'])
        final=aerial.sample(31)
        self.assertEqual(final['projected_actors']['lucan']['native_xy'],list(GROUND_PARTY['lucan']))


if __name__=='__main__':unittest.main()
