# Codex plugin checklist (M27)

Evidence labels only: `passed` | `not-run` | `blocked` | `configured-not-verified`.

| Row | Surface | Evidence |
| --- | --- | --- |
| Manifest `.codex-plugin/plugin.json` | Source `0.8.1+codex.*` | `passed` (prep; GitHub tag `not-run`) |
| Marketplace `.agents/plugins/marketplace.json` | Local `./` single plugin | `passed` |
| Hooks convention `hooks/hooks.json` | SessionStart + statusMessage | `passed` |
| Skill body size | Thin skill; detail in `references/kontrol-et.md` | contract tests |
| SessionStart budget | Dual: char limit + approx-token ≤900 (host ~1000 hard) | contract tests |
| `/hooks` UI trust | Human Codex Work click | `configured-not-verified` |
| Installed vs source verify | `docs/INSTALL_ARTIFACT_CONTRACT.md` | `passed` (runtime profile + `--mode installed`) |
| Integrity fingerprint | Allowlisted `tree_fingerprint` | `passed` (issue #13) |
| Artifact E2E CI smoke | `quality.yml` job | `configured-not-verified` until Actions runs on push |
| Cold-start ms JSON | `pala_cold_start.py` | `passed` (ms only; no %) |

Related: [INSTALL_ARTIFACT_CONTRACT.md](INSTALL_ARTIFACT_CONTRACT.md),
[VIBE_FIRST_SESSION.md](VIBE_FIRST_SESSION.md), [FORK_PACK.md](FORK_PACK.md).
