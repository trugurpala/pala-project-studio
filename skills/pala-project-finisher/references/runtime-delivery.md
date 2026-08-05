# Runtime Delivery

Finish the requested product, not merely its scaffold, plan, landing page, or
successful compilation.

Evidence by surface:

| Surface | Minimum completion evidence |
| --- | --- |
| Frontend | App running, core flow exercised, console/network checked, narrow and wide viewport |
| Backend/API | Process healthy, changed endpoint/job exercised, failure path observed, logs inspected |
| Full stack | Frontend uses the real local backend/data path and the core flow persists or returns the expected result |
| CLI | Installed/declared entry point runs, help works, success and failure behavior checked |
| Desktop/mobile | Build or development runtime starts and the primary interaction works on the available target |

Run the repository's applicable milestone gate at the planned completion
boundary, not after every micro-edit. Classify every gate as passed, failed,
blocked, or not run with exact evidence. Never call an unrun check passed.

Use the strongest honest fallback when credentials or external services are
unavailable: prove startup, configuration validation, local boundaries, and
the visible missing-service state. Do not fake a connected production path.

## Vibe Coder Completion Gate

Ask these questions before the final response:

1. Did I inspect what already existed before creating parallel code?
2. Did I choose the smallest maintained reusable foundation and record its
   license, compatibility, and adaptation?
3. Is the implementation clean and low-duplication, with focused ownership and
   no avoidable monolith?
4. Does the real core workflow work end to end rather than only rendering a
   shell?
5. Did I run the applicable lint, typecheck, tests, build, dependency, and
   secret checks plus runtime or browser checks, and only for gates that already
   exist in this repository?
6. Can the owner open and use it now? If not, is the exact external blocker and
   honest runnable fallback visible?

Any “no” caused by a locally fixable gap means continue working. A material
scope choice, destructive/external action, unavailable credential/service, or
verified environmental limitation is a legitimate blocker; record it in
status with exactly one next action.
