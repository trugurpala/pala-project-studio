# Reuse or Build

Run this gate before scaffolding, importing a template, or adding a dependency.

Search in this order:

1. Existing repository modules, components, generators, and dormant routes.
2. The selected framework's official generator, examples, registry, or blocks.
3. Already-installed packages and design-system primitives.
4. A small set of maintained GitHub repositories that match the exact stack
   and product surface.
5. Custom implementation for the remaining product-owned behavior.

For each material candidate record:

| Field | Required evidence |
| --- | --- |
| Identity | Repository/registry URL and exact release or commit |
| Rights | SPDX license, notices, commercial limits, asset/font terms |
| Compatibility | Runtime, framework, router, styling, package manager |
| Health | Recent releases/commits, issue posture, security advisories |
| Cost | Dependencies, bundle/runtime weight, generated/demo surface |
| Quality | Accessibility, responsive behavior, tests, build reproducibility |
| Adaptation | Files/features kept, removed, rewritten, and owned locally |

Choose the smallest reusable unit:

- Prefer an official primitive or block over a full template.
- Prefer a dependency over copied source when its public API is stable.
- Use a full template only when its information architecture substantially
  matches the requested product and removing demo code costs less than building
  the shell.
- Never inherit authentication, authorization, data models, telemetry,
  branding, fake dashboards, or deployment assumptions without explicit
  review.

Low-code means using trustworthy generators, registries, blocks, libraries, and
automation for undifferentiated work. It does not mean accumulating hidden
frameworks or surrendering product/domain ownership.

Before adoption, reproduce the candidate's install/build path in an isolated
temporary location or through read-only repository evidence. Preserve required
attribution and record the final decision, including why rejected candidates
were not used.
