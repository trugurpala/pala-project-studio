# Install artifact verification contract

Pala ships a **lean marketplace install** (allowlisted plugin files only). Full
repo gates (fork pack, demo seed, DEBUGGING brain, portable ZIP double-build)
require the **source tree**, not `%LOCALAPPDATA%\Pala\marketplace`.

## Profiles

| Surface | Command | Expectation |
| --- | --- | --- |
| Source / release gate | `py -3 scripts/verify.py` (default `--mode source`) | Full unittest discover + self-audit `profile=source` + reproducible ZIP |
| Installed marketplace | `py -3 scripts/pala_self_audit.py --root <marketplace> --profile runtime` | Lean checks: `presence`, `hook_safety`, `soft_claims`, `manifest` |
| Installed verify | `py -3 scripts/verify.py --mode installed --root <marketplace>` | Syntax compile of present scripts + runtime self-audit; no portable pack |

## Integrity

`tree_fingerprint` hashes only allowlisted `bundle_files`. Runtime junk such as
`__pycache__` / `*.pyc` must not mark a healthy install as `drifted` (issue #13).

## Evidence labels

Use only: `passed` | `not-run` | `blocked` | `configured-not-verified`.
Doctor `self_audit` stays `configured-not-verified` until an explicit audit or
verify runs; hooks never start tests or network.
