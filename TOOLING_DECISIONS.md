# Tooling decisions

| Capability | Class | Policy |
| --- | --- | --- |
| Kod anlayışı | DEFAULT | Pala-owned, versioned, integrity-verified; direct-source fallback |
| Güvenlik | DEFAULT | Isolated local rules; findings become blocking only through Quality Engine mapping |
| Tarayıcı doğrulama | PROJECT_PROFILE | Reuse an exact compatible project runner; no default browser MCP |
| Sembol hassasiyeti | LAZY_FALLBACK | Install and invoke only when default context plus source inspection are insufficient |
| Güncel harici belgeler | OPTIONAL_EXTERNAL | Never installed or registered by default; does not affect core health |

Development lint, type, coverage, dependency, and security tools are declared in
`pyproject.toml`, `uv.lock`, `.pala/quality.json`, and `package-lock.json`.
Provider pins and provenance are documented in `docs/ARCHITECTURE.md`.
