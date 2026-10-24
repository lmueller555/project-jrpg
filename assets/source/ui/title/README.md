# Title illustration master

Status: awaiting user review. `eldenmere_dawn.png` is original image-generation
output, copied intact from the generation workspace. References were the approved
sanctuary and watermill sprites and the approved main-cast portrait atlas.

Direction: a warm pixel-art dawn panorama of Eldenmere, with Caelan and Tomas
on the left foreground bridge, lantern, downhill brook, watermill, cottages,
sanctuary, wooded mountains and open sky. The quiet lower-center bank was
reserved for the user's bottom-center menu. No text or UI is baked into the art.

`tools/export_title_art.py` crops to 16:9 and exports 640×360 with nearest-neighbor
sampling. `title_screen.py` renders typography, UI, wheel movement and atmospheric
animation separately. Existing town and character sprite packs are unchanged.
