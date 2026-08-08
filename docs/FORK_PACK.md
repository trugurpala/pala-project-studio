# Fork pack — what you get in 5 minutes

Pala Project Studio is a **Codex plugin** (skills + hooks + Python scripts).
Forking this repo gives you a fillable memory contract demo, not a web app and
not a ChatGPT Plus chat install.

## Quick path

```powershell
git clone https://github.com/trugurpala/pala-project-studio.git
cd pala-project-studio
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
py -3 scripts\pala_demo.py seed --demo-root examples\demo-software-project --catalog-root $env:USERPROFILE\Desktop\Codex
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Status
py -3 scripts\pala_self_audit.py
```

Expected:

- Doctor `plugin_ready` / `healthy` for the core plugin
- Status HTML “Şimdi” line shows the demo active ticket after seed
  (currently `DEMO-005`; timeline still has register / begin / checkpoint)
- Self-audit JSON `status=passed` (presence + fork pack + demo Status HTML)

## Presence in chat

On registered projects, SessionStart starts with:

`Pala burada — bu oturumda yanındayım.`

The Codex status chip for SessionStart is `Pala yanınızda`. The skill Human
Contract opens the same way. Pala does **not** claim larger context windows,
quotas, or magic speedups.

## What ships

| Path | Purpose |
| --- | --- |
| `examples/demo-software-project/` | Filled memory documents + workflow |
| `scripts/pala_demo.py` | Seeds SQLite catalog / events / sample provision |
| `scripts/pala_self_audit.py` | Fail-closed fork + presence quality gate |
| `docs/VIBE_FIRST_SESSION.md` | First 10 minutes in Codex Work |

## What does not ship

- ChatGPT Plus paste-install
- Secrets, tokens, transcripts, or real customer data
- Hook-side test/build/network/commit
- Soft “done” or unverified speed/token percentages without evidence labels

## Multi-agent / task cards

Root `PLAN.md` milestone **M24** shows the card shape forkers can copy — not a
second orchestrator product. Each card has **ID**, **Sahip ajan**, scope files,
**Bitti sayılır**, and **Kanıt** (`passed` / `not-run` / …). Claim one ID;
keep file ownership non-overlapping across agents.

## Limits

See [CODEX_SCOPE_AND_LIMITS.md](CODEX_SCOPE_AND_LIMITS.md) and
[PALA_EVERYWHERE.md](PALA_EVERYWHERE.md).
