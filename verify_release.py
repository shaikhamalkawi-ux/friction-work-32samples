#!/usr/bin/env python3
"""Verify the immutable payload of this release without requiring scientific packages.

Generated files, such as __pycache__ or local test outputs, are not part of the
manifest. The expected manifest must come from the downloaded release, not from
an input dataset. A missing or modified payload file causes a nonzero exit.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    manifest_path = root / 'SHA256SUMS.json'
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if not isinstance(manifest, dict) or not manifest:
            raise ValueError('Manifest must be a nonempty path-to-SHA256 dictionary')
        errors = []
        for relative, expected in manifest.items():
            if not isinstance(relative, str) or not isinstance(expected, str) or len(expected) != 64:
                raise ValueError('Malformed manifest entry')
            path = root / relative
            if path.resolve().is_relative_to(root) is False:
                raise ValueError('Manifest path leaves the release directory')
            if not path.is_file():
                errors.append({'file': relative, 'reason': 'missing'})
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                errors.append({'file': relative, 'reason': 'SHA256 mismatch'})
        print(json.dumps({'status': 'FAIL' if errors else 'PASS',
                          'manifest_payload_files': len(manifest),
                          'failures': errors}, indent=2))
        return 1 if errors else 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print('FAIL: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
