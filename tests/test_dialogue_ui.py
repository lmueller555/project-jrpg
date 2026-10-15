"""Dialogue layout, text wrapping and identity safety regression tests."""
import os
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from engine.dialogue_ui import DialogueBox, FontManager, wrap
import pygame

ROOT = Path(__file__).resolve().parents[1]


class DialogueUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_wrap_uses_actual_font_metrics(self):
        font = FontManager().get(22)
        lines = wrap("Sanctuary memories are waiting to be found here.", font, 165)
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(font.size(line)[0] <= 165 for line in lines))

    def test_pages_advance_and_close(self):
        panel = DialogueBox()
        panel.show(" ".join(["Morning light fills the sanctuary."] * 50), speaker="Eldenmere")
        pages = panel._pages((960, 672))
        self.assertGreater(len(pages), 1)
        while panel.message:
            self.assertTrue(panel.advance((960, 672)))
        self.assertIsNone(panel.message)

    def test_unapproved_character_portrait_never_substituted(self):
        panel = DialogueBox(ROOT / "assets")
        panel.show("The sanctuary is quiet.", speaker="Caelen",
                   mode="character", portrait="other.neutral")
        self.assertIsNone(panel._portrait())
        surface = pygame.Surface((960, 672))
        panel.draw(surface)

    def test_caelen_expression_registry_and_approved_files(self):
        panel = DialogueBox(ROOT / "assets")
        self.assertEqual(set(panel.approved_portraits), {
            "caelen.neutral", "caelen.happy", "caelen.concerned",
            "caelen.determined", "caelen.surprised"})
        panel.show("Ready to go.", speaker="Caelen", mode="character")
        self.assertEqual(panel.message.portrait, "caelen.neutral")
        self.assertEqual(panel._portrait().get_size(), (96, 96))
        for portrait_id, relative_path in panel.approved_portraits.items():
            with self.subTest(portrait_id=portrait_id):
                self.assertTrue((ROOT / "assets" / relative_path).is_file())
                panel.show("Ready.", speaker="Caelen", mode="character", portrait=portrait_id)
                self.assertEqual(panel._portrait().get_size(), (96, 96))
        self.assertIsNone(DialogueBox()._portrait())

    def test_narration_and_character_share_panel(self):
        panel = DialogueBox(ROOT / "assets")
        surface = pygame.Surface((960, 672))
        panel.show("The same styled box.", speaker="Sanctuary", mode="narration")
        panel.draw(surface)
        self.assertTrue(panel.advance(surface.get_size()))
        panel.show("The same styled box.", speaker="Caelen", mode="character")
        panel.draw(surface)
        self.assertIsNotNone(panel._portrait())
        self.assertTrue(panel.advance(surface.get_size()))


if __name__ == "__main__":
    unittest.main()
