#!/usr/bin/env python3
"""R22B prospective-to-this-audit diagnostic: isolate force harmonic vs displacement approximation.
R22 frozen original comparator reproduced exactly; additional counterfactual computes harmonic-force work on measured x.
No new source arrays distributed. Authenticated 18/20 from already admitted raw ZIPs; 20 original R22 remains locked.
"""
from pathlib import Path
import zipfile, csv, json, hashlib, io, sys, time, argparse
import numpy as np
import pandas as pd

parser=argparse.ArgumentParser(description='Independent 18-texture post-outcome ablation, no third-party source redistribution')
parser.add_argument('--source-root',type=Path,required=True,help='Local directory of publisher original fn20...s#.zip archives (18 textures only)')
parser.add_argument('--frozen-derived-zip',type=Path,required=True,help='Official R22 complete 20-texture derived-only ZIP')
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--textures',default='4,5,6,8,9,10,11,12,14,15,16,17,18,19,20,21,22,23',help='Explicit subset of original 18 replayed textures; omitted means all 18')
args=parser.parse_args()
selected=[int(x.strip().lstrip('Ss')) for x in args.textures.split(',')]
if not selected or len(set(selected))!=len(selected) or not set(selected).issubset({4,5,6,8,9,10,11,12,14,15,16,17,18,19,20,21,22,23}): raise ValueError('Invalid or duplicated original replay texture selection')
ROOT=args.source_root
EVID=args.frozen_derived_zip or (ROOT/'H2_Hannover_S4_S23_20Texture_DerivedOnly_20261102.zip')
HERE=args.out
HERE.mkdir(parents=True,exist_ok=True)

import importlib.util
with zipfile.ZipFile(EVID) as z:
    code=z.read('phase8_estimators_frozen.py')
    path=HERE/'_phase8_estimators_frozen_authoritative.py'
    path.write_bytes(code)
spec=importlib.util.spec_from_file_location('ph8_authoritative',path)
ph8=importlib.util.module_from_spec(spec);spec.loader.exec_module(ph8)

cols=['texture','window','n_dense','work','harmonic_orig_worst_pct','harmonic_on_full_x_worst_pct','orig_minus_full_x_max_normref_pct','orig_minus_full_x_max_range_norm','harmonic_fullx_better','harmonic_fullx_exceed5','harmonic_orig_exceed5','max_harmonic_orig_replay_diff_pct']
def fast_cycle_grid(t,x,f,k):
    start=k*ph8.PERIOD;end=start+ph8.PERIOD
    lo=np.searchsorted(t,start,side='right'); hi=np.searchsorted(t,end,side='left')
    tt=np.concatenate(([start],t[lo:hi],[end]))
    return tt,np.interp(tt,t,x),np.interp(tt,t,f)

def fast_sparse_matrix(t,k):
    # Match frozen ph8.sparse_indices exactly, using searchsorted instead of an O(N) scan.
    start=k*ph8.PERIOD; end=start+ph8.PERIOD
    lo=np.searchsorted(t,start,side='left');hi=np.searchsorted(t,end,side='left')
    local=t[lo:hi]
    desired=start+np.arange(16)[:,None]*ph8.DT_NOMINAL+ph8.PERIOD*np.arange(ph8.Q)[None,:]/ph8.Q
    upper=np.clip(np.searchsorted(local,desired,side='left'),0,len(local)-1)
    lower=np.maximum(upper-1,0)
    chosen=np.where(abs(local[upper]-desired)<abs(local[lower]-desired),upper,lower)
    ix=lo+chosen
    assert np.all(np.diff(np.sort(ix,axis=1),axis=1)>0)
    return ix

rows=[]
for texture in selected:
    tag=f'S{texture}';raw=ROOT/f'fn20-0x20-0f20-s{texture}.zip'
    if not raw.exists():raise FileNotFoundError(raw)
    with zipfile.ZipFile(EVID) as z:
        summ=json.loads(z.read(f'derived/{tag}/{tag}_summary.json'))
        locked=pd.read_csv(io.BytesIO(z.read(f'derived/{tag}/{tag}_windows.csv')))
    h=hashlib.sha256(raw.read_bytes()).hexdigest()
    assert h==summ['source_archive_sha256'],f'{tag}: unauthorized original raw bytes'
    with zipfile.ZipFile(raw) as z:
        assert z.testzip() is None
        contents=[p for p in z.namelist() if Path(p).name=='Messreihe1.mat']
        assert len(contents)==1
        blob=z.read(contents[0]);assert hashlib.sha256(blob).hexdigest()==summ['canonical_MAT_sha256']
        d=ph8.get_messreihe(blob)
    t,x,f=(d['time'],d['displacement'],d['force']); assert len(t)==len(x)==len(f)
    num=summ['complete_windows'];assert len(locked)==num
    for k in range(num):
        tt,xx,ff=fast_cycle_grid(t,x,f,k); ref=ph8.polygon(xx,ff)
        assert ref!=0
        r=locked.iloc[k]
        assert np.isclose(ref,r['work_reference_signal_units'],rtol=1e-11,atol=1e-8)
        cx=ph8.sinefit(tt,xx,k*ph8.PERIOD)
        dense_force_coeff=ph8.sinefit(tt,ff,k*ph8.PERIOD)
        theta=2*np.pi*(tt-k*ph8.PERIOD)/ph8.PERIOD
        cost=np.cos(theta);sint=np.sin(theta)
        c_i=0.5*(np.roll(xx,-1)-np.roll(xx,1))
        # For the harmonic-force-only method, all offsets share this exact finite-sample x functional.
        sum_c=np.sum(c_i)
        sum_cos_c=np.dot(cost,c_i);sum_sin_c=np.dot(sint,c_i)
        dense_force_harmonic_work=float(dense_force_coeff[0]*sum_c+dense_force_coeff[1]*sum_cos_c+dense_force_coeff[2]*sum_sin_c)
        dense_force_harmonic_error_pct=float(100*abs(dense_force_harmonic_work-ref)/abs(ref))
        ix=fast_sparse_matrix(t,k)
        if k==0 or k==num-1:
            for so in (0,3,8,15):
                assert np.array_equal(ix[so],ph8.sparse_indices(t,k,so))
        ang=2*np.pi*(t[ix]-k*ph8.PERIOD)/ph8.PERIOD
        mats=np.stack([np.ones_like(ang),np.cos(ang),np.sin(ang)],axis=2)
        y=f[ix]
        # Batched 16 independent, 3x3 least-square fits (same algebra as frozen np.linalg.lstsq).
        af=np.linalg.solve(np.einsum('nki,nkj->nij',mats,mats),np.einsum('nki,nk->ni',mats,y)[...,None])[...,0]
        if k==0 or k==num-1:
            for so in (0,3,8,15):
                np.testing.assert_allclose(af[so],ph8.sinefit(t[ix[so]],f[ix[so]],k*ph8.PERIOD),atol=1e-9,rtol=1e-10)
        orig=np.pi*(af[:,1]*cx[2]-af[:,2]*cx[1])
        fixed=af[:,0]*sum_c+af[:,1]*sum_cos_c+af[:,2]*sum_sin_c
        oe=float(100*np.max(np.abs(orig-ref))/abs(ref))
        fe=float(100*np.max(np.abs(fixed-ref))/abs(ref))
        parity=abs(oe-r['harmonic_worst_pct'])
        if parity>max(1e-8,1e-10*abs(oe)):
            raise AssertionError(f'{tag}/{k}: original harmonic not reproduced: {oe=} {r["harmonic_worst_pct"]=}')
        rows.append(dict(texture=tag,window=k,n_dense=len(tt),work=ref,
            harmonic_orig_worst_pct=oe,harmonic_on_full_x_worst_pct=fe,
            orig_minus_full_x_max_normref_pct=float(100*np.max(np.abs(orig-fixed))/abs(ref)),
            orig_minus_full_x_max_range_norm=float(np.max(np.abs(orig-fixed))/(np.ptp(xx)*np.ptp(ff))),
            dense_force_harmonic_full_x_error_pct=dense_force_harmonic_error_pct,
            sparse_vs_dense_force_harmonic_max_pct=float(100*np.max(np.abs(fixed-dense_force_harmonic_work))/abs(ref)),
            frozen_linear_worst_pct=float(r['linear_worst_pct']),
            harmonic_fullx_beats_linear=fe<float(r['linear_worst_pct']),
            harmonic_fullx_better=fe<oe,harmonic_fullx_exceed5=fe>5,harmonic_orig_exceed5=oe>5,
            max_harmonic_orig_replay_diff_pct=parity))
    print(tag,'PASS',num,'orig>5',sum(x['harmonic_orig_exceed5'] for x in rows if x['texture']==tag),'fullx>5',sum(x['harmonic_fullx_exceed5'] for x in rows if x['texture']==tag),flush=True)

all_df=pd.DataFrame(rows)
all_df.to_csv(HERE/'R22B_18source_window_ablation.csv',index=False,float_format='%.16g')
agg=all_df.groupby('texture',sort=False).agg(windows=('window','size'),orig_median_pct=('harmonic_orig_worst_pct','median'),full_x_median_pct=('harmonic_on_full_x_worst_pct','median'),linear_median_pct=('frozen_linear_worst_pct','median'),dense_force_median_pct=('dense_force_harmonic_full_x_error_pct','median'),sparse_dense_difference_median_pct=('sparse_vs_dense_force_harmonic_max_pct','median'),orig_gt5=('harmonic_orig_exceed5','sum'),full_x_gt5=('harmonic_fullx_exceed5','sum'),dense_force_gt5=('dense_force_harmonic_full_x_error_pct',lambda x:int((x>5).sum())),linear_frozen_gt5=('frozen_linear_worst_pct',lambda x:int((x>5).sum())),median_orig_minus_fullx_max_pct=('orig_minus_full_x_max_normref_pct','median'),max_orig_minus_fullx_max_pct=('orig_minus_full_x_max_normref_pct','max'),orig_replay_max_error=('max_harmonic_orig_replay_diff_pct','max')).reset_index()
agg.to_csv(HERE/'R22B_18source_texture_ablation.csv',index=False,float_format='%.16g')
res={'textures':len(agg),'windows':len(all_df),'original_harmonic_gt5':int(all_df.harmonic_orig_exceed5.sum()),'full_x_harmonic_gt5':int(all_df.harmonic_fullx_exceed5.sum()),'dense_force_harmonic_gt5':int((all_df.dense_force_harmonic_full_x_error_pct>5).sum()),'linear_frozen_gt5':int((all_df.frozen_linear_worst_pct>5).sum()),'harmonic_fullx_beats_frozen_linear_windows':int(all_df.harmonic_fullx_beats_linear.sum()),'median_texture_of_medians_orig_pct':float(agg.orig_median_pct.median()),'median_texture_of_medians_full_x_pct':float(agg.full_x_median_pct.median()),'median_texture_of_medians_dense_force_harmonic_pct':float(agg.dense_force_median_pct.median()),'median_texture_of_medians_linear_pct':float(agg.linear_median_pct.median()),'max_dense_force_model_error_pct':float(all_df.dense_force_harmonic_full_x_error_pct.max()),'num_windows_dense_force_below5_but_sparse_fullx_over5':int(((all_df.dense_force_harmonic_full_x_error_pct<=5)&(all_df.harmonic_on_full_x_worst_pct>5)).sum()),'textures_harmonic_full_x_median_better':int((agg.full_x_median_pct<agg.orig_median_pct).sum()),'max_original_harmonic_parity_error':float(all_df.max_harmonic_orig_replay_diff_pct.max()),'scope':f'Explicit execution subset {selected} of the original 18-texture ablation. Not an extension to S7/S13 or a new experiment.'}
(HERE/'R22B_18source_ablation_summary.json').write_text(json.dumps(res,indent=2)+'\n')
print('ALL',json.dumps(res,indent=2),flush=True)
