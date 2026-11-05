**First time here?** See [START_HERE.md](START_HERE.md) for commands and data boundaries.

# Lubricants MR2 — source-to-result computational companion

## Scope and boundary
This package accompanies *Same 32 Force Samples, Different Work Errors: A 20-Texture
Friction-Loop Study*. It preserves the MR1 results and exposes original scoring and
information-ablation/offset kernels behind an explicit portable command line.
The underlying scripts were present in nested historical archives; MR2 does not claim
that they were newly invented or wholly absent before this release.

Primary scope: Hannover S4–S23, q=32 force readings, 16 offsets, 0.05-s windows.
Diagnostic scope: the original 18-texture ablation/offset cohort (S7/S13 excluded).
Earlier Imperial and S2/S3 protocols are retained as historical context, not covered by
this primary entry point. See `RESULT_TO_COMMAND.csv`.

## Environment and verification
Use Python 3.11 or later in an isolated environment:

```sh
python -m pip install -r requirements.txt
python tools/restore_payload.py
python verify_release.py
python tests/test_guards.py
```

`environment_tested.json` records actual versions; version ranges are not a promise of
bitwise reproducibility on every system. Keep Python assertions enabled (do not use `-O`).
Expected outputs are immutable and every raw rerun is checked against them.

## Acquire original measurements
Provider: Matthias Wangenheim, LUIS V1, DOI https://doi.org/10.25835/66r5bbkq.
The provider describes constant 20-N normal load, 20-micrometre displacement amplitude
and 20-Hz frequency. Those metadata are not a new calibration of the stored channels.
Download the S4–S23 archives from that official dataset and place them in a local directory
outside the release. Use the exact lowercase filenames in `source_pipeline/SOURCE_REGISTER.csv`,
for example `fn20-0x20-0f20-s4.zip`; renaming a downloaded file is allowed, modifying its bytes is not.
The register contains SHA-256 identities for both each ZIP and its unique `Messreihe1.mat`.
A direct URL is recorded only where it was already verified; use the DOI resource listing
when that field is empty. No missing link, measurement or default value is fabricated.

## Full primary raw-source replay (requires all 20 files)

```sh
python reproduce.py --mode raw --source-dir ../local-Hannover --diagnostics --out ../runs/P2_all20
```

The default raw cohort requires S4–S23. It validates every selected archive before any
estimator executes and fails on a missing/mismatched source. It never substitutes saved scores.
All 20 regenerated primary ledgers then feed the threshold/texture-weighting audit.
With `--diagnostics`, the ablation/offset route covers only its original 18-texture cohort;
the report identifies that cohort explicitly. This command's availability is not a claim
that all 20 sources were independently re-executed in MR2.

## Explicit portability test subset

```sh
python reproduce.py --mode raw --source-dir ../local-Hannover --textures S4,S8,S19 --diagnostics --out ../runs/P2_subset
```

MR2 executed this subset from the original archive bytes: 1,265 + 1,223 + 1,263 = 3,751 windows.
All primary, ablation and offset fields matched their retained values exactly in the tested
environment. It reports `EXPLICIT_RAW_SUBSET_PASS`, not a full-20 or new-laboratory pass.
S4/S8/S19 were a post-outcome software execution subset, not a new confirmatory scientific cohort.
The subset run does not compute a misleading full-cohort threshold audit from three textures.

## Separately labelled full-cohort derived audit

```sh
python reproduce.py --mode derived --out ../runs/P2_derived
```

This mode reports `DERIVED_ONLY_PASS`, checks all 24,857 retained windows and reproduces
MR1 threshold/texture-weighting outputs, including the original 5% counts 5,038 versus 107.
It is not source reacquisition, instrument calibration or new empirical evidence.

## What remains unverified
Historical records document original Colab executions of all 20 textures, and independently
reacquired local raw replays of 18. S7 and S13 have not been independently rerun outside
that original route in this release. Their frozen outputs and source hashes are retained;
no synthetic or substituted sources are used. Complete raw replay of the earlier
Imperial/S2/S3 cohorts is also outside this runner.

## Code integrity and rights
`source_pipeline/frozen_code/` preserves the two original primary Python files byte for byte.
`PORTABILITY_PROVENANCE.json` records the original and portable diagnostic hashes.
Diagnostic numerical functions and loop bodies are unchanged; path/CLI/cohort-reporting
changes make execution explicit. `Frozen_Primary_20Texture.zip` contains derived scores
and original scripts, not original MAT/ZIP measurement archives.
Original H2 scripts retain MIT licensing; source-derived ledgers retain their attribution
and source-related licence obligations. Raw Hannover measurements are CC BY 4.0 but are
not redistributed in this release. No repository deposit or new DOI is claimed.
