"""Exact-input, tightly bounded visual-review diagnostics for motion metrics."""
from __future__ import annotations

from hashlib import sha256
import json
import math


def frame_identity(drawing, rendered_image) -> dict:
    """Bind both original source/registration and the actual rendered RGBA view."""
    rgba = rendered_image.convert('RGBA')
    return {'frame': drawing.index, 'source': drawing.source, 'source_sha256': drawing.digest,
            'cell': list(drawing.cell), 'scale': drawing.scale, 'origin': list(drawing.origin),
            'neck': list(drawing.neck), 'belt': list(drawing.belt),
            'rendered_size': list(rgba.size),
            'rendered_rgba_sha256': sha256(rgba.tobytes()).hexdigest()}


def metric_context(metric: str, region: str, identities: list[dict], configuration: dict) -> dict:
    # Copy, rather than retain mutable contract dictionaries: changing a region
    # after review must not mutate the recorded approval along with it.
    return json.loads(json.dumps({'metric': metric, 'region': region,
                                  'frames': identities, 'configuration': configuration},
                                 allow_nan=False))


def find_reviewed_exception(reviews: list[dict], *, context: dict, value: float,
                            default_limit: float) -> dict | None:
    """Only an accepted exact input and a small reviewed metric band can match.

    A default cap is never raised. Changed source, rendering, registration,
    region or metric definition loses this diagnostic classification. The
    observed value must also remain inside the recorded small sampling band.
    """
    for review in reviews:
        if (review.get('review_state') != 'accepted' or review.get('context') != context
                or review.get('default_limit') != default_limit):
            continue
        measured = review.get('reviewed_value')
        tolerance = review.get('sampling_tolerance')
        maximum = review.get('maximum_reviewed_value')
        if (not all(type(item) in (int, float) and math.isfinite(item)
                    for item in (measured, tolerance, maximum, value))
                or not 0 <= tolerance <= 1
                or not measured <= maximum <= measured + tolerance):
            continue
        if abs(value - measured) <= tolerance and value <= maximum:
            return review
    return None
