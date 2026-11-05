from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def compare_frames(expected: pd.DataFrame, actual: pd.DataFrame, *, rtol: float=1e-10, atol: float=1e-9) -> dict:
    if list(expected.columns)!=list(actual.columns) or expected.shape!=actual.shape:
        raise ValueError(f'Column/shape mismatch: {expected.shape} vs {actual.shape}')
    differences={}
    for name in expected.columns:
        a,b=expected[name],actual[name]
        if pd.api.types.is_bool_dtype(a) or not pd.api.types.is_numeric_dtype(a):
            if not a.fillna('').astype(str).equals(b.fillna('').astype(str)):
                raise ValueError('Categorical/Boolean mismatch: '+name)
        else:
            av=a.to_numpy(float);bv=b.to_numpy(float)
            if not np.allclose(av,bv,rtol=rtol,atol=atol,equal_nan=True):
                raise ValueError('Numerical mismatch: '+name)
            finite=np.isfinite(av)&np.isfinite(bv)
            differences[name]=float(np.max(np.abs(av[finite]-bv[finite]))) if finite.any() else 0.0
    return {'status':'PASS','rows':len(expected),'columns':len(expected.columns),'rtol':rtol,'atol':atol,'maximum_absolute_differences':differences}
