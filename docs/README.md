# PrivacyGuard — Milestone 2 evidence package

This folder contains the local evidence behind `Morris_Carson_M2-Data.pptx`.
The data files are a frozen October 3, 2026 snapshot used by the presentation.

## Core evidence

- `data/train.csv`, `data/test.csv` — official BANKING77 source CSVs used by the project.
- `data/banking_records.jsonl` — stable record IDs plus source/provenance fields.
- `data/pii_injections.jsonl` — one synthetic PII insertion per query, including value, type, offsets, placement, seed, Faker version, and date.
- `data/variants.jsonl` — raw, delete, generic, and typed versions for each record.
- `data/eligibility.jsonl` — training eligibility after duplicate/overlap controls; official test is retained.
- `data/profile.json` — computed data-quality counts used on the M2 slides.
- `data/review_samples.jsonl` — four versions for the 24 records selected for the M3 human gate.
- `data/human_review_24.csv` — one row per human-gate record; status is intentionally `PENDING_M3_SIGNOFF` because the deck says sign-off occurs in M3.
- `data/evidence_summary.json` — compact verified totals and the exact sample shown in the presentation.
- `data/source_manifest.json` — raw-source URLs, byte counts, SHA-256 hashes, generator settings, and hashes of derived evidence files.

## Reproducibility

`prepare_data.py` contains the generation logic used for the snapshot. It is pinned to Faker 37.12.0, locale `en_US`, and seed 553. Install the exact dependencies from `requirements.txt` before rebuilding. The script refuses to run with another Faker version.

`verify_evidence.py` audits the existing evidence without Faker. Run:

```bash
python verify_evidence.py
```

A successful run prints `VERIFIED`-style summary lines and confirms the slide-level counts, joins, hashes, eligibility logic, sample values, removal checks, and 24-record human-gate coverage.

## Submission

The M2 rubric calls for a single PowerPoint submission. This evidence package is supporting material for reproducibility and M3; it is not an additional M2 submission unless the instructor specifically asks for it.
