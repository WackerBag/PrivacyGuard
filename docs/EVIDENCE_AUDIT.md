# PrivacyGuard M2 evidence audit

Audit target: `Morris_Carson_M2-Data.pptx` (latest v2 content).

## Result

**PASS.** Every local evidence file explicitly named in the presentation exists in this package:

- `data/source_manifest.json`
- `data/profile.json`
- `data/eligibility.jsonl`
- `data/variants.jsonl`
- `prepare_data.py`

The other local artifacts described by the slides also exist: `data/train.csv`, `data/test.csv`, `data/banking_records.jsonl`, `data/pii_injections.jsonl`, and the 24-record human-gate evidence.

## Verified facts

- BANKING77 raw source: 10,003 train + 3,080 test = 13,083 rows; 77 intent labels.
- Raw file sizes and SHA-256 values match the presentation.
- Faker evidence records version 37.12.0, locale `en_US`, seed 553, and October 3, 2026 generation date.
- Exactly 13,083 injection records and 52,332 text variants exist.
- Exactly 39,249 sanitized variants exist, and all pass the exact known-injected-value absence check.
- Training eligibility is 9,992 records: 7 train/test overlaps + 4 later normalized training duplicates are excluded; all 3,080 official test records are retained.
- The planned M3 modeling inventory is 52,288 text versions: (9,992 + 3,080) × 4.
- The presentation sample `B77_train_00005` exactly matches the stored injection and all four stored variants.
- The human-gate evidence contains 24 unique training records, with 3 records in each of 8 cells (4 PII types × 2 placements). Sign-off remains pending for M3, matching the deck.

## Integrity note

The synthetic values in this package were not regenerated with a different Faker release. They are the stored outputs from the pinned Faker 37.12.0 run used by the project. `prepare_data.py` and `requirements.txt` preserve that exact dependency requirement. `verify_evidence.py` independently audits the stored evidence and does not depend on Faker.