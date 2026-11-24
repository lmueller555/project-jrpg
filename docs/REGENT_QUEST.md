# Iselin's visit and the Sanctuary emergency

This guide owns MQ03's runtime checkpoints, presentation, actor ownership,
and save compatibility. The [MQ03 narrative/script](narrative/game_01/CH01_MQ03.md)
owns its visit, emergency, rescue, and return-home sequence. The runtime source
is `assets/story/regent/scene.json`.

## Boundary after MQ02

MQ02 completes after Caelan's homecoming and clean-cup placement. Iselin's
separate [arrival cinematic](narrative/scenes/REGENT_ARRIVAL.md) returns control to the same
home dining room. Serene's short request separately accepts MQ03. The gift,
homecoming and table-setting conversation are not repeated.

## Objective boundary

Follow the [MQ03 critical path and script](narrative/game_01/CH01_MQ03.md#critical-path-and-player-responsibility).
`sanctuary_arrival_pending` is an intermediate arrival checkpoint. The arrival
handoff gives the cave party control without completing the quest; the later
rescue and acknowledged return-home resolution complete MQ03 and unlock MQ04.

The four ordered objective IDs remain `meet_visitors`, `accompany_visit`,
`welcome_party` and `speak_serene` for compatibility. The final objective now
covers the emergency response; phase-specific tracker text provides the next
step. Its legacy identifier does not force a premature private conversation or
completion. The existing Venn cart detour stays removed.

## Dialogue and presentation

The report and departure use 21 dialogue boxes, retaining Serene’s accusation
and Lucan’s surprise before urgent rescue arrangements. Lucan does not speak
until the secret deployment is exposed.

The survivor's entrance fades the music to silence over 700 ms. His first two
utterances (including Iselin's intervening question) play in silence. **Something is Wrong**
begins on Serene’s “What men?” and loops through departure,
Mira's rejoining and Sanctuary arrival. The arrival scene retains this score
through its final handoff. The first successful cave entry permanently releases
the emergency override; **Elden Vale Sanctuary Cave** plays underground, and
normal area music resumes outside even while MQ03 remains active. Continue
preserves the release, and older saves with durable cave evidence inherit it.
Continue restarts an unfinished report with its silent opening and restores the
score directly at later checkpoints. Cancelling and reopening the report within
the same session does not restart an already-started score.

The current main arrays are `preparations`, `arrival`, `welcome`, `discussion`,
`attack_report`, `departure`, `mira_departure` and `sanctuary_waiting`. The
survivor enters along a real physical route; his first concern is the people
left behind. Serene's questions expose the orders and their timing. Lucan's
surprise precedes his practical rescue questions. New cues support the alarm,
disbelief and survivor care, while the existing greeting and meal cues remain.

The speaker labeled Page retains the technical `regent_clerk` actor/speaker ID
so existing saves and actor registrations stay compatible. The page's knowledge
of the secret deployment is not established. The original `aftermath` and
completed-visit optional replies remain compatibility content for old completed
journeys; new journeys do not use the lantern ending here.

Dialogue is player-paced and cancelable. Fully acknowledged conversations own
progress; a line, pose, footstep, camera movement or partially read report does
not count as a completed scene. Leaving and returning cannot accept unread
prose or replay a committed report as a second emergency.

## Durable progress and old saves

The version-three `regent_quest` stage follows:

`idle → assigned → escorting → welcome → hosted → interruption → attack_report → departure → rejoin_mira → sanctuary_travel → sanctuary_arrival_pending`.

The separate `done` stage preserves completed legacy visits. The greeting
records `meet_visitors`, the actual dining-room arrival records
`accompany_visit`, and the completed meal records `welcome_party`. The fourth
objective remains active while the extended response proceeds. New journeys do
not complete MQ03 or unlock MQ04 at this arrival handoff.

Version-one removed escort stops migrate to the direct escort. An older active
`discussion` checkpoint resumes before the revised discussion, without
inventing a witnessed attack. Completed MQ03/MQ04 journeys retain their progress,
existing lantern access and prior roster. They are not rewound into this new
emergency or granted new Sanctuary visit facts.

## Actor and party ownership

Serene, Tomas and the driver remain at home with the survivor. The existing
Mira actor and resources are reused; MQ03 owns her outing so MQ02 cannot return
her to the bench during it. No equipment, HP or MP is reset and no duplicate
Mira is created. Caelan and Mira are the required combat members on the road
to the reserve. Iselin, Lucan and the page travel as story companions until
arrival. Once its rescue plan is acknowledged, Lucan becomes the temporary
third combat member;
Iselin and the page remain with the workers. His permanent recruitment remains
a later story decision.

The overworld keeps its established leader-scale presentation while the quest
carries the travelers' scene ownership. The group reforms at the reserve's safe
entrance. Saved phases and the party event restore that ownership after load;
New Game releases it. The [arrival scene](SANCTUARY_ARRIVAL.md) owns its durable beat checkpoints
and the three-member rescue handoff.

## Narrative authority

See [MQ03's narrative contract and knowledge boundaries](narrative/game_01/CH01_MQ03.md)
for the secret deployment, witnesses, reveal limits, rescue, and resolution.
The local [faith](narrative/world/ELDEN_VALE_FAITH.md),
[covenant](narrative/world/SANCTUARY_COVENANT.md), and
[regional setting](narrative/world/regions/ELDEN_VALE.md) own their distinct worldbuilding.
This runtime guide does not establish a competing account of those events.
