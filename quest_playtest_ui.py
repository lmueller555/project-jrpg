"""Quest metadata browsing using the existing accessible catalogue controls."""
from gallery_ui import GalleryUI
from quest_playtest import quest_entries


class QuestPlaytestUI(GalleryUI):
    heading = 'Quests (Playtest)'
    subtitle = 'Start before any quest. Temporary progress; normal save and settings stay untouched.'
    play_label = 'Start playtest'
    item_noun = 'quests'
    empty_heading = 'No quest starts yet'
    empty_description = 'Implemented quest starts will appear here.'
    error_heading = 'Playtest unavailable'
    error_back_label = 'Back to Quests'
    show_thumbnails = False

    def __init__(self, game, entries=None):
        super().__init__(game, quest_entries(game.quests) if entries is None else entries)

    def activate(self):
        if self.selected_entry is not None:
            self.error = None
            self.resume()
            self.game.ui.sound('confirm')
            self.game.launch_quest_playtest(self.selected_entry.id)
        return True

    def _back(self):
        self.resume()
        self.game.ui.sound('back')
        self.game.close_quest_playtests()
