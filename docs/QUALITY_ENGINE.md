# Quality Engine and release evidence

Pala has one verification authority: the Quality Engine.

1. Discover applicable checks from the repository contract.
2. Freeze the source verification basis.
3. Run only approved commands through the mechanical runner.
4. Record real exit codes and output digests.
5. Map current required check IDs to explicit acceptance criteria.
6. Allow TaskContract `DONE` only when every mapped item is current and passed.

Verification tiers are `narrow`, `ticket`, `milestone`, and `release`. Hooks do
not execute gates. Provider health or advisory findings never substitute for a
Quality check.

Release verification includes source, portable, installed-profile, dependency,
security, policy, browser, migration/remnant, reproducibility, and publication
truth checks. A release asset is publishable only when two clean builds from the
same frozen source are byte-identical.

Failure Intelligence stores sanitized, verified fixes and does not create a
second completion authority. ReleaseTruth independently reports local build,
remote publication, and real deployment state.
