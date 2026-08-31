# best_available_fantasy_football

Draft-day fantasy football ratings published with Hugo and GitHub Pages.
https://masongrosko.github.io/best_available_fantasy_football/

## Generate a Sleeper draft report

The 2026 report generator uses Sleeper API snapshots plus a rankings CSV:

```powershell
uv run python -m scripts.generate_sleeper_draft_report `
  --rankings "path/to/rankings.csv" `
  --picks "path/to/picks.json" `
  --users "path/to/users.json" `
  --adp-html "rankings/draft_sharks_adp/date/consensus-sleeper-12.html" `
  --output "docs/content/docs/2026/reports/grosko_and_co"
```

Downloaded rankings and ADP sources belong under the ignored folders in rankings  directories. Only the league's draft snapshot and generated reports are committed.

Pushes to `main` trigger `.github/workflows/hugo.yml`, which builds `docs/` and
publishes the generated site to the `gh-pages` branch.
