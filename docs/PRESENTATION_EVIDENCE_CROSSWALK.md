# Presentation-to-evidence crosswalk

| Presentation claim / artifact | Evidence file(s) |
|---|---|
| 13,083 BANKING77 queries; 10,003 train; 3,080 test; 77 intents | `data/train.csv`, `data/test.csv`, `data/profile.json` |
| Raw source byte counts and SHA-256 values | `data/source_manifest.json`, raw CSVs |
| 13,083 synthetic PII insertions; PERSON/EMAIL/PHONE/ADDRESS; seed 553; Faker 37.12.0 | `data/pii_injections.jsonl`, `data/source_manifest.json` |
| 52,332 raw/delete/generic/typed text versions | `data/variants.jsonl`, `data/profile.json`, `data/evidence_summary.json` |
| 39,249 sanitized versions with zero known injected values remaining | `data/variants.jsonl`, `data/profile.json`, verified by `verify_evidence.py` |
| 4 normalized duplicate training rows, 1 normalized duplicate test row, 7 cross-split normalized texts | `data/profile.json`, recomputed by `verify_evidence.py` |
| 9,992 eligible training records after 7 overlap + 4 duplicate exclusions | `data/eligibility.jsonl`, `data/profile.json` |
| 52,288 versions in the planned M3 modeling set | `data/evidence_summary.json` = (9,992 + 3,080) × 4 |
| Sample `B77_train_00005`, `davisstephanie@example.com`, and its four conditions | `data/pii_injections.jsonl`, `data/variants.jsonl`, `data/evidence_summary.json` |
| 24-record human gate = 4 types × 2 placements × 3 | `data/human_review_24.csv`, `data/review_samples.jsonl` |
| Enriched metadata schema / join key | `data/banking_records.jsonl`, `data/pii_injections.jsonl` |
| Reproducible preparation logic | `prepare_data.py`, `requirements.txt` |