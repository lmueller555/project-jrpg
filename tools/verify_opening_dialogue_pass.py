"""Capture the revised morning through MQ02 from an actual New Game.

No main-quest progress or actor stations are seeded. The driver uses production
walking, doors, proximity conversations, normal E/Space and explicit choices.
Historical reviews are left untouched; new evidence goes under work/.
"""
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT));sys.path.insert(0, str(ROOT/'tests'))
import pygame
from test_opening_dialogue_pass import OpeningDialogueDriver, dialogue_sets
from quests import OPENING_QUEST, MILL_QUEST

OUT = ROOT/'work/opening-dialogue-pass'
SELECTED = {
    'opening_greeting': ('breakfast', lambda text: '*' in text),
    'serene_quest_offer': ('household_briefing', lambda text: 'bread and lamp oil' in text),
    'halden_arrival': ('halden_flour', lambda text: 'flour' in text.lower()),
    'halden_goodbye': ('remaining_visits', lambda text: 'southern bridge' in text),
    'elira_resolution': ('elira_remembrance', lambda text: '*' in text),
    'venn_arrival': ('venn_family', lambda text: 'little one' in text.lower()),
    'serene_quest_report': ('serene_report', lambda text: '*' in text),
    'opening_mill_arrival': ('mira_whereabouts', lambda text: 'workbench' in text),
    'mill_reunion': ('mira_reunion', lambda text: '*' in text),
    'mill_diagnosis': ('north_road', lambda text: 'north' in text),
    'mill_prepare_done': ('bypass_after_action', lambda text: True),
    'mill_encouragement_failed': ('small_success', lambda text: '*' in text),
    'mill_repair_done': ('repair_after_action', lambda text: True),
    'mill_resolution': ('festival_flour', lambda text: 'Festival of Light' in text),
}


class Capture:
    def __init__(self):
        OUT.mkdir(parents=True, exist_ok=True)
        self.stills = [];self.layout_checks = []
        self.driver = OpeningDialogueDriver(on_page=self.page)

    def page(self, driver, identifier, page):
        if identifier not in SELECTED:return
        name, predicate = SELECTED[identifier]
        if name+'.png' in self.stills:return
        text = driver.g.social._source_lines[page['source_line']]['text']
        if not predicate(text):return
        g = driver.g;social = g.social;original_scale = g.audio.text_scale;original_index = social.page_index
        g.draw();pygame.image.save(g.ui_surface, OUT/(name+'.png'));self.stills.append(name+'.png')
        for scale in (1.0, 1.5):
            g.audio.set_text_scale(scale);social.refresh_layout();g.draw()
            layout = social.bubble.layout()
            assert pygame.Rect(0, 0, 480, 320).contains(layout.panel)
            self.layout_checks.append({'scene': identifier, 'scale': scale,
                                       'panel': list(layout.panel), 'speaker': social.page['speaker']})
            if scale != 1.0:
                filename = name+'_large.png';pygame.image.save(g.ui_surface, OUT/filename);self.stills.append(filename)
        # The UI comparison never advances story; resume the exact normal-size
        # page/cursor that the real-input driver was acknowledging.
        g.audio.set_text_scale(original_scale);social.refresh_layout();social.page_index = original_index
        if identifier == 'mill_prepare_done':
            assert g.mill_quest.prepared and g.mill_quest.action is None
        if identifier == 'mill_repair_done':
            assert g.mill_quest.restored and g.mill_quest.action is None

    def run(self):
        d = self.driver
        try:
            d.run()
            for name in SELECTED:
                assert name in d.sources, ('Missing main dialogue', name)
            main = [name for name in d.sources
                    if (name in ('serene_quest_offer', 'serene_quest_report') or
                        name.startswith(('opening_', 'halden_', 'elira_', 'venn_', 'mill_')))
                    and not name.endswith(('reminder', 'waiting'))
                    and not name.startswith('mill_reminder_')]
            for identifier in main:
                actual = sum(page['scene'] == identifier for page in d.pages)
                expected = len(d.g.social._make_pages(d.sources[identifier]))
                assert actual == expected, ('Missing/repeated pages', identifier, actual, expected)
            assert d.g.venn_visit.magicks_failed
            assert 'mill_encouragement_failed' in d.sources and 'mill_encouragement' not in d.sources
            assert d.g.quests.status(OPENING_QUEST) == d.g.quests.status(MILL_QUEST) == 'completed'
            assert d.g.elira_visit.lantern == 'table' and d.g.venn_visit.repaired and d.g.mill_quest.restored
            assert all(Path(OUT/name).exists() for name in self.stills)
            data = {'start': 'actual New Game; no MQ01/MQ02 progress, actor positions or household receipts seeded',
                    'input': 'real walking, animated doors, proximity conversations, E and Space key events, explicit choices',
                    'household_order': list(d.order), 'venn_approach': d.method,
                    'mq01_completed': True, 'mq02_completed': True,
                    'main_scenes': main, 'observed_scenes': d.scenes,
                    'dialogue_pages': len(d.pages), 'pages': d.pages,
                    'door_and_trail_transitions': d.transitions,
                    'single_actor_speaker_checks': d.identity_checks,
                    'layout_checks': self.layout_checks, 'stills': self.stills,
                    'quest_snapshots': {'opening': d.g.opening.to_dict(), 'halden': d.g.halden_visit.to_dict(),
                                        'elira': d.g.elira_visit.to_dict(), 'venn': d.g.venn_visit.to_dict(),
                                        'opening_conclusion': d.g.opening_conclusion.to_dict(),
                                        'mill': d.g.mill_quest.to_dict()}}
            (OUT/'verification.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
            transcript = ['# Opening dialogue pass — actual New Game review', '',
                          'Captured through normal production-game progression, including the Venn magick failure.', '']
            for identifier in d.sources:
                transcript += ['## '+identifier, '']
                for line in d.sources[identifier]:
                    speaker = d.g.social.data['speakers'][line['speaker']]['name']
                    # Code preserves the requested literal asterisks in the review.
                    transcript += [speaker+': `'+line['text']+'`', '']
            (OUT/'dialogue.md').write_text('\n'.join(transcript), encoding='utf-8')
            print('Verified actual New Game through MQ02:', len(main), 'main scenes;', len(d.pages), 'pages;',
                  len(d.transitions), 'real door/trail transfers;', d.identity_checks, 'speaker identity checks.')
            print('Captured', len(self.stills), 'native normal/large-text stills in', OUT)
        finally:d.close()


if __name__ == '__main__':Capture().run()
