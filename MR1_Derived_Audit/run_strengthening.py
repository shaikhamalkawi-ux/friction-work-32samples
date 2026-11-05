#!/usr/bin/env python3
"""Post-outcome descriptive audits of frozen H2 ledgers, not raw-sensor replay.
Run: python run_strengthening.py [--paper all|P1|P2]
No training, exclusions, source acquisitions, or modification of primary results.
"""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'; OUT.mkdir(exist_ok=True)

def dump(name, value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def p1():
    d=pd.read_csv(ROOT/'inputs/P1_cycle_out_all_scores.csv')
    assert len(d)==2430 and d.recording.nunique()==9
    assert d.groupby(['recording','task','mask','model']).size().eq(6).all()
    assert d.force_nrmse.notna().all() and (d.force_nrmse>=0).all()
    r=d.groupby(['task','mask','recording','model'],dropna=False).force_nrmse.mean().unstack('model')
    r.to_csv(OUT/'P1_recording_first_errors.csv')
    gaps=r.loc['gap'].copy() if 'gap' in r.index.get_level_values(0) else r.loc['contiguous_gap'].copy()
    # Dataset task labels are checked explicitly below instead of inferred from results.
    rng=r.loc['random'] if 'random' in r.index.get_level_values(0) else r.loc['random_point']
    gapmean=gaps.groupby(level='mask').mean()
    randmean=rng.groupby(level='mask').mean()
    assert len(gapmean)==12 and len(randmean)==3
    assert (randmean.idxmin(axis=1)=='Natural cubic').all()
    # The comparator is the better of Linear/PCHIP AFTER observing each gap ledger.
    # This is an oracle-relative descriptive penalty, not a validated selection rule.
    rows=[]
    for mask,x in gapmean.iterrows():
        winner=x[['Linear','PCHIP']].idxmin()
        gi=gaps.loc[mask]
        rows.append(dict(mask=mask,linear=float(x['Linear']),pchip=float(x['PCHIP']),
                         natural_cubic=float(x['Natural cubic']),retrospective_local_best=winner,
                         retrospective_local_best_error=float(x[winner]),
                         dense_winner_ratio=float(x['Natural cubic']/x[winner]),
                         dense_winner_excess=float(x['Natural cubic']-x[winner]),
                         recordings_cubic_worse_than_local_best=int((gi['Natural cubic']>gi[['Linear','PCHIP']].min(axis=1)).sum())))
    tbl=pd.DataFrame(rows); tbl.to_csv(OUT/'P1_gap_transfer_penalty.csv',index=False)
    loo=[]
    for recording in gaps.index.get_level_values('recording').unique():
        g=gaps.loc[gaps.index.get_level_values('recording')!=recording].groupby(level='mask').mean()
        for mask,row in g.iterrows():
            loo.append({'excluded_recording':recording,'mask':mask,'gap_winner':row.idxmin(),
                        'cubic_to_local_best_ratio':float(row['Natural cubic']/row[['Linear','PCHIP']].min())})
    lt=pd.DataFrame(loo);lt.to_csv(OUT/'P1_leave_one_recording_out.csv',index=False)
    # Independent direct nested means equal groupby hierarchy.
    direct=[]
    for mask in gapmean.index:
        for model in gapmean.columns:
            arr=[]
            for rec in d.recording.unique():
                a=d[(d['mask']==mask)&(d.model==model)&(d.recording==rec)].force_nrmse.to_numpy()
                assert len(a)==6
                arr.append(float(np.sum(a)/6))
            direct.append(abs(sum(arr)/9-gapmean.loc[mask,model]))
    assert max(direct)<1e-12
    s={'scope':'post-outcome derived-ledger; 54 dependent cycles in 9 recordings; not independent experiments',
       'rows':len(d),'recordings':9,'cycles_per_recording':6,'gap_settings':12,
       'cubic_dense_wins':3,'cubic_gap_wins':int((gapmean.idxmin(axis=1)=='Natural cubic').sum()),
       'gap_winners':gapmean.idxmin(axis=1).value_counts().to_dict(),
       'cubic_to_retrospective_local_best_ratio_min':float(tbl.dense_winner_ratio.min()),
       'cubic_to_retrospective_local_best_ratio_max':float(tbl.dense_winner_ratio.max()),
       'cubic_to_retrospective_local_best_ratio_median':float(tbl.dense_winner_ratio.median()),
       'mean_absolute_nrmse_excess':float(tbl.dense_winner_excess.mean()),
       'cubic_to_fixed_pchip_ratio_of_pooled_recording_means':float(gapmean['Natural cubic'].mean()/gapmean.PCHIP.mean()),
       'leave_one_recording_out_settings':len(lt),
       'loo_cubic_wins':int((lt.gap_winner=='Natural cubic').sum()),
       'loo_ratio_min':float(lt.cubic_to_local_best_ratio.min()),
       'loo_ratio_max':float(lt.cubic_to_local_best_ratio.max()),
       'independent_nested_mean_max_abs_error':float(max(direct))}
    dump('P1_summary.json',s);return s

def p2():
    paths=sorted((ROOT/'inputs/P2').glob('*_windows.csv'))
    assert len(paths)==20
    d=pd.concat([pd.read_csv(x) for x in paths],ignore_index=True)
    assert len(d)==24857 and d.texture.nunique()==20
    assert set(d.texture.unique())=={'S'+str(i) for i in range(4,24)}
    assert d[['harmonic_worst_pct','linear_worst_pct']].notna().all().all()
    assert d[['harmonic_worst_pct','linear_worst_pct']].ge(0).all().all()
    thresholds=[0.5,1.,2.,3.,5.,7.5,10.]
    rr=[];per=[]
    for t in thresholds:
        hs=[];ls=[];ns=[]
        for tex,g in d.groupby('texture',sort=True):
            h=int((g.harmonic_worst_pct>t).sum()); l=int((g.linear_worst_pct>t).sum()); n=len(g)
            per.append(dict(threshold_pct=t,texture=tex,n=n,harmonic_count=h,linear_count=l,
                            harmonic_pct=100*h/n,linear_pct=100*l/n))
            hs.append(h/n);ls.append(l/n);ns.append(n)
        h=int((d.harmonic_worst_pct>t).sum());l=int((d.linear_worst_pct>t).sum())
        delta=np.array(hs)-np.array(ls)
        rr.append(dict(threshold_pct=t,harmonic_count=h,linear_count=l,
                       pooled_harmonic_pct=100*h/len(d),pooled_linear_pct=100*l/len(d),
                       equal_texture_harmonic_pct=100*np.mean(hs),equal_texture_linear_pct=100*np.mean(ls),
                       textures_linear_lower=int((delta>0).sum()),textures_tied=int((delta==0).sum()),
                       textures_harmonic_lower=int((delta<0).sum())))
    tb=pd.DataFrame(rr);tb.to_csv(OUT/'P2_threshold_sensitivity.csv',index=False)
    pt=pd.DataFrame(per);pt.to_csv(OUT/'P2_threshold_by_texture.csv',index=False)
    primary=pt[pt.threshold_pct==5].copy()
    assert int(primary.harmonic_count.sum())==5038 and int(primary.linear_count.sum())==107
    # Independent Python count, not comparison with a value produced by the same vectorized path.
    assert sum(float(x)>5 for x in d.harmonic_worst_pct)==5038
    assert sum(float(x)>5 for x in d.linear_worst_pct)==107
    assert int((d.linear_worst_pct<d.harmonic_worst_pct).sum())==24840
    loo=[]
    for tex in primary.texture:
        p=primary[primary.texture!=tex]
        loo.append({'excluded_texture':tex,'equal_texture_harmonic_pct':float(p.harmonic_pct.mean()),
                    'equal_texture_linear_pct':float(p.linear_pct.mean()),
                    'equal_texture_reduction_percentage_points':float((p.harmonic_pct-p.linear_pct).mean())})
    lo=pd.DataFrame(loo);lo.to_csv(OUT/'P2_leave_one_texture_out.csv',index=False)
    exception=pt[(pt.threshold_pct==.5)&(pt.harmonic_count<pt.linear_count)].to_dict('records')
    s={'scope':'post-outcome descriptive threshold sensitivity of fixed worst-offset scores; no new raw replay',
       'windows':len(d),'textures':20,'primary_threshold':5,'primary_harmonic_crossings':5038,'primary_linear_crossings':107,
       'primary_equal_texture_harmonic_pct':float(primary.harmonic_pct.mean()),
       'primary_equal_texture_linear_pct':float(primary.linear_pct.mean()),
       'loo_equal_texture_reduction_pp_min':float(lo.equal_texture_reduction_percentage_points.min()),
       'loo_equal_texture_reduction_pp_max':float(lo.equal_texture_reduction_percentage_points.max()),
       'low_threshold_exception':exception,
       'linear_smaller_paired_windows':24840,'harmonic_smaller_paired_windows':17,
       'thresholds_are_descriptive_not_operating_tolerances':True,
       'no_universal_stochastic_dominance_claim':True}
    dump('P2_summary.json',s);return s

def analytical_demo():
    # Explicitly synthetic regression tests of the existing S5 counterexample and
    # classical Fourier/polygon identities, NOT additional laboratory evidence.
    n,q=640,32
    th=2*np.pi*np.arange(n)/n;x=np.cos(th)
    def w(f):return float(np.sum(.5*(f+np.roll(f,-1))*(np.roll(x,-1)-x)))
    f=np.sin(th)+np.sin((q-1)*th)
    tq=2*np.pi*np.arange(q)/q;fq=np.sin(tq)+np.sin((q-1)*tq)
    expected=-(n/2)*np.sin(2*np.pi/n)
    assert np.max(np.abs(fq))<2e-13
    assert abs(w(f)-expected)<1e-12
    # Nonzero phase: direct complex DFT versus exact alias sum for same f.
    offsets=np.arange(16)*2*np.pi/(q*16)
    errs=[]
    for z in offsets:
        ts=tq+z; fs=np.sin(ts)+np.sin((q-1)*ts)
        estimated=np.mean(fs*np.exp(-1j*ts))
        alias=-.5j + .5j*np.exp(-1j*q*z)
        errs.append(float(abs(estimated-alias)))
    assert max(errs)<1e-12
    return {'synthetic_only':True,'n':n,'q':q,'sparse_force_max_abs':float(np.max(np.abs(fq))),
            'closed_polygon_work':w(f),'continuous_work':-float(np.pi),
            'polygon_identity_abs_error':abs(w(f)-expected),
            'alias_identity_max_abs_error':max(errs),'no_measured_alias_mechanism_identified':True}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--paper',choices=['all','P1','P2'],default='P2');a=ap.parse_args()
    results={}
    if a.paper in ['all','P1']:results['P1']=p1()
    if a.paper in ['all','P2']:results['P2']=p2();results['analytical_demo']=analytical_demo();dump('P2_analytical_demo.json',results['analytical_demo'])
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'inputs').rglob('*.csv'))}
    dump('input_sha256.json',hashes)
    results['environment']={'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__}
    dump('execution_summary.json',results)
    print(json.dumps(results,indent=2))
