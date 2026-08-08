# M27 Install Artifact Contract + Standards Canary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make installed Pala marketplace bundles self-honest (no false `drifted`, no impossible verify), land uncommitted M25 work as `0.8.1`, and run live Codex + cold-start evidence on this Windows PC.

**Architecture:** Keep a **lean runtime install** (Option A from issue #13) but add an explicit **`installed` verification profile** so shipped commands exit 0. Integrity fingerprinting must hash only the immutable allowlisted bundle (`bundle_files`), never `__pycache__` or other runtime junk. Source-tree `verify.py` remains the full release gate.

**Tech Stack:** Python 3.10+ stdlib, Windows PowerShell `Install-Pala.ps1`, Codex CLI/desktop hooks, unittest, GitHub Actions (existing `quality.yml`).

## Global Constraints

- Evidence labels only: `passed` | `not-run` | `blocked` | `configured-not-verified`.
- Hooks never start network, tests, builds, commit, or push (ADR-007).
- No soft speed/quota/context-enlarge claims; cold-start reports milliseconds only.
- UTF-8 no BOM, LF line endings; preserve Turkish Unicode.
- Do not commit `codex-try-proof*.png` or secrets.
- Open PR check (2026-08-08): **no open PRs**. Closed stale PR `#5`. Open **issue [#13](https://github.com/trugurpala/pala-project-studio/issues/13)** (owner via ChatGPT Codex Connector) is the P0 driver — treat as external user report.
- Commit/push/tag/`gh release` only when owner explicitly authorizes (plan steps still show commit boundaries).

## Evaluation snapshot (why this plan)

| Area | Verdict |
| --- | --- |
| Codex shape | Correct: `.codex-plugin/plugin.json` + `skills/` + `hooks/hooks.json` |
| Source quality | Strong contract tests + `verify.py` on full repo |
| Installed artifact | **Broken contract** — issue #13: self-audit/verify fail in `%LOCALAPPDATA%\Pala\marketplace`; `__pycache__` → false `drifted` |
| Local tree | M25 shared memory + M10 canary **uncommitted** ahead of tag `v0.8.0` |
| Live Codex on this PC | Allowed now; `/hooks` UI still may need one human trust click |
| World-standard gap | Artifact E2E CI + release metadata single source |

## File map

| File | Responsibility |
| --- | --- |
| `scripts/pala_installer.py` | `tree_fingerprint` → allowlisted; ignore runtime junk |
| `scripts/pala_self_audit.py` | `--profile source\|runtime` |
| `scripts/verify.py` | `--mode source\|installed` |
| `scripts/test_pala_installer.py` | Fingerprint / drift regression tests |
| `scripts/test_pala_self_audit.py` | Runtime profile tests |
| `scripts/pala_cold_start.py` | N≥3 Doctor/memory/report timings (ms) |
| `scripts/test_pala_cold_start.py` | Contract for cold-start JSON shape |
| `scripts/test_code_intelligence.py` | Fix `PYTHONUTF8` idempotence assertion |
| `docs/CODEX_PLUGIN_CHECKLIST.md` | Codex plugin surface checklist |
| `docs/INSTALL_ARTIFACT_CONTRACT.md` | Source vs installed verification contract |
| `.github/workflows/quality.yml` | Add install-artifact smoke job |
| `STATUS.md` / `PLAN.md` / `PROGRESS.md` / `CHANGELOG.md` | Evidence + M27 tickets |
| `README.md` | Release download links match latest tag |
| Existing uncommitted M25/M10 files | Ship with `0.8.1` bump |

---

### Task 1: Integrity fingerprint ignores runtime junk (issue #13 P0)

**Files:**
- Modify: `scripts/pala_installer.py` (`tree_fingerprint`, helpers near `bundle_files`)
- Modify: `scripts/test_pala_installer.py`
- Test: `scripts/test_pala_installer.py`

**Interfaces:**
- Consumes: `bundle_files(source: Path) -> list[Path]`, `FORBIDDEN_PARTS`
- Produces: `tree_fingerprint(root: Path) -> str` hashing only allowlisted relative paths that exist under `root` (same set as `bundle_files` would select); never `__pycache__` / `*.pyc`

- [ ] **Step 1: Write the failing test**

```python
def test_tree_fingerprint_ignores_pycache(self) -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        # minimal allowlisted shape: copy a tiny fake bundle or use fixture
        (root / ".codex-plugin").mkdir()
        (root / ".codex-plugin" / "plugin.json").write_text(
            '{"name":"pala-project-studio","version":"0.0.0-test"}', encoding="utf-8"
        )
        (root / "scripts").mkdir()
        (root / "scripts" / "pala_hook.py").write_text("# x\n", encoding="utf-8")
        # ... create other REQUIRED_FILES stubs as needed for bundle_files ...
        before = pala_installer.tree_fingerprint(root)
        cache = root / "scripts" / "__pycache__"
        cache.mkdir()
        (cache / "pala_hook.cpython-312.pyc").write_bytes(b"\0\0")
        after = pala_installer.tree_fingerprint(root)
        self.assertEqual(before, after)
```

(Adapt stubs so `bundle_files(root)` is non-empty; prefer installing from real `PLUGIN_ROOT` into a temp dir via `copy_bundle` if easier.)

Preferred stronger test using real copy:

```python
def test_installed_fingerprint_stable_after_pycache(self) -> None:
    with tempfile.TemporaryDirectory() as temp:
        dest = Path(temp) / "install"
        pala_installer.copy_bundle(PLUGIN_ROOT, dest)
        before = pala_installer.tree_fingerprint(dest)
        pyc = dest / "scripts" / "__pycache__"
        pyc.mkdir(parents=True)
        (pyc / "x.pyc").write_bytes(b"abc")
        self.assertEqual(before, pala_installer.tree_fingerprint(dest))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m unittest scripts.test_pala_installer.InstallerCoreTests.test_installed_fingerprint_stable_after_pycache -v`

Expected: FAIL (current `tree_fingerprint` hashes all files → digest changes)

- [ ] **Step 3: Write minimal implementation**

Replace `tree_fingerprint` in `scripts/pala_installer.py`:

```python
def tree_fingerprint(root: Path) -> str:
    """Fingerprint only allowlisted bundle files under an install root.

    Runtime junk (__pycache__, *.pyc) must not mark a healthy install as drifted.
    """
    root = root.resolve()
    digest = hashlib.sha256()
    for path in bundle_files(root):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest().upper()
```

Note: `bundle_files` already filters via `safe_source_file` / `FORBIDDEN_PARTS` including `__pycache__`.

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 -m unittest scripts.test_pala_installer -v`

Expected: PASS for new test; existing installer tests still PASS

- [ ] **Step 5: Commit** (when owner authorizes)

```bash
git add scripts/pala_installer.py scripts/test_pala_installer.py
git commit -m "$(cat <<'EOF'
fix: fingerprint only allowlisted install files

Stop false Doctor drifted after __pycache__ from installed verify.
EOF
)"
```

---

### Task 2: `pala_self_audit --profile runtime` (issue #13 P0)

**Files:**
- Modify: `scripts/pala_self_audit.py`
- Modify: `scripts/test_pala_self_audit.py`
- Modify: `scripts/pala_installer.py` Doctor `self_audit` command hint
- Create: `docs/INSTALL_ARTIFACT_CONTRACT.md`

**Interfaces:**
- Consumes: existing `audit_*` helpers
- Produces: `run_audit(root, profile: str = "source") -> dict` where `profile in {"source","runtime"}`; runtime skips fork_pack/demo_seed/debugging_brain repo-only gates OR runs lean substitutes that only require files present in `PACKAGE_FILES` / install allowlist

- [ ] **Step 1: Write the failing test**

```python
def test_runtime_profile_passes_on_copied_bundle(self) -> None:
    with tempfile.TemporaryDirectory() as temp:
        dest = Path(temp) / "install"
        from pala_installer import copy_bundle
        copy_bundle(PLUGIN_ROOT, dest)
        payload = pala_self_audit.run_audit(dest, profile="runtime")
        self.assertEqual(payload["status"], "passed", payload)
        names = {c["name"] for c in payload["checks"]}
        self.assertIn("presence", names)
        self.assertIn("hook_safety", names)
        self.assertNotIn("fork_pack", names)  # source-only
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m unittest scripts.test_pala_self_audit.SelfAuditUnitTests.test_runtime_profile_passes_on_copied_bundle -v`

Expected: FAIL (`run_audit` has no `profile` kwarg / fork_pack fails)

- [ ] **Step 3: Write minimal implementation**

In `pala_self_audit.py`:

```python
RUNTIME_CHECKS = (
    "presence",
    "hook_safety",
    "soft_claims",
    "manifest",
)

def run_audit(root: Path | None = None, profile: str = "source") -> dict[str, object]:
    root = (root or PLUGIN_ROOT).resolve()
    if profile not in {"source", "runtime"}:
        raise ValueError("profile must be source or runtime")
    all_checks = [
        audit_presence(root),
        audit_hook_safety(root),
        audit_fork_pack(root),
        audit_demo_seed(root),
        audit_soft_claims(root),
        audit_debugging_brain(root),
        audit_agent_tasks(root),
        audit_shared_memory(root),
        audit_manifest(root),
    ]
    if profile == "runtime":
        checks = [c for c in all_checks if c["name"] in RUNTIME_CHECKS]
    else:
        checks = all_checks
    # ... existing failed/summary logic ...
```

CLI: `--profile {source,runtime}` default `source`.

Doctor hint in `pala_installer.doctor_installation` `self_audit.command`:

```text
py -3 scripts/pala_self_audit.py --profile runtime
```

(when documenting installed path use absolute marketplace root).

Write `docs/INSTALL_ARTIFACT_CONTRACT.md` stating: source verify = full repo; installed = `--profile runtime` / `--mode installed`.

- [ ] **Step 4: Run tests**

Run: `py -3 -m unittest scripts.test_pala_self_audit -v`

Expected: PASS

- [ ] **Step 5: Commit** (when authorized)

```bash
git add scripts/pala_self_audit.py scripts/test_pala_self_audit.py scripts/pala_installer.py docs/INSTALL_ARTIFACT_CONTRACT.md
git commit -m "$(cat <<'EOF'
feat: runtime self-audit profile for installed marketplace bundles

Align Doctor guidance with lean install artifacts (issue #13).
EOF
)"
```

---

### Task 3: `verify.py --mode installed` (issue #13 P0)

**Files:**
- Modify: `scripts/verify.py`
- Modify: `scripts/test_plugin_experience.py` or add `scripts/test_pala_verify_modes.py`
- Modify: `docs/INSTALL_ARTIFACT_CONTRACT.md`, Doctor/README install verify docs if they point at bare `verify.py` for installed roots

**Interfaces:**
- Consumes: unittest discover, `pala_self_audit.run_audit`
- Produces: CLI `--mode source|installed`; `installed` runs: JSON/syntax on present files, **runtime** self-audit, **skips** portable ZIP double-build and source-only test modules that need README/demo/DEBUGGING

- [ ] **Step 1: Write the failing test**

```python
def test_verify_installed_mode_exits_zero_on_copy_bundle(self) -> None:
    with tempfile.TemporaryDirectory() as temp:
        dest = Path(temp) / "install"
        pala_installer.copy_bundle(PLUGIN_ROOT, dest)
        # invoke verify as subprocess with cwd=dest OR import run(mode=)
        code = pala_verify.main(["--mode", "installed", "--root", str(dest)])
        self.assertEqual(code, 0)
```

Refactor `verify.py` `main` to accept argv + optional root.

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL (no `--mode`)

- [ ] **Step 3: Minimal implementation**

```python
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("source", "installed"), default="source")
    p.add_argument("--root", type=Path, default=None)
    return p

def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = (args.root or ROOT).resolve()
    if args.mode == "installed":
        # compile scripts/*.py under root; run runtime self-audit; skip packager
        ...
        return 0 if audit["status"] == "passed" else 1
    # existing source path unchanged
```

Installed mode must not create lasting `__pycache__` that breaks Doctor: set `PYTHONDONTWRITEBYTECODE=1` in subprocess env **and** rely on Task 1 fingerprint fix.

- [ ] **Step 4: Run tests + reproduce issue #13 locally**

```powershell
py -3 -m unittest scripts.test_pala_verify_modes -v
$root = "$env:LOCALAPPDATA\Pala\marketplace"
py -3 "$root\scripts\pala_self_audit.py" --root $root --profile runtime
# expect exit 0 after Install from this branch
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
# expect healthy=True and plugin not drifted after runtime audit
```

- [ ] **Step 5: Commit** (when authorized)

```bash
git add scripts/verify.py scripts/test_pala_verify_modes.py docs/INSTALL_ARTIFACT_CONTRACT.md
git commit -m "$(cat <<'EOF'
feat: add verify --mode installed for lean marketplace roots

Close the source-vs-install verification mismatch from issue #13.
EOF
)"
```

---

### Task 4: Fix PYTHONUTF8 idempotence test fragility (issue #13)

**Files:**
- Modify: `scripts/test_code_intelligence.py` (`test_update_uses_bounded_brief_output`)

**Interfaces:**
- Consumes: `pala_code_intel.run_graph`
- Produces: assertion that env has `PYTHONUTF8=1` and is a **copy** (identity `is not os.environ`), without requiring the parent env lacked the key

- [ ] **Step 1: Write the failing clarification** (edit test first)

Replace:

```python
self.assertNotEqual(run.call_args.kwargs["env"], os.environ)
```

With:

```python
env = run.call_args.kwargs["env"]
self.assertIsNot(env, os.environ)
self.assertEqual(env.get("PYTHONUTF8"), "1")
```

- [ ] **Step 2: Run test**

Run: `py -3 -m unittest scripts.test_code_intelligence.CodeIntelligenceTests.test_update_uses_bounded_brief_output -v`

Expected: PASS even when parent already has `PYTHONUTF8=1`

- [ ] **Step 3: Commit** (when authorized)

```bash
git add scripts/test_code_intelligence.py
git commit -m "$(cat <<'EOF'
test: allow PYTHONUTF8 already set in parent env

Avoid false failure when hosts export PYTHONUTF8=1 (issue #13).
EOF
)"
```

---

### Task 5: README / release metadata hygiene (issue #13 P1)

**Files:**
- Modify: `README.md` (download badge / ZIP links)
- Modify: `CHANGELOG.md`
- Optional small helper or CI check in `scripts/verify.py` source mode: assert README contains current manifest major.minor matching `.codex-plugin/plugin.json` when releasing

- [ ] **Step 1: Inspect README for `0.7.1` / stale asset links**

```powershell
Select-String -Path README.md -Pattern "0\.7\.1|releases/latest|pala-project-studio-"
```

- [ ] **Step 2: Point primary download to `v0.8.0` / `pala-project-studio-0.8.0.zip` until `0.8.1` ships; when bumping version in Task 8, update again in same PR**

- [ ] **Step 3: Add contract test**

```python
def test_readme_download_matches_manifest_minor(self) -> None:
    manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    version = str(manifest["version"]).split("+")[0]  # 0.8.1
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    self.assertIn(f"pala-project-studio-{version}.zip", readme)
```

- [ ] **Step 4: Run test; fix README until PASS**

- [ ] **Step 5: Commit** (when authorized)

---

### Task 6: Live Codex canary on this PC (M27-T0)

**Files:**
- Modify: `STATUS.md`, `PROGRESS.md`, `DEBUGGING.md` (INC only if blocked)
- Optional: `scripts/pala_hook_smoke.py` — stdin SessionStart JSON → assert presence line (no UI)

**Interfaces:**
- Consumes: `Install-Pala.ps1`, `pala_hook.session_context` / hook CLI
- Produces: STATUS rows for hooks UI + SessionStart smoke

- [ ] **Step 1: Doctor + Codex path**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
```

Record `healthy`, `plugin_ready`, `codex_cli.executable`, `hook_safety`.

- [ ] **Step 2: Hook SessionStart smoke (no UI)**

```powershell
@'
{"hook_event_name":"SessionStart","cwd":"C:\\Users\\Pala-Pc\\Desktop\\Cursor\\pala-project-studio","session_id":"m27-smoke","source":"startup"}
'@ | py -3 scripts\pala_hook.py
```

Expected stdout JSON contains `Pala burada` in `additionalContext` when project registered; else empty/no-op exit 0.

- [ ] **Step 3: Human `/hooks` trust**

Owner: Codex Work → `/hooks` → trust Pala → **new chat**. Agent records result `passed` or `blocked` with reason (no bypass flags).

- [ ] **Step 4: Update STATUS Owner canary table** with evidence labels only

- [ ] **Step 5: Commit docs evidence** (when authorized)

---

### Task 7: Cold-start backtest script (M27-T2)

**Files:**
- Create: `scripts/pala_cold_start.py`
- Create: `scripts/test_pala_cold_start.py`
- Modify: `STATUS.md` (ms median row)

**Interfaces:**
- Consumes: subprocess timing for Doctor JSON, `pala_state` memory, `pala_report` render
- Produces: `{"n":3,"samples_ms":[...],"median_ms":...,"commands":[...]}` — **no percentages**

- [ ] **Step 1: Failing test for JSON shape**

```python
def test_cold_start_report_has_median_ms(self) -> None:
    report = pala_cold_start.run_benchmark(n=1, root=PLUGIN_ROOT)
    self.assertIn("median_ms", report)
    self.assertIsInstance(report["median_ms"], int)
    self.assertNotIn("%", json.dumps(report))
```

- [ ] **Step 2: Run — FAIL (module missing)**

- [ ] **Step 3: Implement `run_benchmark(n: int, root: Path) -> dict`**

Time only local commands; no network. Default `n=3`.

- [ ] **Step 4: Run unittest PASS; run CLI once; paste median into STATUS**

- [ ] **Step 5: Commit** (when authorized)

---

### Task 8: Version bump `0.8.1` + land M25/M10 working tree

**Files:**
- Modify: `.codex-plugin/plugin.json` version → `0.8.1+codex.<timestamp>`
- Modify: `CHANGELOG.md` `[0.8.1]` including issue #13 fixes + M25 shared memory
- Modify: `STATUS.md` / `PLAN.md` M27 tickets
- Include already-present uncommitted files: `pala_shared_memory.py`, `portable/cursor/`, `.cursor/rules/`, `pala_m10.py`, etc.
- Exclude: `codex-try-proof.png`, `codex-try-proof2.png`

- [ ] **Step 1: Bump manifest version string**

- [ ] **Step 2: Full gate**

```powershell
py -3 scripts\verify.py
```

Expected: PASSED + new ZIP SHA

- [ ] **Step 3: Reinstall from source + issue #13 acceptance**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Install
$root = "$env:LOCALAPPDATA\Pala\marketplace"
py -3 "$root\scripts\pala_self_audit.py" --root $root --profile runtime
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
# second Doctor after runtime audit must stay ready (not drifted)
```

- [ ] **Step 4: Close issue #13 checklist items that are done** via comment (owner)

- [ ] **Step 5: Commit + push + tag `v0.8.1` + `gh release create`** — **only with explicit owner emir**

---

### Task 9: Artifact E2E CI smoke (issue #13 P1, trimmed)

**Files:**
- Modify: `.github/workflows/quality.yml`

**Interfaces:**
- Consumes: `build_portable.py`, checkout
- Produces: job `artifact-install-smoke` on Windows: unzip portable → copy to temp marketplace-like root → `pala_self_audit --profile runtime` → assert exit 0; optional fingerprint stability after creating `__pycache__`

- [ ] **Step 1: Add job YAML** (no network install of Codex required)

- [ ] **Step 2: Push branch / watch Actions** (when authorized)

- [ ] **Step 3: Commit**

---

### Task 10: Codex plugin checklist doc (M27-T1)

**Files:**
- Create: `docs/CODEX_PLUGIN_CHECKLIST.md`
- Modify: `docs/README.md` index link
- Modify: `STATUS.md` checklist evidence table

Map each row to: manifest, marketplace, hooks convention, skill budget, SessionStart limit, `/hooks` trust, installed vs source verify.

- [ ] **Step 1: Write checklist with `passed`/`not-run` columns filled from Tasks 1–8**

- [ ] **Step 2: Commit** (when authorized)

---

## Self-review (writing-plans)

1. **Spec coverage:** Issue #13 P0 fingerprint + runtime verify + PYTHONUTF8 + README + E2E CI → Tasks 1–5, 9. M27 live Codex + cold-start → Tasks 6–7. Uncommitted M25 ship → Task 8. Open PR: none; issue #13 tracked.
2. **Placeholders:** None intentional; Task 1 test may need REQUIRED_FILES stubs — preferred path uses `copy_bundle(PLUGIN_ROOT)`.
3. **Types:** `run_audit(root, profile: str)`, `verify --mode`, `tree_fingerprint(root) -> str` consistent across tasks.

## Out of scope

- ChatGPT Plus install surface
- Cloud shared DB / Cursor hook parity
- OpenAI Plugins Directory submission (separate authority)
- Force-push, `--dangerously-bypass-hook-trust`

---

Plan complete and saved to `docs/superpowers/plans/2026-08-08-m27-install-artifact-and-standards.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — this session with executing-plans style checkpoints  

Which approach?
