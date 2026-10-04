# PrivacyGuard

PrivacyGuard is the S553 Milestone 2 project for a controlled study of how PII sanitization affects downstream intent classification.

## Code

- `prepare_data.py` — downloads and verifies BANKING77, profiles the data, applies duplicate/overlap controls, generates synthetic PII with Faker 37.12.0 using seed 553, and creates the raw/delete/generic/typed variants and evidence files.
- `verify_evidence.py` — verifies an existing generated evidence package, including hashes, row counts, joins, removal checks, eligibility logic, sample values, and human-review coverage.
- `requirements.txt` — pinned Python dependencies.

## Reproduce the evidence

```bash
python -m pip install -r requirements.txt
python prepare_data.py --acquired-date 2026-10-03 --generated-date 2026-10-03
python verify_evidence.py
```

Generated files are written under `data/` and are intentionally ignored by Git because they can be rebuilt from the verified public source files.

## Project documentation

Supporting audit/crosswalk material is in `docs/`.

## Data sources

- BANKING77 (PolyAI), CC BY 4.0: public banking intent-classification dataset.
- Faker, MIT license: used locally to generate synthetic PERSON, EMAIL, PHONE, and ADDRESS values.

No real customer or employer PII is used by the project.