# Layered content and licensing

- `reproduce.py`, `source_pipeline/` H2-authored code and tests: MIT, subject to the original notices.
- `MR1_Derived_Audit/`: unchanged MR1 original-code notice and accompanying provenance.
- `source_pipeline/expected/` and the MR1 retained ledgers: source-derived numerical outputs, not raw measurements; preserve dataset attribution.
- Historical `Legacy_Companion_Unchanged.zip` is retained in the separate author-controlled release candidate, not duplicated in GitHub.
- No upstream raw measurement arrays, original source MAT/JSON files, private research correspondence, tokens or standalone font files are included.
- `verification/`: statements of completed software tests with explicit coverage, not independent experimental replication.
- Original dataset licences are not replaced by the code licence. Consult `DATA_AND_RIGHTS.md` and `OFFICIAL_SOURCES.md` for the retained source boundaries.

- `payload/` preserves the exact original derived-only CSV/ZIP bytes in reversible checksum-locked chunks. Run `python tools/restore_payload.py` before verification. It contains **no original laboratory measurement files**.
