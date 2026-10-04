"""Address-rule checks (Steps 1 and 3 of ADDRESS_RULE_AND_REVIEW_BRIEF).

  regex  : run the address regex alone (no Presidio) over every ledger row.
           ADDRESS rows -> full / partial / none; other rows -> false positives.
  fp     : run Presidio + the address rule over the NON-ADDRESS rows and count ADDRESS
           detections that do not overlap the injected span.
Usage: python evidence/address_rule_checks.py {regex|fp} [--out evidence/address_rule_<mode>.json]
"""
import argparse, collections, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from address_recognizer import COMBINED_RE, add_to  # noqa: E402


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def regex_check(rows):
    out = collections.Counter(); fp = collections.Counter(); examples = []
    for r in rows:
        s0, e0, text = r["start_char"], r["end_char"], r["raw_text"]
        ms = [(m.start(), m.end()) for m in COMBINED_RE.finditer(text)]
        if r["pii_type"] == "ADDRESS":
            out["rows"] += 1
            if any(s <= s0 and e >= e0 for s, e in ms):
                out["full"] += 1
            elif any(s < e0 and e > s0 for s, e in ms):
                out["partial"] += 1
                examples.append({"record_id": r["record_id"], "text": text, "matches": ms})
            else:
                out["none"] += 1
                examples.append({"record_id": r["record_id"], "text": text, "matches": ms})
        else:
            fp["rows"] += 1
            if ms:
                fp["false_positive_rows"] += 1
                examples.append({"record_id": r["record_id"], "type": r["pii_type"], "text": text, "matches": ms})
    return {"address_rows": dict(out), "non_address_rows": dict(fp), "examples": examples[:10]}


def fp_check(rows):
    from presidio_analyzer import AnalyzerEngine
    eng = add_to(AnalyzerEngine())
    c = collections.Counter(); examples = []
    for r in rows:
        if r["pii_type"] == "ADDRESS":
            continue
        s0, e0, text = r["start_char"], r["end_char"], r["raw_text"]
        c["non_address_records"] += 1
        bad = [x for x in eng.analyze(text=text, language="en")
               if x.entity_type == "ADDRESS" and not (x.start < e0 and x.end > s0)]
        if bad:
            c["records_with_non_overlapping_ADDRESS"] += 1
            c["non_overlapping_ADDRESS_detections"] += len(bad)
            examples.append({"record_id": r["record_id"], "type": r["pii_type"], "text": text,
                             "detections": [(x.start, x.end, round(x.score, 2)) for x in bad]})
    return {"counts": dict(c), "examples": examples[:10]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("regex", "fp"))
    ap.add_argument("--ledger", default="data/pii_injections.jsonl")
    ap.add_argument("--out")
    a = ap.parse_args()
    rows = read_jsonl(a.ledger)
    res = regex_check(rows) if a.mode == "regex" else fp_check(rows)
    json.dump(res, open(a.out or f"evidence/address_rule_{a.mode}.json", "w", encoding="utf-8"), indent=2)
    print(json.dumps(res, indent=2))
