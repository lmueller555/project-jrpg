# Mira — new facing appearance inputs

Status: approved by the user as part of the directional walking animations.

`turnaround_concept.png` is generated appearance reference art for back, left and right views, using Mira's front design and Caelan's directional scale guide. It is not a walking animation source.

`appearance_back.png`, `appearance_left.png` and `appearance_right.png` are palette-mapped 24×36 inputs. After native export, the five-pixel flower and single visible profile eyes are cleaned up for readability. The flower stays on anatomical left: viewer-left in back view, visible in left profile, hidden in right profile. The short ponytail extends behind the head in both profiles and rests at the nape in back view. `appearance.json` records head regions and feature positions.

The animation builder extracts head/neck and appearance parts from these images, then uses the retained Caelan pose masks and shared leg art for all walking frames. The complete appearance inputs are retained for editing, not registered as approved idle sprites. The approved front idle and walk are unchanged.
