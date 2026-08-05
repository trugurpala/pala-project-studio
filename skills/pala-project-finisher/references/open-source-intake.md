# Open Source Intake

Use external code to reduce undifferentiated work, not to surrender product
architecture. Before copying or adding it, compare a small set of maintained
candidates using primary repository evidence:

- exact repository and release/commit;
- SPDX license and attribution obligations;
- framework/version and runtime compatibility;
- maintenance and security posture;
- accessibility and responsiveness where relevant;
- dependency and bundle weight;
- amount of demo code, fake integration, branding, and dead assets;
- local test/build reproducibility.

Prefer a dependency or a small adapted component over importing a full
template. Preserve required notices. Do not use unclear-license material or
copy secrets, vendor data, placeholder credentials, proprietary assets, or
irrelevant demo routes.

Record every material intake in the mapped open-source document:

| Source | Version/commit | License | Imported scope | Modifications | Attribution |
| --- | --- | --- | --- | --- | --- |

Verify the adapted code using the repository's normal checks. The project's
domain logic, authorization, data provenance, financial rules, and other
high-risk boundaries remain project-owned.
