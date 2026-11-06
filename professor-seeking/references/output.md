# Output template

Write in the user's language. Keep the reply scannable; put long evidence in the CSV rather than the chat.

## 1. Summary (two lines)

`<School>: <N> faculty in the roster → <M> after filtering → <K> recommended for a <tier> cycle.` Then one line on the main pattern (for example "the strongest fits are two new assistant professors; the NLP flagship group is High competition").

## 2. Ranked table

| # | Professor | Title · start year | Fit (0–5) | Anchor paper (year, venue) | Recruiting signal | Competition | Score |
|---|---|---|---|---|---|---|---|

## 3. One card per recommended professor

- **Why them**: one sentence connecting a named applicant project to the anchor paper (the evidence-bridge seed for the cold email).
- **Recruiting**: the recorded signal, with link and date, or "not publicly confirmed".
- **Stage / competition**: e.g. "Assistant professor since 2025, first cohort; Low".
- **Contact**: official email from the homepage, or "verify on homepage".
- **Watch out**: anything that changes the approach (co-advises with someone already emailed; asks applicants not to email; joint ECE appointment, so apply through ECE).

## 4. Backups

2–4 names with one line each.

## 5. Excluded

Name: reason (already contacted on <date>; moved to <school>; not recruiting per <source>; unrelated area).

## 6. Not verified

Anything left unchecked, and why (blocked page, no public email, OpenAlex profile looks merged).

## 7. Sources

Links actually used.

## CSV for drafting

When working in a project folder, save `outreach/<cycle>/candidates/<school-slug>.csv` with these columns, matching the cold-email skill's tracker:

`target_id, professor, institution, department, email, homepage_url, research_anchor, applicant_anchor, fit_rationale, fit_level, recruiting_status, source_urls, checked_on, status, next_action`

Use `status = researching` (or `ready_to_draft` when the email and anchor paper are verified), `fit_level` = High / medium / exploratory, and ISO dates in `checked_on`.
