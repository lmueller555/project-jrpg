# Dialogue UI and Portrait Standards

This is a Project JRPG visual/technical standard.

## Readable UI text
Dialogue and location text must be rendered with genuine rasterized fonts at the final window resolution, *after* pixel-art world scaling. Maintain font size of at least 15 display pixels, adequate line spacing, safe-area padding, and measured word wrapping. Use a compatible licensed font asset when available; system-font fallbacks must not be mistaken for a bundled font.

## Shared panel
All notices use the same navy-and-gold framed panel. Character speech may reserve a square left-side portrait and speaker-name row. Narration, landmark inspections and transitions do not reserve portrait space. Long messages paginate and advance with E/Space.

## Portrait identity
A portrait must faithfully resemble approved reference artwork for the exact speaker, including face, hair, clothing, colors, accessories and expression continuity. Dedicated square RGBA sprites are required. Generic lookalikes, unrelated faces, enlarged tiny walking sprites and unapproved AI-generated portraits are **not permitted**. If an approved portrait is absent, omit the image until the art gate is satisfied, and keep the speaker name.

Each approved portrait must document its character ID, expression, provenance, source reference, owner approval, and native UI screenshot. Do not silently replace missing character art.
