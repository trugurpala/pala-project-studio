# Codex plugin checklist (M27)

Evidence labels only: `passed` | `not-run` | `blocked` | `configured-not-verified`.

| Row | Surface | Evidence |
| --- | --- | --- |
| Manifest `.codex-plugin/plugin.json` | Source `1.1.1` | `configured-not-verified` (M74 candidate; public remains `v1.1.0`) |
| Marketplace `.agents/plugins/marketplace.json` | Local `./` single plugin | `passed` |
| Hooks convention `hooks/hooks.json` | SessionStart + statusMessage | `passed` |
| Skill body size | Thin skill; detail in `references/kontrol-et.md` | contract tests |
| SessionStart budget | Ayrı sözleşmeler: host spill 1800, Pala char 1800, Pala approx-token ≤900 | contract tests |
| `/hooks` UI trust | Human Codex Work click | `configured-not-verified` |
| Installed vs source verify | `docs/INSTALL_ARTIFACT_CONTRACT.md` | `passed` (runtime profile + `--mode installed`) |
| Integrity fingerprint | Allowlisted `tree_fingerprint` | `passed` (issue #13) |
| Artifact E2E CI smoke | `quality.yml` job | `configured-not-verified` until Actions runs on push |
| Cold-start ms JSON | `pala_cold_start.py` | `passed` (ms only; no %) |
| OpenSSF Scorecard | Haftalık/manual gözlem workflow'u; PR/release kapısı değil | `not-run` until push |

Related: [INSTALL_ARTIFACT_CONTRACT.md](INSTALL_ARTIFACT_CONTRACT.md),
[VIBE_FIRST_SESSION.md](VIBE_FIRST_SESSION.md), [FORK_PACK.md](FORK_PACK.md).
