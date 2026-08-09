# Pala 0.9 — Open-source pattern intake matrix

This is a pattern benchmark, not a dependency list and not permission to copy
skills. Each source must be rechecked at the pinned snapshot before adopting a
pattern: license, maintenance, tests/evaluations, and the narrow implementation
fit are all required. No listed repository is automatically installed or
executed by Pala.

Scoring scale: `0` absent/unsuitable, `1` partial, `2` proven fit, `3` strong
reference. The initial delivery engine uses only the explicitly named patterns
below; every other row remains research input.

| # | Reference | Lens | Pattern considered | Initial fit |
| ---: | --- | --- | --- | ---: |
| 1 | [Agent Skills](https://github.com/agentskills/agentskills) | extensibility | progressive disclosure package shape | 3 |
| 2 | [Superpowers](https://github.com/obra/superpowers) | workflow | explicit SDLC checkpoints | 3 |
| 3 | [Agent Brain](https://github.com/rohitg00/agentbrain) | evidence | artifact/evidence/handoff | 3 |
| 4 | [Playwright](https://github.com/microsoft/playwright) | testing | real user-flow artefacts | 3 |
| 5 | [OpenSpec](https://github.com/Fission-AI/OpenSpec) | planning | spec before broad change | 2 |
| 6 | [Spec Kit](https://github.com/github/spec-kit) | planning | structured delivery spec | 2 |
| 7 | [Planning with Files](https://github.com/OthmanAdi/planning-with-files) | memory | file-backed continuity | 2 |
| 8 | [Serena](https://github.com/oraios/serena) | code context | symbol-aware exploration | 2 |
| 9 | [Codebase Memory MCP](https://github.com/DeusData/codebase-memory-mcp) | memory | scoped recall boundary | 1 |
| 10 | [Graphify](https://github.com/Graphify-Labs/graphify) | architecture | dependency graph review | 1 |
| 11 | [Agent Browser](https://github.com/vercel-labs/agent-browser) | UX test | browser-flow evidence | 2 |
| 12 | [Everything Claude Code](https://github.com/affaan-m/everything-claude-code) | orchestration | curated workflow prompts | 1 |
| 13 | [Karpathy Skills](https://github.com/forrestchang/andrej-karpathy-skills) | skill UX | small reusable expert prompts | 1 |
| 14 | [Autoresearch](https://github.com/karpathy/autoresearch) | evaluation | measurable experiment loop | 1 |
| 15 | [Gitleaks](https://github.com/gitleaks/gitleaks) | security | explicit secret scan evidence | 3 |
| 16 | [OSV-Scanner](https://github.com/google/osv-scanner) | dependency | advisory scan evidence | 3 |
| 17 | [Zizmor](https://github.com/woodruffw/zizmor) | CI security | workflow risk scan | 3 |
| 18 | [OpenSSF Scorecard](https://github.com/ossf/scorecard) | supply chain | release review signals | 2 |
| 19 | [Trail of Bits Claude config](https://github.com/trailofbits/claude-code-config) | security UX | secure default agent guardrails | 2 |
| 20 | [RTK](https://github.com/rtk-ai/rtk) | context speed | bounded tool output | 1 |

## Adopted in 0.9

- Superpowers: narrow test → ticket gate → milestone/release separation.
- Agent Brain: ledger is the handoff evidence source, rather than prose claims.
- Playwright: browser gate means an existing real user-flow command and its
  report/trace artefact, not a visual claim.
- Gitleaks, OSV-Scanner, Zizmor: use only if already present in project CI or
  the local tool is already installed.
- Agent Skills: thin router plus supporting references; no third-party skill
  content is copied.

## Rejection rules

Reject a pattern if it would add cloud memory, a daemon, hidden network work,
automatic package installation, automatic deploy, shared write authority, or a
second source of truth for project state. Pala remains Windows-first,
local-first, and explicit-authority-first.
