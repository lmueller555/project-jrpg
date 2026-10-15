"""Dialogue layout, text wrapping and identity safety regression tests."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from engine.dialogue_ui import DialogueBox, FontManager, wrap
import pygame


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
        panel = DialogueBox()
        panel.show("The sanctuary is quiet.", speaker="Caelen",
                   mode="character", portrait="caelen.neutral")
        self.assertIsNone(panel._portrait())
        surface = pygame.Surface((960, 672))
        panel.draw(surface)

    def test_caelen_expression_registry_and_safe_missing_files(self):
        panel = DialogueBox()
        self.assertEqual(set(panel.approved_portraits), {
            "caelen.neutral", "caelen.happy", "caelen.concerned",
            "caelen.determined", "caelen.surprised"})
        panel.show("Ready to go.", speaker="Caelen", mode="character")
        self.assertEqual(panel.message.portrait, "caelen.neutral")
        self.assertIsNone(panel._portrait())
        self.assertIsNone(DialogueBox()._portrait())

    def test_narration_and_character_share_panel(self):
        panel = DialogueBox()
        surface = pygame.Surface((960, 672))
        for mode in ("narration", "character"):
            panel.show("The same styled box.", speaker="Sanctuary", mode=mode)
            panel.draw(surface)
            self.assertTrue(panel.advance(surface.get_size()))


if __name__ == "__main__":
    unittest.main()
