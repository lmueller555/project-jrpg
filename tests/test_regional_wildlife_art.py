"""Native wildlife clip integrity and physical contact registration."""
import hashlib
import json
import math
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'assets/characters/regional_wildlife'
FAMILIES = {
    'sheep': ([24, 20], [12, 18], ('graze', 'walk', 'look', 'nuzzle')),
    'cat': ([24, 18], [12, 16], ('sleep', 'stretch', 'walk', 'sit')),
    'bird': ([12, 12], [6, 10], ('land', 'peck', 'fly')),
    'butterfly': ([12, 12], [6, 10], ('flutter', 'settle')),
}
# Frozen approved reference hashes prevent an updated provenance file from
# silently blessing a change to the original decorative countryside animals.
ORIGINAL_HASHES = {
    'sheep_1': 'f7028a71c03df742a6b316ca98d374d9edc2a9f110965818549c01a1dbf34a28',
    'sheep_2': '968055b5ecf054defe500f777eec8447b4be483a05fe4afb44b4ebf73625db08',
    'bird_1': 'f336266b2e2261cd8b75959644185ff15301a1fcfb0ee94f25c5bcc19a967e9d',
    'bird_2': 'b4f0d1e563e5b1e6c8bf01b68f123fa4b7c239b69d3087de501a7efd5c712fec',
    'butterfly_1': '4c1839ecd8b75305ae115c15a792b31c2380aa5e92d0106cae3ecd15034cf409',
    'butterfly_2': 'c2f5bca2340cc00959bd97ea19bdb6fd19d6ee85ddd375c110a18c7fea984f43',
}


class RegionalWildlifeArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ART / 'animation.json').read_text())
        cls.clips = cls.manifest['clips']

    def image(self, filename):
        path = ART / filename
        self.assertEqual(path.parent, ART, 'Clip frames must be local exports.')
        with Image.open(path) as source:
            self.assertEqual(source.mode, 'RGBA')
            return source.copy()

    def test_complete_native_family_and_pose_contract(self):
        self.assertEqual(set(self.manifest['families']), set(FAMILIES))
        expected = set()
        for family, (size, anchor, poses) in FAMILIES.items():
            self.assertEqual(self.manifest['families'][family],
                             {'size': size, 'anchor': anchor})
            expected.update(f'{family}_{pose}_{direction}'
                            for pose in poses for direction in ('left', 'right'))
        self.assertEqual(set(self.clips), expected)
        exported = {name for clip in self.clips.values() for name in clip['frames']}
        exported.update(prop['file'] for prop in self.manifest['props'].values())
        self.assertEqual({p.name for p in ART.glob('*.png')}, exported)

    def test_frames_and_timing_are_complete_finite_native_pixels(self):
        for key, clip in self.clips.items():
            with self.subTest(clip=key):
                family = clip['family']
                self.assertTrue(key.startswith(family + '_'))
                self.assertGreaterEqual(len(clip['frames']), 2)
                self.assertEqual(len(clip['frames']), len(clip['durations']))
                self.assertEqual(len(clip['frames']), len(clip['landmarks']))
                self.assertIs(type(clip['loop']), bool)
                for filename, duration in zip(clip['frames'], clip['durations']):
                    self.assertTrue(math.isfinite(duration) and duration > 0)
                    im = self.image(filename)
                    self.assertEqual(list(im.size), FAMILIES[family][0])
                    self.assertIsNotNone(im.getbbox())
                    self.assertEqual(set(im.getchannel('A').tobytes()), {0, 255})
        for family, pose in (('sheep', 'nuzzle'), ('cat', 'stretch'), ('bird', 'land')):
            for direction in ('left', 'right'):
                self.assertFalse(self.clips[f'{family}_{pose}_{direction}']['loop'])

    def test_landmarks_touch_painted_pixels_and_ground_plane(self):
        for key, clip in self.clips.items():
            anchor_y = FAMILIES[clip['family']][1][1]
            for filename, landmarks in zip(clip['frames'], clip['landmarks']):
                with self.subTest(frame=filename):
                    im = self.image(filename)
                    contacts = landmarks['ground_contacts']
                    if landmarks.get('airborne'):
                        self.assertEqual(contacts, [])
                    else:
                        self.assertTrue(contacts, 'Grounded frames require visible support.')
                    points = list(contacts)
                    for name in ('muzzle', 'beak'):
                        if name in landmarks:
                            points.append(landmarks[name])
                    for x, y in points:
                        self.assertTrue(0 <= x < im.width and 0 <= y < im.height)
                        self.assertEqual(im.getpixel((x, y))[3], 255,
                                         'A declared contact floats outside the sprite.')
                    for _, y in contacts:
                        self.assertEqual(y, anchor_y)

    def test_actions_change_animal_silhouettes(self):
        # A blink or a palette flicker cannot substitute for articulated motion.
        for family, pose in (('sheep', 'walk'), ('sheep', 'graze'),
                             ('sheep', 'nuzzle'), ('cat', 'walk'),
                             ('cat', 'stretch'), ('bird', 'land'),
                             ('bird', 'peck'), ('bird', 'fly'),
                             ('butterfly', 'flutter')):
            for direction in ('left', 'right'):
                key = f'{family}_{pose}_{direction}'
                with self.subTest(clip=key):
                    silhouettes = {
                        self.image(filename).getchannel('A').tobytes()
                        for filename in self.clips[key]['frames']
                    }
                    self.assertGreater(len(silhouettes), 1)

    def test_grazing_and_pecking_reach_below_alert_heads(self):
        for direction in ('left', 'right'):
            graze = self.clips[f'sheep_graze_{direction}']['landmarks']
            look = self.clips[f'sheep_look_{direction}']['landmarks']
            self.assertGreater(min(p['muzzle'][1] for p in graze),
                               max(p['muzzle'][1] for p in look))
            peck = self.clips[f'bird_peck_{direction}']['landmarks']
            self.assertEqual(max(p['beak'][1] for p in peck), FAMILIES['bird'][1][1])
            self.assertGreater(max(p['beak'][1] for p in peck), peck[0]['beak'][1])

    def test_seed_spill_is_one_small_static_ground_prop(self):
        self.assertEqual(set(self.manifest['props']), {'seeds'})
        prop = self.manifest['props']['seeds']
        self.assertEqual(prop['size'], [16, 8])
        self.assertEqual(prop['anchor'], [8, 6])
        im = self.image(prop['file'])
        self.assertEqual(list(im.size), prop['size'])
        self.assertEqual(set(im.getchannel('A').tobytes()), {0, 255})
        # Keep the spill sparse enough to leave the farm ground visible.
        self.assertLess(sum(a == 255 for a in im.getchannel('A').tobytes()), 32)

    def test_provenance_matches_exports_and_preserves_approved_originals(self):
        provenance = json.loads((ART / 'provenance.json').read_text())
        actual_originals = {}
        for record in provenance['original_references']:
            path = ROOT / record['file']
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, record['sha256'])
            actual_originals[path.stem] = digest
        self.assertEqual(actual_originals, ORIGINAL_HASHES)
        builder = ROOT / provenance['builder']
        self.assertEqual(hashlib.sha256(builder.read_bytes()).hexdigest(),
                         provenance['builder_sha256'])
        exports = set()
        for record in provenance['exports']:
            path = ROOT / record['file']
            self.assertEqual(path.parent, ART)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record['sha256'])
            exports.add(path.name)
        expected = {p.name for p in ART.iterdir() if p.suffix == '.png'} | {'animation.json'}
        self.assertEqual(exports, expected)


if __name__ == '__main__':
    unittest.main()
