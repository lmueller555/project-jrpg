# Three villager households — approved

`households.json` assigns the six approved generic adult appearances:

| Home | Mother | Father |
| --- | --- | --- |
| home_a, western terracotta cottage | female_02, existing sanctuary gardener | male_01, olive shirt |
| home_b, purple-roof village cottage | female_01, blue dress | male_02, rust shirt |
| home_c, southwestern green-roof cottage | female_03, plum dress | male_03, slate shirt |

Each person has one stable ID, partner ID, family role and home scene. Names,
ages and children remain unassigned. Five adults are placed as stationary
residents inside their homes using existing approved front idles. They have
normal solid foot probes and leave all furnishing approaches and exits clear.
The gardener keeps her existing town instance and well/flower watering routine;
her home is assigned without a second copy inside. Returning home is a later
schedule addition. Halden, Elira, the Venns and Liam retain their existing homes.

Build with `python tools/build_villager_households.py`. The canonical interior
compiler reapplies this extension after the family home and school. Re-entering
a cached home preserves its residents. New dialogue and daily schedules are
not assigned at this stage. See the
[three room previews and parent reference](../../../../docs/reviews/villager_households/README.md).
