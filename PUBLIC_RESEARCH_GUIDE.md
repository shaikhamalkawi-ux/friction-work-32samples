# Public reader guide — H2 Lubricants (2026)

**This GitHub repository is public.** Any researcher, including non-authors without a GitHub login, may view, clone and download the code and the distributable source-derived results. Only maintainers can push directly; others can fork and open pull requests.

The companion manuscript is *Same 32 Force Samples, Different Work Errors: A 20-Texture Friction-Loop Study* (pre-submission; no article DOI assigned).

## Download and run the public-derived check

```sh
git clone https://github.com/shaikhamalkawi-ux/friction-work-32samples.git
cd friction-work-32samples
python -m venv .venv
# Activate: source .venv/bin/activate (macOS/Linux)
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python public_quickcheck.py
```

This new convenience script restores the SHA-256-locked **derived-only** transport artifacts when necessary, verifies the original manifest, runs all negative-path/guard tests and recomputes the retained derived audit in a temporary directory. Successful completion prints `PUBLIC_DERIVED_CHECK_PASS`. It is **not a replay from new original instrument records**. Individual commands are in [START_HERE.md](START_HERE.md).

## What has and has not been verified?

| Scope | Frozen evidence | Scientific boundary |
| --- | --- | --- |
| Primary 20-texture comparison | Hannover S4–S23, **24,857 dependent windows**, 32 force readings, 16 offsets per window | Windows and offsets are not independent experimental laboratories |
| 5% descriptive threshold | First-harmonic: **5,038** worst-offset windows above threshold; periodic-linear: **107** | 5% is descriptive, not a metrological tolerance, sensor-saving target or universal recommendation |
| Three-texture raw portability check | Original S4/S8/S19 archive bytes, **3,751 windows**, exact checked agreement in the reported environment | Post-outcome software subset, not a fresh confirmatory study |
| Historical 18-texture diagnostic | Ablation/offset cohort excludes S7/S13 | Do not substitute retained derived scores for a new raw replay |
| S7/S13 and legacy Imperial/S2/S3 | Source identities / legacy context retained | Independent S7/S13 local raw replay and full earlier-cohort replay are not certified in MR2 |

The [frozen numerical summary](MR1_Derived_Audit/outputs/P2_summary.json), [raw-subset verification](verification/portable_P2_raw.json), [coverage matrix](RESULT_TO_COMMAND.csv) and [source register](source_pipeline/SOURCE_REGISTER.csv) document the exact evidence.

## Optional raw-source reproduction

Download original Hannover archives directly from the [LUIS source DOI](https://doi.org/10.25835/66r5bbkq), verify the hashes in the register, and keep the original ZIP/MAT files **outside** the repository. Only then run the `--mode raw` instructions in [README.md](README.md). The command fails if any required input is missing or differs from the registered identity; it does not invent or replace measurements.

## Rights, public reuse and citation

* The team's original software is MIT as explained in [DATA_AND_RIGHTS.md](DATA_AND_RIGHTS.md). Source-derived numerical ledgers retain original-provider attribution and separate conditions. The original Hannover data are CC BY 4.0 but are **not mirrored here**.
* [CITATION.cff](CITATION.cff) includes **provisional** software attribution until approved by the research team. Cite original data providers separately.
* **GitHub Release and Zenodo DOI have not been verified or issued for this code snapshot.** Zenodo is useful for a permanent, versioned software DOI, but not required to make code openly accessible on GitHub.
* Download a ZIP from GitHub's Code menu or use the clone command above. Anonymous read access does not mean anonymous write access.

This guide and public check runner are supplementary navigation; no scientific estimator, frozen result, source archive or manuscript is changed.
