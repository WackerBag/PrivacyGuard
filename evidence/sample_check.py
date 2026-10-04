"""Step 2: run the slide-12 sample sentence through Presidio and apply the three masks.

Prints two masking variants:
  literal : the brief's mask() exactly as written (overlapping spans applied back-to-front)
  merged  : overlapping spans merged first (highest-score span's type wins)
"""
from presidio_analyzer import AnalyzerEngine

TEXT = "When did you send me my new card? My email is davisstephanie@example.com."


# Presidio entity -> project type name used in the deck's typed condition (e.g. [EMAIL]).
# Entities outside the four project types keep Presidio's own name.
TYPE_LABEL = {"EMAIL_ADDRESS": "EMAIL", "PHONE_NUMBER": "PHONE", "LOCATION": "ADDRESS"}


def mask_literal(text, spans, method):
    for s, e, t in sorted(spans, reverse=True):
        rep = "" if method == "delete" else "[REDACTED]" if method == "generic" else f"[{TYPE_LABEL.get(t, t)}]"
        text = text[:s] + rep + text[e:]
    return " ".join(text.split()) if method == "delete" else text


def merge_spans(spans):
    """spans: (start, end, type, score). Merge overlaps; type of highest-score member."""
    out = []
    for s, e, t, sc in sorted(spans, key=lambda x: (x[0], -x[1])):
        if out and s < out[-1][1]:
            ps, pe, pt, psc = out[-1]
            out[-1] = (ps, max(pe, e), t if sc > psc else pt, max(sc, psc))
        else:
            out.append((s, e, t, sc))
    return [(s, e, t) for s, e, t, _ in out]


def mask_merged(text, spans4, method):
    return mask_literal(text, merge_spans(spans4), method)


if __name__ == "__main__":
    res = AnalyzerEngine().analyze(text=TEXT, language="en")
    print("TEXT:", repr(TEXT))
    print("Results (entity_type, start, end, score, matched):")
    for r in sorted(res, key=lambda r: r.start):
        print(f"  {r.entity_type}, {r.start}, {r.end}, {r.score:.2f}, {TEXT[r.start:r.end]!r}")
    if not res:
        print("  (no detections)")
    spans3 = [(r.start, r.end, r.entity_type) for r in res]
    spans4 = [(r.start, r.end, r.entity_type, r.score) for r in res]
    for m in ("delete", "generic", "typed"):
        print(f"literal {m:8s}: {mask_literal(TEXT, spans3, m)!r}")
    for m in ("delete", "generic", "typed"):
        print(f"merged  {m:8s}: {mask_merged(TEXT, spans4, m)!r}")
