# Owner Demo Handoff

Apply this profile when the product has a user-visible runtime or the user asks
for an ongoing owner, patron, stakeholder, or demo report. Reuse an existing
demo document. Otherwise create `reports/OWNER_DEMO.md` from the bundled
template after the first coherent ticket produces something meaningful to
show. Do not create it for a read-only or plan-only request.

After creating it in a registered project whose manifest has no demo path, run
`register --demo reports/OWNER_DEMO.md` with the existing project paths so the
file joins future checkpoint fingerprints. Do not rewrite product content or
registration state merely to create a read-only report.

Update the report at a coherent ticket, milestone, or user-visible acceptance
boundary—not after every edit. Keep it short and in the user's language:

- what is usable now and what visibly changed;
- exact local URL or start command;
- 1–5 safe steps the owner can try;
- login/setup method without a static credential;
- verification marked `passed`, `failed`, `blocked`, or `not run`;
- known visible limits and exactly one next visible outcome;
- timestamp plus commit/build identity when available.

Capture a screenshot only after opening the actual runtime in a real browser,
checking the relevant flow, console/network state, and narrow/wide layout when
applicable. Prefer a repository-relative link under the project's chosen
report-artifact directory. Say `not run` when browser tooling or runtime is not
available. Never use image generation as proof of implemented UI and never
claim an old screenshot represents a newer ticket.

Never include passwords, tokens, private URLs with credentials, customer data,
payment or identity data, production records, or sensitive documents. Use
synthetic fixtures, redact visible identifiers, and follow the repository's
artifact/Git policy before tracking an image. The owner report summarizes
evidence; it does not replace technical status, tests, or phase reports.

Template: [OWNER_DEMO_TEMPLATE.md](../assets/OWNER_DEMO_TEMPLATE.md).
