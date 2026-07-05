#!/usr/bin/env python3
"""Look up DOIs for each paper in data/publications.yaml via the Crossref API.

Writes import/dois.json  ->  { "<pub id>": "<doi>", ... }
Re-runnable and incremental: existing matches in dois.json are kept and skipped.

Run:  python3 import/fetch_dois.py
(Network required; uses an unverified SSL context because this machine's proxy
breaks Python cert verification — we only read public bibliographic metadata.)
"""
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBS = ROOT / "data" / "publications.yaml"
OUT = Path(__file__).resolve().parent / "dois.json"
MAILTO = "tengfei@tsinghua.edu.cn"
CTX = ssl._create_unverified_context()


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def parse_pubs():
    """Yield (id, title, year) from the generated YAML (regex; no yaml dep)."""
    out = []
    for block in PUBS.read_text(encoding="utf-8").split("\n- id:")[1:]:
        mid = re.match(r"\s*(\S+)", block)
        mt = re.search(r'\n  title: (".*")', block)
        my = re.search(r"\n  year: (\d+)", block)
        if not (mid and mt and my):
            continue
        out.append((mid.group(1), json.loads(mt.group(1)), int(my.group(1))))
    return out


def query_crossref(title):
    q = urllib.parse.urlencode({
        "query.bibliographic": title, "rows": "5", "mailto": MAILTO,
    })
    url = "https://api.crossref.org/works?" + q
    req = urllib.request.Request(url, headers={
        "User-Agent": f"acad-site/1.0 (mailto:{MAILTO})"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                return json.load(r)["message"]["items"]
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
            else:
                print(f"   ! query failed: {e}", file=sys.stderr)
    return []


BAD_TYPES = {"peer-review"}


def best_doi(title, year, items):
    nt = norm(title)
    best = (0.0, None)
    for it in items:
        if it.get("type") in BAD_TYPES:
            continue
        doi = it.get("DOI", "")
        if "/review" in doi.lower():
            continue
        ctitle = (it.get("title") or [""])[0]
        ratio = SequenceMatcher(None, nt, norm(ctitle)).ratio()
        cy = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
        teng = any("teng" in (a.get("family", "").lower()) for a in it.get("author", []))
        year_ok = cy is not None and abs(cy - year) <= 1
        ok = ratio >= 0.93 or (ratio >= 0.85 and year_ok and teng)
        if ok and ratio > best[0]:
            best = (ratio, doi)
    return best[1]


def main():
    existing = {}
    if OUT.exists():
        existing = json.loads(OUT.read_text(encoding="utf-8"))
    pubs = parse_pubs()
    found, todo = dict(existing), [p for p in pubs if p[0] not in existing]
    print(f"{len(pubs)} papers; {len(existing)} already resolved; querying {len(todo)} ...")
    for i, (pid, title, year) in enumerate(todo, 1):
        doi = best_doi(title, year, query_crossref(title))
        if doi:
            found[pid] = doi
        if i % 20 == 0 or i == len(todo):
            OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  [{i}/{len(todo)}] resolved so far: {len(found)}")
        time.sleep(0.34)
    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE: {len(found)}/{len(pubs)} papers have a DOI -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
