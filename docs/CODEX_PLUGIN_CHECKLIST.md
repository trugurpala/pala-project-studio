# Codex plugin checklist (M27)

Evidence labels only: `passed` | `not-run` | `blocked` | `configured-not-verified`.

| Row | Surface | Evidence |
| --- | --- | --- |
| Manifest `.codex-plugin/plugin.json` | Local candidate `1.2.0` | `configured-not-verified`; public baseline remains `v1.1.2` |
| Marketplace `.agents/plugins/marketplace.json` | Local `./` single plugin | `passed` |
| Hooks convention `hooks/hooks.json` | SessionStart + statusMessage | `passed` |
| Skill body size | Thin skill; detail in `references/kontrol-et.md` | contract tests |
| SessionStart budget | Ayrı sözleşmeler: host spill 1800, Pala char 1800, Pala approx-token ≤900 | contract tests |
| `/hooks` UI trust | Human Codex Work click | `configured-not-verified` |
| Installed vs source verify | `docs/INSTALL_ARTIFACT_CONTRACT.md` | `passed` (runtime profile + `--mode installed`) |
| Integrity fingerprint | Allowlisted `tree_fingerprint` | `passed` (issue #13) |
| Artifact E2E CI smoke | `quality.yml` job | `configured-not-verified` until branch CI runs on the candidate commit |
| Cold-start ms JSON | `pala_cold_start.py` | `passed` (ms only; no %) |
| OpenSSF Scorecard | Haftalık/manual gözlem workflow'u; PR/release kapısı değil | `not-run` until push |

Related: [INSTALL_ARTIFACT_CONTRACT.md](INSTALL_ARTIFACT_CONTRACT.md),
[VIBE_FIRST_SESSION.md](VIBE_FIRST_SESSION.md), [FORK_PACK.md](FORK_PACK.md).
