#!/usr/bin/env python3
"""R23B post-outcome offset aggregation sensitivity on 18 independent original source replays.
Strictly no new model tuning or third-party raw redistribution. Frozen q32 and 16 offsets.
"""
import zipfile,io,json,hashlib,importlib.util,sys,os
from pathlib import Path
import numpy as np,pandas as pd
import argparse
parser=argparse.ArgumentParser(description='Portable execution of the frozen R24 offset diagnostic')
parser.add_argument('--source-root',type=Path,required=True)
parser.add_argument('--frozen-derived-zip',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--textures',default='4,5,6,8,9,10,11,12,14,15,16,17,18,19,20,21,22,23')
args=parser.parse_args()
selected=[int(x.strip().lstrip('Ss')) for x in args.textures.split(',')]
if not selected or len(set(selected))!=len(selected) or not set(selected).issubset({4,5,6,8,9,10,11,12,14,15,16,17,18,19,20,21,22,23}): raise ValueError('Invalid or duplicated original replay texture selection')
ROOT=args.source_root;OUT=args.out;ZIP=args.frozen_derived_zip
OUT.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(ZIP) as z:
 script=OUT/'_phase8_frozen_code.py';script.write_bytes(z.read('phase8_estimators_frozen.py'))
spec=importlib.util.spec_from_file_location('ph8audit',script);ph8=importlib.util.module_from_spec(spec);spec.loader.exec_module(ph8)

rows=[];texture=[]
for n in selected:
 tag='S'+str(n);raw=ROOT/f'fn20-0x20-0f20-s{n}.zip'
 with zipfile.ZipFile(ZIP) as z:
  summary=json.loads(z.read(f'derived/{tag}/{tag}_summary.json'))
  frozen=pd.read_csv(io.BytesIO(z.read(f'derived/{tag}/{tag}_windows.csv')))
 assert hashlib.sha256(raw.read_bytes()).hexdigest()==summary['source_archive_sha256']
 with zipfile.ZipFile(raw) as z:
  assert z.testzip() is None
  names=[s for s in z.namelist() if Path(s).name=='Messreihe1.mat']
  assert len(names)==1
  blob=z.read(names[0]);assert hashlib.sha256(blob).hexdigest()==summary['canonical_MAT_sha256']
  d=ph8.get_messreihe(blob)
 t,x,f=d['time'],d['displacement'],d['force']; count=summary['complete_windows']
 assert len(frozen)==count
 WINS={'w_h_mean':0,'w_l_mean':0,'w_h_median':0,'w_l_median':0,'w_h_same':0,'w_l_same':0}
 for k in range(count):
  start=k*ph8.PERIOD;end=start+ph8.PERIOD
  lo=np.searchsorted(t,start,side='right');hi=np.searchsorted(t,end,side='left')
  tt=np.r_[start,t[lo:hi],end];xx=np.interp(tt,t,x);ff=np.interp(tt,t,f)
  ref=ph8.polygon(xx,ff)
  assert np.isclose(ref,float(frozen.iloc[k]['work_reference_signal_units']),rtol=1e-11,atol=1e-8)
  ax=ph8.sinefit(tt,xx,start)
  # Preserved 32 sparse picks for the 16 fixed offsets
  local_lo=np.searchsorted(t,start,side='left');local_hi=np.searchsorted(t,end,side='left');local=t[local_lo:local_hi]
  desired=start+np.arange(16)[:,None]*ph8.DT_NOMINAL+ph8.PERIOD*np.arange(ph8.Q)[None,:]/ph8.Q
  upper=np.clip(np.searchsorted(local,desired,side='left'),0,len(local)-1);lower=np.maximum(upper-1,0)
  ix=local_lo+np.where(np.abs(local[upper]-desired)<np.abs(local[lower]-desired),upper,lower)
  if k in (0,count-1):
   for j in [0,3,8,15]:assert np.array_equal(ix[j],ph8.sparse_indices(t,k,j))
  ts_all=t[ix];fs_all=f[ix]
  angle=2*np.pi*(ts_all-start)/ph8.PERIOD
  mats=np.stack((np.ones_like(angle),np.cos(angle),np.sin(angle)),axis=-1)
  af=np.linalg.solve(np.einsum('nki,nkj->nij',mats,mats),np.einsum('nki,nk->ni',mats,fs_all)[...,None])[...,0]
  if k in (0,count-1):
   for j in [0,3,8,15]:np.testing.assert_allclose(af[j],ph8.sinefit(ts_all[j],fs_all[j],start),atol=1e-9,rtol=1e-10)
  orig=np.pi*(af[:,1]*ax[2]-af[:,2]*ax[1])
  he=100*np.abs(orig-ref)/abs(ref)
  le=[]
  # Only the originally prescribed 16 offsets; interpolation on time, then work on measured displacement.
  cc=0.5*(np.roll(xx,-1)-np.roll(xx,1))
  for j in range(16):
   ts=ts_all[j];fs=fs_all[j]
   tim=np.r_[ts[-1]-ph8.PERIOD,ts,ts[0]+ph8.PERIOD]
   values=np.r_[fs[-1],fs,fs[0]]
   Fhat=np.interp(tt,tim,values)
   wl=float(np.dot(Fhat,cc))
   le.append(100*abs(wl-ref)/abs(ref))
  le=np.asarray(le)
  assert np.isclose(he.max(),frozen.iloc[k]['harmonic_worst_pct'],atol=1e-9,rtol=1e-11)
  assert np.isclose(le.max(),frozen.iloc[k]['linear_worst_pct'],atol=1e-9,rtol=1e-11)
  rows.append({'texture':tag,'window_index':k,'harm_worst_pct':he.max(),'lin_worst_pct':le.max(),
     'harm_mean_offset_pct':he.mean(),'lin_mean_offset_pct':le.mean(),
     'harm_median_offset_pct':np.median(he),'lin_median_offset_pct':np.median(le),
     'harm_maximum_minus_median_pct':he.max()-np.median(he),
     'lin_maximum_minus_median_pct':le.max()-np.median(le),
     'harm_wins_num_offsets':int(np.sum(he<le)),
     'linear_wins_num_offsets':int(np.sum(le<he)),
     'exact_tie_num_offsets':int(np.sum(he==le))})
 print(f'{tag}: {count} windows, clean q32 parity PASS',flush=True)

D=pd.DataFrame(rows)
D.to_csv(OUT/'R23B_18texture_offset_sensitivity_windows.csv',index=False,float_format='%.14g')
agg=D.groupby('texture',sort=False).agg(windows=('window_index','size'),harm_worst_texture_median=('harm_worst_pct','median'),linear_worst_texture_median=('lin_worst_pct','median'),harm_mean_offset_texture_median=('harm_mean_offset_pct','median'),linear_mean_offset_texture_median=('lin_mean_offset_pct','median'),harm_median_offset_texture_median=('harm_median_offset_pct','median'),linear_median_offset_texture_median=('lin_median_offset_pct','median'),harm_wins_same_offsets=('harm_wins_num_offsets','sum'),linear_wins_same_offsets=('linear_wins_num_offsets','sum'),harm_wins_worst_windows=('harm_worst_pct',lambda x:0)).reset_index()
agg['harm_wins_worst_windows']=D.groupby('texture',sort=False).apply(lambda x:(x.harm_worst_pct<x.lin_worst_pct).sum(),include_groups=False).values
agg['harm_wins_meanoffset_windows']=D.groupby('texture',sort=False).apply(lambda x:(x.harm_mean_offset_pct<x.lin_mean_offset_pct).sum(),include_groups=False).values
agg['harm_wins_medianoffset_windows']=D.groupby('texture',sort=False).apply(lambda x:(x.harm_median_offset_pct<x.lin_median_offset_pct).sum(),include_groups=False).values
agg.to_csv(OUT/'R23B_18texture_offset_sensitivity_texture.csv',index=False,float_format='%.14g')
res={'source_textures':len(selected),'source_windows':len(D),'paired_offset_evaluations':len(D)*16,
'orig_worst_harm_wins_windows':int((D.harm_worst_pct<D.lin_worst_pct).sum()),
'mean_offset_harm_wins_windows':int((D.harm_mean_offset_pct<D.lin_mean_offset_pct).sum()),
'median_offset_harm_wins_windows':int((D.harm_median_offset_pct<D.lin_median_offset_pct).sum()),
'harm_wins_per_offset_total':int(D.harm_wins_num_offsets.sum()),
'linear_wins_per_offset_total':int(D.linear_wins_num_offsets.sum()),
'mean_offset_texture_median_h_vs_l':[float(agg.harm_mean_offset_texture_median.median()),float(agg.linear_mean_offset_texture_median.median())],
'median_offset_texture_median_h_vs_l':[float(agg.harm_median_offset_texture_median.median()),float(agg.linear_median_offset_texture_median.median())],
'worst_texture_median_h_vs_l':[float(agg.harm_worst_texture_median.median()),float(agg.linear_worst_texture_median.median())],
'num_textures_higher_median_harmonic_for_worst':int((agg.harm_worst_texture_median>agg.linear_worst_texture_median).sum()),
'num_textures_higher_median_harmonic_for_mean_offset':int((agg.harm_mean_offset_texture_median>agg.linear_mean_offset_texture_median).sum()),
'num_textures_higher_median_harmonic_for_median_offset':int((agg.harm_median_offset_texture_median>agg.linear_median_offset_texture_median).sum()),
'scope':f'Explicit execution subset {selected} of the original 18-texture offset diagnostic. Frozen 16 offsets and q32. Windows and offsets dependent.'}
(OUT/'R23B_18texture_offset_sensitivity_summary.json').write_text(json.dumps(res,indent=2)+'\n')
print(json.dumps(res,indent=2),flush=True)
