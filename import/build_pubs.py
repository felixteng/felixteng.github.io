#!/usr/bin/env python3
"""Convert import/scholar_raw.txt (and later RIS) into data/publications.yaml.

Re-runnable. Pipeline:
  1. parse "YEAR ||| TITLE ||| AUTHORS ||| VENUE" lines
  2. normalize the author's own name variants -> "F Teng" (so the template bolds it)
  3. classify type: journal | conference | report
  4. drop obvious Google-Scholar parsing fragments (EXCLUDE)
  5. de-duplicate by normalized title, preferring journal > conference > report, newest year
  6. flag flagship papers as featured: true
  7. emit valid YAML (scalars via json.dumps -> always valid, authors stay inline)
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_FILES = [
    Path(__file__).resolve().parent / "scholar_raw.txt",
    Path(__file__).resolve().parent / "chinese_raw.txt",
]
CORR_FILE = Path(__file__).resolve().parent / "corresponding.txt"
DOIS_FILE = Path(__file__).resolve().parent / "dois.json"
OUT = ROOT / "data" / "publications.yaml"

# --- the author's own name, in every form Scholar shows it -> canonical "F Teng"
SELF = {"f teng", "teng f", "fei teng", "teng fei", "t fei", "tengfei", "滕飞"}
CANON = "F Teng"

# --- clear Scholar artifacts / fragments to drop (exact title match, case-insensitive)
EXCLUDE = {
    "country report",
    "coal transition in",
    "economies",
    "mitigation actions in china",  # 2009 fragment; the WRI working paper is kept separately
    "environmental performance of china's overseas coal plants",  # dup of 2021 ERL journal paper
}

# --- flagship papers shown on the home page (normalized-title substring match)
FEATURED = [
    "largemethanemitigation",
    "exploringnegativeemissionpotentialofbiochar",
    "nationalclimateinstitutionscomplement",
    "damagefunctionuncertaintyincreases",
]
# --- also feature every paper published in these venues (lowercase substring of venue)
FEATURED_VENUES = ["one earth"]

CONF_KW = ["procedia", "conference", "ieee", "iaee", "proceedings",
           "securing energy in insecure times", "meeting the energy demands"]
REPORT_KW = ["出版社", "working paper", "world resources institute", "harvard project", "iddri",
             "institut du developpement", "nota di lavoro", "pact", "act 2015", "ariadne",
             "kopernikus", "ipcc", "climate change 2014", "climate change 2022",
             "annual report", "global climate change institute", "oxford university",
             "smith school", "verlag", "post-kyoto", "future energy", "deepening reform",
             "modelling and informing low emission", "working group",
             "towards a deep climate", "digital transformation for inclusive"]


def norm_title(t):
    # \w is Unicode-aware in Python 3 -> keeps CJK characters, not just ASCII.
    return re.sub(r"[^\w]", "", t.lower(), flags=re.UNICODE)


def load_corresponding():
    """One title (or distinctive substring) per line marks a corresponding-author paper."""
    if not CORR_FILE.exists():
        return []
    subs = []
    for ln in CORR_FILE.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            subs.append(norm_title(ln))
    return subs


def norm_author(a):
    return re.sub(r"\s+", " ", a.replace(".", "").strip().lower())


def fix_authors(raw):
    out = []
    for tok in re.split(r"[,，;；]", raw):
        tok = tok.strip()
        if not tok:
            continue
        if tok in ("...", "…", "et al", "et al."):
            out.append("et al.")
        elif norm_author(tok) in SELF:
            # Keep Chinese-script self-name as-is (e.g. "滕飞") rather than
            # replacing it with the English canonical form -- hugo.toml's
            # params.selfNames already lists "滕飞" so the template still bolds it.
            out.append(tok if re.search(r"[一-鿿]", tok) else CANON)
        else:
            out.append(tok)
    return out


def classify(venue):
    v = venue.lower()
    if any(k in v for k in CONF_KW):
        return "conference"
    if any(k in v for k in REPORT_KW):
        return "report"
    return "journal"


def slugify(title, year):
    if re.search(r"[一-鿿]", title):
        h = hashlib.md5(title.encode("utf-8")).hexdigest()[:8]
        return f"zh-{year}-{h}"
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return "-".join(s.split("-")[:8]) + f"-{year}"


TYPE_RANK = {"journal": 0, "conference": 1, "report": 2}


def main():
    corr_subs = load_corresponding()
    dois = json.loads(DOIS_FILE.read_text(encoding="utf-8")) if DOIS_FILE.exists() else {}
    entries, excluded = [], []
    raw_lines = []
    for f in RAW_FILES:
        if f.exists():
            raw_lines += f.read_text(encoding="utf-8").splitlines()
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|||")]
        while len(parts) < 4:
            parts.append("")
        year, title, authors, venue = parts[0], parts[1], parts[2], parts[3]
        if title.lower() in EXCLUDE:
            excluded.append(f"{year}  {title}")
            continue
        venue = "" if venue in ("(Venue not specified)",) else venue
        try:
            yr = int(year)
        except ValueError:
            continue
        nt = norm_title(title)
        entries.append({
            "_nt": nt,
            "title": title,
            "authors": fix_authors(authors),
            "venue": venue,
            "year": yr,
            "type": classify(venue),
            "featured": any(f in nt for f in FEATURED) or any(v in venue.lower() for v in FEATURED_VENUES),
        })

    # de-dup by normalized title: prefer journal > conference > report, then newest year
    best = {}
    for e in entries:
        k = e["_nt"]
        if k not in best or (TYPE_RANK[e["type"]], -e["year"]) < (TYPE_RANK[best[k]["type"]], -best[k]["year"]):
            # keep featured flag if either copy had it
            if k in best:
                e["featured"] = e["featured"] or best[k]["featured"]
            best[k] = e
    deduped = list(best.values())
    dropped_dupes = len(entries) - len(deduped)

    deduped.sort(key=lambda e: (-e["year"], e["type"]))

    # unique ids
    seen, out = {}, []
    for e in deduped:
        base = slugify(e["title"], e["year"])
        sid = base
        n = 2
        while sid in seen:
            sid = f"{base}-{n}"
            n += 1
        seen[sid] = True
        out.append((sid, e))

    lines = [
        "# Publications — GENERATED by import/build_pubs.py from import/scholar_raw.txt.",
        "# Re-run:  python3 import/build_pubs.py",
        "# Manual edits are safe but will be overwritten on re-run — prefer editing the source.",
        "#",
        "# Mark a paper where you are the corresponding author:  set  corresponding: true",
        "# Show a paper on the home page:                        set  featured: true",
        "# type: journal | conference | report",
        "",
    ]
    for sid, e in out:
        lines.append(f"- id: {sid}")
        lines.append(f"  title: {json.dumps(e['title'], ensure_ascii=False)}")
        lines.append(f"  authors: {json.dumps(e['authors'], ensure_ascii=False)}")
        lines.append(f"  venue: {json.dumps(e['venue'], ensure_ascii=False)}")
        lines.append(f"  year: {e['year']}")
        lines.append(f"  type: {e['type']}")
        is_corr = any(s in e["_nt"] for s in corr_subs)
        lines.append(f"  corresponding: {'true' if is_corr else 'false'}")
        if sid in dois:
            lines.append(f'  doi: "{dois[sid]}"')
        if e["featured"]:
            lines.append(f"  featured: true")
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")

    # report
    by_type = {}
    for _, e in out:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    print(f"Wrote {len(out)} publications to {OUT.relative_to(ROOT)}")
    print(f"  by type: {by_type}")
    print(f"  featured: {sum(1 for _, e in out if e['featured'])}")
    print(f"  corresponding: {sum(1 for _, e in out if any(s in e['_nt'] for s in corr_subs))}")
    print(f"  with DOI: {sum(1 for sid, _ in out if sid in dois)}")
    print(f"  de-duplicated (removed): {dropped_dupes}")
    if excluded:
        print(f"  excluded {len(excluded)} fragment(s):")
        for x in excluded:
            print(f"    - {x}")


if __name__ == "__main__":
    main()
