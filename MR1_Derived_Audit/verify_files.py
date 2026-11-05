#!/usr/bin/env python3
"""Verify exact release input/source identities before a derived-only replay."""
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parent
expect=json.loads((root/'SHA256SUMS.json').read_text())
failed=[]
for name,h in expect.items():
    p=root/name
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=h: failed.append(name)
print(f"Verified {len(expect)-len(failed)}/{len(expect)} manifest entries")
if failed: print('\n'.join(failed));sys.exit(1)
