---
name: professor-seeking-skill-by-school
description: Find and rank potential PhD advisors at one specific university for a CS PhD applicant. Pulls the school's full CSRankings roster, reads each candidate's last two years of papers, prioritizes new assistant professors, checks recruiting signals (homepage, X, LinkedIn, 1point3acres) and how competitive each lab is, removes people already contacted, and returns a ranked shortlist ready for cold-email drafting. Use whenever the user asks to find, recommend, screen or add professors/advisors at a named school (e.g. "OSU 再找几个合适的教授", "who should I email at UMass", "find advisors at Penn State for my Fall 2027 PhD"), even if they never say "skill". Not for writing the emails themselves; hand the shortlist to the cold-email skill for that.
---

# Professor seeking by school（按学校找导师）

Turn "find me good advisors at school X" into a ranked, verified shortlist. The order matters: start from the **complete** roster so nobody is missed, narrow by **recent papers**, then rank by **career stage, recruiting signals and competitiveness** for this applicant's cycle, and only then spend effort on person-by-person searching.

## Inputs (collect first, don't stall on them)

1. **School** and, if not CS, the department or program the applicant will apply to.
2. **Applicant profile**: research keywords and the 2–3 strongest projects. Look in the project-root `.local.md` (the same profile the cold-email skill uses); otherwise take them from the user's CV or recently sent cold emails; otherwise ask for 5–8 keywords.
3. **Cycle tier**: reach, target or safety (保底). It changes how competitiveness is weighed (see [references/scoring.md](references/scoring.md)). If unknown, assume *target* and say so.
4. **Already contacted / ruled out**: if a mail connector is available, search sent mail for the school's domains (Gmail: `in:sent to:(osu.edu)`); also check any tracker such as `outreach/<cycle>/targets.csv` or the user's dashboard, and anyone the user said they decided against.

## Workflow

### 1. Full roster from CSRankings

```bash
python scripts/csrankings_roster.py --list-schools "ohio"            # find the exact affiliation
python scripts/csrankings_roster.py --school "Ohio State University" \
    --focus ai,ml,cv,nlp,ir --since <last year> --out roster.csv
```

The script downloads CSRankings' public data from GitHub (cached for a week) and lists **every** faculty member CSRankings has at the school, including those with zero counted papers, with homepage, Google Scholar link and per-area top-venue counts, sorted by recent papers in the focus areas. Pick `--focus` from the applicant's profile (groups: ai, ml, cv, nlp, ir, robotics, hci, vis, graphics, bio, other). Names carry DBLP suffixes such as `Yu Su 0001`; keep them for DBLP lookups.

Know its blind spots: it only counts papers in CSRankings' venue list, it adds new hires with a lag, and it may list joint-appointment faculty from ECE or other departments under the school. Treat it as the starting pool, not the answer.

### 2. Fill the gaps CSRankings misses

Check the department's faculty directory and its "new faculty / welcome" news for the last two academic years, plus affiliated faculty in ECE, data science, biomedical informatics or an iSchool whose work matches the applicant. Add anyone found, noting the source. New assistant professors are the most likely to be missing and the most valuable for a safety or target cycle.

### 3. Coarse filter

Keep anyone with recent focus-area papers, clear keyword overlap, or a recent hire date. Drop unrelated areas, emeriti, and anyone who has left: confirm the current affiliation on the person's own homepage, because department lists and CSRankings lag (professors do move mid-cycle).

### 4. Read the last two years of papers

```bash
python scripts/openalex_recent.py --institution "Ohio State University" \
    --names-file roster.csv --top 15 --since <last year> \
    --keywords "vision-language,multimodal,retrieval,rag,hallucination,agent,benchmark" \
    --out recent.csv --papers-out papers.csv
```

This gives each person's recent titles, venues, keyword hits and rough citation stats. Then open the DBLP person page or Google Scholar for the top ~10 with WebFetch to confirm (DBLP blocks scripted access from some networks; WebFetch usually works). For each candidate pick **1–2 anchor papers** that connect to a specific applicant project and write one sentence on why; this becomes the cold email's evidence bridge.

OpenAlex sometimes merges two people with the same name or splits one person into several profiles, so treat its h-index and citation numbers as rough, and check that the titles belong to the right person.

### 5. Career stage

Confirm title and start year at this school from the homepage, CV, department news or LinkedIn. Call someone a **new assistant professor** if they started within about three years, and flag **building a first cohort** if they started this or last academic year. CSRankings' `first_year` (first counted paper) is only a hint.

### 6. Recruiting signals

Look where professors actually announce openings: lab page "prospective students / openings", department admissions pages, X or Bluesky posts, LinkedIn posts, 1point3acres or Zhihu posts, new-hire announcements. Record the exact wording, URL, date seen and which term it covers. Activity is not recruiting: say "not publicly confirmed" unless a source says so. Details and search phrasings: [references/signals.md](references/signals.md).

### 7. Competitiveness

Rate Low / Medium / High from proxies: title and seniority, number of current PhD students, citations and recent output, awards, and whether the lab is a well-known group with several star PIs. For a safety cycle, a famous group should drop down the list even if fit is excellent. Proxies are in [references/scoring.md](references/scoring.md).

### 8. LinkedIn pass

Do a **school-level** keyword scan first, through web search of public posts, e.g. `site:linkedin.com/posts "Ohio State" "PhD students" 2027` or `"looking for PhD students" "Ohio State"`. If it finds nothing useful, skip it and move on; do per-professor LinkedIn and X searches later, only for the shortlist after scoring. Use the user's logged-in LinkedIn only through their own browser, only with their explicit permission, read-only (no connection requests, messages or reactions), and for a handful of pages.

### 9. Remove contacted people and flag pairs

Remove anyone already emailed this cycle (unless a follow-up is planned) and anyone the user ruled out. Flag co-advising pairs or shared labs, so emails to them make different points instead of near-duplicates.

### 10. Score and rank

Apply the rubric in [references/scoring.md](references/scoring.md). Return 3–6 recommended professors plus 2–4 backups.

## Output

Use the template in [references/output.md](references/output.md): a two-line summary, a ranked table, one short card per recommended professor (fit, anchor paper, recruiting signal, stage, competitiveness, official email), the excluded people with reasons, what could not be verified, and sources. When working inside a project folder, also save `outreach/<cycle>/candidates/<school-slug>.csv` using the column names of the cold-email skill's tracker so the picks can move straight into drafting. Offer to hand the top picks to the cold-email skill.

## Guardrails

- This skill researches only. It never emails, messages or connects with anyone.
- Prefer official pages, then bibliographic indexes, then forums; date-stamp anything that changes (recruiting, affiliation, deadlines).
- Never present a guessed email address or recruiting status as fact; mark it unverified.
- OpenAlex without a key shares a small daily budget (the script uses about two calls per person). Keep runs to roughly 30 people unless the user has a key in `OPENALEX_API_KEY`; don't sign up for a key with the user's email without asking.
- Say plainly what you could not check and why.
