#!/usr/bin/env python3
"""Recent papers and citation stats for faculty at one institution, via OpenAlex.

Use it after csrankings_roster.py to read the last ~2 years of each
candidate's work and count title hits for the applicant's keywords.

Examples
  python openalex_recent.py --institution "Ohio State University" \
      --names-file roster.csv --top 15 --since 2025 \
      --keywords "vision-language,multimodal,VLM,retrieval,RAG,hallucination,agent,benchmark,evaluation" \
      --out recent.csv --papers-out papers.csv

  python openalex_recent.py --institution "Ohio State University" --name "Huan Sun"

Notes
  - Names like "Yu Su 0001" (DBLP disambiguation) are cleaned to "Yu Su".
  - Without an API key OpenAlex gives a small shared daily budget (about two
    calls per person here). Set OPENALEX_API_KEY or pass --api-key if the user
    has one. Do not sign up for a key on the user's behalf without asking.
  - Author matching is by name within the institution and can be wrong for
    common names: check the openalex_id / top titles before relying on a row.
Standard library only.
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.openalex.org/"


def get(path, params, key):
    if key:
        params = dict(params, api_key=key)
    url = API + path + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "professor-seeking-skill"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    return {}


def clean(name):
    return re.sub(r"\s+\d{4}$", "", name).strip()


def find_institution(name, key):
    res = get("institutions", {"search": name, "per-page": 5, "select": "id,display_name,country_code"}, key).get("results", [])
    if not res:
        sys.exit(f'OpenAlex has no institution matching "{name}"')
    return res[0]["id"].rsplit("/", 1)[-1], res[0]["display_name"]


def find_author(name, inst_id, key):
    res = get("authors", {
        "search": name,
        "filter": f"last_known_institutions.id:{inst_id}",
        "per-page": 5,
        "select": "id,display_name,works_count,cited_by_count,summary_stats",
    }, key).get("results", [])
    toks = set(name.lower().replace("-", " ").split())
    good = [r for r in res if toks <= set(r["display_name"].lower().replace("-", " ").replace(".", " ").split()) or r["display_name"].lower() == name.lower()]
    pool = good or res
    return max(pool, key=lambda r: r.get("works_count", 0)) if pool else None


def recent_works(author_id, since, n, key):
    return get("works", {
        "filter": f"author.id:{author_id},from_publication_date:{since}-01-01",
        "sort": "publication_date:desc",
        "per-page": n,
        "select": "display_name,publication_year,primary_location,cited_by_count",
    }, key).get("results", [])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--institution", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--name", action="append", help="faculty name (repeatable)")
    g.add_argument("--names-file", help="CSV with a name column (e.g. roster.csv from csrankings_roster.py)")
    ap.add_argument("--name-col", default="name")
    ap.add_argument("--top", type=int, default=15, help="with --names-file, take the first N rows (default 15)")
    ap.add_argument("--since", type=int, default=time.localtime().tm_year - 1)
    ap.add_argument("--keywords", default="", help="comma-separated title keywords to count (case-insensitive)")
    ap.add_argument("--per-author", type=int, default=30, help="recent works to read per person (default 30)")
    ap.add_argument("--api-key", default=os.environ.get("OPENALEX_API_KEY", ""))
    ap.add_argument("--out", help="summary CSV, one row per person")
    ap.add_argument("--papers-out", help="CSV of every recent paper read")
    a = ap.parse_args()

    if a.names_file:
        with open(a.names_file, newline="", encoding="utf-8") as f:
            names = [r[a.name_col] for r in csv.DictReader(f)][: a.top]
    else:
        names = a.name
    kws = [k.strip().lower() for k in a.keywords.split(",") if k.strip()]
    inst_id, inst_name = find_institution(a.institution, a.api_key)
    print(f"OpenAlex institution: {inst_name} ({inst_id}); works since {a.since}\n")

    summary, papers = [], []
    for raw in names:
        name = clean(raw)
        try:
            au = find_author(name, inst_id, a.api_key)
        except Exception as e:
            print(f"- {name}: lookup failed ({e})")
            continue
        if not au:
            print(f"- {name}: not found at {inst_name} in OpenAlex")
            summary.append({"name": name, "openalex_id": "", "note": "not found"})
            continue
        aid = au["id"].rsplit("/", 1)[-1]
        works = recent_works(aid, a.since, a.per_author, a.api_key)
        scored = []
        for w in works:
            title = w.get("display_name") or ""
            hits = [k for k in kws if k in title.lower()]
            venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
            scored.append((len(hits), w.get("publication_year"), venue, title, hits))
            papers.append({"name": name, "year": w.get("publication_year"), "venue": venue, "title": title,
                           "keyword_hits": ";".join(hits), "cited_by": w.get("cited_by_count", 0)})
        scored.sort(key=lambda x: (-x[0], -(x[1] or 0)))
        st = au.get("summary_stats") or {}
        row = {
            "name": name,
            "openalex_id": aid,
            "h_index": st.get("h_index", ""),
            "cited_by_count": au.get("cited_by_count", ""),
            "two_year_mean_citedness": round(st.get("2yr_mean_citedness") or 0, 1),
            "recent_works": len(works),
            "keyword_hit_papers": sum(1 for s in scored if s[0]),
            "top_titles": " || ".join(f"{y} | {v} | {t}" for _, y, v, t, _ in scored[:5]),
            "note": "",
        }
        summary.append(row)
        print(f"- {name}  h={row['h_index']}  cites={row['cited_by_count']}  recent={row['recent_works']}  keyword-hit papers={row['keyword_hit_papers']}")
        for n_hits, y, v, t, hits in scored[:3]:
            print(f"    {y} {v[:40]:<40} {t[:100]}" + (f"  [{', '.join(hits)}]" if hits else ""))
        time.sleep(0.2)

    if a.out and summary:
        keys = ["name", "openalex_id", "h_index", "cited_by_count", "two_year_mean_citedness", "recent_works", "keyword_hit_papers", "top_titles", "note"]
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for r in summary:
                w.writerow({k: r.get(k, "") for k in keys})
    if a.papers_out and papers:
        with open(a.papers_out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(papers[0].keys()))
            w.writeheader()
            w.writerows(papers)


if __name__ == "__main__":
    main()
