# Aldric's visit and the Sanctuary emergency

MQ03, **The Regent's Road**, begins with Aldric's welcome and meal at Serene's
home. Its revised post-meal sequence exposes his secret deployment at Elden
Vale Sanctuary, brings Mira back into the party and takes the cast to the
regional reserve. The [canonical script](narrative/game_01/CH01_MQ03.md) mirrors
the playable dialogue in `assets/story/regent/scene.json`.

## Boundary after MQ02

MQ02 completes after Caelan's homecoming and clean-cup placement. Aldric's
separate [arrival cinematic](REGENT_ARRIVAL.md) returns control to the same
home dining room. Serene's short request separately accepts MQ03. The gift,
homecoming and table-setting conversation are not repeated.

## Playing through

1. Speak with Serene in the dining room, then meet Aldric by the lower bridge.
2. Greet Aldric, Lucan, the page and driver. Lucan is Aldric's personal guard;
   his observation about Mira's sword establishes his practical attention.
3. Guide the visitors directly through the courtyard and hall into the dining
   room. The relief wagon remains at the village approach.
4. Share the meal once everyone is gathered. The family and visitors retain
   their existing conversation, eating and guard-attention beats.
5. Hear the mining proposal. Serene explains the Sanctuary's duty to guide the
   region's dead back to the planet and remember them, and the disruption
   mining would cause. She reports growling from the cave since the bridge
   incident. No agreement is reached.
6. A wounded survivor runs through the hall and enters the dining room. His
   report of an attack reveals the advance party. Aldric confirms he dispatched
   it before coming to Eldenmere, to establish Crown control and prepare the
   mining work. Lucan was not informed and is visibly taken aback.
7. Serene treats the survivor, helped by Tomas and the driver. Caelan volunteers
   to help the people still at the reserve and proposes bringing Mira. Aldric,
   Lucan and the page accompany him to her workshop.
8. Speak with Mira. She chooses to bring her existing kit and Rivet, rejoins
   for the outing, and travels with the group through the existing town exit
   and overworld route.
9. Reach the real Sanctuary reserve. The cast gathers at safe arrival positions
   and MQ03 remains active at `sanctuary_arrival_pending`. The arrival cutscene
   and subsequent resolution are future work. Player control is not left
   permanently locked at this checkpoint.

The four ordered objective IDs remain `meet_visitors`, `accompany_visit`,
`welcome_party` and `speak_serene` for compatibility. The final objective now
covers the emergency response; phase-specific tracker text provides the next
step. Its legacy identifier does not force a premature private conversation or
completion. The existing Venn cart detour stays removed.

## Dialogue and presentation

The survivor's entrance fades the music to silence over 700 ms. His first two
utterances (including Aldric's intervening question) play in silence. Kindled
Courage begins on Lucan's following question and loops through departure,
Mira's rejoining and Sanctuary arrival. The pending arrival retains this score;
the future arrival scene must release emergency music ownership when it ends.
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
Mira is created. Caelan and Mira are the required combat members for this
outing. Aldric, Lucan and the page travel as story companions; traveling with
Lucan does not recruit him into combat yet.

The overworld keeps its established leader-scale presentation while the quest
carries the travelers' scene ownership. The group reforms at the reserve's safe
entrance. Saved phases and the party event restore that ownership after load;
New Game releases it. The future arrival scene will determine the next party
and quest handoff.

## Story boundaries

The user-approved Sanctuary guidance role and Aldric's deliberate concealment
supersede the older good-faith inspection compromise. His relief needs remain
real, and his secret assertion of Crown control is still a breach of trust.
Serene's treatment of the survivor gives aid without settling that conflict.

The growling began after the bridge incident, the crew entered the reserve and
something from the cave attacked them. This sequence does not identify the
creature or prove that mining caused the attack. The amount of work completed
at the site remains for the arrival cutscene. The cave barrier, miniboss,
Sanctuary arrival cutscene and MQ03 resolution are not fabricated by this
implementation. Tomas's lantern invitation must be positioned after that later
sequence rather than firing from the removed ending.

See the [faith guide](world/ELDEN_VALE_FAITH.md),
[covenant](world/SANCTUARY_COVENANT.md) and
[regional setting](world/regions/ELDEN_VALE.md) for the revised societal role.
