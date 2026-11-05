#!/usr/bin/env python3
"""Restore three original derived-only artifacts, verified by SHA256.

No original laboratory measurements are included or downloaded. This reconstructs
only frozen derived score ledgers and their source-derived transport ZIP from
base64 chunks, without modifying scientific data or numerical calculations.
"""
from __future__ import annotations
import base64,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(b):return hashlib.sha256(b).hexdigest()

def main():
    manifest=json.loads((ROOT/'payload/MANIFEST.json').read_text())
    for rel,obj in manifest.items():
        path=ROOT/rel
        if not path.resolve().is_relative_to(ROOT):raise ValueError('invalid payload path')
        expected=obj['sha256']
        if path.exists():
            if sha(path.read_bytes())!=expected: raise ValueError('existing payload hash mismatch: '+rel)
            print('VERIFIED',rel);continue
        chunks=[]
        for part in obj['chunks']:
            q=ROOT/part
            if not q.resolve().is_relative_to(ROOT):raise ValueError('invalid chunk path')
            chunks.append(q.read_text(encoding='ascii'))
        packed=base64.b64decode(''.join(chunks),validate=True)
        if sha(packed)!=obj['compressed_sha256']:raise ValueError('encoded payload mismatch: '+rel)
        raw=gzip.decompress(packed) if obj['encoding']=='base64-gzip' else packed
        if len(raw)!=obj['bytes'] or sha(raw)!=expected:raise ValueError('restored payload mismatch: '+rel)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
        print('RESTORED',rel)
    print('PAYLOAD_RESTORE_PASS')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError) as exc:print('PAYLOAD_RESTORE_FAIL:',exc,file=sys.stderr);sys.exit(2)
