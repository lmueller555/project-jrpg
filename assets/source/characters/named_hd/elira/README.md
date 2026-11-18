# Elira native migration

Identity reference: four original assets/story/elira/idle_*.png views and the original detailed portrait. New four-view master drawn with built-in image generation. Technical export uses one uniform scale per master, hard alpha, fixed crown and centered body axis; no individual pose fitting.

`export_idles.py` reproduces native 48x72 idles; `author_walks.py` constructs eight complete drawings per facing from literal pose contours. Run from any directory. The explicit compatible innkeeper_06 gait contours preserve 68px adult height, 560ms cadence and ground registration. The named head, costume, palette and anatomical-facing construction are independent. The native source code is the editable complete-drawing source, not a runtime limb rig. Original idle fabric clusters are retained inside the newly drawn matching material masks only. No pose scaling, rigid limb rotation, tweening or flattened-idle warp is used.

Portrait is the exact original detailed 72x72 image, not a new face. Household object-action sprites in assets/story/elira belong to Caelan; they are deliberately unaffected. No missing named action bank is silently activated.

Body/world ratio: 48x72 artwork, 24x36 world; anchor [24,60] artwork/[12,30] logical; foot [24,69] artwork/[12,34.5] logical. This migration changes no placement, collision, travel speed, plot, quest, rewards, schedule or save field.
