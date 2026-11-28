#!/usr/bin/env python3
"""Verify Lucan's whole-figure source lineage and reproduce declared RGBA exports.

Default invocation writes source_provenance.json only after all checks pass.
--check verifies that the existing ledger describes the current inputs exactly.
No visual, animation, approval, or baked-scene acceptance is inferred here.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys

from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
PROFILE = ROOT / 'assets/story/fire_veinhold_opening/shot08/characters/lucan/actorperformance.json'
LEDGER = HERE / 'source_provenance.json'
UPSTREAM = ROOT / 'assets/source/cinematics/fire_veinhold/face_reveal/lucan/source_art_48.json'
OLD_RUNTIME = ROOT / 'assets/story/fire_veinhold_opening/shot07/characters/lucan'
SHA_PATTERN = re.compile(r'^[0-9a-fA-F]{64}$')


class ProvenanceError(ValueError):
    """A declared source contract does not describe the retained files."""


def require(condition, message):
    if not condition:
        raise ProvenanceError(message)


def relative(path):
    path = path.resolve()
    require(path.is_relative_to(ROOT), f'Input is not retained in the repository: {path}')
    return path.relative_to(ROOT).as_posix()


def declared_hash(value, location):
    require(isinstance(value, str) and SHA_PATTERN.fullmatch(value),
            f'Missing or invalid SHA-256 at {location}')
    return value.lower()


class Snapshot:
    """Hash each dependency and reject files changed during this invocation."""

    def __init__(self):
        self.files = {}

    def digest(self, path):
        path = path.resolve()
        if path in self.files:
            return self.files[path]['sha256']
        require(path.is_file(), f'Missing retained input: {path}')
        stat = path.stat()
        digest = sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        self.files[path] = {'sha256': digest.hexdigest(),
                            'signature': (stat.st_size, stat.st_mtime_ns)}
        return digest.hexdigest()

    def verify(self, path, expected, location):
        expected = declared_hash(expected, location)
        actual = self.digest(path)
        require(actual == expected, f'Changed bytes at {location}: {path}')
        return actual

    def read_json(self, path):
        self.digest(path)
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise ProvenanceError(f'Cannot read JSON {path}: {error}') from error

    def read_text(self, path):
        self.digest(path)
        return path.read_text()

    def assert_stable(self):
        for path, record in self.files.items():
            stat = path.stat()
            require((stat.st_size, stat.st_mtime_ns) == record['signature'],
                    f'Inputs changed during verification; rerun after export completes: {path}')

    def manifest(self):
        return {relative(path): record['sha256']
                for path, record in sorted(self.files.items())}


def retained_path(value, document):
    require(isinstance(value, str) and value.strip(), f'Missing retained path in {document}')
    path = Path(value)
    if not path.is_absolute():
        # Repository-relative paths are the existing convention. Basenames and
        # child-local paths resolve beside their own generation record instead.
        path = ROOT / path if (ROOT / path).is_file() else document.parent / path
    relative(path)
    return path.resolve()


def dictionaries(value, pointer=''):
    if isinstance(value, dict):
        yield pointer, value
        for key, child in value.items():
            escaped = str(key).replace('~', '~0').replace('/', '~1')
            yield from dictionaries(child, f'{pointer}/{escaped}')
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from dictionaries(child, f'{pointer}/{index}')


def normalize_references(record, document, pointer, snapshot):
    references = record.get('references', [])
    hashes = record.get('reference_sha256', record.get('references_sha256', {}))
    if isinstance(references, dict):
        references = [{'path': path, 'sha256': digest}
                      for path, digest in references.items()]
    require(isinstance(references, list), f'Invalid references at {document}{pointer}')
    result = []
    for index, item in enumerate(references):
        if isinstance(item, str):
            item = {'path': item, 'sha256': hashes.get(item)}
        require(isinstance(item, dict), f'Invalid reference at {document}{pointer}/{index}')
        path = retained_path(item.get('path'), document)
        digest = snapshot.verify(path, item.get('sha256'),
                                 f'{relative(document)}{pointer}/references/{index}')
        result.append({'path': relative(path), 'sha256': digest})
    return result


def generation_records(snapshot):
    """Discover completed generation records, including future child folders."""
    generations = []
    by_master = defaultdict(list)
    for document in sorted(HERE.rglob('*.json')):
        if document.resolve() == LEDGER:
            continue
        data = snapshot.read_json(document)
        for pointer, record in dictionaries(data):
            if not all(key in record for key in ('generation_id', 'prompt', 'output')):
                continue  # Tasks and measurements are not completed generation records.
            generation_id = record['generation_id']
            require(isinstance(generation_id, str) and generation_id.strip(),
                    f'Missing generation ID at {relative(document)}{pointer}')
            prompt = record['prompt']
            require(isinstance(prompt, str) and prompt.strip(),
                    f'Missing exact prompt at {relative(document)}{pointer}')
            master = retained_path(record['output'], document)
            expected = record.get('output_sha256', record.get('source_sha256'))
            digest = snapshot.verify(master, expected,
                                     f'{relative(document)}{pointer}/output')
            references = normalize_references(record, document, pointer, snapshot)
            # The retained master is portable. An original tool workspace copy
            # can strengthen the check when present, but is not a required path
            # on another checkout and does not affect the normalized ledger.
            original = record.get('raw_original', record.get('original_generation_path'))
            if original and Path(original).is_file():
                with Path(original).open('rb') as stream:
                    original_digest = sha256(stream.read()).hexdigest()
                require(original_digest == digest,
                        f'Retained master differs from original generation: {master}')
            entry = {'document': relative(document), 'pointer': pointer,
                     'generation_id': generation_id, 'master': relative(master),
                     'master_sha256': digest, 'prompt': prompt,
                     'references': references}
            generations.append(entry)
            by_master[master].append(entry)
    require(generations, 'No completed ImageGen generation records were found')
    return generations, by_master


def profile_rows(profile):
    require(profile.get('version') == 1 and profile.get('actor') == 'lucan',
            'Unexpected actor performance version or actor')
    require(profile.get('canvas') == [1024, 1536], 'Unexpected default source canvas')
    require(profile.get('anchor') == [512, 960], 'Unexpected default ground anchor')
    require(profile.get('art_pixels_per_metre') == 500, 'Unexpected artwork density')
    transitions = profile.get('transition_frames', [])
    cycles = profile.get('overhead_cycle', {}).get('frames', [])
    require(len(transitions) == 133, 'Expected exactly 133 transition sample records')
    require(len(cycles) == 48, 'Expected exactly 48 chronological overhead phases')
    rows = []
    for index, row in enumerate(transitions):
        require(row.get('index') == index, f'Transition index mismatch at sample {index}')
        require(row.get('gait_frame') == index % 48,
                f'Transition gait phase mismatch at sample {index}')
        require(isinstance(row.get('file'), str), f'Missing transition file at sample {index}')
        rows.append(('transition', index, row))
    for phase, row in enumerate(cycles):
        require(row.get('gait_frame') == phase, f'Overhead phase order mismatch at {phase}')
        require(isinstance(row.get('file'), str), f'Missing overhead file at phase {phase}')
        rows.append(('overhead', phase, row))
    return rows


def registration_records(snapshot):
    by_output = defaultdict(list)
    for name in ('early_registration.json', 'bank_registration.json', 'special_registration.json'):
        document = HERE / name
        records = snapshot.read_json(document)
        require(isinstance(records, list), f'Invalid registration list: {document}')
        for index, record in enumerate(records):
            kind = record.get('kind', 'transition')
            frame = record.get('index')
            if kind not in ('transition', 'overhead') or not isinstance(frame, int):
                continue
            output = PROFILE.parent / f'{kind}_{frame:03d}.png'
            by_output[output.resolve()].append((document, index, record))
    return by_output


def render_recipe(source, recipe, canvas, alpha_floor):
    require(isinstance(canvas, list) and len(canvas) == 2 and
            all(isinstance(value, int) and value > 0 for value in canvas),
            'Invalid export canvas')
    cell = recipe.get('cell')
    require(isinstance(cell, list) and len(cell) == 4 and
            all(isinstance(value, int) for value in cell), f'Invalid crop for {source}')
    scale = recipe.get('scale')
    require(isinstance(scale, (int, float)) and not isinstance(scale, bool) and
            math.isfinite(scale) and scale > 0, f'Invalid uniform scale for {source}')
    origin = recipe.get('origin')
    require(isinstance(origin, list) and len(origin) == 2 and
            all(isinstance(value, (int, float)) and math.isfinite(value) for value in origin),
            f'Invalid whole-image origin for {source}')
    require(isinstance(alpha_floor, int) and 0 <= alpha_floor <= 16,
            f'Alpha floor exceeds the allowed whole-image operation: {source}')
    with Image.open(source) as original:
        require(0 <= cell[0] < cell[2] <= original.width and
                0 <= cell[1] < cell[3] <= original.height,
                f'Crop is outside the complete master: {source}')
        image = original.convert('RGBA').crop(cell)
    if alpha_floor:
        image.putalpha(image.getchannel('A').point(lambda value: 0 if value <= alpha_floor else value))
    # Exporters use premultiplied-alpha uniform sampling. Equal-size resize does
    # not invoke a different anatomical operation; it preserves one whole cell.
    if scale != 1:
        image = image.convert('RGBa').resize(
            (round(image.width * scale), round(image.height * scale)),
            Image.Resampling.LANCZOS).convert('RGBA')
    result = Image.new('RGBA', tuple(canvas))
    result.alpha_composite(image, tuple(round(value) for value in origin))
    return result


def rgba_digest(image):
    return sha256(image.convert('RGBA').tobytes()).hexdigest()


def reused_entry(path, phase, row, upstream, snapshot):
    expected_runtime = (OLD_RUNTIME / f'frame_{phase:02d}.png').resolve()
    require(path == expected_runtime, f'Entry {phase} does not directly reuse the approved runtime PNG')
    require(row.get('canvas') == [768, 1024] and row.get('anchor') == [384, 960],
            f'Entry {phase} does not preserve the original canvas/anchor')
    recipe = upstream['frames'][phase]
    source = (UPSTREAM.parent / recipe['source']).resolve()
    expected = upstream.get('source_sha256', {}).get(recipe['source'])
    source_hash = snapshot.verify(source, expected, f'upstream phase {phase} raw source')
    generation_id = recipe.get('generation_id')
    require(isinstance(generation_id, str) and generation_id.strip(),
            f'Missing upstream generation ID for entry {phase}')
    prompt_path = source.with_name(source.stem + '_prompt.txt')
    prompt = snapshot.read_text(prompt_path)
    require(prompt.strip(), f'Empty upstream exact prompt: {prompt_path}')
    reconstruction = render_recipe(source, recipe, upstream['canvas'], upstream['alpha_floor'])
    with Image.open(path) as actual:
        require(actual.size == reconstruction.size and
                actual.convert('RGBA').tobytes() == reconstruction.tobytes(),
                f'Entry {phase} differs from the retained upstream whole-image recipe')
    return {'kind': 'direct_upstream_reuse', 'upstream_profile': relative(UPSTREAM),
            'upstream_frame': phase, 'raw_source': relative(source),
            'raw_source_sha256': source_hash, 'generation_id': generation_id,
            'exact_prompt_file': relative(prompt_path),
            'exact_prompt_sha256': snapshot.digest(prompt_path),
            'upstream_whole_image_recipe_rgba_match': True,
            'historical_reference_scope': 'Existing upstream metadata is retained; historical reference lists are not inferred.'}


def build_ledger():
    snapshot = Snapshot()
    snapshot.digest(Path(__file__))
    profile = snapshot.read_json(PROFILE)
    rows = profile_rows(profile)
    declared = profile.get('source_sha256')
    require(isinstance(declared, dict), 'Profile must declare source_sha256 for every used PNG')
    used_names = {row['file'] for _, _, row in rows}
    require(set(declared) == used_names, 'Profile hash keys differ from the set of used PNG paths')
    generations, by_master = generation_records(snapshot)
    registrations = registration_records(snapshot)
    upstream = snapshot.read_json(UPSTREAM)
    uses = defaultdict(list)
    for kind, index, row in rows:
        uses[row['file']].append({'kind': kind, 'index': index,
                                  'gait_frame': row['gait_frame'],
                                  'canvas': row.get('canvas', profile['canvas']),
                                  'anchor': row.get('anchor', profile['anchor']),
                                  'art_pixels_per_metre': row.get('art_pixels_per_metre', profile['art_pixels_per_metre'])})
    exports = []
    adopted_masters = set()
    for name in sorted(used_names):
        path = (PROFILE.parent / name).resolve()
        relative(path)
        digest = snapshot.verify(path, declared[name], f'profile PNG {name}')
        usage = uses[name]
        first = usage[0]
        with Image.open(path) as actual_image:
            actual = actual_image.convert('RGBA')
        entry = {'file': name, 'retained_path': relative(path), 'sha256': digest,
                 'rgba_sha256': rgba_digest(actual), 'canvas': list(actual.size),
                 'uses': usage}
        if path.is_relative_to(OLD_RUNTIME):
            require(len(usage) == 1 and first['kind'] == 'transition' and first['index'] < 16,
                    f'Unexpected old-source reuse: {name}')
            entry['lineage'] = reused_entry(path, first['index'],
                                            rows[first['index']][2], upstream, snapshot)
        else:
            candidates = [(document, index, recipe)
                          for document, index, recipe in registrations.get(path, [])
                          if recipe.get('output_sha256') == digest]
            require(candidates, f'No current hash-bound registration for {name}')
            # Equivalent bank/special records may both bind the same output;
            # choosing the last source preserves explicit special overrides.
            document, index, recipe = candidates[-1]
            source = retained_path(recipe.get('source'), document)
            raw_hash = snapshot.verify(source, recipe.get('source_sha256'),
                                       f'{relative(document)}/{index}/source')
            require(source in by_master, f'No completed ImageGen lineage for adopted master: {source}')
            alpha_floor = recipe.get('alpha_floor', 0)
            reconstruction = render_recipe(source, recipe, first['canvas'], alpha_floor)
            require(actual.size == reconstruction.size and actual.tobytes() == reconstruction.tobytes(),
                    f'Export pixels differ from the single whole-image recipe: {name}')
            require(all(item['canvas'] == first['canvas'] for item in usage),
                    f'Conflicting canvas declarations for reused PNG: {name}')
            entry['lineage'] = {'kind': 'single_generated_master_cell',
                                'registration_document': relative(document),
                                'registration_pointer': f'/{index}',
                                'raw_source': relative(source), 'raw_source_sha256': raw_hash,
                                'generation_ids': sorted({item['generation_id'] for item in by_master[source]}),
                                'cell': recipe['cell'], 'uniform_scale': recipe['scale'],
                                'whole_image_origin': recipe['origin'], 'alpha_floor': alpha_floor,
                                'whole_image_recipe_rgba_match': True}
            adopted_masters.add(relative(source))
        exports.append(entry)
    for generation in generations:
        generation['role'] = ('selected_export_master' if generation['master'] in adopted_masters
                              else 'retained_generation_reference_or_history')
    snapshot.assert_stable()
    return {'version': 1, 'actor': 'lucan', 'performance_profile': relative(PROFILE),
            'performance_profile_sha256': snapshot.digest(PROFILE),
            'coverage': {'transition_records': 133, 'overhead_phase_records': 48,
                         'unique_used_pngs': len(exports), 'direct_upstream_pngs': 16,
                         'selected_new_raw_masters': len(adopted_masters),
                         'retained_generation_records': len(generations)},
            'verified_operations': ['one complete master-cell crop', 'whole-image alpha floor from 0 through 16',
                                    'one uniform premultiplied-alpha Lanczos resize', 'one whole-image translation'],
            'verification_scope': 'Each adopted local PNG and each reused upstream PNG was reconstructed to identical RGBA bytes from its declared whole-image recipe. This does not establish anatomy, gait, framing, or visual approval.',
            'exports': exports, 'generations': generations, 'input_sha256': snapshot.manifest()}


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--check', action='store_true', help='Check the existing ledger without writing files')
    args = parser.parse_args(argv)
    try:
        ledger = build_ledger()
        if args.check:
            require(LEDGER.is_file(), 'Missing source_provenance.json; run without --check first')
            require(json.loads(LEDGER.read_text()) == ledger,
                    'source_provenance.json is stale; regenerate it after the final source export')
        else:
            LEDGER.write_text(json.dumps(ledger, indent=2) + '\n')
    except (ProvenanceError, OSError, json.JSONDecodeError) as error:
        print(f'Lucan provenance check failed: {error}', file=sys.stderr)
        return 1
    coverage = ledger['coverage']
    print(f'Lucan provenance verified: {coverage["transition_records"]} transition records, '
          f'{coverage["overhead_phase_records"]} phases, {coverage["unique_used_pngs"]} PNGs; '
          f'{coverage["retained_generation_records"]} generation records retained.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
