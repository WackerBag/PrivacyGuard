#!/usr/bin/env python3
"""Audit the completed PrivacyGuard M2 evidence without requiring Faker."""
import csv, hashlib, json, re, unicodedata, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent
D = ROOT / "data"
EXPECTED = {
    "train.csv": (839073, "b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b", 10003),
    "test.csv": (239961, "d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d", 3080),
}
REQUIRED = [
    "train.csv", "test.csv", "banking_records.jsonl", "pii_injections.jsonl",
    "variants.jsonl", "eligibility.jsonl", "profile.json", "source_manifest.json",
    "review_samples.jsonl", "human_review_24.csv", "evidence_summary.json",
]

def norm(t):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", t)).strip()

def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read_jsonl(name):
    with (D/name).open(encoding="utf-8") as f:
        return [json.loads(x) for x in f]

def check(cond, msg):
    if not cond:
        raise AssertionError(msg)

def main():
    missing = [x for x in REQUIRED if not (D/x).exists()]
    check(not missing, "Missing required evidence files: " + ", ".join(missing))

    raw = {}
    for name, (nbytes, digest, nrows) in EXPECTED.items():
        p = D/name
        check(p.stat().st_size == nbytes, f"{name} byte count mismatch")
        check(sha256(p) == digest, f"{name} SHA-256 mismatch")
        with p.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        check(list(rows[0].keys()) == ["text", "category"], f"{name} schema mismatch")
        check(len(rows) == nrows, f"{name} row count mismatch")
        raw[name] = rows

    records = read_jsonl("banking_records.jsonl")
    spans = read_jsonl("pii_injections.jsonl")
    variants = read_jsonl("variants.jsonl")
    eligibility = read_jsonl("eligibility.jsonl")
    review = read_jsonl("review_samples.jsonl")
    profile = json.loads((D/"profile.json").read_text(encoding="utf-8"))
    summary = json.loads((D/"evidence_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((D/"source_manifest.json").read_text(encoding="utf-8"))

    check(len(records) == 13083, "banking_records count")
    check(len(spans) == 13083, "pii_injections count")
    check(len(variants) == 52332, "variants count")
    check(len(eligibility) == 13083, "eligibility count")
    check(len({r["record_id"] for r in records}) == 13083, "record IDs are not unique")
    check({r["record_id"] for r in records} == {s["record_id"] for s in spans}, "record/injection join mismatch")
    check(len({(v["record_id"], v["mask_method"]) for v in variants}) == 52332, "duplicate/missing variant key")
    check(set(v["mask_method"] for v in variants) == {"raw","delete","generic","typed"}, "variant methods mismatch")

    record_by_id = {r["record_id"]: r for r in records}
    span_by_id = {s["record_id"]: s for s in spans}
    variants_by_id = collections.defaultdict(dict)
    for v in variants:
        variants_by_id[v["record_id"]][v["mask_method"]] = v

    for s in spans:
        check(s["seed"] == 553, "seed mismatch")
        check(s["faker_version"] == "37.12.0", "Faker version mismatch")
        check(s["generated_date"] == "2026-10-03", "generation date mismatch")
        check(s["pii_type"] in {"PERSON","EMAIL","PHONE","ADDRESS"}, "PII type mismatch")
        check(s["template_id"] in {"prefix","suffix"}, "placement mismatch")
        check(s["raw_text"][s["start_char"]:s["end_char"]] == s["pii_value"], "recorded span mismatch")
        vv = variants_by_id[s["record_id"]]
        check(vv["raw"]["transformed_text"] == s["raw_text"], "raw variant mismatch")
        for method in ["delete","generic","typed"]:
            check(s["pii_value"].casefold() not in vv[method]["transformed_text"].casefold(), "known value remains after sanitization")
            check(vv[method]["removal_pass"] is True, "removal flag mismatch")

    train_recs = [r for r in records if r["split"] == "train"]
    test_recs = [r for r in records if r["split"] == "test"]
    check(len(train_recs) == 10003 and len(test_recs) == 3080, "split counts mismatch")
    check(len({r["category"] for r in records}) == 77, "intent class count mismatch")

    def stats(rows):
        counts = collections.Counter(r["category"] for r in rows)
        return {
            "rows": len(rows), "classes": len(counts), "class_min": min(counts.values()), "class_max": max(counts.values()),
            "blank_text": sum(not r["text"].strip() for r in rows), "blank_label": sum(not r["category"].strip() for r in rows),
            "exact_duplicate_texts": len(rows)-len({r["text"] for r in rows}),
            "normalized_duplicate_texts": len(rows)-len({norm(r["text"]).casefold() for r in rows}),
            "min_chars": min(len(r["text"]) for r in rows), "max_chars": max(len(r["text"]) for r in rows),
        }
    check(profile["train"] == stats(train_recs), "train profile mismatch")
    check(profile["test"] == stats(test_recs), "test profile mismatch")
    train_keys = {hashlib.sha256(norm(r["text"]).casefold().encode()).hexdigest() for r in train_recs}
    test_keys = {hashlib.sha256(norm(r["text"]).casefold().encode()).hexdigest() for r in test_recs}
    check(len(train_keys & test_keys) == 7 == profile["cross_split_normalized_overlap"], "cross-split overlap mismatch")
    check(sum(r["text"] != norm(r["text"]) for r in records) == 569 == profile["normalization_changed_rows"], "normalization-change count mismatch")

    reasons = collections.Counter(x["reason"] for x in eligibility if x["split"] == "train")
    check(reasons == {"keep":9992,"train_test_overlap":7,"duplicate_train_text":4}, f"eligibility mismatch: {reasons}")
    check(sum(x["eligible"] and x["split"] == "train" for x in eligibility) == 9992, "eligible train mismatch")
    check(sum(x["split"] == "test" and x["eligible"] for x in eligibility) == 3080, "test preservation mismatch")

    check(sum(v["mask_method"] != "raw" for v in variants) == 39249, "sanitized row count mismatch")
    check(sum(v["removal_pass"] is False for v in variants) == 0, "failed removals found")
    check((9992 + 3080) * 4 == 52288, "modeling version count mismatch")

    sample_id = "B77_train_00005"
    s = span_by_id[sample_id]
    check(record_by_id[sample_id]["category"] == "card_arrival", "sample category mismatch")
    check(s["pii_type"] == "EMAIL" and s["pii_value"] == "davisstephanie@example.com", "sample injection mismatch")
    expected_sample = {
        "raw": "When did you send me my new card? My email is davisstephanie@example.com.",
        "delete": "When did you send me my new card? My email is .",
        "generic": "When did you send me my new card? My email is [REDACTED].",
        "typed": "When did you send me my new card? My email is [EMAIL].",
    }
    for method, text in expected_sample.items():
        check(variants_by_id[sample_id][method]["transformed_text"] == text, f"sample {method} mismatch")

    review_ids = {r["record_id"] for r in review}
    check(len(review) == 96 and len(review_ids) == 24, "human-gate sample size mismatch")
    coverage = collections.Counter((span_by_id[rid]["pii_type"], span_by_id[rid]["template_id"]) for rid in review_ids)
    check(set(coverage.values()) == {3} and len(coverage) == 8, f"human-gate coverage mismatch: {coverage}")
    with (D/"human_review_24.csv").open(encoding="utf-8", newline="") as f:
        review_csv = list(csv.DictReader(f))
    check(len(review_csv) == 24, "human_review_24.csv row count mismatch")
    check({r["record_id"] for r in review_csv} == review_ids, "human_review_24.csv IDs mismatch")
    check(set(r["review_status"] for r in review_csv) == {"PENDING_M3_SIGNOFF"}, "human review status mismatch")

    check(summary["source_rows"] == 13083 and summary["variant_rows"] == 52332, "evidence summary mismatch")
    check(summary["sanitized_known_value_absence_passed"] == 39249, "evidence summary removal count mismatch")
    check(summary["modeling_version_rows"] == 52288, "evidence summary modeling count mismatch")
    check(summary["human_review_records"] == 24, "evidence summary review count mismatch")

    check(manifest["generator"]["seed"] == 553, "manifest seed mismatch")
    check(manifest["generator"]["version"] == "37.12.0", "manifest Faker version mismatch")
    for split, name in [("train","train.csv"),("test","test.csv")]:
        check(manifest["banking77"][split]["sha256"] == sha256(D/name), f"manifest hash mismatch: {name}")
    for name, meta in manifest["derived_files"].items():
        check((D/name).exists(), f"manifest-derived file missing: {name}")
        check(meta["sha256"] == sha256(D/name), f"derived hash mismatch: {name}")
        check(meta["bytes"] == (D/name).stat().st_size, f"derived byte count mismatch: {name}")

    print("VERIFIED: PrivacyGuard M2 evidence is internally consistent with the v2 presentation.")
    print("13,083 source rows | 13,083 injections | 52,332 variants | 39,249 sanitized passes")
    print("9,992 eligible train + 3,080 official test | 52,288 four-condition modeling rows")
    print("24 human-gate records | seed 553 | Faker 37.12.0 | 0 known-value removal failures")

if __name__ == "__main__":
    main()