"""Personal props are visible only during their authored stationary use."""
def personal_prop_visible(actor, interacting=False):
    return bool(interacting and not getattr(actor, 'moving', False))
