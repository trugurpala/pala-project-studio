# Quality Gates

Derive commands from package metadata, lock files, repository docs, CI, and
existing targets. Never invent a second quality stack or weaken strictness.

## Verification tiers

| Tier | Run when | Scope |
| --- | --- | --- |
| `narrow` | Red/green development loop | Smallest reproducing test or changed unit |
| `ticket` | One coherent outcome is ready to checkpoint | Affected tests plus applicable format, lint, typecheck, build, or smoke checks |
| `milestone` | A phase or integration boundary closes | Repository-wide quality suite, real persistence/runtime, and browser acceptance where applicable |
| `release` | Packaging, publishing, deployment, or handoff | Milestone gate plus dependency, secret, package, and delivery checks |

Do not run a milestone or release gate after every edit or micro-checkbox unless
the repository's explicit plan requires it. Do not skip that gate when its
planned boundary is reached. Pala hooks record and restore state; they never
start tests, builds, network calls, or GitHub mutations automatically.

## Working loop

1. Reproduce with the narrowest existing check.
2. Identify the first causal error and separate code defects from environment,
   credentials, network, and performance limitations.
3. Add or update a behavior test before a feature or bug fix when feasible.
4. Apply the minimal root-cause fix.
5. Rerun the narrow check; at ticket completion run only applicable ticket
   checks and review the diff.
6. At the planned milestone/release boundary run the corresponding full gate.

Report each applicable gate as `passed`, `failed`, `blocked`, or `not run` with
the command and evidence. Do not report a speed or token-saving percentage
without a measured baseline and comparison in the same environment. Record
warm/cold conditions, command, run count, and duration when performance matters.
