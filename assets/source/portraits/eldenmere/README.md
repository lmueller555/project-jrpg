# Dialogue portrait master artwork

Status: awaiting user review. Generated from approved character sprites and
full-body concepts using the image generation tool. Preserve these masters;
the game-sized exports are reproducible through `tools/export_dialogue_portraits.py`.

- `main_cast_atlas.png`: 2×2 equal square cells, ordered Caelan, Mira, Serene,
  Tomas in reading order.
- `villagers_atlas.png`: 3×2 equal square cells; the first row is male palettes
  01–03, and the second row is female palettes 01–03.
- `lantern_atlas.png`: 3×3 equal square cells, ordered Liam, Liam's mother,
  Tessa / Finn, Rowan, Ada / Pippa, empty, empty. Generated from their approved
  world sprites for the MQ04 preparation session. Child faces retain their
  opening ages; the teacher retains her teal dress and cream apron. The last
  two cells are unused dark-green background.

Portraits are new detailed head-and-shoulder art. The approved world sprite
files are unchanged. Neutral expressions are the initial set; additional
expression sheets are not included in this milestone.


`aldric_master.png` is the generated head-and-shoulders master for Regent Aldric,
matched to his MQ03 slate/navy traveling coat, pale neckcloth and brown-gray
hair. The 72×72 export is included in `tools/export_dialogue_portraits.py`.

`liam_father_master.png` is the generated head-and-shoulders master for Liam's
father, introduced in the MQ04 home break. It follows his approved mid-thirties
sprite identity: dark brown hair, short beard, hazel eyes, clay-red tunic and
ivory sleeves. His personal name remains unassigned. The original square master
is retained, and the 72×72 RGB export is reproducible with the portrait exporter.
