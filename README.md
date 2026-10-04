# PrivacyGuard

PrivacyGuard is the S553 Milestone 2 project for a controlled study of how PII sanitization affects downstream intent classification.

## Code

- `prepare_data.py` — downloads and verifies BANKING77, profiles the data, applies duplicate/overlap controls, generates synthetic PII with Faker 37.12.0 using seed 553, and creates the raw/delete/generic/typed variants and evidence files.
- `verify_evidence.py` — verifies an existing generated evidence package, including hashes, row counts, joins, removal checks, eligibility logic, sample values, and human-review coverage.
- `requirements.txt` — pinned Python dependencies.

## Reproduce and verify the evidence

The repository includes the frozen data/evidence snapshot used by the M2 presentation.

```bash
python -m pip install -r requirements.txt
python prepare_data.py --download
python verify_evidence.py
```

`prepare_data.py` rebuilds the machine-generated evidence from the verified BANKING77 source files using Faker 37.12.0 and seed 553. It writes the deterministic pre-review sheet to `data/human_review_24.pre_review.csv` and deliberately does **not** overwrite the completed human-reviewed artifact `data/human_review_24.csv`.

`verify_evidence.py` checks the frozen source hashes, joins, counts, sanitization outputs, eligibility logic, the completed 24-record human review, and hashes recorded in `data/source_manifest.json`.

## Project documentation

Supporting audit/crosswalk material is in `docs/`.

## Data sources

- BANKING77 (PolyAI), CC BY 4.0: public banking intent-classification dataset.
- Faker, MIT license: used locally to generate synthetic PERSON, EMAIL, PHONE, and ADDRESS values.

No real customer or employer PII is used by the project.