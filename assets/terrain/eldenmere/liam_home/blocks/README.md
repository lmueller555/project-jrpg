# Wooden block box and five building blocks — approved

The open wooden box uses the approved cottage furniture palette. Six 32×24
states show zero through five blocks inside; the box exterior stays fixed.
`front_overlay.png` is the front rim/body for correct hand and held-block depth.
All variants retain transparent source layers for exact reconstruction.

The box is registered at [44,180], in the wall gap between the two beds.
Its relative floor rectangle is [2,15,28,8]. Liam's box access is [80,200],
putting the left-hand contact at [70,191] inside the opening. `blocks.json`
records these registrations and full repository-relative asset paths.

Four cube sprites are 5×5 pixels, centered using anchor [2,2]. The fifth is a
16×4 wooden beam with anchor [8,2]. Each has a stable identity (`block_1` through
`block_5`) for box, held, built and scattered runtime states. The art never
changes the total number of blocks; the controller tracks their ownership.

Build with `python tools/build_liam_blocks.py`. Existing furniture, character
idles and walking/running assets remain unchanged.
