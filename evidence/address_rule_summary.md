# Address rule re-run summary

Date run: 2026-10-04. All 13,083 records, seed 553, local only.

## Versions

presidio-analyzer 2.2.364, spaCy 3.8.16, en_core_web_lg 3.8.0 (from `evidence/versions.txt`); Python 3.11.3.

## Caveat: the rule is tuned to the synthetic data

`evidence/address_recognizer.py` is a regex written by looking at the Faker en_US address shapes in the ledger (street + city, ST ZIP, and military APO/FPO/DPO forms). It is tuned to this synthetic data and is **not** claimed to generalize to real-world addresses.

## Before vs after (all 13,083 records)

Before = Presidio default (`presidio_pilot_full.json`). After = Presidio + address rule (`presidio_pilot_full_address_rule.json`). "Found" = a matching-type span overlaps the injected value at all; "full" = matching-type spans cover the whole value. "Value left" = the complete injected value is still in the masked text (delete / generic / typed). The merged-mask and literal-mask numbers were identical in every cell, so one set is shown.

| Type | n | found before -> after | full span before -> after | value left before (del / gen / typed) | value left after (del / gen / typed) |
|---|---|---|---|---|---|
| ADDRESS | 3,351 | 1,125 -> 3,351 | 0 -> 3,347 | 912 / 912 / 912 | 0 / 0 / 0 |
| EMAIL | 3,161 | 3,161 -> 3,161 | 3,161 -> 3,161 | 0 / 0 / 0 | 0 / 0 / 0 |
| PERSON | 3,235 | 3,191 -> 3,191 | 3,101 -> 3,101 | 32 / 32 / 32 | 32 / 32 / 32 |
| PHONE | 3,336 | 3,336 -> 3,336 | 3,336 -> 3,336 | 0 / 0 / 0 | 0 / 0 / 0 |

Overall detector recall (found): **0.8265 before -> 0.9966 after** (10,813 -> 13,039 of 13,083). Records with overlapping spans rose from 3,428 to 5,859.

## Regex-only check (no Presidio, `evidence/address_rule_checks.py regex`)

On the 3,351 ADDRESS rows, run case-sensitively: 3,351 full, 0 partial, 0 none; 0 false positives on the 9,732 non-ADDRESS rows. This matches the sandbox result.

**This is not what the pipeline sees.** Presidio compiles custom patterns case-insensitively. Re-running the regex with those flags gives **3,347 full, 4 partial, 0 none, 0 false-positive rows**, which matches the pipeline exactly.

## The 4 partial addresses (real defect in the rule)

Under case-insensitivity, `[A-Z]{2}` also matches lowercase words, so on four records the rule matched earlier text in the sentence instead of the address. Example (B77_train_00578): the rule returned `1 in a transaction. My address is 93811` (15-54), reading "is" as the state. The rest of the address was covered only by small LOCATION / DATE_TIME fragments from spaCy.

| record_id | injected value | spans returned |
|---|---|---|
| B77_train_00578 | 93811 Dana Field Suite 003 Sellershaven, IA 21653 | ADDRESS 15-54; LOCATION 90-92; DATE_TIME 93-98 |
| B77_train_02348 | 07950 Morris Walks Suite 069 Hernandezville, MA 69599 | ADDRESS 55-77 |
| B77_train_02404 | 35054 Antonio Place West Victoria, NY 10939 | ADDRESS 31-53; LOCATION 68-81, 83-91 |
| B77_test_00793 | 59228 Choi Land Apt. 355 Feliciashire, SD 02831 | ADDRESS 36-59; DATE_TIME 54-59 |

These four are counted as "found" but not "full". The "value left" metric counts only the complete value still present, so it reports 0 for ADDRESS and does not show that part of each of these four addresses remains in the masked text. I did not change `address_recognizer.py` (the brief says not to rewrite it). A likely fix is to make the uppercase state match case-sensitive (e.g. an inline `(?-i:[A-Z]{2})`), then re-run.

## Remaining misses (44 total, all PERSON)

| record_id | type | injected value | spans returned |
|---|---|---|---|
| B77_test_00540 | PERSON | Alison Simmons | nothing |
| B77_test_00920 | PERSON | Bianca Stuart | nothing |
| B77_test_00980 | PERSON | Tiffany Ruiz | nothing |
| B77_test_01525 | PERSON | Autumn Davidson | nothing |
| B77_test_01802 | PERSON | Morgan Jackson | nothing |

All 5 are in "My name is <name>." sentences. The rule does not affect PERSON, so these 44 are the same as before.

## False positives

Presidio + rule over the 9,732 non-ADDRESS records: **0** ADDRESS detections that do not overlap the injected span (`evidence/address_rule_fp.json`).

## What this does and does not show

Adding a regex tuned to Faker's address shapes lifts ADDRESS found from 33.6% to 100% and removes all complete addresses from masked text, but 4 addresses (0.12%) are only partly covered because of a case-sensitivity bug in the rule, and it says nothing about real-world addresses, other locales or other sentence templates.

## Commands

```powershell
.\.venv-presidio\Scripts\python.exe evidence\address_rule_checks.py regex
.\.venv-presidio\Scripts\python.exe evidence\address_rule_checks.py fp
.\.venv-presidio\Scripts\python.exe evidence\presidio_pilot_v2.py --ledger data\pii_injections.jsonl --texts data\variants.jsonl --all --address-rule --out evidence\presidio_pilot_full_address_rule.json
```
