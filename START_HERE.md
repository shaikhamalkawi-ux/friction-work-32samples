# First steps — Lubricants H2 software

This source accompanies *Same 32 Force Samples, Different Work Errors: A 20-Texture Friction-Loop Study*.

## Reproduce checks with the derived numerical data included here

```bash
python -m venv .venv
source .venv/bin/activate # on Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python tools/restore_payload.py
python verify_release.py
python tests/test_guards.py
python reproduce.py --mode derived --out ../runs/derived
```

`DERIVED_ONLY_PASS` verifies derived output consistency. **It is not raw-source reproduction**. Do not use `-O` with Python. The 20 texture files in `MR1_Derived_Audit/inputs/P2/` are source-derived numerical summaries, not force/displacement measurements.

## Recompute from original measurements

Read [README.md](README.md), [OFFICIAL_SOURCES.md](OFFICIAL_SOURCES.md), [DATA_AND_RIGHTS.md](DATA_AND_RIGHTS.md) and [RESULT_TO_COMMAND.csv](RESULT_TO_COMMAND.csv). Acquire the original Hannover ZIPs from the publisher and verify each hash against `source_pipeline/SOURCE_REGISTER.csv`. Keep raw files outside the repo.

```bash
python reproduce.py --mode raw --source-dir ../Hannover_raw --out ../runs/raw
```

The default run requires all 20 original recordings. **S7/S13 have not been independently replayed outside the original Colab source execution**. Use `--textures S4,S8,S19` only for an explicit 3-texture diagnostic. Failed or missing inputs are errors, not replaced with saved scores.

The data license and software license differ. No journal DOI, Zenodo DOI, physical calibration, sensor saving or full instrument-level validation is claimed.
