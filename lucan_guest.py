"""The Sanctuary outing's fixed-level guest profile and EXP eligibility.

Temporary membership is the boundary: a future permanent Lucan is never
retuned or excluded here. The cave owner persists one-time profile adoption.
"""

GUEST_LEVEL = 5


def is_lucan_guest(party):
    return bool(party.members.get('lucan', {}).get('temporary'))


def guest_xp_excluded(party):
    return ('lucan',) if is_lucan_guest(party) else ()


def initialize_lucan_guest(game, *, new=False):
    """Adopt the level-five profile once, preserving old guest injuries on load.

    A pending legacy victory must settle against its original before/after
    stats first. The restore owner supplies the explicit deferral flag before
    rebuilding story ownership; ordinary pending combat remains deferred too.
    """
    cave = getattr(game, 'sanctuary_cave', None)
    progression = getattr(game, 'character_progression', None)
    if (cave is None or progression is None or not is_lucan_guest(game.party)
            or getattr(cave, 'lucan_guest_initialized', False)):
        return False
    combat = getattr(game, 'combat', None)
    if (getattr(game, '_lucan_guest_defer_profile', False)
            or getattr(combat, 'active', False)
            or getattr(combat, 'post_phase', None)
            or getattr(combat, '_pending', None)):
        return False
    if not progression.initialize_guest_level('lucan', GUEST_LEVEL, preserve_resources=not new):
        return False
    cave.lucan_guest_initialized = True
    return True
