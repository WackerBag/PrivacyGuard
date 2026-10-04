"""Human review of the 24 prepared samples (the M2 human-in-the-loop gate).
Run:  python evidence/review_samples.py --reviewer "Carson Morris"
For each sample you see raw / delete / generic / typed. Answer y (approve), n (reject), q (quit, progress saved).
Checks: intent is still clear, the PII is gone/replaced as shown, nothing looks like real personal data.
Writes data/human_review_24.csv in place (review_status, reviewer, review_date, note); a copy of the
original is kept at data/human_review_24.pre_review.csv."""
import argparse, csv, datetime, shutil, os
ap = argparse.ArgumentParser(); ap.add_argument("--reviewer", required=True)
ap.add_argument("--file", default="data/human_review_24.csv"); a = ap.parse_args()
bak = a.file.replace(".csv", ".pre_review.csv")
if not os.path.exists(bak): shutil.copy(a.file, bak)
rows = list(csv.DictReader(open(a.file, encoding="utf-8", newline="")))
for extra in ("reviewer", "review_date", "note"):
    for r in rows: r.setdefault(extra, "")
today = datetime.date.today().isoformat()
for i, r in enumerate(rows, 1):
    if r["review_status"] in ("APPROVED", "REJECTED"): continue
    print(f"\n[{i}/{len(rows)}] {r['record_id']}  intent={r['category']}  {r['pii_type']}/{r['placement']}")
    for k in ("raw", "delete", "generic", "typed"): print(f"  {k:8}: {r[k]}")
    ans = input("approve? (y/n/q) ").strip().lower()
    if ans == "q": break
    r["review_status"] = "APPROVED" if ans == "y" else "REJECTED"
    r["reviewer"], r["review_date"] = a.reviewer, today
    if ans != "y": r["note"] = input("  reason: ").strip()
fields = list(rows[0].keys())
with open(a.file, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
done = sum(r["review_status"] in ("APPROVED", "REJECTED") for r in rows)
print(f"\nSaved. {done}/{len(rows)} reviewed; approved={sum(r['review_status']=='APPROVED' for r in rows)}")
