"""Shared gearblade focus identities; selecting a gem never teaches a skill."""

GEM_ORDER = ('nature', 'water', 'fire', 'ice')
DEFAULT_GEM = 'water'
GEM_NAMES = {'nature': 'Nature', 'water': 'Water', 'fire': 'Fire', 'ice': 'Ice'}
GEM_COLORS = {'nature': (93, 190, 113), 'water': (91, 166, 235),
              'fire': (226, 92, 83), 'ice': (235, 242, 247)}

# Ice has a selector position, but no starting action or unlock. Its requirement
# is reserved here so a later authored Ice Edge can use the same eligibility.
REQUIRED_GEMS = {'nature_edge': 'nature', 'aqua_edge': 'water',
                 'flame_edge': 'fire', 'ice_edge': 'ice'}


def valid_gem(value):
    """Accept only canonical saved gem identities, without coercion."""
    return isinstance(value, str) and value in GEM_ORDER
