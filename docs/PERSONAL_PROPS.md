# Personal weapons, tools and props

This is the visibility companion to the mandatory
[character–object interaction standard](OBJECT_INTERACTION_STANDARD.md).
That standard governs approach, facing, realistic anatomy, deliberate snaps,
object ownership, camera depth, and restoration.

Personal objects appear for their authored use and disappear when that use
finishes. Ordinary player travel must not render a separate sword, toolkit,
or tool floating beside the character merely because it is owned or equipped.
Current stationary personal overlays use
`personal_prop_visible(actor, interacting)`: the action must be active and the
actor stationary. Integrated battle and cutscene poses may show equipment for
their authored action. Authored continuous manipulation and transport use their
registered action/carry artwork under the global standard.

Deposited world objects remain at their destination, with ownership and depth
following the global standard. Equipment and inventory ownership are independent
of visibility. Explicit transport objectives retain their registered carrying
animations until the delivery is complete.

Sanctuary care demonstrates this lifecycle: Mira uses a stationary kit, stows
it before leaving, and leaves linen beside the patient. The mill/MQ03 blade
appearance is restricted to its authored scabbard interaction; combat and the
weapon-gift presentation retain their own integrated artwork.
