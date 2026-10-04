"""Presidio pilot: does a local AI detector find the injected PII?
Usage: python evidence/presidio_pilot.py --ledger data/pii_injections.jsonl \
       --texts data/variants.jsonl --n 1000

Adaptations to the brief's script (all disclosed in the summary):
  * load_raw_texts() reads variants.jsonl rows with mask_method == "raw" and the
    transformed_text field (the real schema), and asserts the text equals the ledger's raw_text.
  * Leak counts are reported for BOTH the brief's literal mask() and an overlap-merged mask,
    because the literal mask corrupts offsets when Presidio returns overlapping spans.
"""
import argparse, json, random, collections, os, sys
from presidio_analyzer import AnalyzerEngine

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sample_check import mask_literal, merge_spans  # noqa: E402

# project type -> Presidio entity types that count as a correct find
TYPE_MAP = {
    "PERSON": {"PERSON"},
    "EMAIL": {"EMAIL_ADDRESS"},
    "PHONE": {"PHONE_NUMBER"},
    "ADDRESS": {"LOCATION", "ADDRESS"},
}
METHODS = ("delete", "generic", "typed")


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def load_raw_texts(path):
    """Return {record_id: raw injected text} from variants.jsonl (mask_method == raw)."""
    out = {}
    for r in read_jsonl(path):
        if r.get("mask_method") == "raw":
            out[r["record_id"]] = r["transformed_text"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--texts", required=True)
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default="evidence/presidio_pilot.json")
    a = ap.parse_args()

    ledger = {r["record_id"]: r for r in read_jsonl(a.ledger)}
    texts = load_raw_texts(a.texts)
    ids = sorted(set(ledger) & set(texts))
    assert ids, "No overlapping record_ids: check field names"
    mismatch = [i for i in ids if ledger[i].get("raw_text") != texts[i]]
    assert not mismatch, f"raw variant text != ledger raw_text for {len(mismatch)} records"
    span_bad = [i for i in ids
                if texts[i][ledger[i]["start_char"]:ledger[i]["end_char"]] != ledger[i]["pii_value"]]
    assert not span_bad, f"ledger offsets do not match pii_value for {len(span_bad)} records"
    if not a.all:
        random.Random(553).shuffle(ids)
        ids = ids[: a.n]

    eng = AnalyzerEngine()
    tot = collections.Counter(); found = collections.Counter(); full = collections.Counter()
    leak_lit = collections.Counter(); leak_mrg = collections.Counter()
    overlap_records = 0
    misses = []
    for rid in ids:
        L, text = ledger[rid], texts[rid]
        s0, e0, typ, val = L["start_char"], L["end_char"], L["pii_type"], L["pii_value"]
        res = eng.analyze(text=text, language="en")
        matching = [r for r in res if r.entity_type in TYPE_MAP.get(typ, set()) and r.start < e0 and r.end > s0]
        covered = {i for r in matching for i in range(max(r.start, s0), min(r.end, e0))}
        tot[typ] += 1
        full[typ] += len(covered) == e0 - s0
        if matching:
            found[typ] += 1
        else:
            misses.append({"record_id": rid, "type": typ, "value": val, "text": text,
                           "detected": [(r.entity_type, r.start, r.end, round(r.score, 2)) for r in res]})
        spans3 = [(r.start, r.end, r.entity_type) for r in res]
        merged = merge_spans([(*s, r.score) for s, r in zip(spans3, res)])
        overlap_records += len(merged) != len(spans3)
        for m in METHODS:
            if val.lower() in mask_literal(text, spans3, m).lower():
                leak_lit[(typ, m)] += 1
            if val.lower() in mask_literal(text, merged, m).lower():
                leak_mrg[(typ, m)] += 1

    summary = {"records_checked": len(ids), "seed": 553, "records_with_overlapping_spans": overlap_records,
               "by_type": {}}
    for t in sorted(tot):
        summary["by_type"][t] = {
            "n": tot[t], "found": found[t],
            "detector_recall": round(found[t] / tot[t], 4),
            "found_full_span": full[t],
            "full_span_recall": round(full[t] / tot[t], 4),
            "value_still_present_after_literal_mask": {m: leak_lit[(t, m)] for m in METHODS},
            "value_still_present_after_merged_mask": {m: leak_mrg[(t, m)] for m in METHODS},
        }
    all_n, all_f = sum(tot.values()), sum(found.values())
    summary["overall_detector_recall"] = round(all_f / all_n, 4)
    json.dump({"summary": summary, "first_30_misses": misses[:30], "total_misses": len(misses)},
              open(a.out, "w", encoding="utf-8"), indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
