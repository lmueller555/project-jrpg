# Dialogue UI and Portrait Standards

This is a Project JRPG visual/technical standard.

## Readable UI text
Dialogue and location text must be rendered with genuine rasterized fonts at the final window resolution, *after* pixel-art world scaling. Maintain font size of at least 15 display pixels, adequate line spacing, safe-area padding, and measured word wrapping. Use a compatible licensed font asset when available; system-font fallbacks must not be mistaken for a bundled font.

## Shared panel
All notices use the same navy-and-gold framed panel. Character speech may reserve a square left-side portrait and speaker-name row. Narration, landmark inspections and transitions do not reserve portrait space. Long messages paginate and advance with E/Space.

## Portrait identity
A portrait must faithfully resemble approved reference artwork for the exact speaker, including face, hair, clothing, colors, accessories and expression continuity. Dedicated square RGBA sprites are required. Generic lookalikes, unrelated faces, enlarged tiny walking sprites and unapproved AI-generated portraits are **not permitted**. If an approved portrait is absent, omit the image until the art gate is satisfied, and keep the speaker name.

Each approved portrait must document its character ID, expression, provenance, source reference, owner approval, and native UI screenshot. Do not silently replace missing character art.


## Caelen V1 expression delivery (2026-10-15)

The user-approved portrait board defines five expressive Caelen variants. Export names and IDs are fixed:

| ID | Asset path | Expression |
|---|---|---|
| caelen.neutral | portraits/caelen/neutral.png | Calm, attentive |
| caelen.happy | portraits/caelen/happy.png | Warm, eyes nearly closed |
| caelen.concerned | portraits/caelen/concerned.png | Uneasy, furrowed brows |
| caelen.determined | portraits/caelen/determined.png | Focused, resolved |
| caelen.surprised | portraits/caelen/surprised.png | Wide eyes, open mouth |

All five should be square 96×96 RGBA, share framing and identity, and be inspected at UI presentation size. Caelen dialogue defaults to neutral unless a scene selects a different approved expression ID; others never get a Caelen portrait. The source is the approved UI board, not independent image regeneration. If files are unavailable, the UI omits the picture but retains readable text. Do not call an asset-integrated release complete until the actual PNG files exist in the repository and are validated.

The approved delivery is `caelen_approved_portrait_pack.zip` (SHA-256 `dcfc421ffedd05ce264163b82d266660fe2d3c8542fbc3a74ad1c7b7896a1688`), installed as the five paths above. The dialogue regression suite decodes and loads every variant at its native size.
