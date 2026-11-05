#!/usr/bin/env python3
"""Fail-closed CLI and comparison guards. No measured data or fake science results."""
from pathlib import Path
import importlib.util, json, subprocess, sys, tempfile, unittest, zipfile
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source_pipeline'))
from compare import compare_frames

class Guards(unittest.TestCase):
    def fail_command(self, extra, cwd=None, python_options=()):
        p=subprocess.run([sys.executable,*python_options,str(ROOT/'reproduce.py'),*extra],capture_output=True,text=True,cwd=cwd)
        self.assertNotEqual(p.returncode,0,p.stdout)
        self.assertNotIn('SOURCE_TO_ARTS_RESULT_PASS',p.stdout)
        self.assertNotIn('FULL20_PRIMARY_RAW_PASS',p.stdout)
        self.assertNotIn('EXPLICIT_RAW_SUBSET_PASS',p.stdout)
        return p
    def test_numerical_mismatch_is_rejected(self):
        with self.assertRaises(ValueError): compare_frames(pd.DataFrame({'x':[1.0]}),pd.DataFrame({'x':[2.0]}),atol=0,rtol=0)
    def test_boolean_mismatch_is_rejected(self):
        with self.assertRaises(ValueError): compare_frames(pd.DataFrame({'x':[True]}),pd.DataFrame({'x':[False]}))
    def test_column_mismatch_is_rejected(self):
        with self.assertRaises(ValueError): compare_frames(pd.DataFrame({'x':[1]}),pd.DataFrame({'y':[1]}))
    def test_missingness_mismatch_is_rejected(self):
        with self.assertRaises(ValueError): compare_frames(pd.DataFrame({'x':[np.nan,1.0]}),pd.DataFrame({'x':[0.0,1.0]}))
    def test_exact_comparison_pass(self):
        a=pd.DataFrame({'x':[1.0,2.0],'b':[True,False],'id':['one','two']})
        result=compare_frames(a,a.copy(),rtol=0,atol=0)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['rows'],2)
    def test_missing_raw_input_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fail_command(['--mode','raw','--out',str(Path(d)/'run')])
            self.assertIn('FAIL:',p.stderr)
            self.assertFalse((Path(d)/'run/REPLAY_QA.json').exists())
    def test_existing_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'run';out.mkdir();(out/'keep.txt').write_text('keep')
            self.fail_command(['--mode','derived','--out',str(out)])
            self.assertEqual((out/'keep.txt').read_text(),'keep')
    def test_disabled_assertions_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            self.fail_command(['--mode','derived','--out',str(Path(d)/'run')],python_options=['-O'])

    def test_missing_selected_texture_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fail_command(['--mode','raw','--source-dir',d,'--textures','S7','--out',str(Path(d)/'run')])
            self.assertIn('required raw archive missing',p.stderr)
    def test_source_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'fn20-0x20-0f20-s4.zip').write_bytes(b'untrusted bytes')
            p=self.fail_command(['--mode','raw','--source-dir',d,'--textures','S4','--out',str(Path(d)/'run')])
            self.assertIn('source ZIP hash mismatch',p.stderr)
    def test_duplicate_selection_rejected(self):
        with tempfile.TemporaryDirectory() as d:self.fail_command(['--mode','raw','--source-dir',d,'--textures','S4,S4','--out',str(Path(d)/'run')])
    def test_out_of_scope_selection_rejected(self):
        with tempfile.TemporaryDirectory() as d:self.fail_command(['--mode','raw','--source-dir',d,'--textures','S24','--out',str(Path(d)/'run')])
    def test_derived_mode_cannot_impersonate_raw_subset(self):
        with tempfile.TemporaryDirectory() as d:self.fail_command(['--mode','derived','--textures','S4','--out',str(Path(d)/'run')])
    def test_derived_mode_cannot_claim_raw_diagnostics(self):
        with tempfile.TemporaryDirectory() as d:self.fail_command(['--mode','derived','--diagnostics','--out',str(Path(d)/'run')])

if __name__=='__main__':unittest.main(verbosity=2)
