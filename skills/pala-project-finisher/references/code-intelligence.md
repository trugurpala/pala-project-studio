# Code intelligence and Professional Workbench routing

Use structural code intelligence when a repository is unfamiliar, the change
crosses modules, impact is unclear, or repeated broad scans would waste
context. Direct `git diff`, `rg`, and focused source reads remain the safe
fallback. Small or obvious changes normally stay on that direct path.

## CodeGraph workflow

1. Resolve `pala_codegraph.py` from the installed Pala bundle and run the
   bounded lifecycle stage for the current project.
2. At takeover run `init/sync/status`; before context run
   `sync/status/explore`; after implementation run `sync/status` plus impact;
   before Quality verify freshness.
3. Use only the Pala-owned CodeGraph 1.5.0 artifact and Pala MCP wrapper. Do not
   run third-party installers, updaters, watchers, telemetry, or shared daemons.
4. Treat graph output as advisory context, never Quality evidence. Verify
   findings against current source, diff, configuration, tests, and runtime.
5. If the graph is missing, stale, or fails, continue with direct source
   inspection and report the capability truthfully.

Do not claim token savings, impact recall, risk, or coverage unless measured in
the current repository. Graph candidates can contain false positives.
`.codegraph/` is generated state and must not be made a
canonical project authority or silently added to a project `.gitignore`.

## Fallbacks

Serena 1.7.0 is a lazy, read-only fallback only after CodeGraph and direct
source inspection are insufficient. It has no memory, dashboard, paid backend,
or autonomous edit authority. Context7 4.0.2 is explicit optional external and
does not affect core health. Retired helper stacks are not routing candidates.
