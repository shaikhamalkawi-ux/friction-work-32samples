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
    # Git's text transport normalizes CRLF in CSVs. Recover canonical original
    # byte streams from the already checksum-verified frozen derived-only ZIP.
    # The ZIP contains no original laboratory measurement arrays.
    import zipfile
    expected=json.loads((ROOT/'SHA256SUMS.json').read_text())
    with zipfile.ZipFile(ROOT/'source_pipeline/Frozen_Primary_20Texture.zip') as archive:
        if archive.testzip() is not None:raise ValueError('frozen derived ZIP CRC failure')
        for n in range(4,24):
            tex=f'S{n}'
            rel=f'MR1_Derived_Audit/inputs/P2/{tex}_windows.csv'
            member=f'derived/{tex}/{tex}_windows.csv'
            data=archive.read(member)
            if sha(data)!=expected[rel]:raise ValueError('frozen derived CSV mismatch: '+rel)
            p=ROOT/rel
            p.parent.mkdir(parents=True,exist_ok=True)
            if not p.exists() or sha(p.read_bytes())!=expected[rel]:p.write_bytes(data)
    # This metadata table also used CRLF in the frozen research package.
    rel='RESULT_TO_COMMAND.csv'
    p=ROOT/rel
    data=p.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
    if sha(data)!=expected[rel]:raise ValueError('result-to-command metadata mismatch')
    if sha(p.read_bytes())!=expected[rel]:p.write_bytes(data)
    print('PAYLOAD_RESTORE_PASS')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError) as exc:print('PAYLOAD_RESTORE_FAIL:',exc,file=sys.stderr);sys.exit(2)
