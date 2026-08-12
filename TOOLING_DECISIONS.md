# Tooling decisions

| Tool | Status | Evidence | Notes |
| --- | --- | --- | --- |
| uv | installed | `uv.lock`; project-local `.venv` | Dev-only; installer and portable bundle remain unchanged. |
| Ruff | installed | `artifacts/quality/m47-ruff-*.json` | `E,F,I,UP,B,SIM`, Python 3.10 target; changed-surface ratchet only. |
| Coverage.py | installed | `artifacts/quality/m47-coverage-final.{txt,json}` | Canonical `unittest` runner; measured 75% baseline. |
| Mypy | installed | `artifacts/quality/m47-mypy-baseline.txt` | Strict for six clean critical modules; broader core is deferred after baseline triage. |
| Pytest | installed | `artifacts/quality/m47-pytest-baseline.txt` | Compatibility runner only; `unittest` remains canonical. |
| Bandit | installed | `artifacts/quality/m47-bandit.json` | Release gate blocks High findings; lower findings require contextual triage. |
| pip-audit | installed | `artifacts/quality/m47-pip-audit.txt` | Audits project-local `.venv`; `uv.lock` direct mode is unsupported by pip-audit. |
| Pydantic v2 | not_installed | M47 decision | No external validation boundary justified a production dependency. |
| Loguru | not_installed | M47 decision | Stdlib logging insufficiency was not demonstrated. |

Statuses: installed | recommended | installed_unverified | not_installed | unavailable
