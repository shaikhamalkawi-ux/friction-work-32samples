# P2_Lubricants: MR1 derived-only audit

## Run
Python 3.11 or newer is required by the pinned NumPy package. Tested here with Python 3.13.5, NumPy 2.3.5 and pandas 2.2.3.

```sh
python -m pip install -r requirements.txt
python verify_files.py
python run_strengthening.py --paper P2
```

Run commands in this directory. Paths are relative to this script, not the current working directory. No network, raw-signal archive, random draw or fitting step is required. The other paper's inputs are deliberately excluded.

## Scope
24,857 retained worst-offset window scores across 20 textures. Thresholds 0.5, 1, 2, 3, 5, 7.5 and 10% are post-outcome descriptive checks, not operational tolerances. The analytical demo is synthetic, not an experimental replay.

Input CSVs are byte copies of the frozen companion ledgers. The script validates row counts, record identifiers, required fields and established primary counts before producing descriptive output. The SHA-256 manifest pins the exact input bytes. Original source provenance and licensing conditions remain in `../Legacy_Companion_Unchanged.zip`.

The existing published-data creators retain credit and rights in their original measurements. No raw measurement files are distributed. The MIT permission below covers the new audit Python scripts only; it does not relicense third-party data, libraries, figures, manuscript text or the retained legacy companion.

The outputs are deterministic at the stated environment. Last-bit differences may arise under other numerical-library versions. New output files may be compared with the distributed release outputs; they are not a certificate of sensor calibration or source-to-result completeness.
