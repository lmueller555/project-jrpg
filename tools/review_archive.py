"""Verify retained review evidence against the revision that produced it.

Capture commands intentionally compare their sources with the current checkout.
Once approved assets are deployed, their original review remains historical
evidence: it must retain its exact media and source hashes, without requiring a
new walkthrough merely because gameplay changed later.
"""
from hashlib import sha256
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def revision_hashes(revision, paths):
    """Read many Git blobs in one process, preserving binary file contents."""
    paths = sorted(set(paths))
    assert all('\n' not in path for path in paths)
    requests = ''.join(f'{revision}:{path}\n' for path in paths).encode()
    result = subprocess.run(['git', 'cat-file', '--batch'], input=requests,
                            cwd=ROOT, check=True, capture_output=True)
    output = result.stdout
    offset = 0
    hashes = {}
    for path in paths:
        end = output.index(b'\n', offset)
        header = output[offset:end].split()
        assert len(header) == 3 and header[1] == b'blob', (revision, path, header)
        size = int(header[2])
        start = end+1
        hashes[path] = sha256(output[start:start+size]).hexdigest()
        assert output[start+size:start+size+1] == b'\n'
        offset = start+size+1
    assert offset == len(output)
    return hashes


def check_review_archive(output, report_sha256, *snapshot_keys, source_revision=None):
    """Check immutable provenance and media, including in a shallow checkout.

    The report digest pins every original source fingerprint. An optional Git
    revision also verifies those sources when the original history is available;
    ordinary tests need no network or historical blobs.
    """
    output = Path(output)
    report_bytes = (output/'verification.json').read_bytes()
    assert sha256(report_bytes).hexdigest() == report_sha256, 'Archived provenance changed'
    report = json.loads(report_bytes)
    keys = ('source_sha256', *snapshot_keys)
    for key in keys:
        expected = report[key]
        assert expected, f'Empty archived snapshot: {key}'
        assert all(len(digest) == 64 and int(digest, 16) >= 0
                   for digest in expected.values()), key
    if source_revision:
        paths = set().union(*(report[key] for key in keys))
        recorded = revision_hashes(source_revision, paths)
        for key in keys:
            expected = report[key]
            assert expected == {path: recorded[path] for path in expected}, (source_revision, key)
    assert report['artifact_sha256'], 'Archived review contains no artifacts'
    for name, expected in report['artifact_sha256'].items():
        assert sha256((output/name).read_bytes()).hexdigest() == expected, name
    return report
