# Feature ideas for Pytest Report Viewer

For clients who use the app to **see runs and bugs**, here are ideas to make it more useful.

---

## Run types

- **UI vs API comparison runs** — Second type of run: compare UI vs API results. Different report structure, labels, mismatches. Report format to be provided; app will integrate this run type alongside existing pytest execution runs.

---

## Runs & history

- **Pass rate over time** — Dashboard widget or chart: e.g. Run 1 100%, Run 2 85%, Run 3 90%.
- **Run comparison** — Select two runs and diff: which tests passed in one and failed in the other.
- **Run tags/labels** — Tag runs (e.g. `nightly`, `release-1.2`) and filter by tag.
- **Copy run link** — “Share” button that copies the run URL for Slack/email.
- **Bulk delete old runs** — e.g. “Delete runs older than 30 days” or select multiple runs to delete.

---

## Bugs

- **Filters on Bugs page** — Filter by run (“Show only bugs from Run #5”), by project, or by date range.
- **Sort options** — Sort by most linked, by label A–Z, or by “first seen” run.
- **Bug notes** — Optional note per bug (e.g. “Fixed in build 123”).
- **Export bugs list** — CSV/Excel of all unique bugs with run IDs and test counts.

---

## Test analysis

- **Flaky test detection** — Highlight tests that failed in one run and passed in another (same nodeid).
- **Slow tests** — Sort or filter by duration; highlight tests above a threshold.
- **Full-text search** — Search across all runs (nodeid, error messages) from the dashboard.

---

## Reporting & export

- **Export run as HTML report** — Single HTML file with stats, table, and screenshots (for archiving or sharing).
- **PDF export** — One-click PDF of the current run for stakeholders.
- **Scheduled summary** — Optional email/digest: “Last 7 days: X runs, Y failures, Z unique bugs.”

---

## UX

- **Dark/light theme toggle** — User preference for theme.
- **Keyboard shortcuts** — e.g. `/` to focus search, `j`/`k` to move between runs or rows.
- **Dashboard summary** — On the main page: total runs, total tests, total unique bugs (with link to Bugs page).

---

## Integrations (future)

- **Jira / Azure DevOps** — Link to ticket and optionally show status (e.g. “Open”, “Done”) from the tracker.
- **CI webhook** — POST a run JSON from CI; app creates the run and notifies (e.g. Slack) when there are failures.

---

Pick what fits your client’s workflow first (e.g. “pass rate over time” and “export bugs CSV”), then add the rest as needed.
