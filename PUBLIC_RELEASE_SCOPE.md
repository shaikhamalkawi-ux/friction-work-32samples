# H2 Lubricants: Sparse Force Sampling and Numerical Friction-Loop Work — Code and Derived Results

## Release status
Public repository source snapshot (not yet a GitHub Release or Zenodo record).

## Linked manuscript
Same 32 Force Samples, Different Work Errors: A 20-Texture Friction-Loop Study (pre-submission research manuscript; no journal DOI assigned).

## Evidence that can be reproduced
20 Hannover textures / 24,857 dependent windows in derived audit; S4, S8, S19 original-source portability test covers 3,751 windows. The 18-texture ablation excludes S7/S13; a new complete raw replay of all 20 textures is not claimed.

Run `python verify_release.py` for the original unchanged manifest, then `python tests/test_guards.py`; a derived-only check can be run as documented in README.md. Raw modes require the original source archives from the provider and will stop if required files are absent.

## Rights and provenance
The authors' original Python code is under MIT. Derived analytical ledgers have separate rights depending on their source. Read `DATA_AND_RIGHTS.md` and `RIGHTS_AND_CONTENT_MAP.md`. Third-party raw measurements are **not distributed**. The source providers remain: https://doi.org/10.25835/66r5bbkq (also referenced legacy Fantetti: https://doi.org/10.17632/gy587m7gx7.1).

## Citation metadata
`CITATION.cff` proposes the seven manuscript authors in publication order. It must be approved specifically for software credit and may require ORCIDs before publication. No Zenodo DOI is reserved or asserted.

## Other boundaries
This is an executable software/data provenance package, not a new scientific validation, independent sensor calibration, source-independent method guarantee or representation that the paper was accepted or published.
