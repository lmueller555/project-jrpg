These are legacy data fixtures captured from commit
`aa4b7ace` (the unchanged runtime immediately after documentation PR #650).

Each settled fixture was built by an actual old `Game`, using the shipped
`quest_playtest` prerequisite helpers and actual quest/party owners, then passed
that old Game's complete journey validator before writing. They are supported
checkpoint fixtures, not a claim of an uninterrupted input-driven playthrough.
The pending-battle fixture additionally calls the old boss owner to create its
real resumable boss-entry ticket, then passes old validation before combat settles.

MQ01/MQ02 cover early retained progress; completed MQ02, assigned/travel MQ03,
completed-cave MQ03 and active MQ04 cover retirement boundaries. Later fixtures
include earned EXP, the gearblade, Aqua Edge, settled elemental focuses, Vespermaw
reward receipts and temporary guest history. Resources were deliberately left
partly depleted. No player save or personal information supplied these fixtures.

The source reference is the detached old tree `/tmp/jrpg-retirement-base` used
during this migration. New tests exercise copy-only normalization and actual
current Game validation/Continue; they do not import retired runtime modules.
