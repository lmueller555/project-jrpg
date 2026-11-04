"""Keep planetary-return teaching and its implementation scripts aligned."""
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AetherDoctrineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lantern = json.loads((ROOT/'assets/story/lantern/rest_scene.json').read_text())
        cls.regent = json.loads((ROOT/'assets/story/regent/scene.json').read_text())

    def test_lantern_teaches_planetary_return_without_soul_lanterns(self):
        text = ' '.join(line['text'] for name in
                        ('liam_questions', 'sanctuary_welcome', 'returning_life')
                        for line in self.lantern[name])
        self.assertIn('plants and animals', text.lower())
        self.assertIn('aether returns to the planet', text.lower())
        self.assertIn("It's still a lamp", text)
        self.assertNotIn('gods', text.lower())

    def test_regent_stewardship_uses_the_planetary_cycle(self):
        text = ' '.join(line['text'] for lines in self.regent.values()
                        for line in lines if line['speaker'] == 'serene')
        self.assertIn("planet's aether cycle", text)
        self.assertNotIn('return it to the gods', text)

    def test_current_implementation_scripts_match_the_doctrine_exchanges(self):
        punctuation = str.maketrans({'\u201c': '"', '\u201d': '"', '\u2019': "'"})
        cases = (
            ('docs/narrative/game_01/CH01_MQ04_PR3.md',
             [line for name in ('liam_questions', 'sanctuary_welcome', 'returning_life')
              for line in self.lantern[name]]),
            ('docs/narrative/game_01/CH01_MQ03.md',
             [line for lines in self.regent.values() for line in lines
              if line['speaker'] == 'serene' and
              ('planet' in line['text'].lower() or 'return it to the gods' in line['text'])]),
        )
        for filename, lines in cases:
            with self.subTest(script=filename):
                self.assertTrue(lines)
                document = (ROOT/filename).read_text().translate(punctuation)
                actual = re.findall(r'^- \*\*[^*]+:\*\* "(.*)"$', document, re.MULTILINE)
                for line in lines:
                    self.assertIn(line['text'].translate(punctuation), actual)
