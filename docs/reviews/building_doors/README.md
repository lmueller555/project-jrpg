# Building-door and interior review

These captures come from the actual `main.py` runtime.

- `doors_and_interior.gif`: Caelan stands near the sanctuary as its doors open, steps away so they close, approaches again, walks inside, explores the hall, and returns outside. Movement advances the real controller at 60 Hz; the GIF samples about 15 fps at 2× pixel scale with exact native colors.
- `sanctuary_open.png`: open double doors with the exterior frame intact.
- `sanctuary_hall.png`: the approved hall with its two internal doors and a dynamically drawn Caelan.
- `elira_interior.png`: the compact cottage with its lantern shelf and stool.
- `mira_interior.png`, `mill_interior.png`: functional workrooms furnished from the existing approved kit.

All nine exterior round trips and both internal sanctuary connections are checked in `tests/test_doors.py`, alongside proximity timing, hold/reversal behavior, wall/furniture collision and return-spawn checks. Run `python main.py` to explore; approach a door and walk through without pressing an action key.
