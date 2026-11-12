# Personal weapons, tools and props

Personal objects appear for their authored use and disappear when that use
finishes. Ordinary player travel must not render a separate sword, toolkit,
or tool floating beside the character merely because it is owned or equipped.
Use `personal_prop_visible(actor, interacting)` for separate personal overlays:
the action must be active and the actor stationary. Integrated battle and
cutscene poses may show equipment for their authored action.

Deposited world objects have fixed world coordinates and correct depth order;
they do not follow the previous holder. Equipment and inventory ownership are
independent of visibility. Completed actions, Continue, scene transfer and
Gallery reset must all reconstruct or clear the corresponding visual state.
Explicit transport objectives retain their registered carrying animations
until the delivery is complete.

Sanctuary care demonstrates this lifecycle: Mira uses a stationary kit, stows
it before leaving, and leaves linen beside the patient. The mill/MQ03 blade
appearance is restricted to its authored scabbard interaction; combat and the
weapon-gift presentation retain their own integrated artwork.
