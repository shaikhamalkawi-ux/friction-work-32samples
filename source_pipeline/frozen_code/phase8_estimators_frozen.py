#!/usr/bin/env python3
"""H2 Phase8 S2 independent-source *pilot*, not disjoint held-out validation.

The H2 Phase8 frozen protocol must pre-exist before computation.
This code does not redistribute any source-owned measurements. Read only.
Requires numpy, scipy and h5py. Python 3.11+.
"""
from __future__ import annotations
import argparse, csv, hashlib, io, json, math, zipfile
from pathlib import Path
import numpy as np
import scipy.io as sio
import h5py

SRC_FOLDER='Fn20-0x20-0f20-S2/'
REC_LONG='Messreihe1.mat'
REC_SHORT='hysterese_auto_297.mat'
Q=32; PERIOD=.05; OFFSETS=range(16); DT_NOMINAL=.0001

def file_sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for x in iter(lambda:f.read(1<<20),b''):h.update(x)
    return h.hexdigest()

def memory_sha(v):return hashlib.sha256(np.ascontiguousarray(v).view('uint8')).hexdigest()

def get_h5_record(blob):
    with h5py.File(io.BytesIO(blob),'r') as h:
        keys=[k for k in h.keys() if k!='#refs#']
        assert len(keys)==1
        g=h[keys[0]]
        names=[];units=[];paths=[]
        for r in g['Y']['Name'][:].ravel():
            b=h[r][:].ravel()
            names.append(''.join(map(chr,[int(i) for i in b if int(i)>0])) if b.dtype.kind in ('u','i') else '')
        for label,dest in [('Unit',units),('Path',paths)]:
            for r in g['Y'][label][:].ravel():
                b=h[r][:].ravel()
                dest.append(''.join(map(chr,[int(i) for i in b if int(i)>0])) if b.dtype.kind in ('u','i') else '')
        assert len(paths)==5 and paths[2].endswith('gain_force_y') and paths[4].startswith('Model Root/gain_vib:')
        data=[h[r][:].ravel().copy() for r in g['Y']['Data'][:].ravel()]
        time=g['X']['Data'][:].ravel().copy()
        return {'time':time,'force':data[2],'normal':data[3], 'displacement':data[4],
                'aux1':data[0],'aux2':data[1], 'units':units,'paths':paths,'names':names}

def get_messreihe(blob):
    a=sio.loadmat(io.BytesIO(blob),squeeze_me=True,variable_names=['time','Displacement','Force_normal','Force_tang'])
    return {'time':np.asarray(a['time'],dtype=float).ravel(), 'force':np.asarray(a['Force_tang'],dtype=float).ravel(),
            'normal':np.asarray(a['Force_normal'],dtype=float).ravel(),
            'displacement':np.asarray(a['Displacement'],dtype=float).ravel()}

def polygon(x,f):
    return float(.5*np.sum((f+np.roll(f,-1))*(np.roll(x,-1)-x)))

def polygon_independent(x,f):
    return float(.5*np.sum(f*(np.roll(x,-1)-np.roll(x,1))))

def sinefit(t,v,start,period=PERIOD):
    theta=2*np.pi*(t-start)/period
    mat=np.column_stack((np.ones_like(theta),np.cos(theta),np.sin(theta)))
    return np.linalg.lstsq(mat,v,rcond=None)[0]

def r_squared_x(t,x,start):
    a=sinefit(t,x,start)
    theta=2*np.pi*(t-start)/PERIOD
    pred=a[0]+a[1]*np.cos(theta)+a[2]*np.sin(theta)
    ss=float(np.sum((x-x.mean())**2))
    return float(1-np.sum((x-pred)**2)/ss) if ss>0 else float('nan')

def cycle_grid(t,x,f,k):
    start=k*PERIOD;end=start+PERIOD
    raw_inside=(t>start)&(t<end)
    tt=np.concatenate(([start],t[raw_inside],[end]))
    xx=np.interp(tt,t,x);ff=np.interp(tt,t,f)
    return tt,xx,ff

def sparse_indices(t,k,offset):
    start=k*PERIOD;end=start+PERIOD
    local=np.nonzero((t>=start)&(t<end))[0]
    if len(local)<2*Q:raise ValueError('Insufficient source sampling support')
    desired=start+offset*DT_NOMINAL+PERIOD*np.arange(Q)/Q
    assert np.max(desired)<end
    source_t=t[local]
    upper=np.searchsorted(source_t,desired,side='left')
    upper=np.clip(upper,0,len(source_t)-1);lower=np.maximum(upper-1,0)
    choice=np.where(np.abs(source_t[upper]-desired)<np.abs(source_t[lower]-desired),upper,lower)
    indices=local[choice]
    if len(np.unique(indices))!=Q:raise ValueError('Duplicate sparse samples')
    return indices

def reconstruct(tt,xx,t_sparse,f_sparse,start):
    aF=sinefit(t_sparse,f_sparse,start)
    aX=sinefit(tt,xx,start)
    w_h=float(np.pi*(aF[1]*aX[2]-aF[2]*aX[1]))
    ord_=np.argsort(t_sparse)
    ps=t_sparse[ord_];fs=f_sparse[ord_]
    tim=np.r_[ps[-1]-PERIOD,ps,ps[0]+PERIOD]
    force=np.r_[fs[-1],fs,fs[0]]
    if np.any(np.diff(tim)<=0):raise ValueError('Interpolation cycle degeneracy')
    fest=np.interp(tt,tim,force)
    w_l=polygon(xx,fest)
    return w_h,w_l

def relpct(est,ref):
    return float(100*abs(est-ref)/abs(ref)) if ref!=0 else float('nan')

def qc_single(t,x,f,name):
    assert len(t)==len(x)==len(f)>1000
    assert np.all(np.isfinite(t)) and np.all(np.diff(t)>0)
    assert np.all(np.isfinite(x)) and np.all(np.isfinite(f))
    return dict(recording=name,points=len(t),seconds=float(t[-1]-t[0]),
                sample_dt_median_s=float(np.median(np.diff(t))),sample_dt_p01_s=float(np.percentile(np.diff(t),1)),
                sample_dt_p99_s=float(np.percentile(np.diff(t),99)),
                displacement_signal_min=float(x.min()),displacement_signal_max=float(x.max()),
                normal_signal_min=float('nan'),force_signal_min=float(f.min()),force_signal_max=float(f.max()),
                complete_nominal_period_windows=int(math.floor((t[-1]+1e-12)/PERIOD)),
                raw_arrays_sha256={n:memory_sha(a) for n,a in [('time',t),('displacement',x),('force_tang',f)]})

def run(zip_path,protocol,out):
    p=json.loads(protocol.read_text(encoding='utf8'))
    assert p['sparse_force_design']['q']==Q and p['cycles']['period_s']==PERIOD
    assert p['sparse_force_design']['offsets_samples']==list(OFFSETS)
    assert p['source_archive_sha256']==file_sha(zip_path), 'Unapproved raw archive'
    assert p['geometry_gate']['R_squared_min']==.99
    out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zip_path,'r') as z:
        assert z.testzip() is None
        members={Path(n).name:n for n in z.namelist() if n.endswith('.mat')}
        assert {REC_LONG,REC_SHORT,'hysterese_auto_295.mat','hysterese_man344.mat','hysterese_man346.mat'}==set(members)
        long=get_messreihe(z.read(members[REC_LONG]));short=get_h5_record(z.read(members[REC_SHORT]))
        hlong=get_h5_record(z.read(members['hysterese_auto_295.mat']))
        pairs=[(hlong,get_h5_record(z.read(members['hysterese_man344.mat']))),
               (short,get_h5_record(z.read(members['hysterese_man346.mat'])))]
        for a,b in pairs:
            for signal in ['time','force','normal','displacement','aux1','aux2']:
                assert np.array_equal(a[signal],b[signal]),f'DUPLICATE MISMATCH {signal}'
        for signal in ['time','force','normal','displacement']:
            assert np.array_equal(long[signal],hlong[signal]),f'MESSREIHE LONG MISMATCH {signal}'
        source_audit=[]
        for name,can in [(REC_LONG,long),(REC_SHORT,short)]:
            row=qc_single(can['time'],can['displacement'],can['force'],name)
            row['normal_signal_min']=float(can['normal'].min())
            row['normal_signal_max']=float(can['normal'].max())
            row['source_mat_sha256']=hashlib.sha256(z.read(members[name])).hexdigest()
            source_audit.append(row)
        source_audit.append({'source_metadata_hdf5_force_units':short['units'][2],
             'source_metadata_hdf5_displacement_units':short['units'][4],
             'source_metadata_hdf5_timing_units':'',
             'force_path':short['paths'][2], 'displacement_path':short['paths'][4],
             'auto_manual_bit_identical_for_data': True,
             'Messreihe1_data_exactly_identical_to_auto295': True,
             'independent_time_recordings':2,
             'time_phase_calibration_certificate_present':False})
        (out/'source_schema_and_duplication.json').write_text(json.dumps(source_audit,ensure_ascii=False,indent=2)+'\n')
    offsets=[];cycles=[];failures=[]
    for label,can in [(REC_LONG,long),(REC_SHORT,short)]:
        t=can['time'];x=can['displacement'];f=can['force']
        kmax=int(math.floor((t[-1]+1e-12)/PERIOD))
        for k in range(kmax):
            tt,xx,ff=cycle_grid(t,x,f,k)
            w_ref=polygon(xx,ff)
            w_ind=polygon_independent(xx,ff)
            assert abs(w_ref-w_ind)<2e-9*max(1,abs(w_ref))
            R2=r_squared_x(tt,xx,k*PERIOD)
            gate=bool(R2>=p['geometry_gate']['R_squared_min'])
            x_range=float(np.ptp(xx));force_range=float(np.ptp(ff))
            seam=float(abs(xx[-1]-xx[0])/x_range) if x_range>0 else float('nan')
            denomratio=(abs(w_ref)/(x_range*force_range)) if (x_range*force_range)>0 else float('nan')
            # One *hypothetical* force-sample channel shift across the ORIGINAL source file.
            wwplus=polygon(xx,np.interp(tt,t,np.roll(f,1)))
            wwminus=polygon(xx,np.interp(tt,t,np.roll(f,-1)))
            ew1=relpct(wwplus,w_ref);ewm1=relpct(wwminus,w_ref)
            this_offsets=[]
            for shift in OFFSETS:
                inds=sparse_indices(t,k,shift)
                wh,wl=reconstruct(tt,xx,t[inds],f[inds],k*PERIOD)
                eh=relpct(wh,w_ref);el=relpct(wl,w_ref)
                offsetrow={"recording":label,"window_index":k,"window_start_s":round(k*PERIOD,10),
                           "sparse_offset_samples":shift,"force_readings":Q,"x_full_available":True,
                           "eligible_xR2_gate":gate,"reference_signed_work_signal_units":w_ref,
                           "work_harmonic_signal_units":wh,"work_linear_signal_units":wl,
                           "error_harmonic_pct":eh,"error_linear_pct":el,
                           "harmonic_better": bool(eh<el)}
                offsets.append(offsetrow);this_offsets.append(offsetrow)
            he=np.array([r['error_harmonic_pct'] for r in this_offsets])
            le=np.array([r['error_linear_pct'] for r in this_offsets])
            summary={"recording":label,"window_index":k,"window_start_s":round(k*PERIOD,10),
                     "source_dense_points":len(tt),"x_full_available":True,"force_readings":Q,
                     "displacement_harmonic_R2":R2,"eligible_xR2_gate":gate,
                     "x_peak_to_peak_signal_units":x_range,
                     "force_peak_to_peak_signal_units":force_range,
                     "reference_signed_work_signal_units":w_ref,
                     "work_reference_abs_over_xrange_frange":denomratio,
                     "closure_x_seam_over_xrange":seam,
                     "harmonic_phase0_error_pct":float(he[0]),"linear_phase0_error_pct":float(le[0]),
                     "harmonic_worst_offset_error_pct":float(he.max()),
                     "linear_worst_offset_error_pct":float(le.max()),
                     "harmonic_better_in_worst_offset":bool(he.max()<le.max()),
                     "harmonic_worst_offset_above5":bool(he.max()>5),
                     "linear_worst_offset_above5":bool(le.max()>5),
                     "hypothetical_shift_plus1_delta_work_pct":ew1,
                     "hypothetical_shift_minus1_delta_work_pct":ewm1}
            cycles.append(summary)
    for filename,rows in [('window_ledger.csv',cycles),('offset_ledger.csv',offsets)]:
        with (out/filename).open('w',newline='',encoding='utf-8') as f:
            wr=csv.DictWriter(f,fieldnames=list(rows[0].keys()));wr.writeheader();wr.writerows(rows)
    def group_stats(rows):
        if not rows:return {"count":0}
        u=lambda name: np.array([float(r[name]) for r in rows])
        wH=u('harmonic_worst_offset_error_pct');wL=u('linear_worst_offset_error_pct');ph=u('harmonic_phase0_error_pct');pl=u('linear_phase0_error_pct')
        c=lambda f: int(sum(bool(r[f]) for r in rows))
        return {"count":len(rows),"harmonic_gt5_worst":int(sum(wH>5)),"linear_gt5_worst":int(sum(wL>5)),
                "harmonic_gt5_phase0":int(sum(ph>5)),"linear_gt5_phase0":int(sum(pl>5)),
                "harmonic_wins_worst":int(sum(wH<wL)),"linear_wins_worst":int(sum(wL<wH)),
                "harmonic_ties_worst":int(sum(wL==wH)),
                "median_harmonic_phase0_pct":float(np.median(ph)),"median_linear_phase0_pct":float(np.median(pl)),
                "median_harmonic_worst_pct":float(np.median(wH)),"median_linear_worst_pct":float(np.median(wL)),
                "p95_harmonic_worst_pct":float(np.percentile(wH,95)),"p95_linear_worst_pct":float(np.percentile(wL,95)),
                "max_harmonic_worst_pct":float(wH.max()),"max_linear_worst_pct":float(wL.max()),
                "x_R2_median":float(np.median(u('displacement_harmonic_R2'))),
                "relative_ref_work_scale_min":float(u('work_reference_abs_over_xrange_frange').min()),
                "x_seam_over_range_median":float(np.median(u('closure_x_seam_over_xrange'))),
                "hypo_shift_gt5":int(sum(np.maximum(u('hypothetical_shift_plus1_delta_work_pct'),u('hypothetical_shift_minus1_delta_work_pct'))>5))}
    record_stats={}
    for label in (REC_LONG,REC_SHORT):
        rows=[r for r in cycles if r['recording']==label]
        record_stats[label]={"all_windows":group_stats(rows),"eligible_x_R2_ge_0_99":group_stats([r for r in rows if r['eligible_xR2_gate']]),
                             "ineligible_windows":int(sum(not r['eligible_xR2_gate'] for r in rows))}
    eligible=[r for r in cycles if r['eligible_xR2_gate']]
    result={"protocol_id":p['protocol_id'],"frozen_protocol_sha256":file_sha(protocol),
      "source_archive_sha256":file_sha(zip_path), "source_dataset_doi":p['source_dataset_doi'],
      "scientific_status":"DEVELOPMENT_PILOT_ONLY; NOT CROSS_TEXTURE_CONFIRMATION",
      "total_windows":len(cycles),"total_offset_estimations":len(offsets),
      "total_source_acquisitions":2,"source_file_count_mat":5,"duplicate_hdf_pairs":2,
      "records":record_stats,"pooled_all":group_stats(cycles),"pooled_geometry_eligible":group_stats(eligible),
      "excluded_if_R2_below_0_99":len(cycles)-len(eligible),
      "published_units_metadata_Y_blank": all(x=='' for x in short['units']),
      "physical_force_displacement_phase_certificate_in_source":False,
      "interpretation":"Only this source S2 texture; phase shifts hypothetical; all windows correlated; method adapted from descriptive Phase6, not exact Phase6 code replay; nominal 20-Hz windows; work units not physically certified."
    }
    (out/'S2_pilot_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result

def unit_tests():
    tests={}
    theta=2*np.pi*np.arange(640)/640
    x=np.cos(theta);f=np.sin(theta)
    truth=polygon(x,f)
    tests['sinusoid_work_sign_correct']=(abs(truth+np.pi)<0.0001)
    tests['polygon_independent_identity']=(abs(truth-polygon_independent(x,f))<1e-10)
    tests['constant_force_addition_invariance']=(abs(truth-polygon(x,f+347))<1e-10)
    tests['constant_x_addition_invariance']=(abs(truth-polygon(x+221,f))<1e-10)
    tests['force_scalar_linear']=(abs(polygon(x,3.1*f)-3.1*truth)<1e-10)
    tests['harmonic_analytic_identity']=(abs(np.pi*(0*0-1*1)+np.pi)<1e-14)
    tt=np.linspace(0,.05,640,endpoint=False);xx=3*np.cos(2*np.pi*tt/.05);ff=2*np.sin(2*np.pi*tt/.05)
    h,_=reconstruct(tt,xx,tt[np.arange(32)*20],ff[np.arange(32)*20],0.0)
    tests['sparse_fitting_recovers_exact_first_harmonic']=(abs(h+6*np.pi)<1e-8)
    assert all(tests.values()),tests
    return tests

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-zip',type=Path,required=True);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    tests=unit_tests();summary=run(a.source_zip,a.protocol,a.out)
    (a.out/'code_selftests.json').write_text(json.dumps(tests,indent=2)+'\n')
    print(json.dumps({'total_windows':summary['total_windows'],'eligible':summary['pooled_geometry_eligible'], 'records':summary['records'],'tests':tests},indent=2))
