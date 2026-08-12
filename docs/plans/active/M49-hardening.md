# M49 — Tavsiye mektubu sertleştirmesi

## Amaç

Pala 0.9.0'ı tek makinede çalışan, canonical task/lease/evidence/handoff
çekirdeği olarak sertleştirmek. GitHub yazma, çok-makine koordinasyonu ve host
edit sandbox'ı kapsam dışıdır.

## Kartlar

- M49-T0 — State authority ve mevcut kapı denetimi: `passed`
- M49-T1 — v4 task contract, assignee/lease, acceptance/evidence/basis: `passed`
- M49-T2 — Git common-dir repo-global claim ve stale/orphan lease: `passed`
- M49-T3 — Recovery transition, dependency DAG, retry/block policy: `passed`
- M49-T4 — Source/portable/installed knowledge link ve artifact contract: `passed`
- M49-T5 — GitHub read-only allowlist ve typed conflict: `passed`
- M49-T6 — Skill, limitations ve completion-loop entegrasyonu: `passed`
- M49-T7 — Tam kapı, self-audit ve yeni aday ZIP: `passed`

## Son kanıt

- Full discovery: `454` test, `1` controlled skip, exit `0`.
- P0 smoke: `passed`, `rows=10`.
- Source/installed/portable verify: `passed`.
- Self-audit: `passed`, `9/9` checks.
- Portable candidate: `dist/pala-project-studio-0.9.0-final-r5.zip`, `188` entries,
  SHA-256 `17619BA93999CC58F915168027A6E8C5BF22207C3F6C064311C6F608A02619F0`.

## Kanıt politikası

`passed` yalnız gerçek exit code/evidence sonrası yazılır. `/hooks` insan güveni
`configured-not-verified`; uzak Scorecard ve yayın işlemleri `not-run` kalır.
