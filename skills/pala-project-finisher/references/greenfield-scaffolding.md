# Greenfield Scaffolding

Scaffold only after product and architecture decisions are recorded. Use the
selected framework's current official generator when it produces less custom
maintenance than hand-written setup. Pin the package manager and create one lock
file.

Create the minimum structure needed for the first vertical slice:

```text
project/
  AGENTS.md
  product/plan/status/decision documents
  application source
  tests
  environment example without secrets
  package/build metadata
```

Add nested `AGENTS.md` files only where a subtree has stable rules that differ
from the root, such as frontend, backend, mobile, infrastructure, or shared
contracts. Keep dynamic status and plans out of instruction files. Verify the
effective chain and instruction-byte budget for each created subtree.

Scaffolding rules:

- No empty architecture layers created “for later.”
- No duplicate package manager, formatter, linter, test runner, or config style.
- No placeholder APIs, fake production integrations, unused sample pages, demo
  accounts, copied branding, or speculative environment variables.
- Keep generated code identifiable and separate from product-owned modules.
- Put the first behavior test beside or near its owning feature.
- Provide one documented development command and one complete verification
  path.

The first milestone must exercise a real user action through its true local
boundaries. A polished shell with inert controls is not a vertical slice.

After generation, inspect every created file. Remove unused demo routes,
assets, dependencies, scripts, analytics, and deployment assumptions before
product work continues.
