"""Full-width Aether Lattice exploration and explicit purchases."""
import math
import pygame

from attribute_icons import draw_attribute_icon
from ui_style import (FOREST, FOREST_DARK, FOREST_LIGHT, IVORY, GOLD, BRASS,
                      MUTED, DISABLED, ERROR)


class LatticeUI:
    MIN_ZOOM = .05
    MAX_ZOOM = 2.0
    CAMERA_DURATION = .18
    ZOOM_DURATION = .18
    CURSOR_SPEED = 180.0
    PULSE_PERIOD = 1.2
    DIRECTIONS = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0),
                  pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}

    @staticmethod
    def _steps_label(amount):return str(amount)+' Step'+('' if amount == 1 else 's')

    def __init__(self, game):
        self.game = game
        self.character_id = getattr(game.attributes, 'character_id', 'caelan')
        self.close_rect = pygame.Rect(438, 14, 24, 24)
        self.help_rect = pygame.Rect(410, 14, 22, 24)
        self.map_rect = pygame.Rect(16, 78, 448, 226)
        self.zoom_out_rect = pygame.Rect(24, 275, 24, 22)
        self.zoom_in_rect = pygame.Rect(52, 275, 24, 22)
        self.zoom_readout_rect = pygame.Rect(82, 275, 50, 22)
        self.fit_rect = pygame.Rect(138, 275, 48, 22)
        self.reset_zoom_rect = pygame.Rect(192, 275, 82, 22)
        self.help_panel = pygame.Rect(32, 40, 416, 248)
        self.help_view = pygame.Rect(46, 80, 386, 188)
        self.help_close_rect = pygame.Rect(410, 47, 24, 24)
        self.confirm_panel = pygame.Rect(28, 56, 424, 188)
        self.confirm_view = pygame.Rect(42, 94, 396, 114)
        self.confirm_rect = pygame.Rect(250, 216, 84, 20)
        self.cancel_rect = pygame.Rect(344, 216, 84, 20)
        self.reset()

    @property
    def lattice(self):return self.game.lattice

    @property
    def board(self):return self.lattice.board

    def _painter(self, canvas=None):
        return self.game.ui.painter(canvas if canvas is not None else self.game.ui_surface)

    def reset(self):
        self.is_open = False
        self.selected = None
        self.hovered = None
        self.pointer = None
        self.zoom = .8
        self.target_zoom = self.zoom
        self._zoom_start = self.zoom
        self._zoom_elapsed = self.ZOOM_DURATION
        self._zoom_anchor = None
        self.pan = pygame.Vector2(0, 0)
        self.cursor_position = pygame.Vector2(0, 0)
        self._keys = set()
        self._camera_start = self.pan.copy()
        self._camera_target = self.pan.copy()
        self._camera_elapsed = self.CAMERA_DURATION
        self._pulse_elapsed = 0.0
        self._drag_moved = False
        self._drag_start = None
        self._drag_pan = None
        self._click_world = None
        self.pending = None
        self.message = ''
        self.notice_open = False
        self.notice_title = ''
        self._held = False
        self.dragging = False
        self.help_open = False
        self.help_scroll = 0
        self.help_max_scroll = 0
        self.confirm_scroll = 0
        self.confirm_max_scroll = 0

    def open(self):
        self.is_open = True
        self.pending = None
        self.message = ''
        self.notice_open = False
        self.hovered = None
        self.pointer = None
        self.help_open = False
        self._held = self.dragging = False
        self._keys.clear()
        self._pulse_elapsed = 0.0
        self._select(self.lattice.state(self.character_id)['position'], center=True)
        self.center_on(self.selected, immediate=True)
        self.game.ui.sound('confirm')

    def close(self):
        self.is_open = False
        self.pending = None
        self.notice_open = False
        self.hovered = None
        self.pointer = None
        self.help_open = False
        self._held = self.dragging = False
        self._keys.clear()
        self._cancel_zoom()
        self.game.ui.sound('back')

    def _select(self, identifier, center=False):
        if identifier not in self.board.nodes:return
        self._zoom_anchor = None
        self.cursor_position.update(self.board.nodes[identifier]['position'])
        self._pulse_elapsed = 0.0
        if identifier != self.selected:
            self.selected = identifier
            self.pending = None
            self.notice_open = False
            self.message = ''
            self.game.ui.sound('move')
        if center:self.center_on(identifier)

    @property
    def navigating(self):return bool(self._keys) or self.dragging

    @property
    def pulse_strength(self):
        if getattr(self.game.audio, 'reduced_motion', False):return 1.0
        return .5+.5*math.cos(self._pulse_elapsed*math.tau/self.PULSE_PERIOD)

    def _camera_to(self, position, immediate=False):
        self._zoom_anchor = None
        target = pygame.Vector2(position)
        if immediate or getattr(self.game.audio, 'reduced_motion', False):
            self.pan.update(target)
            self._camera_elapsed = self.CAMERA_DURATION
        else:
            self._camera_start = self.pan.copy()
            self._camera_elapsed = 0.0
        self._camera_target = target

    def center_on(self, identifier, immediate=False):
        if identifier in self.board.nodes:
            self._camera_to(self.board.nodes[identifier]['position'], immediate)

    def _nearest_node(self, position):
        point = pygame.Vector2(position)
        return min(self.board.nodes, key=lambda identifier:
                   (point.distance_squared_to(self.board.nodes[identifier]['position']), identifier))

    def _clamp_cursor(self):
        points = [node['position'] for node in self.board.nodes.values()]
        padding = 48
        self.cursor_position.x = max(min(p[0] for p in points)-padding,
                                     min(max(p[0] for p in points)+padding, self.cursor_position.x))
        self.cursor_position.y = max(min(p[1] for p in points)-padding,
                                     min(max(p[1] for p in points)+padding, self.cursor_position.y))

    def _settle_cursor(self):
        self._select(self._nearest_node(self.cursor_position), center=True)

    def _stop_navigation(self, settle=True):
        was_navigating = self.navigating
        self._keys.clear()
        self.dragging = False
        self._drag_pan = self._drag_start = self._click_world = None
        self._drag_moved = False
        if settle and was_navigating:self._settle_cursor()

    def _drag_to(self, point):
        """Keep the grabbed map point under the pointer, without camera lag."""
        if not self.dragging or point is None:return
        delta = pygame.Vector2(point)-self._drag_start
        if not self._drag_moved and delta.length_squared() < 9:return
        self._drag_moved = True
        self.pan.update(self._drag_pan-delta/self.zoom)
        self.cursor_position.update(self.pan)
        self._camera_target = self.pan.copy()
        self._camera_elapsed = self.CAMERA_DURATION

    def update(self, dt):
        """Advance exploration and selection feedback while the world is paused."""
        if not self.is_open:return
        dt = max(0.0, min(float(dt), .25))
        if self.pending is not None or self.help_open or self.notice_open:
            self._stop_navigation()
        if self._zoom_elapsed < self.ZOOM_DURATION:
            self._zoom_elapsed = min(self.ZOOM_DURATION, self._zoom_elapsed+dt)
            t = self._zoom_elapsed/self.ZOOM_DURATION
            eased = 1-(1-t)**3
            self.zoom = (self.target_zoom if self._zoom_elapsed >= self.ZOOM_DURATION
                         or getattr(self.game.audio, 'reduced_motion', False)
                         else self._zoom_start+(self.target_zoom-self._zoom_start)*eased)
        if self._keys and not self.dragging:
            direction = sum((pygame.Vector2(self.DIRECTIONS[key]) for key in self._keys), pygame.Vector2())
            if direction.length_squared():
                direction.normalize_ip()
                self.cursor_position += direction*self.CURSOR_SPEED*dt/self.zoom
                self._clamp_cursor()
        if self.navigating:
            self._zoom_anchor = None
            # Drag events position the camera directly; keyboard exploration follows.
            if not self.dragging:
                if getattr(self.game.audio, 'reduced_motion', False):self.pan.update(self.cursor_position)
                else:self.pan += (self.cursor_position-self.pan)*(1-math.exp(-24*dt))
            self._camera_target = self.pan.copy()
            self._camera_elapsed = self.CAMERA_DURATION
        elif self._zoom_anchor is not None:
            world, offset = self._zoom_anchor
            self.pan.update(world-offset/self.zoom)
            if self._zoom_elapsed >= self.ZOOM_DURATION:self._zoom_anchor = None
        elif self._camera_elapsed < self.CAMERA_DURATION:
            if getattr(self.game.audio, 'reduced_motion', False):
                self._camera_to(self._camera_target, immediate=True)
            self._camera_elapsed = min(self.CAMERA_DURATION, self._camera_elapsed+dt)
            t = self._camera_elapsed/self.CAMERA_DURATION
            eased = 1-(1-t)**3
            self.pan.update(self._camera_start.lerp(self._camera_target, eased))
        if not self.navigating:self._pulse_elapsed = (self._pulse_elapsed+dt) % self.PULSE_PERIOD

    def node_position(self, identifier):
        return self._map_position(self.board.nodes[identifier]['position'])

    def _map_position(self, position):
        return pygame.Vector2(self.map_rect.center)+(pygame.Vector2(position)-self.pan)*self.zoom

    def edge_points(self, edge):
        """Sample an authored curve; an ordinary connection stays one straight line."""
        start, end = (pygame.Vector2(self.board.nodes[edge[key]]['position'])
                      for key in ('from', 'to'))
        if 'curve' not in edge:return [self._map_position(start), self._map_position(end)]
        control = pygame.Vector2(edge['curve'])
        length = (start.distance_to(control)+control.distance_to(end))*self.zoom
        segments = max(3, min(64, math.ceil(length/7)))
        return [self._map_position(start*(1-t)**2+control*(2*(1-t)*t)+end*t*t)
                for t in (index/segments for index in range(segments+1))]

    def _edge_midpoint(self, edge):
        start, end = (pygame.Vector2(self.board.nodes[edge[key]]['position'])
                      for key in ('from', 'to'))
        point = ((start+end)/2 if 'curve' not in edge else
                 start*.25+pygame.Vector2(edge['curve'])*.5+end*.25)
        return self._map_position(point)

    @staticmethod
    def _draw_path(painter, color, points, width=1, dashed=False):
        if not dashed:
            pygame.draw.lines(painter.canvas, color, False,
                              [painter.point(point) for point in points],
                              max(1, round(width*painter.scale)))
            return
        # Keep dash lengths continuous across the sampled curve's segments.
        drawing, remaining = True, 5.0
        for start, end in zip(points, points[1:]):
            delta = end-start
            length = delta.length()
            if not length:continue
            direction = delta/length
            cursor = start.copy()
            while length > 1e-7:
                step = min(length, remaining)
                target = cursor+direction*step
                if drawing:painter.line(color, cursor, target, width)
                cursor = target
                length -= step
                remaining -= step
                if remaining <= 1e-7:
                    drawing = not drawing
                    remaining = 5.0 if drawing else 4.0

    def fit_board(self):
        points = [pygame.Vector2(node['position']) for node in self.board.nodes.values()]
        points.extend(pygame.Vector2(edge['curve']) for edge in self.board.edges if 'curve' in edge)
        left, right = min(p.x for p in points), max(p.x for p in points)
        top, bottom = min(p.y for p in points), max(p.y for p in points)
        self._stop_navigation(settle=False)
        target = min((self.map_rect.width-44)/max(1, right-left),
                     (self.map_rect.height-74)/max(1, bottom-top))
        self._zoom_to(target, focus=((left+right)/2, (top+bottom)/2))

    def reset_zoom(self):
        self._stop_navigation()
        self._zoom_to(1.0, focus=self.board.nodes[self.selected]['position'])

    def _cancel_zoom(self):
        self.target_zoom = self._zoom_start = self.zoom
        self._zoom_elapsed = self.ZOOM_DURATION
        self._zoom_anchor = None

    def _zoom_to(self, amount, focus=None, anchor=None):
        """Retarget from the rendered view, preserving a wheel's world anchor."""
        self.target_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, amount))
        self._zoom_start = self.zoom
        self._zoom_elapsed = 0.0
        if anchor is not None and not self.navigating:
            offset = pygame.Vector2(anchor)-pygame.Vector2(self.map_rect.center)
            self._zoom_anchor = (self.pan+offset/self.zoom, offset)
            self._camera_elapsed = self.CAMERA_DURATION
        else:
            self._zoom_anchor = None
            if focus is not None:self._camera_to(focus)
        if getattr(self.game.audio, 'reduced_motion', False):
            self.zoom = self.target_zoom
            self._zoom_elapsed = self.ZOOM_DURATION
            if self._zoom_anchor is not None:
                world, offset = self._zoom_anchor
                self.pan.update(world-offset/self.zoom)
                self._zoom_anchor = None

    def _zoom(self, factor, anchor=None):
        if self.dragging:return
        target = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.target_zoom*factor))
        if math.isclose(target, self.target_zoom):return
        focus = self.cursor_position if self.navigating else self.board.nodes[self.selected]['position']
        self._zoom_to(target, focus=focus, anchor=anchor)

    def _node_at(self, point):
        if point is None or not self.map_rect.collidepoint(point):return None
        radius = max(8, 11*self.zoom)
        nodes = [(self.node_position(identifier).distance_squared_to(point), identifier)
                 for identifier in self.board.nodes]
        distance, identifier = min(nodes)
        return identifier if distance <= radius*radius else None

    def _move_reason(self):
        return self.game.lattice_move_reason(self.selected)

    def _activation_reason(self):
        return self.game.lattice_activation_reason(self.selected)

    def _prepare(self, action):
        self._stop_navigation()
        reason = self._move_reason() if action == 'move' else self._activation_reason()
        if reason:
            self._show_notice(action, reason)
            return False
        self.pending = (action, self.selected)
        self.notice_open = False
        self.confirm_scroll = 0
        self.message = ''
        self.game.ui.sound('confirm')
        return True

    def _show_notice(self, action, reason):
        self._stop_navigation()
        self.pending = None
        self.message = reason
        self.notice_title = 'Cannot travel' if action == 'move' else 'Cannot activate'
        self.notice_open = True
        self.confirm_scroll = 0

    def _dismiss_notice(self):
        self.notice_open = False
        self.message = ''
        self.confirm_scroll = 0
        self.game.ui.sound('back')

    def _commit(self):
        if self.pending is None:return False
        action, identifier = self.pending
        self.pending = None
        if identifier != self.selected:return False
        success = (self.game.move_lattice(identifier) if action == 'move'
                   else self.game.activate_lattice(identifier))
        if success:
            self.message = 'Travel complete.' if action == 'move' else 'Node activated.'
            if action == 'move':self.center_on(identifier)
            self.game.ui.sound('confirm')
        else:
            reason = self._move_reason() if action == 'move' else self._activation_reason()
            self._show_notice(action, reason or 'This action is unavailable.')
        return success

    def _action(self, action):
        if self.pending == (action, self.selected):return self._commit()
        return self._prepare(action)

    def detail_text(self):
        if self.selected not in self.board.nodes:return []
        node = self.board.nodes[self.selected]
        state = self.lattice.state(self.character_id)
        lines = [node.get('name', self.selected)]
        if self.selected == state['position']:lines.append('Current position')
        if self.selected in state['activated']:lines.append('Activated')
        elif self.selected in state['visited']:lines.append('Visited')
        if node['kind'] == 'stat':
            label = self.game.attributes.definitions[node['stat']]['label']
            value = self.game.attributes.value(node['stat'])
            lines.append(label+' +'+str(node['amount']))
            if self.selected not in state['activated']:
                lines.append('After activation: '+str(value)+' → '+str(value+node['amount']))
            if node['stat'] in ('hp', 'mp'):lines.append('Current '+label+' stays unchanged.')
        elif node['kind'] == 'ability':
            ability = self.board.abilities[node['ability_id']]
            lines.extend((ability['name'], ability['description']))
        else:lines.append('Blank node: travel only.')
        route = self.lattice.route(self.selected, self.character_id)
        if route is not None:
            distance = max(0, len(route)-1)
            lines.append('Travel: '+self._steps_label(distance))
            if distance:lines.append('Return along this route: '+self._steps_label(distance))
        else:lines.append('No open route at this Attunement.')
        reason = self._move_reason()
        if reason:lines.append(reason)
        if node['cost']:
            lines.append('Activation cost')
            for crystal, amount in node['cost'].items():
                name = self.board.crystals[crystal]['name']
                lines.append(name+' ×'+str(amount)+' ('+str(self.game.inventory.quantity(crystal))+' owned)')
            reason = self._activation_reason()
            if reason:lines.append(reason)
        lines.append(node.get('description', ''))
        if self.pending is not None:lines.append('Enter confirms. Esc cancels.')
        if self.message:lines.insert(0, self.message)
        lines.append('Aether Crystals')
        for identifier, crystal in self.board.crystals.items():
            lines.append(crystal['name']+': '+str(self.game.inventory.quantity(identifier)))
        learned = self.lattice.learned_abilities(self.character_id)
        if learned:
            lines.append('Known abilities')
            lines.extend(self.board.abilities[identifier]['name'] for identifier in learned)
        return [line for line in lines if line]

    def confirmation_text(self):
        if self.pending is None:return []
        action, identifier = self.pending
        node = self.board.nodes[identifier]
        if action == 'move':
            route = self.lattice.route(identifier, self.character_id) or []
            cost = max(0, len(route)-1)
            return ['Move to '+node.get('name', identifier),
                    'Spend '+self._steps_label(cost)+' ('+str(self.lattice.steps(self.character_id))+' available).',
                    'Return along this path also costs '+self._steps_label(cost)+'.',
                    'No crystals are spent.',
                    'Attunement remains '+str(self.lattice.rank(self.character_id))+'.']
        lines = []
        if node['kind'] == 'stat':
            label = self.game.attributes.definitions[node['stat']]['label']
            value = self.game.attributes.value(node['stat'])
            lines.append(label+': '+str(value)+' → '+str(value+node['amount']))
            if node['stat'] in ('hp', 'mp'):
                current = self.game.attributes.current_hp if node['stat'] == 'hp' else self.game.attributes.current_mp
                lines.append('Current '+label+' remains '+str(current)+'.')
        elif node['kind'] == 'ability':lines.append('Learn '+self.board.abilities[node['ability_id']]['name']+'.')
        for crystal, amount in node['cost'].items():
            lines.append(self.board.crystals[crystal]['name']+' ×'+str(amount)+
                         ' ('+str(self.game.inventory.quantity(crystal))+' owned).')
        lines.append('This node can activate once for '+self.game.attributes.name+'.')
        return lines

    def _confirmation_layout(self, painter):
        lines = []
        text_lines = [self.message] if self.notice_open else self.confirmation_text()
        for text in text_lines:lines.extend(painter.wrap(text, self.confirm_view.width, role='small'))
        height = painter.font('small').get_linesize()+3
        self.confirm_max_scroll = max(0, len(lines)*height-self.confirm_view.height)
        self.confirm_scroll = max(0, min(self.confirm_scroll, self.confirm_max_scroll))
        return lines, height

    def _layout(self, painter):
        heading_height = painter.font('heading', bold=True).get_linesize()
        small_height = painter.font('small').get_linesize()
        top = 16+heading_height+5+small_height*2+10
        self.map_rect = pygame.Rect(16, top, 448, 304-top)
        self.zoom_out_rect = pygame.Rect(24, self.map_rect.bottom-29, 24, 22)
        self.zoom_in_rect = pygame.Rect(52, self.map_rect.bottom-29, 24, 22)
        self.zoom_readout_rect = pygame.Rect(82, self.map_rect.bottom-29, 50, 22)
        self.fit_rect = pygame.Rect(138, self.map_rect.bottom-29, 48, 22)
        self.reset_zoom_rect = pygame.Rect(192, self.map_rect.bottom-29, 82, 22)
        return heading_height, small_height

    def _help_lines(self, painter):
        text = ('Hold the arrow keys to explore with the gold cursor. Release to select the nearest node. '
                'Click the map to inspect its nearest node, or use Tab / Shift+Tab to cycle nodes. '
                'Exploration never spends Steps or crystals.\n'
                'M prepares travel. A prepares activation. Press Enter or click Confirm to proceed. '
                'Esc cancels a prepared action, then returns to Pause.\n'
                'Hold the left mouse button and drag to pan the camera. Release to center the node nearest the gold cursor. '
                'Use + / - or the buttons to zoom around the selected node. The map wheel zooms at the pointer. '
                'F / Fit shows the entire lattice. 0 / 100% returns to a readable close-up. '
                'The percentage shows the current camera zoom.\n'
                'Page Up / Page Down and Home / End read longer confirmation messages.\n'
                'Each connection costs one Step, including return travel and blank nodes. '
                'Activation uses the crystals shown in its confirmation. Rank is never spent.')
        lines = painter.wrap(text, self.help_view.width, role='small')
        height = painter.font('small').get_linesize()+2
        self.help_max_scroll = max(0, len(lines)*height-self.help_view.height)
        self.help_scroll = max(0, min(self.help_scroll, self.help_max_scroll))
        return lines, height

    def handle_event(self, event):
        if not self.is_open:return False
        painter = self._painter()
        self._layout(painter)
        point = self.game.to_canvas(event.pos) if hasattr(event, 'pos') else None
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.pointer = point
        # Release/focus events must clear input even when a modal owns the keyboard.
        if event.type == pygame.KEYUP and event.key in self.DIRECTIONS:
            held = event.key in self._keys
            self._keys.discard(event.key)
            if held and not self.navigating:self._settle_cursor()
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag_to(point)
            if self.dragging and not self._drag_moved and self._click_world is not None:
                self.cursor_position.update(self._click_world)
            was_dragging = self.dragging
            self._held = self.dragging = False
            self._drag_pan = self._drag_start = self._click_world = None
            self._drag_moved = False
            if was_dragging and not self._keys:self._settle_cursor()
            return True
        if event.type in (pygame.WINDOWLEAVE, pygame.WINDOWFOCUSLOST):
            self.hovered = None
            self.pointer = None
            self._held = False
            self._stop_navigation()
            self._cancel_zoom()
            return True
        if self.notice_open:
            self._confirmation_layout(painter)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    if not getattr(event, 'repeat', False):self._dismiss_notice()
                elif event.key == pygame.K_PAGEUP:self.confirm_scroll = max(0, self.confirm_scroll-self.confirm_view.height)
                elif event.key == pygame.K_PAGEDOWN:self.confirm_scroll = min(self.confirm_max_scroll, self.confirm_scroll+self.confirm_view.height)
                elif event.key == pygame.K_HOME:self.confirm_scroll = 0
                elif event.key == pygame.K_END:self.confirm_scroll = self.confirm_max_scroll
            elif event.type == pygame.MOUSEWHEEL:
                self.confirm_scroll = max(0, min(self.confirm_max_scroll, self.confirm_scroll-event.y*24))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and point is not None:
                if self._held:return True
                self._held = True
                if self.cancel_rect.collidepoint(point):self._dismiss_notice()
            return True
        if self.help_open:
            self._help_lines(painter)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):self.help_open = False
                elif event.key in (pygame.K_PAGEDOWN, pygame.K_DOWN):self.help_scroll = min(self.help_max_scroll, self.help_scroll+64)
                elif event.key in (pygame.K_PAGEUP, pygame.K_UP):self.help_scroll = max(0, self.help_scroll-64)
            elif event.type == pygame.MOUSEWHEEL:self.help_scroll = max(0, min(self.help_max_scroll, self.help_scroll-event.y*24))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and point is not None and self.help_close_rect.collidepoint(point):self.help_open = False
            return True
        if self.pending is not None:
            self._confirmation_layout(painter)
            if event.type == pygame.MOUSEMOTION:
                self.hovered = None
                return True
            if event.type == pygame.MOUSEWHEEL:
                self.confirm_scroll = max(0, min(self.confirm_max_scroll, self.confirm_scroll-event.y*24))
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and point is not None:
                if self._held:return True
                self._held = True
                if self.confirm_rect.collidepoint(point):self._commit();return True
                if self.cancel_rect.collidepoint(point):self.pending = None;self.message = '';return True
                if self.confirm_panel.collidepoint(point):return True
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_HOME, pygame.K_END):
                if event.key == pygame.K_PAGEUP:self.confirm_scroll = max(0, self.confirm_scroll-self.confirm_view.height)
                elif event.key == pygame.K_PAGEDOWN:self.confirm_scroll = min(self.confirm_max_scroll, self.confirm_scroll+self.confirm_view.height)
                elif event.key == pygame.K_HOME:self.confirm_scroll = 0
                else:self.confirm_scroll = self.confirm_max_scroll
                return True
            if event.type == pygame.KEYDOWN and (event.key in self.DIRECTIONS or event.key in
                    (pygame.K_TAB, pygame.K_f, pygame.K_0, pygame.K_KP0, pygame.K_F1, pygame.K_QUESTION,
                     pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS,
                     pygame.K_MINUS, pygame.K_KP_MINUS)):
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and not getattr(event, 'repeat', False):
                if self.pending is not None:self.pending = None;self.message = ''
                else:self.close()
            elif event.key in self.DIRECTIONS:
                if self.dragging:return True
                self._zoom_anchor = None
                self._keys.add(event.key)
                self.hovered = None
            elif event.key == pygame.K_TAB:
                self._stop_navigation(settle=False)
                ids = tuple(self.board.nodes)
                backwards = bool(getattr(event, 'mod', 0)&pygame.KMOD_SHIFT)
                self._select(ids[(ids.index(self.selected)+(-1 if backwards else 1)) % len(ids)], center=True)
            elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):self._zoom(1.2)
            elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):self._zoom(1/1.2)
            elif event.key == pygame.K_f:self.fit_board()
            elif event.key in (pygame.K_0, pygame.K_KP0):self.reset_zoom()
            elif event.key == pygame.K_m and not getattr(event, 'repeat', False):self._action('move')
            elif event.key == pygame.K_a and not getattr(event, 'repeat', False):self._action('activate')
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and not getattr(event, 'repeat', False):self._commit()
            elif event.key in (pygame.K_F1, pygame.K_QUESTION):
                self._stop_navigation()
                self.help_open = True
        elif event.type == pygame.MOUSEWHEEL:
            pointer = self.pointer
            if pointer is None:pointer = self.game.to_canvas(pygame.mouse.get_pos())
            if pointer is not None and self.map_rect.collidepoint(pointer):
                self._zoom(1.2**max(-10, min(10, event.y)), anchor=pointer)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._held:return True
            self._held = True
            if point is None:return True
            if self.close_rect.collidepoint(point):self.close()
            elif self.help_rect.collidepoint(point):
                self._stop_navigation()
                self.help_open = True
            elif self.zoom_out_rect.collidepoint(point):self._zoom(1/1.2)
            elif self.zoom_in_rect.collidepoint(point):self._zoom(1.2)
            elif self.fit_rect.collidepoint(point):self.fit_board()
            elif self.reset_zoom_rect.collidepoint(point):self.reset_zoom()
            elif self.map_rect.collidepoint(point):
                self._cancel_zoom()
                self._keys.clear()
                self.dragging = True
                self._drag_start = pygame.Vector2(point)
                self._drag_pan = self.pan.copy()
                self._camera_target = self.pan.copy()
                self._camera_elapsed = self.CAMERA_DURATION
                self._click_world = self.pan+(pygame.Vector2(point)-pygame.Vector2(self.map_rect.center))/self.zoom
                self._drag_moved = False
                self.cursor_position.update(self.pan)
        elif event.type == pygame.MOUSEMOTION:
            self.hovered = self._node_at(point)
            if self.dragging and point is not None:
                self._drag_to(point)
                self.hovered = None
            elif self.dragging and point is None:self._stop_navigation()
        return True

    def _circle(self, painter, color, center, radius, width=0):
        pygame.draw.circle(painter.canvas, color, painter.point(center), max(1, round(radius*painter.scale)),
                           max(1, round(width*painter.scale)) if width else 0)

    def _node_radius(self, identifier, node):
        radius = max(1.5, 10*self.zoom)
        formation_id = getattr(self.board, 'node_formations', {}).get(identifier)
        formation = getattr(self.board, 'formations', {}).get(formation_id)
        if formation and formation['center_node'] == identifier:
            baseline = {'hp': 20, 'mp': 2}.get(node.get('stat'), 1)
            if node['kind'] == 'ability' or (node['kind'] == 'stat' and node['amount'] > baseline):
                radius *= 1.25
        return radius

    def _draw_map(self, painter):
        painter.panel(self.map_rect)
        painter.clip(self.map_rect.inflate(-3, -3))
        state = self.lattice.state(self.character_id)
        rank = self.lattice.rank(self.character_id)
        route = self.lattice.route(self.selected, self.character_id) or []
        pairs = {frozenset((a, b)) for a, b in zip(route, route[1:])}
        for edge in self.board.edges:
            points = self.edge_points(edge)
            required = edge.get('min_rank', 1)
            color = GOLD if frozenset((edge['from'], edge['to'])) in pairs else BRASS
            if rank < required:
                color = DISABLED
                self._draw_path(painter, color, points, dashed=True)
                middle = self._edge_midpoint(edge)
                if self.zoom >= .35 and self.map_rect.inflate(-30, -30).collidepoint(middle):
                    painter.text('Rank '+str(required), middle+(0, -13), role='small', color=MUTED, anchor='midbottom')
            else:self._draw_path(painter, color, points, 2 if color == GOLD else 1)
        for identifier, node in self.board.nodes.items():
            center = self.node_position(identifier)
            radius = self._node_radius(identifier, node)
            if not self.map_rect.inflate(radius*2, radius*2).collidepoint(center):continue
            crystal = next(iter(node['cost']), None)
            color = self.board.crystals[crystal]['color'] if crystal else BRASS
            active = identifier in state['activated']
            selected = identifier == self.selected and not self.navigating
            fill = pygame.Color(color if active else FOREST_DARK)
            if selected:
                strength = self.pulse_strength
                glow = pygame.Color(FOREST_DARK).lerp(pygame.Color(GOLD), .35+.5*strength)
                halo = max(1.25, 5*self.zoom)+strength*max(.5, 2*self.zoom)
                self._circle(painter, glow, center, radius+halo, max(.7, 2*self.zoom))
                fill = fill.lerp(pygame.Color(GOLD), .12+.18*strength)
            self._circle(painter, fill, center, radius)
            self._circle(painter, IVORY if identifier in state['visited'] else color, center, radius, 1)
            if self.zoom >= .65 and node['kind'] == 'stat':
                icon = pygame.Rect(0, 0, max(9, radius*1.3), max(9, radius*1.3));icon.center = center
                draw_attribute_icon(painter, node['stat'], icon, FOREST_DARK if active else color)
            elif self.zoom >= .4 and node['kind'] == 'ability':
                painter.lantern(center, color=FOREST_DARK if active else color, size=radius*.8)
            if identifier == state['position']:
                gap = max(1.0, 4*self.zoom)
                self._circle(painter, GOLD, center, radius+gap, max(.7, 2*self.zoom))
                painter.line(GOLD, center+(0, -radius-gap-max(1, 5*self.zoom)),
                             center+(0, -radius-gap-max(.5, self.zoom)), max(.7, 2*self.zoom))
            if not selected and identifier == self.hovered:
                self._circle(painter, IVORY, center, radius+max(1.0, 3*self.zoom), 1)
        if self.navigating:
            center = pygame.Vector2(self.map_rect.center)+(self.cursor_position-self.pan)*self.zoom
            radius = max(1.5, 10*self.zoom)
            self._circle(painter, FOREST_DARK, center, radius+max(1, 2*self.zoom))
            self._circle(painter, GOLD, center, radius)
        painter.clip()
        painter.button(self.zoom_out_rect, '−', disabled=self.target_zoom <= self.MIN_ZOOM)
        painter.button(self.zoom_in_rect, '+', disabled=self.target_zoom >= self.MAX_ZOOM)
        painter.text(str(round(self.zoom*100))+'%', self.zoom_readout_rect.center,
                     role='small', color=GOLD, anchor='center')
        painter.button(self.fit_rect, 'Fit')
        painter.button(self.reset_zoom_rect, '100%')

    def draw(self, canvas):
        if not self.is_open:return
        painter = self._painter(canvas)
        heading_height, small_height = self._layout(painter)
        painter.veil(215)
        painter.panel((8, 8, 464, 304))
        painter.text('Aether Lattice', (20, 16), role='heading', color=GOLD, bold=True)
        rank = self.lattice.rank(self.character_id)
        progress, needed = self.lattice.rp_progress(self.character_id)
        y = 16+heading_height+5
        painter.text(self.game.attributes.name+' · Attunement '+str(rank), (20, y), role='small')
        painter.text('RP '+str(progress)+' / '+str(needed)+' · '+self._steps_label(self.lattice.steps(self.character_id)),
                     (20, y+small_height), role='small', color=GOLD)
        painter.button(self.help_rect, '?')
        painter.button(self.close_rect, '×')
        self._draw_map(painter)
        move_pending = self.pending == ('move', self.selected)
        if self.pending is not None or self.notice_open:
            painter.veil(80)
            painter.panel(self.confirm_panel)
            painter.text(self.notice_title if self.notice_open else
                         'Confirm travel' if move_pending else 'Confirm activation',
                         (42, 67), color=GOLD, bold=True)
            confirm_lines, height = self._confirmation_layout(painter)
            painter.clip(self.confirm_view)
            for index, line in enumerate(confirm_lines):
                painter.text(line, (self.confirm_view.left, self.confirm_view.top+index*height-self.confirm_scroll), role='small')
            painter.clip()
            if self.confirm_max_scroll:
                painter.text('PgUp / PgDn: read', (42, 226), role='small', color=MUTED, anchor='midleft')
            elif not self.notice_open:painter.text('Enter confirms', (42, 226), role='small', color=MUTED, anchor='midleft')
            if not self.notice_open:painter.button(self.confirm_rect, 'Confirm')
            painter.button(self.cancel_rect, 'Close' if self.notice_open else 'Cancel')
        if self.help_open:
            painter.veil(100)
            painter.panel(self.help_panel)
            painter.text('Lattice controls', (46, 50), color=GOLD, bold=True)
            painter.button(self.help_close_rect, '×')
            help_lines, height = self._help_lines(painter)
            painter.clip(self.help_view)
            for index, line in enumerate(help_lines):
                painter.text(line, (self.help_view.left, self.help_view.top+index*height-self.help_scroll), role='small')
            painter.clip()
