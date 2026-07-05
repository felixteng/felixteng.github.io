#!/usr/bin/env python3
"""Parse import/chinese-papers.ris (Zotero RIS export) into the same
"YEAR ||| TITLE ||| AUTHORS ||| VENUE" line format used by scholar_raw.txt,
appended to import/chinese_raw.txt for build_pubs.py to pick up.

Also:
  - drops entries that are the Chinese-language original of a paper already
    present (in English-titled form) in scholar_raw.txt / publications.yaml
    -- cross-checked by hand against the Scholar list (see EXCLUDE_ZH below).
  - fixes a source-data glitch where some Chinese author names are doubled
    (e.g. "王文涛文涛" -> "王文涛"), apparently from Zotero's name splitting.
  - harvests real DOIs (RIS "DO" field) for standalone Chinese papers and
    merges them straight into import/dois.json, keyed the same way
    build_pubs.py's slugify() would generate the id.

Run:  python3 import/parse_ris.py
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RIS = Path(__file__).resolve().parent / "chinese-papers.ris"
OUT = Path(__file__).resolve().parent / "chinese_raw.txt"
DOIS_FILE = Path(__file__).resolve().parent / "dois.json"

TYPE_VENUE_TAG = {"JOUR": "T2", "BOOK": "T3", "ELEC": "T2"}

# Chinese titles confirmed (by manual cross-check against scholar_raw.txt) to be
# the Chinese-language original of a paper already included under its
# English title. Comment shows the matching English entry for traceability.
EXCLUDE_ZH = {
    "在公平原则下积极推进全球应对气候变化进程":  # = Addressing Global Climate Change Under Guidance of Principle of Equity (2009)
        None,
    "照常情景的定义及其对减缓努力评价的影响":  # = Definition of business as usual... (2012)
        None,
    "我国部门减排行动可测量、可报告、可核实现状分析":  # = Sector mitigation policies and measures in China... (2010)
        None,
    "温室气体减排的协同效益":  # = A comprehensive review of co-benefit of GHG mitigation (2013)
        None,
    "中国深度脱碳路径及政策分析":  # = Pathway and policy analysis to China's deep decarbonization (2017)
        None,
    "地球系统模式与综合评估模型的双向耦合及应用":  # = Coupling Earth System Model and integrated assessment model (2016)
        None,
    "新气候经济学的研究任务和方向探讨":  # = Towards a new climate economics (2015)
        None,
    "“一带一路”沿线国家适应气候变化的技术需求评估":  # = Technology Needs Assessment for adaptation... (2023)
        None,
    "2℃温升目标下中国排放配额分析":  # already in scholar_raw.txt verbatim (2015)
        None,
    "减缓气候变化社会经济评价研究的最新进展——对IPCC第五次评估报告第三工作组报告的评述":  # = The Latest Progress in Socioeconomic Assessment... (2014)
        None,
    "碳公平的测度:基于人均历史累计排放的碳基尼系数":  # = Metric of carbon equity... (2011)
        None,
    "实施边界碳调节对中国对外贸易的影响":  # = Influences of Border Carbon Adjustments... (2012)
        None,
    "全球长期减排目标与碳排放权分配原则":  # = Long-term climate change mitigation target... (2009)
        None,
    "国际合作碳减排机制模型":  # = International cooperation mechanisms for carbon reduction (2005)
        "10.16511/j.cnki.qhdxxb.2005.06.036",
    "可计算一般均衡框架下的气候变化经济影响综合评估":  # = Review of economic impacts from climate change under CGE framework (2020)
        None,
    "何谓“碳中和”？":  # = What is carbon neutrality? (2021)
        None,
    "“一带一路”共建国家气候变化的技术需求评估及推动南南技术合作的政策建议":  # = Climate technology demand assessment for participating countries... (2023)
        "10.16418/j.issn.1000-3045.20230526003",
    "我国极端天气气候事件直接和间接经济损失的评估及归因":  # = Attribution and assessment of direct and indirect economic losses... (2025)
        "10.12006/j.issn.1673-1719.2024.305",
}


def norm_title(t):
    return re.sub(r"[^\w]", "", t.lower(), flags=re.UNICODE)


def slugify_zh(title, year):
    h = hashlib.md5(title.encode("utf-8")).hexdigest()[:8]
    return f"zh-{year}-{h}"


def collapse_duplicated_suffix(name):
    """Fix source glitch: '王文涛文涛' -> '王文涛', '滕飞飞' -> '滕飞', '南雁雁' -> '南雁'."""
    for k in (3, 2, 1):
        if len(name) >= 2 * k + 1 and name[-k:] == name[-2 * k:-k]:
            return name[:-k]
    return name


def parse_entries(text):
    entries = []
    cur = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^([A-Z][A-Z0-9])  - (.*)$", line)
        if not m:
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == "TY":
            if cur:
                entries.append(cur)
            cur = {"TY": val, "AU": []}
        elif tag == "AU":
            cur.setdefault("AU", []).append(val)
        elif tag == "ER":
            if cur:
                entries.append(cur)
            cur = {}
        else:
            cur[tag] = val
    if cur:
        entries.append(cur)
    return entries


def fmt_author(name):
    name = collapse_duplicated_suffix(name.strip())
    if "," in name:
        fam, given = [p.strip() for p in name.split(",", 1)]
        if re.search(r"[一-鿿]", fam + given):
            return collapse_duplicated_suffix(fam) + collapse_duplicated_suffix(given)
        initials = "".join(w[0] for w in given.split())
        return f"{initials} {fam}"
    return name


def main():
    text = RIS.read_text(encoding="utf-8")
    entries = parse_entries(text)
    excl_norm = {norm_title(t): doi for t, doi in EXCLUDE_ZH.items()}

    dois = json.loads(DOIS_FILE.read_text(encoding="utf-8")) if DOIS_FILE.exists() else {}
    lines = []
    kept, skipped, doi_patched = 0, 0, 0

    for e in entries:
        title = e.get("TI", "").strip()
        if not title:
            continue
        year_raw = e.get("PY") or (e.get("DA", "").split("/")[0] if e.get("DA") else "")
        year_digits = re.sub(r"\D", "", year_raw)[:4]

        nt = norm_title(title)
        if nt in excl_norm:
            # DOIs for these were already cross-matched and merged into dois.json
            # by hand under the existing English-titled entry's slug.
            skipped += 1
            continue

        if not year_digits:
            continue  # no usable year and not a known duplicate -> skip rather than guess

        author_list = []
        for a in e.get("AU", []):
            for part in re.split(r"[;；]", a):  # some RIS records jam multiple authors into one AU tag
                part = part.strip()
                if part:
                    author_list.append(fmt_author(part))
        authors = ", ".join(author_list)
        if not authors:
            continue  # stub/bookmark entries with no authors

        venue_tag = TYPE_VENUE_TAG.get(e["TY"], "T2")
        venue = e.get(venue_tag, "") or e.get("T2", "") or e.get("PB", "")
        lines.append(f"{year_digits} ||| {title} ||| {authors} ||| {venue}")
        kept += 1

        doi = e.get("DO")
        if doi:
            slug = slugify_zh(title, year_digits)
            if dois.get(slug) != doi:
                dois[slug] = doi
                doi_patched += 1

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    DOIS_FILE.write_text(json.dumps(dois, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Parsed {len(entries)} RIS records: kept {kept}, skipped {skipped} (duplicates of existing English entries)")
    print(f"DOIs harvested for standalone Chinese papers: {doi_patched}")


if __name__ == "__main__":
    main()
