#!/usr/bin/env python3
"""Source-to-window replay of Hannover primary scores and optional original diagnostics.

Raw mode requires every explicitly selected provider archive with the locked
ZIP and canonical MAT hashes. A missing archive is an error, never silently
replaced by a saved ledger. Default raw cohort is all 20 textures S4-S23.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, os, shutil, subprocess, sys, zipfile
from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'source_pipeline'))
from compare import sha256,compare_frames
ALL=tuple('S'+str(i) for i in range(4,24))
DIAGNOSTIC=tuple(t for t in ALL if t not in ('S7','S13'))

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=['raw','derived'],required=True)
    ap.add_argument('--source-dir',type=Path)
    ap.add_argument('--textures',default=','.join(ALL),help='Explicit subset for execution tests; defaults to all 20, without omissions')
    ap.add_argument('--diagnostics',action='store_true',help='Also replay the original 18-texture ablation/offset diagnostics for selected eligible textures')
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if sys.flags.optimize: raise ValueError('Frozen assertions require Python without -O')
    selected=[x.strip().upper() for x in args.textures.split(',') if x.strip()]
    if not selected or len(set(selected))!=len(selected) or not set(selected).issubset(ALL): raise ValueError('Invalid or duplicate texture selection')
    if args.mode=='derived' and (selected!=list(ALL) or args.diagnostics):raise ValueError('Derived mode audits all 20 saved ledgers; raw diagnostic options are not applicable')
    src=args.source_dir.resolve() if args.source_dir else None
    out=args.out.resolve()
    if out.exists() and any(out.iterdir()):raise FileExistsError('Output directory is nonempty; immutable inputs will not be overwritten')
    reg=pd.read_csv(HERE/'source_pipeline/SOURCE_REGISTER.csv').set_index('texture')
    frozen=HERE/'source_pipeline/Frozen_Primary_20Texture.zip'
    preflight=[]
    if args.mode=='raw':
        if src is None or not src.is_dir():raise FileNotFoundError('Raw mode needs a directory of original publisher ZIPs')
        for tex in selected:
            p=src/str(reg.loc[tex,'source_filename'])
            if not p.is_file(): raise FileNotFoundError(f'{tex}: required raw archive missing; no saved score substituted')
            if sha256(p)!=reg.loc[tex,'source_sha256']: raise ValueError(f'{tex}: source ZIP hash mismatch')
            with zipfile.ZipFile(p) as z:
                if z.testzip() is not None:raise ValueError(f'{tex}: CRC failure')
                names=[n for n in z.namelist() if Path(n).name=='Messreihe1.mat']
                if len(names)!=1 or hashlib.sha256(z.read(names[0])).hexdigest()!=reg.loc[tex,'canonical_mat_sha256']:raise ValueError(f'{tex}: canonical MAT identity mismatch')
            preflight.append({'texture':tex,'source_sha256':reg.loc[tex,'source_sha256'],'canonical_mat_sha256':reg.loc[tex,'canonical_mat_sha256']})
    out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    qa={'paper':'Lubricants','mode':args.mode,'primary_selected':selected,'source_identity':preflight,'full_20_raw_replay':False,'thresholds_are_descriptive':True}
    tables={}
    if args.mode=='raw':
        for tex in selected:
            dest=out/'primary'/tex
            result=subprocess.run([sys.executable,str(HERE/'source_pipeline/frozen_code/run_hannover_frozen_holdout.py'),'--source-zip',str(src/reg.loc[tex,'source_filename']),'--out',str(dest)],env=env,capture_output=True,text=True)
            (out/(tex+'.log')).write_text(result.stdout+'\n'+result.stderr)
            if result.returncode: raise RuntimeError(f'{tex}: scientific runner failed')
            with zipfile.ZipFile(frozen) as z:expected=pd.read_csv(io.BytesIO(z.read(f'derived/{tex}/{tex}_windows.csv')))
            actual=pd.read_csv(dest/f'{tex}_windows.csv')
            tables[tex]=compare_frames(expected,actual,rtol=1e-11,atol=1e-11)
        qa['primary_checks']=tables
        qa['primary_rows']=sum(t['rows'] for t in tables.values())
        qa['full_20_raw_replay']=set(selected)==set(ALL)
    # All-cohort derived audit, or raw-first audit only when every primary texture was replayed.
    if args.mode=='derived' or qa['full_20_raw_replay']:
        audit=out/'threshold_audit';audit.mkdir()
        shutil.copy2(HERE/'MR1_Derived_Audit/run_strengthening.py',audit)
        (audit/'inputs/P2').mkdir(parents=True)
        for tex in ALL:
            p=out/'primary'/tex/f'{tex}_windows.csv' if args.mode=='raw' else HERE/'MR1_Derived_Audit/inputs/P2'/f'{tex}_windows.csv'
            shutil.copy2(p,audit/'inputs/P2'/p.name)
        result=subprocess.run([sys.executable,str(audit/'run_strengthening.py'),'--paper','P2'],env=env,capture_output=True,text=True)
        (out/'threshold.log').write_text(result.stdout+'\n'+result.stderr)
        if result.returncode:raise RuntimeError('Threshold audit failed')
        qa['threshold_checks']={name:compare_frames(pd.read_csv(HERE/'MR1_Derived_Audit/outputs'/name),pd.read_csv(audit/'outputs'/name),rtol=1e-12,atol=1e-12) for name in ('P2_threshold_by_texture.csv','P2_threshold_sensitivity.csv','P2_leave_one_texture_out.csv')}
    else:
        qa['threshold_audit']='NOT RUN from a partial raw cohort; use --mode derived separately for the frozen full cohort'
    if args.diagnostics:
        ds=[t for t in selected if t in DIAGNOSTIC]
        if not ds:raise ValueError('No selected textures belong to the original 18-texture diagnostic cohort')
        qa['diagnostic_cohort']=ds
        for script,kind,filename,expected_name in [
          ('ablation_portable.py','ablation','R22B_18source_window_ablation.csv','R23_18texture_window_ablation.csv'),
          ('offset_portable.py','offset','R23B_18texture_offset_sensitivity_windows.csv','R24_18texture_window_offset.csv')]:
            dest=out/kind
            result=subprocess.run([sys.executable,str(HERE/'source_pipeline'/script),'--source-root',str(src),'--frozen-derived-zip',str(frozen),'--out',str(dest),'--textures',','.join(ds)],env=env,capture_output=True,text=True)
            (out/(kind+'.log')).write_text(result.stdout+'\n'+result.stderr)
            if result.returncode:raise RuntimeError(kind+' source replay failed')
            a=pd.read_csv(HERE/'source_pipeline/expected'/expected_name);a=a[a.texture.isin(ds)].reset_index(drop=True)
            b=pd.read_csv(dest/filename)
            qa[kind+'_checks']=compare_frames(a,b,rtol=1e-10,atol=1e-8)
    qa['status']=('FULL20_PRIMARY_RAW_PASS' if qa['full_20_raw_replay'] else 'EXPLICIT_RAW_SUBSET_PASS') if args.mode=='raw' else 'DERIVED_ONLY_PASS'
    qa['not_claimed']='A new independent laboratory, calibration certificate, or raw replay of earlier Imperial/S2/S3 cohorts'
    (out/'REPLAY_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2));return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,FileNotFoundError,FileExistsError,RuntimeError,zipfile.BadZipFile,KeyError) as exc:
        print('FAIL: '+str(exc),file=sys.stderr);raise SystemExit(2)
