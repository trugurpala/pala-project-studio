# Code Intelligence and Review Graphs

Use structural code intelligence when a repository is large or unfamiliar,
the change crosses modules, review impact is unclear, or repeated broad scans
would waste context. For a small or obvious edit, direct `git diff`, `rg`, and
focused file reads are usually cheaper and more precise.

## Bounded workflow

1. Resolve `../../scripts/pala_code_intel.py` from the skill, then run `status
   --cwd <project>`.
2. If `code-review-graph` and a local graph are available, update/build only
   when authorized, then use `review` to identify changed symbols, dependents,
   execution flows, and likely test gaps.
3. Treat graph output as a candidate context slice, not proof. Verify every
   finding against source, diff, tests, configuration, and runtime behavior.
4. If unavailable or stale, continue with `git diff`, `rg`, package metadata,
   and focused source reads. Report the graph as blocked tooling, not a failed
   project.

Do not claim token savings, impact recall, risk, or coverage unless measured in
the current repository. Graph-derived blast radius can produce false positives,
and small changes may cost more context than direct reads.

`code-review-graph` is optional external software and is not bundled. Installing
it or changing MCP configuration requires authorization. Its local database is
stored under `.code-review-graph/`; never place secrets, private source excerpts,
or production data in Pala memory documents.
