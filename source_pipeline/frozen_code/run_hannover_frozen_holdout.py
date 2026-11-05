#!/usr/bin/env python3
"""H2 R19 independent-texture runner - pre-existing frozen q=32 Phase8 estimator.
Research-only: S4-S23 outcome not seen at authoring. Preserves all windows; HOLD on schema failure.
Source data never redistributed. Requires numpy/scipy/h5py (official original source ZIP separately).
"""
from __future__ import annotations
import csv, zipfile, io, re, json, math, hashlib, argparse
from pathlib import Path
import numpy as np
import phase8_estimators_frozen as ph8

def hashfile(path):
    with open(path,'rb') as f: return hashlib.sha256(f.read()).hexdigest()

def write_rows(path,rows):
    if not rows:return
    with open(path,'w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def grid(t,x,f,k):
    start=k*ph8.PERIOD;end=start+ph8.PERIOD
    lo=np.searchsorted(t,start,side='right');hi=np.searchsorted(t,end,side='left')
    tt=np.concatenate(([start],t[lo:hi],[end]))
    return tt,np.interp(tt,t,x),np.interp(tt,t,f)

def sparse(t,k,s):
    start=k*ph8.PERIOD;end=start+ph8.PERIOD
    lo=np.searchsorted(t,start,side='left');hi=np.searchsorted(t,end,side='left')
    local=t[lo:hi]
    if len(local)<64:raise ValueError('Fewer than 64 nominal samples in window')
    desired=start+s*ph8.DT_NOMINAL+ph8.PERIOD*np.arange(ph8.Q)/ph8.Q
    if desired.max()>=end:raise ValueError('Bad offset grid')
    upper=np.searchsorted(local,desired,side='left');upper=np.clip(upper,0,len(local)-1)
    lower=np.maximum(upper-1,0)
    chosen=np.where(abs(local[upper]-desired)<abs(local[lower]-desired),upper,lower)
    result=lo+chosen
    if len(set(result))!=ph8.Q:raise ValueError('Duplicate sparse samples')
    return result

def replay_one(source_zip:Path,output_dir:Path,save_offsets=False):
    output_dir.mkdir(parents=True,exist_ok=True)
    texture=re.search(r'(?:^|[-_])s(\d+)(?:[._-]|$)',source_zip.name,re.I)
    if not texture:raise ValueError('Cannot identify texture S# in source archive filename')
    n=int(texture.group(1));tex=f'S{n}'
    # By explicit protocol, S4–S23 are the prospective held-texture targets.
    if n not in range(1,24):raise ValueError('Only source texture S1..S23')
    with zipfile.ZipFile(source_zip) as z:
        if z.testzip() is not None:raise ValueError('Source ZIP CRC failed')
        candidates=[name for name in z.namelist() if Path(name).name=='Messreihe1.mat']
        if len(candidates)!=1:raise ValueError('Expected exactly one canonical Messreihe1.mat; no source substitution')
        sourceblob=z.read(candidates[0])
        mhash=hashlib.sha256(sourceblob).hexdigest()
        d=ph8.get_messreihe(sourceblob)
    t=d['time'];x=d['displacement'];f=d['force']
    if not (len(t)==len(x)==len(f) and len(t)>1000):raise ValueError('Unexpected MAT time/response array lengths')
    if not(np.all(np.isfinite(t)) and np.all(np.diff(t)>0) and np.all(np.isfinite(x)) and np.all(np.isfinite(f))):raise ValueError('Nonfinite or unordered source channels')
    meddt=float(np.median(np.diff(t)))
    if not(8e-5 < meddt < 1.2e-4):raise ValueError('Unmatched source sampling grid: not nominal 0.1ms')
    if abs(t[0])>meddt*1.1:raise ValueError('Unexpected source time origin; reject rather than silently shift')
    kmax=int(math.floor((t[-1]+1e-12)/ph8.PERIOD))
    if kmax<30:raise ValueError('Not enough nominal full 0.05-s windows (need 30)')
    windows=[]; offsets=[]
    for k in range(kmax):
        tt,xx,ff=grid(t,x,f,k)
        ref=ph8.polygon(xx,ff)
        independent=ph8.polygon_independent(xx,ff)
        if abs(ref-independent)>2e-9*max(1,abs(ref)):raise ValueError('Polygon formula cross-check failed')
        xspan=float(np.ptp(xx));fspan=float(np.ptp(ff));span=xspan*fspan
        if not(xspan>0 and fspan>0):raise ValueError(f'Zero channel range at window {k}: HOLD entire texture')
        r2=ph8.r_squared_x(tt,xx,k*ph8.PERIOD)
        results_h=[];results_l=[];offrows=[]
        for s in range(16):
            ix=sparse(t,k,s)
            wh,wl=ph8.reconstruct(tt,xx,t[ix],f[ix],k*ph8.PERIOD)
            row={'texture':tex,'recording':'Messreihe1.mat','window_index':k,'offset':s,'ref_work_signal_units':ref,
                 'harmonic_work_signal_units':wh,'linear_work_signal_units':wl,
                 'harmonic_abs_error':abs(wh-ref),'linear_abs_error':abs(wl-ref),
                 'harmonic_rel_error_pct':ph8.relpct(wh,ref),'linear_rel_error_pct':ph8.relpct(wl,ref)}
            results_h.append(wh);results_l.append(wl);offrows.append(row)
        h=np.asarray(results_h);l=np.asarray(results_l)
        dah=float(np.max(abs(h-ref)));dal=float(np.max(abs(l-ref)))
        relh=100*dah/abs(ref) if ref!=0 else float('nan')
        rell=100*dal/abs(ref) if ref!=0 else float('nan')
        # Any sampling offset changes the numerical sign of the stored integral;
        # this never establishes negative physical dissipation.
        signh=int(np.any(h*ref<0)) if ref!=0 else 0
        signl=int(np.any(l*ref<0)) if ref!=0 else 0
        windows.append({'texture':tex,'recording':'Messreihe1.mat','window_index':k,
          'window_start_s':round(k*ph8.PERIOD,10),'source_dense_points':len(tt),'r2_displacement':r2,
          'geometry_r2_ge_0p99':bool(r2>=.99),'x_span_signal_units':xspan,'force_span_signal_units':fspan,
          'work_reference_signal_units':ref,'absolute_work_scale':abs(ref)/span,
          'negative_reference_work':bool(ref<0),'undefined_pct_reference_zero':bool(ref==0),
          'harmonic_worst_abs_work_error':dah,'linear_worst_abs_work_error':dal,
          'harmonic_worst_pct':relh,'linear_worst_pct':rell,
          'harmonic_worst_range_normalized':dah/span,'linear_worst_range_normalized':dal/span,
          'harmonic_worst_pct_gt5':bool(relh>5),'linear_worst_pct_gt5':bool(rell>5),
          'harmonic_any_offset_sign_flip':bool(signh),'linear_any_offset_sign_flip':bool(signl)})
        if save_offsets:offsets.extend(offrows)
        if (k+1)%250==0:print(tex,k+1,'/',kmax,flush=True)
    initial_span=float(np.median([r['x_span_signal_units'] for r in windows[:30]]))
    for row in windows:
        row['low_motion_initial30_20pct_posthoc_S2_rule']=row['x_span_signal_units']<.2*initial_span
    write_rows(output_dir/f'{tex}_windows.csv',windows)
    if save_offsets:write_rows(output_dir/f'{tex}_offsets.csv',offsets)
    valid=[r for r in windows if not r['undefined_pct_reference_zero']]
    stats=lambda fld:float(np.median([r[fld] for r in valid])) if valid else None
    summary={'texture':tex,'source_archive_sha256':hashfile(source_zip),'canonical_MAT_sha256':mhash,
       'schema':'Messreihe1.mat original signals; original units as recorded; not calibrated physical work',
       'canonical_recordings':1,'source_points':len(t),'complete_windows':len(windows),
       'sample_dt_median_s':meddt,'offset_grid_count_per_window':16,
       'r2_ge_0p99_count':sum(r['geometry_r2_ge_0p99'] for r in windows),
       'relative_error_undefined_zero_work_count':len(windows)-len(valid),
       'harmonic_gt5':sum(r['harmonic_worst_pct_gt5'] for r in valid),
       'linear_gt5':sum(r['linear_worst_pct_gt5'] for r in valid),
       'negative_integral_count':sum(r['negative_reference_work'] for r in windows),
       'harmonic_sign_flip_count':sum(r['harmonic_any_offset_sign_flip'] for r in windows),
       'low_motion_20pct_first30_count':sum(r['low_motion_initial30_20pct_posthoc_S2_rule'] for r in windows),
       'harmonic_median_pct':stats('harmonic_worst_pct'),
       'linear_median_pct':stats('linear_worst_pct'),
       'harmonic_median_abs':stats('harmonic_worst_abs_work_error'),
       'harmonic_median_rectangle_norm':stats('harmonic_worst_range_normalized'),
       'linear_median_rectangle_norm':stats('linear_worst_range_normalized'),
       'no_source_device_calibration_or_timelag_claim':True,
       'scope':'Frozen comparator re-analysis only. Textures from the same Hannover programme, not independent-rig proof.'}
    (output_dir/f'{tex}_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-zip',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path);p.add_argument('--save-offsets',action='store_true')
    args=p.parse_args()
    if not all(ph8.unit_tests().values()):raise ValueError('Frozen Phase8 estimator unit tests failed')
    replay_one(args.source_zip,args.out,args.save_offsets)
if __name__=='__main__':main()
