"""Keyboard/mouse save browser and shared defeat choices."""
from __future__ import annotations

from datetime import datetime
import pygame

from leveling import level_for_total_xp
from ui_style import FOREST_DARK, GOLD, IVORY, MUTED


class SaveMenu:
    PAGE_SIZE = 4

    def __init__(self, game):
        self.game = game
        self.is_open = False
        self.mode = 'load'
        self.selected = 0
        self.rows = []
        self.confirming = False
        self.confirm_yes = False
        self.message = ''
        self._held = False
        self.buttons = []
        self.back_rect = pygame.Rect(354, 284, 108, 26)
        self.prev_rect = pygame.Rect(18, 284, 45, 26)
        self.next_rect = pygame.Rect(70, 284, 45, 26)

    def open(self, mode='load'):
        self.mode = mode
        self.is_open = True
        self.selected = 0
        self.confirming = self.confirm_yes = self._held = False
        self.message = ''
        self.refresh()
        if mode=='game_over':
            self.selected=next(i for i,row in enumerate(self.rows)
                               if row[2]!='quick' or row[1] is not None)
        self.game._mouse_held = False

    def refresh(self):
        saves = self.game.saves
        if self.mode == 'game_over':
            self.rows = [('Load Last Manual Save', saves.latest('manual'), 'quick'),
                         ('Load Last Autosave', saves.latest('auto'), 'quick'),
                         ('Load Game', None, 'browse'), ('Return to Title', None, 'title')]
        else:
            self.rows = saves.entries(all_campaigns=self.mode == 'load')
            if self.mode == 'save':self.rows = [row for row in self.rows if row[2][0] == 'manual']
        self.selected = min(self.selected, max(0,len(self.rows)-1))

    def close(self):
        self.is_open = False
        self.confirming = self._held = False
        self.game._mouse_held = False

    def back(self):
        if self.confirming:
            self.confirming = False
        elif self.mode == 'game_over':return
        elif self.game.game_over:self.open('game_over')
        else:self.close()

    def activate(self):
        if not self.rows:return
        row = self.rows[self.selected]
        if self.mode == 'game_over':
            if row[2] == 'browse':self.open('load')
            elif row[2] == 'title':self.game.return_to_title()
            elif row[1] is not None:
                if not self.game.saves.load(row[1]):self.message = self.game.saves.notice
            return
        if self.mode == 'save':
            if not self.confirming and self.game.saves.library.occupied(row[2][1]):
                self.confirming = True
                self.confirm_yes = False
                return
            if self.game.saves.manual(row[2][1]):
                self.confirming = False
                self.refresh()
            self.message = self.game.saves.notice
        elif row[1] is not None:
            if not self.confirming and not (self.game.on_title or self.game.game_over):
                self.confirming = True
                self.confirm_yes = False
                return
            if not self.game.saves.load(row):
                self.confirming = False
                self.message = self.game.saves.notice
        else:self.message = 'No readable save in this slot.'

    def handle_event(self, event):
        if event.type == pygame.WINDOWFOCUSLOST:self._held = False
        if not self.game._music_focused:return True
        if event.type == pygame.KEYDOWN and not getattr(event,'repeat',False):
            if event.key == pygame.K_ESCAPE:self.back()
            elif self.confirming:
                if event.key in (pygame.K_LEFT,pygame.K_RIGHT,pygame.K_UP,pygame.K_DOWN):
                    self.confirm_yes = not self.confirm_yes
                elif event.key in (pygame.K_RETURN,pygame.K_KP_ENTER,pygame.K_SPACE):
                    if self.confirm_yes:self.activate()
                    else:self.back()
            elif event.key in (pygame.K_UP,pygame.K_w,pygame.K_DOWN,pygame.K_s):
                self.selected = (self.selected+(-1 if event.key in (pygame.K_UP,pygame.K_w) else 1)) % max(1,len(self.rows))
            elif event.key in (pygame.K_LEFT,pygame.K_PAGEUP,pygame.K_RIGHT,pygame.K_PAGEDOWN):
                step = -1 if event.key in (pygame.K_LEFT,pygame.K_PAGEUP) else 1
                self.selected = max(0,min(len(self.rows)-1,self.selected+step*self.PAGE_SIZE))
            elif event.key in (pygame.K_RETURN,pygame.K_KP_ENTER,pygame.K_SPACE):self.activate()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:self._held = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self._held:
            self._held = True
            point = self.game.to_canvas(event.pos)
            if point is None:return True
            if self.confirming:
                if pygame.Rect(120,166,110,32).collidepoint(point):self.activate()
                elif pygame.Rect(250,166,110,32).collidepoint(point):self.back()
            elif self.back_rect.collidepoint(point):self.back()
            elif self.prev_rect.collidepoint(point):self.selected = max(0,self.selected-self.PAGE_SIZE)
            elif self.next_rect.collidepoint(point):self.selected = min(len(self.rows)-1,self.selected+self.PAGE_SIZE)
            else:
                for index, rect in self.buttons:
                    if rect.collidepoint(point):
                        self.selected = index
                        self.activate()
                        break
        return True

    @staticmethod
    def summary(entry):
        if entry is None:return 'Empty slot'
        metadata = entry['metadata']
        try:date = datetime.fromisoformat(metadata['saved_at']).astimezone().strftime('%b %d, %H:%M')
        except (ValueError,TypeError):date = 'Unknown date'
        seconds = int(metadata.get('playtime',0))
        payload=entry['payload']
        party=payload.get('party',{})
        progression=payload.get('character_levels',{})
        active=party.get('active',['caelan']) if isinstance(party,dict) else []
        records=progression.get('characters',{}) if isinstance(progression,dict) else {}
        levels=[]
        if isinstance(active,list) and isinstance(records,dict):
            for key in active:
                if not isinstance(key,str):continue
                try:levels.append(str(level_for_total_xp(records[key]['total_xp'])))
                except (KeyError,TypeError,ValueError):continue
        levels='/'.join(levels)
        return f'{date}  ·  {seconds//3600}:{seconds//60%60:02}  ·  Lv {levels or "1"}'

    def draw(self):
        g = self.game
        _,size,origin = g._ensure_ui_surface()
        surface = g.ui_surface
        surface.fill(FOREST_DARK)
        p = g.ui.painter(surface)
        heading = {'save':'Save Game','load':'Load Game','game_over':'Game Over'}[self.mode]
        p.text(heading,(240,12),role='heading',anchor='midtop',bold=True,color=GOLD)
        hint = 'Playtest saves' if g._is_quest_playtest else 'Manual slots and autosaves'
        p.text(hint,(240,40),role='small',anchor='midtop',color=MUTED)
        page = self.selected//self.PAGE_SIZE
        first = page*self.PAGE_SIZE
        self.buttons = []
        for index in range(first,min(first+self.PAGE_SIZE,len(self.rows))):
            row = self.rows[index]
            rect = pygame.Rect(18,62+(index-first)*49,444,46)
            self.buttons.append((index,rect))
            p.button(rect,'',selected=index==self.selected,
                     disabled=self.mode=='game_over' and row[2]=='quick' and row[1] is None)
            p.clip(rect.inflate(-12,-4))
            entry = row[1][1] if self.mode=='game_over' and row[2]=='quick' and row[1] else row[1]
            if self.mode=='game_over' and row[2] in ('browse','title'):detail = ''
            elif entry:
                location=str(entry['metadata'].get('location','Journey'))
                player=entry['payload'].get('player',{})
                scene=player.get('scene') if isinstance(player,dict) else None
                if location==scene:
                    try:location=g._scene_by_id(scene).data['name']
                    except (KeyError,ValueError,OSError,pygame.error):location='Journey'
                detail = self.summary(entry)
            else:detail = 'Unavailable' if self.mode=='game_over' else 'Empty slot'
            label = row[0] if not entry or self.mode=='game_over' else row[0]+' · '+location
            p.text(label,(rect.x+8,rect.y+3),role='small',bold=True,color=IVORY)
            p.text(detail,(rect.x+8,rect.y+25),role='small',color=MUTED)
            p.clip()
        selected_entry=self.rows[self.selected][1] if self.rows and self.mode!='game_over' else None
        detail=self.message or (selected_entry['metadata'].get('quest','') if selected_entry else '')
        p.clip(pygame.Rect(18,260,444,23))
        p.text(detail,(18,262),role='small',color=GOLD)
        p.clip()
        if self.mode!='game_over':
            p.button(self.prev_rect,'<')
            p.button(self.next_rect,'>')
            p.text(f'{page+1}/{max(1,(len(self.rows)+3)//4)}',(130,290),role='small',color=MUTED)
            p.button(self.back_rect,'Back')
        if self.confirming:
            p.veil(210)
            p.panel((45,92,390,120))
            prompt='Overwrite this save?' if self.mode=='save' else 'Load and leave current progress?'
            for i,line in enumerate(p.wrap(prompt,360)):
                p.text(line,(240,102+i*p.font().get_linesize()),anchor='midtop',color=GOLD)
            p.button((120,166,110,32),'Confirm',selected=self.confirm_yes)
            p.button((250,166,110,32),'Cancel',selected=not self.confirm_yes)
        g.window.fill(FOREST_DARK)
        g.window.blit(surface,origin)
        if not g._is_embedded:pygame.display.flip()
