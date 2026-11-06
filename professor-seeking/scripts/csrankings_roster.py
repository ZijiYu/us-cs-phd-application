#!/usr/bin/env python3
"""Pull a school's full faculty roster from CSRankings and rank it by recent
top-venue papers in the areas you care about.

CSRankings publishes its data on GitHub (emeryberger/CSrankings, gh-pages):
  - csrankings-[a-z].csv     faculty -> affiliation, homepage, Google Scholar id
  - generated-author-info.csv  faculty -> (venue, year, paper count)

Examples
  python csrankings_roster.py --list-schools "ohio"
  python csrankings_roster.py --school "Ohio State University" --out roster.csv
  python csrankings_roster.py --school "Ohio State University" --focus nlp,cv,ml,ai,ir --since 2025

Only the Python standard library is used. Downloads are cached (default
~/.cache/csrankings) and refreshed when older than --max-age-days.
"""
import argparse
import csv
import datetime as dt
import io
import os
import string
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

BASE = "https://raw.githubusercontent.com/emeryberger/CSrankings/gh-pages/"

# CSRankings venue codes grouped into the areas used for filtering.
GROUPS = {
    "ai": ["aaai", "ijcai"],
    "ml": ["icml", "nips", "iclr", "kdd"],
    "cv": ["cvpr", "iccv", "eccv"],
    "nlp": ["acl", "emnlp", "naacl"],
    "ir": ["sigir", "www"],
    "robotics": ["icra", "iros", "rss"],
    "hci": ["chiconf", "uist", "ubicomp"],
    "vis": ["vis", "vr"],
    "graphics": ["siggraph", "siggraph-asia", "eurographics"],
    "bio": ["ismb", "recomb"],
}
VENUE_TO_GROUP = {v: g for g, vs in GROUPS.items() for v in vs}
GROUP_ORDER = list(GROUPS) + ["other"]


def fetch(name, cache, max_age_days):
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, name)
    fresh = os.path.exists(path) and (time.time() - os.path.getmtime(path)) < max_age_days * 86400
    if not fresh:
        url = BASE + urllib.parse.quote(name)
        req = urllib.request.Request(url, headers={"User-Agent": "professor-seeking-skill"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r, open(path + ".tmp", "wb") as f:
                f.write(r.read())
            os.replace(path + ".tmp", path)
        except Exception as e:  # keep a stale copy if the download fails
            if not os.path.exists(path):
                sys.exit(f"Could not download {url}: {e}")
            print(f"warning: using cached {name} ({e})", file=sys.stderr)
    return path


def load_faculty(cache, max_age_days):
    rows = []
    for letter in string.ascii_lowercase:
        path = fetch(f"csrankings-{letter}.csv", cache, max_age_days)
        with open(path, newline="", encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
    return rows


def load_pubs(cache, max_age_days):
    path = fetch("generated-author-info.csv", cache, max_age_days)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve_school(query, depts):
    q = query.lower().strip()
    exact = [d for d in depts if d.lower() == q]
    if exact:
        return exact[0]
    hits = sorted(d for d in depts if q in d.lower())
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f'No CSRankings affiliation matches "{query}". Try --list-schools with a shorter word.')
    sys.exit("Several affiliations match; pass one exactly with --school:\n  " + "\n  ".join(hits))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--school", help='CSRankings affiliation, e.g. "Ohio State University" (substring OK if unique)')
    ap.add_argument("--list-schools", metavar="TEXT", help="list affiliations containing TEXT and exit")
    ap.add_argument("--focus", default="ai,ml,cv,nlp,ir", help="comma-separated area groups to rank by (default ai,ml,cv,nlp,ir); groups: " + ",".join(GROUP_ORDER))
    ap.add_argument("--since", type=int, default=dt.date.today().year - 1, help="first year counted as 'recent' (default: last year, i.e. a two-year window)")
    ap.add_argument("--cache", default=os.path.expanduser("~/.cache/csrankings"))
    ap.add_argument("--max-age-days", type=float, default=7)
    ap.add_argument("--out", help="write the full roster to this CSV")
    ap.add_argument("--show", type=int, default=40, help="rows to print (default 40)")
    a = ap.parse_args()

    focus = [g.strip() for g in a.focus.split(",") if g.strip()]
    bad = [g for g in focus if g not in GROUP_ORDER]
    if bad:
        sys.exit(f"Unknown group(s): {bad}. Choose from {GROUP_ORDER}")

    faculty = load_faculty(a.cache, a.max_age_days)
    depts = sorted({r["affiliation"] for r in faculty})
    if a.list_schools:
        for d in depts:
            if a.list_schools.lower() in d.lower():
                print(d)
        return
    if not a.school:
        ap.error("--school or --list-schools is required")
    school = resolve_school(a.school, depts)

    roster = {}
    for r in faculty:
        if r["affiliation"] == school and r["name"] not in roster:
            roster[r["name"]] = r

    stats = defaultdict(lambda: {"total": 0.0, "first": None, "last": None, "all": Counter(), "recent": Counter()})
    for r in load_pubs(a.cache, a.max_age_days):
        if r["dept"] != school:
            continue
        s = stats[r["name"]]
        y, c = int(r["year"]), float(r["count"])
        g = VENUE_TO_GROUP.get(r["area"], "other")
        s["total"] += c
        s["all"][g] += c
        if y >= a.since:
            s["recent"][g] += c
        s["first"] = y if s["first"] is None else min(s["first"], y)
        s["last"] = y if s["last"] is None else max(s["last"], y)

    names = set(roster) | set(stats)
    out = []
    for n in names:
        s = stats[n]
        f = roster.get(n, {})
        sid = (f.get("scholarid") or "").strip()
        row = {
            "name": n,
            "homepage": f.get("homepage", ""),
            "scholar_url": f"https://scholar.google.com/citations?user={sid}" if sid and sid.upper() != "NOSCHOLARPAGE" else "",
            "dblp_search": "https://dblp.org/search?q=" + urllib.parse.quote(n),
            "first_year": s["first"] or "",
            "last_year": s["last"] or "",
            "total": round(s["total"], 1),
            "focus_total": round(sum(s["all"][g] for g in focus), 1),
            "focus_recent": round(sum(s["recent"][g] for g in focus), 1),
            "recent_by_area": " ".join(f"{g}:{s['recent'][g]:g}" for g in GROUP_ORDER if s["recent"][g]),
        }
        for g in GROUP_ORDER:
            row[g] = round(s["all"][g], 1)
        out.append(row)
    out.sort(key=lambda r: (-r["focus_recent"], -r["focus_total"], r["name"]))

    if a.out:
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else ["name"])
            w.writeheader()
            w.writerows(out)

    active = sum(1 for r in out if r["focus_recent"] > 0)
    print(f"{school}: {len(out)} faculty in CSRankings; {active} with {'/'.join(focus)} papers since {a.since}.")
    print(f"{'focus_recent':>12} {'focus_total':>11} {'first':>5}  name  [recent by area]")
    for r in out[: a.show]:
        print(f"{r['focus_recent']:>12g} {r['focus_total']:>11g} {str(r['first_year']):>5}  {r['name']}  [{r['recent_by_area']}]")
    if a.out:
        print(f"\nFull roster written to {a.out}")


if __name__ == "__main__":
    main()
