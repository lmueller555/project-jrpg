# Three villager households — approved

`households.json` assigns the six approved generic adult appearances:

| Home | Mother | Father |
| --- | --- | --- |
| home_a, western terracotta cottage | female_02, existing sanctuary gardener | male_01, olive shirt |
| home_b, purple-roof village cottage | female_01, blue dress | male_02, rust shirt |
| home_c, southwestern green-roof cottage | female_03, plum dress | male_03, slate shirt |

Each person has one stable ID, partner ID, family role and home scene. Parent names and ages remain unassigned; five named children now belong to
the households. Five adults are placed as stationary
residents inside their homes using existing approved front idles. They have
normal solid foot probes and leave all furnishing approaches and exits clear.
The gardener keeps her existing town instance and well/flower watering routine;
her home is assigned without a second copy inside. Returning home is a later
schedule addition. Halden, Elira, the Venns and Liam retain their existing homes.

Build with `python tools/build_villager_households.py`. The canonical interior
compiler reapplies this extension after the family home and school. Re-entering
a cached home preserves its residents. New dialogue and daily schedules are not assigned at this stage. See the
[three room previews and parent reference](../../../../docs/reviews/villager_households/README.md).

## Five children and compact twin beds — approved

| Home | Children | Beds |
| --- | --- | --- |
| home_a | Tessa, 10; Finn, 6 | Two compact sage-quilt beds |
| home_b | Rowan, 9; Ada, 7 | Two compact blue-quilt beds |
| home_c | Pippa, 8 | One compact plum-quilt bed |

The registry records each child's parents, age, sprite root, standing position,
owned bed and bed approach. All children are initially stationary residents;
their four-direction idles, walks and runs are ready for later schedules.
Each 32×48 compact bed has a 24×32 ground footprint. The original parents' bed
and other furniture remain in place. Private collision maps for home_a/b/c add
the beds without changing the shared standard cottage mask or other houses.

`tools/build_villager_households.py` reapplies the adults, then invokes
`tools/build_village_children.py` when the child registry is present. This also
runs through the canonical interior compiler. All furnishing approaches, child
beds and exits remain reachable using Caelan's full 24×12 ground probe.
See [all sprites, walks/runs and furnished homes](../../../../docs/reviews/village_children/README.md).
