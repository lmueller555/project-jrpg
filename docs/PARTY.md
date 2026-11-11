# Party system

The party has a recruited roster and a separate active formation of one to three
characters. Recruitment does not give every recruited character a combat slot.
The active formation supplies combatants and up to two exploration followers.
Caelan starts as the required leader; current encounters retain him in slot one.

Open **Pause → Party** to choose the formation. Select a slot, then a recruited
companion. Confirm saves the draft; Cancel or Escape discards it. Keyboard,
mouse, roster scrolling, and 150% text at the minimum 480 × 320 window are
supported. Unavailable companions remain inspectable, with a reason, and cannot
be selected. Required characters and event locks explain why a change is blocked.

Characters retain their own attributes, HP and MP in active slots and reserves.
Switching slots, leaving the formation, returning, and saving/loading do not
heal or revive them. A KO character can be selected; at least one active member
must be able to fight to enter combat. Resting at Caelan's bed recovers available
recruited characters, including reserves. Unavailable characters keep their
resources while away. Existing battle outcome recovery rules remain in effect.

This work does not change progression, distribute reserve XP, recruit future
characters through new quests, or give them skills or equipment. Mira retains
her existing mill combat ratings. Lucan, Rhea and Edran have registered metadata
and use the existing starter ratings until their authored recruitment is tuned.
They stay hidden from the roster until explicitly recruited.

The [traditional leveling foundation](LEVELING.md) supplies separate approved
growth profiles for all five characters. The approved allocation rule gives the
full encounter XP to each active combatant alive at battle end; KO'd characters
and reserves receive none. Recruitment levels and story-absence catch-up remain
pending. The pure allocation helper accepts the combat-party IDs explicitly, so
living reserves in the roster cannot receive an accidental share. Live combat
still awards receipt-backed items until saved level records and enemy levels are
integrated. Level-up stat gains leave current HP and MP unchanged.

## Story ownership

Mira's existing MQ02 meeting recruits her as a temporary guest. The mill outing
requires her in the active party. Once the outing ends, she stays in the recruited
roster as unavailable, with the reason **Working in Eldenmere.** The mill's
authored following and staging continue to own her during that quest; passive
party travel does not create a second Mira or overwrite her story position.
Later story events can return her through `set_party_member_available()`; mill
reconciliation will preserve that later availability across saves and reloads.

Use the game methods for story changes so a successful change is checkpointed:

```python
game.recruit_party_member('lucan')
game.set_party_member_available('lucan', False, 'Guarding the western pass.')
game.set_party_member_available('lucan', True)
```

Recruitment fills an empty active slot when the formation is unlocked. A recruit
joining a full formation prompts the player to manage it. Making an optional
active member unavailable removes that member and prompts for a replacement.
Returning availability does not displace a formation the player has chosen.
Repeated recruitment does not reset resources.

For a dungeon, boss or other named event, request a selection gate:

```python
game.request_party_selection(
    'western_vault',
    required=('mira',),
    unavailable=('rhea',),
    title='Choose vault party',
    reason='This party stays together inside the vault.',
    lock_after=True,
)
```

The named event is saved before its menu opens. Its required members, scoped
unavailability, previous formation, pending selection and eventual lock survive
reload. Confirm checkpoints the selection and lock together before continuing.
A failed save keeps the menu open and preserves the prior committed formation.
Cancel restores the previous valid formation. Only one party event may exist at
a time; finish it before requesting another, including the same event ID.

Story controllers should use the persisted event state to resume after a load:

```python
if story_phase == 'awaiting_vault_party' and game.party_event_ready('western_vault'):
    # Advance/checkpoint the owning story phase, then enter the vault.
    begin_vault()
```

`party_event_ready()` is true when that event is current and its selection is
confirmed. `game.party.current_event_id` identifies the event, and
`game.party.pending_selection` describes a gate that still needs confirmation.
An optional `on_confirm` callback is useful during the current session; Python
callbacks are not serialized. A durable story phase and the event ID must own
continuation after reload, and prevent starting the same scene repeatedly.

Release the constraints when the event ends:

```python
game.end_party_event('western_vault')
# Or restore the prior formation if it remains valid:
game.end_party_event('western_vault', restore_previous=True)
```

Event availability is an overlay. Ending the event releases its restrictions
without undoing independent story availability changes made during it. The
default keeps the player's latest valid formation. Menus cannot change the party
during combat or while a blocking conversation/scene owns play.

## Persistence and encounter boundaries

`PartyState` owns recruited membership, availability, the ordered active IDs,
per-character attribute/resource snapshots and the current event. Its version-1
record is stored in the journey's `party` field. Validation is atomic: malformed
membership, duplicate or unknown IDs, invalid resources, unavailable active
members, missing required members and formations larger than three are rejected
before live objects change. Caelan's attribute object remains the same object
used by the existing game systems.

Older saves without a party record start from Caelan and reconcile the existing
mill story state. Battles copy the selected formation and its current resources. Every active participant settles resources together; reserves are untouched. Pending victory/spoils checkpoints also retain the participants and their
resources so continuing a saved result does not refill companions or repeat the
reward.

Exploration followers use the player's traversed, collision-checked route.
Doors/teleports reset the trail; followers appear once there is enough clear
route behind the leader. Menus and dialogue pause their movement. Authored story
actors retain priority, and the regional overworld keeps its existing travel
representation.

## Review artifacts

See [the captured review](reviews/mira_rig_continuity/README.md) for native menu stills,
a short silent video, a menu GIF, input evidence and reproducible source hashes.
The review fixture explicitly recruits future characters to exercise reserves;
it adds no story events to the game.
