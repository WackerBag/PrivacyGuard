# Presidio pilot summary

Date run: 2026-10-04

## 1. Versions

| Component | Version |
|---|---|
| presidio-analyzer | 2.2.364 |
| spaCy | 3.8.16 |
| spaCy model | en_core_web_lg 3.8.0 (the large model the brief requires; no smaller model used) |
| Python | 3.11.3 (venv built from the existing `torch` conda env's interpreter; the default Python 3.9 could not install current spaCy) |

Source: `evidence/versions.txt`.

## 2. Sample check (slide 12 sentence)

Text: `When did you send me my new card? My email is davisstephanie@example.com.`

| Entity | Start | End | Score | Matched text |
|---|---|---|---|---|
| EMAIL_ADDRESS | 46 | 72 | 1.00 | davisstephanie@example.com |
| URL | 61 | 72 | 0.50 | example.com |

Presidio found the EMAIL span at exactly 46-72 with score 1.00, matching the ledger. It also returned a second, overlapping URL span (61-72, score 0.50).

Masked outputs (overlapping spans merged first; typed uses the project's type name, as on slide 12):

- delete: `When did you send me my new card? My email is .`
- generic: `When did you send me my new card? My email is [REDACTED].`
- typed: `When did you send me my new card? My email is [EMAIL].`

Deviation from the brief: the brief's `mask()` applied literally to both overlapping spans drops the trailing period (e.g. `... My email is [REDACTED]`), because the second replacement uses offsets shifted by the first. Both versions are in `evidence/sample_check_output.txt`. Presidio can return overlapping spans, so slide wording should not imply a clean one-span-per-value result.

## 3. Dataset check

Schema confirmed first: the ledger has `record_id`, `pii_type`, `pii_value`, `start_char`, `end_char` plus `raw_text`; the raw text also appears in `variants.jsonl` as `mask_method == "raw"` / `transformed_text`. The script asserts these are identical for all 13,083 records and that each ledger offset slices to `pii_value`; both checks passed.

Definitions:
- **found**: Presidio returned an entity of a matching type that overlaps the injected span at all.
- **full span**: matching-type spans together cover every character of the injected value.
- **still present**: the complete injected value is still in the masked text, masking every span Presidio returned (overlaps merged). Partial leaks (e.g. only a zip code left) are not counted.

### 3a. All 13,083 records (primary result)

Overall detector recall (found): **0.8265** (10,813 of 13,083). 3,428 records had overlapping spans. Output: `evidence/presidio_pilot_full.json`.

| PII type | n | found | recall | full span | full-span recall | still present after delete / generic / typed |
|---|---|---|---|---|---|---|
| ADDRESS | 3,351 | 1,125 | 0.3357 | 0 | 0.0000 | 912 / 912 / 912 |
| EMAIL | 3,161 | 3,161 | 1.0000 | 3,161 | 1.0000 | 0 / 0 / 0 |
| PERSON | 3,235 | 3,191 | 0.9864 | 3,101 | 0.9586 | 32 / 32 / 32 |
| PHONE | 3,336 | 3,336 | 1.0000 | 3,336 | 1.0000 | 0 / 0 / 0 |

Total misses (not found): 2,270 (2,226 ADDRESS, 44 PERSON).

### 3b. Random sample of 1,000 (seed 553), run first

Overall recall 0.817 (817 of 1,000). Output: `evidence/presidio_pilot.json`.

| PII type | n | found | recall | full span | still present (each method) |
|---|---|---|---|---|---|
| ADDRESS | 263 | 85 | 0.3232 | 0 | 79 |
| EMAIL | 235 | 235 | 1.0000 | 235 | 0 |
| PERSON | 267 | 262 | 0.9813 | 256 | 3 |
| PHONE | 235 | 235 | 1.0000 | 235 | 0 |

The sample is close to the full run (overall 0.817 vs 0.8265).

## 4. Real misses

From the full run (`first_30_misses` were all ADDRESS) plus one PERSON miss from the 1,000-record sample:

| record_id | type | injected value | what Presidio returned |
|---|---|---|---|
| B77_test_00007 | ADDRESS | 318 James Fields Haileyville, ME 46827 | PERSON (46-70) only |
| B77_test_00029 | ADDRESS | Unit 5772 Box 4255 DPO AE 13176 | PERSON (19-27) + DATE_TIME (33-45); no address |
| B77_test_00032 | ADDRESS | 8494 Jeffrey Manors Marcusside, AL 30146 | DATE_TIME (14-44) only |
| B77_test_00033 | ADDRESS | 387 Fischer Summit South Stephanie, MA 10553 | nothing |
| B77_train_01652 | PERSON (sample) | Bryan Wood (in "My name is Bryan Wood.") | nothing |

## 5. What this shows and does not show

On all 13,083 synthetic Faker insertions in templated sentences, Presidio (en_core_web_lg) found every EMAIL and PHONE value, found 98.6% of PERSON values (95.9% fully), and found 33.6% of ADDRESS values but never covered a whole address with a matching-type span, so 912 full addresses survived masking with the detector's spans; this does not show how it performs on real customer text, other templates or locales, or partial leaks, and the match rule treats any overlap with the right type as "found".

## 6. Reproduce (PowerShell, from the PrivacyGuard folder)

```powershell
& "C:\Users\carso\anaconda3\envs\torch\python.exe" -m venv .venv-presidio
.\.venv-presidio\Scripts\python.exe -m pip install presidio-analyzer
.\.venv-presidio\Scripts\python.exe -m spacy download en_core_web_lg
.\.venv-presidio\Scripts\python.exe -m pip freeze | Select-String "presidio|spacy|en-core-web|en_core_web" | % { $_.Line } | Set-Content evidence\versions.txt
.\.venv-presidio\Scripts\python.exe evidence\sample_check.py
.\.venv-presidio\Scripts\python.exe evidence\presidio_pilot.py --ledger data\pii_injections.jsonl --texts data\variants.jsonl --n 1000
.\.venv-presidio\Scripts\python.exe evidence\presidio_pilot.py --ledger data\pii_injections.jsonl --texts data\variants.jsonl --all --out evidence\presidio_pilot_full.json
```
