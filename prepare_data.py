#!/usr/bin/env python3
"""Rebuild the PrivacyGuard Milestone 2 evidence from the official BANKING77 CSVs.

This is the reproducibility script for the October 3, 2026 M2 snapshot.
It intentionally refuses to run with a different Faker version because generated
PII values would change and would no longer match the submitted evidence.

Usage:
    python prepare_data.py
    python prepare_data.py --download   # re-download raw BANKING77 first, hash-checked
"""
import csv
import hashlib
import io
import json
import random
import re
import sys
import unicodedata
import urllib.request
import collections
from pathlib import Path

import faker
from faker import Faker

ROOT = Path(__file__).resolve().parent
D = ROOT / "data"
D.mkdir(exist_ok=True)

URL = "https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/"
EXPECTED = {
    "train.csv": {
        "sha256": "b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b",
        "bytes": 839073,
        "rows": 10003,
    },
    "test.csv": {
        "sha256": "d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d",
        "bytes": 239961,
        "rows": 3080,
    },
}
SEED = 553
DATE = "2026-10-03"
EXPECTED_FAKER_VERSION = "37.12.0"
TYPES = ["PERSON", "EMAIL", "PHONE", "ADDRESS"]
PLACEMENTS = ["prefix", "suffix"]


def norm(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def write_jsonl(name, rows):
    with (D / name).open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(name, obj):
    (D / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_review_csv(path, chosen_ids, spans, variants, records):
    span_by_id = {s["record_id"]: s for s in spans}
    rec_by_id = {r["record_id"]: r for r in records}
    variants_by_id = collections.defaultdict(dict)
    for v in variants:
        variants_by_id[v["record_id"]][v["mask_method"]] = v["transformed_text"]
    fields = [
        "record_id", "category", "pii_type", "placement", "source_text",
        "raw", "delete", "generic", "typed", "review_status"
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for rid in chosen_ids:
            s, r, vv = span_by_id[rid], rec_by_id[rid], variants_by_id[rid]
            w.writerow({
                "record_id": rid,
                "category": r["category"],
                "pii_type": s["pii_type"],
                "placement": s["template_id"],
                "source_text": r["text"],
                "raw": vv["raw"],
                "delete": vv["delete"],
                "generic": vv["generic"],
                "typed": vv["typed"],
                "review_status": "PENDING_M3_SIGNOFF",
            })


def main():
    if faker.VERSION != EXPECTED_FAKER_VERSION:
        raise SystemExit(
            f"Faker version mismatch: found {faker.VERSION}; expected {EXPECTED_FAKER_VERSION}. "
            "Install requirements.txt before rebuilding this snapshot."
        )

    if "--download" in sys.argv:
        for name, spec in EXPECTED.items():
            data = urllib.request.urlopen(URL + name, timeout=60).read()
            if len(data) != spec["bytes"] or sha256_bytes(data) != spec["sha256"]:
                raise RuntimeError(f"Source changed for {name}; review before replacing the frozen snapshot.")
            (D / name).write_bytes(data)

    fake = Faker("en_US")
    fake.seed_instance(SEED)
    rng = random.Random(SEED)

    records, spans, variants = [], [], []
    report = {}
    source_rows = {}
    type_counts = collections.Counter()

    for split in ["train", "test"]:
        name = split + ".csv"
        spec = EXPECTED[name]
        data = (D / name).read_bytes()
        if len(data) != spec["bytes"] or sha256_bytes(data) != spec["sha256"]:
            raise RuntimeError(f"Raw source verification failed for {name}.")
        rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
        if len(rows) != spec["rows"]:
            raise RuntimeError(f"Unexpected row count for {name}: {len(rows)}")
        if list(rows[0].keys()) != ["text", "category"]:
            raise RuntimeError(f"Unexpected columns in {name}: {list(rows[0].keys())}")

        counts = collections.Counter(r["category"] for r in rows)
        report[split] = {
            "rows": len(rows),
            "classes": len(counts),
            "class_min": min(counts.values()),
            "class_max": max(counts.values()),
            "blank_text": sum(not r["text"].strip() for r in rows),
            "blank_label": sum(not r["category"].strip() for r in rows),
            "exact_duplicate_texts": len(rows) - len({r["text"] for r in rows}),
            "normalized_duplicate_texts": len(rows) - len({norm(r["text"]).casefold() for r in rows}),
            "min_chars": min(len(r["text"]) for r in rows),
            "max_chars": max(len(r["text"]) for r in rows),
        }
        source_rows[split] = len(rows)

        for i, row in enumerate(rows):
            rid = f"B77_{split}_{i:05d}"
            t = norm(row["text"])
            h = hashlib.sha256(t.casefold().encode()).hexdigest()
            rec = {
                "record_id": rid,
                "text": row["text"],
                "category": row["category"],
                "split": split,
                "source_row": i,
                "language": "en",
                "source_file": name,
                "acquired_date": DATE,
                "text_sha256": h,
                "char_count": len(t),
            }
            records.append(rec)

            typ = rng.choice(TYPES)
            template = rng.choice(PLACEMENTS)
            type_counts[typ] += 1
            if typ == "PERSON":
                value = fake.name(); context = "My name is "
            elif typ == "EMAIL":
                value = fake.user_name() + "@example.com"; context = "My email is "
            elif typ == "PHONE":
                value = fake.numerify("202-555-01##"); context = "My phone is "
            else:
                value = norm(fake.address()); context = "My address is "
            assert value.casefold() not in t.casefold()
            contact = context + value + "."
            raw = (contact + " " + t) if template == "prefix" else (t + " " + contact)
            start = raw.index(value); end = start + len(value)
            span = {
                "record_id": rid,
                "pii_type": typ,
                "pii_value": value,
                "start_char": start,
                "end_char": end,
                "template_id": template,
                "locale": "en_US",
                "seed": SEED,
                "faker_version": faker.VERSION,
                "generated_date": DATE,
                "raw_text": raw,
                "is_synthetic": True,
            }
            spans.append(span)
            assert raw[start:end] == value

            for method in ["raw", "delete", "generic", "typed"]:
                rep = {"delete": "", "generic": "[REDACTED]", "typed": "[" + typ + "]"}.get(method)
                out = raw if method == "raw" else norm(raw[:start] + rep + raw[end:])
                passed = None if method == "raw" else value.casefold() not in out.casefold()
                assert method == "raw" or passed
                variants.append({
                    "record_id": rid,
                    "split": split,
                    "category": row["category"],
                    "mask_method": method,
                    "transformed_text": out,
                    "removal_pass": passed,
                })

    train_hashes = {r["text_sha256"] for r in records if r["split"] == "train"}
    test_hashes = {r["text_sha256"] for r in records if r["split"] == "test"}
    report.update({
        "cross_split_normalized_overlap": len(train_hashes & test_hashes),
        "total_records": len(records),
        "total_spans": len(spans),
        "total_variants": len(variants),
        "sanitized_variants": sum(v["mask_method"] != "raw" for v in variants),
        "failed_removals": sum(v["removal_pass"] is False for v in variants),
        "type_counts": dict(type_counts),
        "faker_version": faker.VERSION,
        "seed": SEED,
        "date": DATE,
        "normalization_changed_rows": sum(r["text"] != norm(r["text"]) for r in records),
        "unique_ids": len({r["record_id"] for r in records}),
        "join_orphans": len({s["record_id"] for s in spans} - {r["record_id"] for r in records}),
        "human_review": "pending student sign-off before M3 model runs",
    })
    if len({(v["record_id"], v["mask_method"]) for v in variants}) != len(variants):
        raise RuntimeError("Duplicate record/method combination in variants.")

    # Modeling eligibility: preserve official test; exclude train/test overlap and later train duplicates.
    byhash = collections.defaultdict(list)
    for r in records:
        if r["split"] == "train":
            byhash[r["text_sha256"]].append(r)
    conflicts = {h for h, rs in byhash.items() if len({r["category"] for r in rs}) > 1}
    seen, eligibility = set(), []
    for r in records:
        h = r["text_sha256"]
        reason = "keep"
        if r["split"] == "train":
            if h in test_hashes: reason = "train_test_overlap"
            elif h in conflicts: reason = "conflicting_train_labels"
            elif h in seen: reason = "duplicate_train_text"
            seen.add(h)
        eligibility.append({
            "record_id": r["record_id"], "split": r["split"],
            "eligible": reason == "keep", "reason": reason
        })
    report["train_eligible"] = sum(x["eligible"] and x["split"] == "train" for x in eligibility)
    report["exclusion_reasons"] = dict(collections.Counter(x["reason"] for x in eligibility if not x["eligible"]))
    report["conflicting_train_text_groups"] = len(conflicts)
    report["test_retained"] = sum(x["split"] == "test" for x in eligibility)

    # Deterministic 24-record human-gate set: 3 examples for each type x placement cell.
    chosen = []
    review_rng = random.Random(SEED)
    for typ in TYPES:
        for template in PLACEMENTS:
            candidates = [
                s["record_id"] for s in spans
                if s["pii_type"] == typ and s["template_id"] == template and s["record_id"].startswith("B77_train_")
            ]
            chosen += review_rng.sample(candidates, 3)

    write_jsonl("banking_records.jsonl", records)
    write_jsonl("pii_injections.jsonl", spans)
    write_jsonl("variants.jsonl", variants)
    write_jsonl("eligibility.jsonl", eligibility)
    write_jsonl("review_samples.jsonl", [v for v in variants if v["record_id"] in chosen])
    write_json("profile.json", report)
    # Machine-generated review sheet. The approved human-review artifact is kept
    # separately so reproducible reruns never overwrite a completed review.
    write_review_csv(D / "human_review_24.pre_review.csv", chosen, spans, variants, records)

    sample_id = "B77_train_00005"
    sample_span = next(s for s in spans if s["record_id"] == sample_id)
    sample_record = next(r for r in records if r["record_id"] == sample_id)
    sample_variants = [v for v in variants if v["record_id"] == sample_id]
    summary = {
        "snapshot_date": DATE,
        "source_rows": len(records),
        "train_rows": source_rows["train"],
        "test_rows": source_rows["test"],
        "intent_classes": len({r["category"] for r in records}),
        "injection_rows": len(spans),
        "variant_rows": len(variants),
        "sanitized_rows": report["sanitized_variants"],
        "sanitized_known_value_absence_passed": report["sanitized_variants"] - report["failed_removals"],
        "eligible_train_rows": report["train_eligible"],
        "official_test_rows": report["test_retained"],
        "modeling_version_rows": (report["train_eligible"] + report["test_retained"]) * 4,
        "human_review_records": len(chosen),
        "sample_record": {
            "record_id": sample_id,
            "category": sample_record["category"],
            "source_text": sample_record["text"],
            "injection": sample_span,
            "variants": sample_variants,
        },
    }
    write_json("evidence_summary.json", summary)

    # Rich manifest records the frozen source, generator settings, and derived hashes.
    manifest = {
        "project": "PrivacyGuard",
        "milestone": 2,
        "snapshot_date": DATE,
        "generator": {
            "library": "Faker", "version": faker.VERSION, "locale": "en_US", "seed": SEED,
            "pii_types": TYPES, "placements": PLACEMENTS,
        },
        "banking77": {},
        "derived_files": {},
    }
    for split in ["train", "test"]:
        name = split + ".csv"; spec = EXPECTED[name]; p = D / name
        manifest["banking77"][split] = {
            "source_url": URL + name,
            "local_file": "data/" + name,
            "bytes": p.stat().st_size,
            "sha256": sha256_bytes(p.read_bytes()),
            "rows": spec["rows"],
            "acquired_date": DATE,
        }
    derived_names = [
        "banking_records.jsonl", "pii_injections.jsonl", "variants.jsonl", "eligibility.jsonl",
        "profile.json", "review_samples.jsonl", "human_review_24.pre_review.csv", "evidence_summary.json"
    ]
    # If the human review has been completed, include that immutable reviewed
    # artifact in the manifest without regenerating or modifying it.
    if (D / "human_review_24.csv").exists():
        derived_names.append("human_review_24.csv")
    for name in derived_names:
        p = D / name
        manifest["derived_files"][name] = {
            "bytes": p.stat().st_size,
            "sha256": sha256_bytes(p.read_bytes()),
        }
    write_json("source_manifest.json", manifest)

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()