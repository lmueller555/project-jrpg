# Venn native integration QA

**74/74 legacy cases passed**, each in an isolated Python process. **9/9 focused native/gate cases passed** (three integrated candidate checks; one father bank; one mother bank; two child bank/live-bedrest; one dormant activity asset contract; one activation gate).

Legacy module counts: {'test_venn_visit': 18, 'test_venn_magicks': 10, 'test_lantern_village': 17, 'test_lantern_quest': 24, 'test_villager_households': 5}.

Command shape: `PYTHONPATH=.:tests SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /tmp/roof-qa-venv/bin/python -m unittest <fully-qualified-case>` from the isolated `venn-qa` overlay. Exact case IDs, exit codes, durations and final retry selection are in `integration/final-results.json`; verbatim outputs are in `integration/test-logs/`. Focused initial3-case command/output is `tests.test_venn_named_hd_candidate` / `integration/native-integration-tests.txt`.

The original combined suite was OS-killed; a heavy two-method case was initially OS-killed, and the household-order helper needed tests/ on PYTHONPATH. After isolating cases, correcting only invocation paths and honoring the shared-memory pause, both original cases passed unchanged. Coordination-skipped imports are explicitly superseded by real passing executions, not counted as passes.

## Native visual and lifecycle observations
Actual Venn home rendering through `WorldCanvas` captured at native960x640 for open/blink states. Inspected full room and enlarged pillow crop: brown-haired child's head rests within the existing pillow, bedpost/blanket overlap remains coherent, eyelid closure does not shift head or silhouette. Parents render in their original stations, in preserved cream/brown and teal/apron named costumes, beside unchanged environment/player. Captures: `integration/bedside-{open,blink}-native.png` and `-detail.png`.

Runtime tests compare source native PNG bytes against loaded parent idles and density-aware walk blits, verify child source/native equality at0/4639/4640/4799/4800ms, conversation-facing stability, original story_position60,112,12,12 draw anchor, sort_y167 and zero-sized child blocker. Parent probes12x8 and stations remain unchanged. Walk banks are standby; no live travel is introduced or claimed as gameplay-tested travel.

Activity-first rollout verified using real VennResident with a lightweight world: activity manifest alone stays legacy/dormant; adding replacement design activates native rest frames. Both states preserve child zero blocker. The exact check is included in child replacement tests and activation-gate-checks.json.

## Package sequence
Use PACKAGE_INDEX.md: father replacement; mother replacement; child bedrest activity dormant; child base replacement+final gate/activation patch. No publication, commits or shared runtime modifications performed. Overlay only: `venn-qa`; source `gardener-runtime` untouched by this worker.
