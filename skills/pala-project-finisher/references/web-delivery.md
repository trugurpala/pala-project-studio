# Web Delivery

Preserve the working framework, router, package manager, styling system, and
server/client boundary. Detect installed versions before using version-specific
patterns. Do not migrate to Next.js, Tailwind, shadcn/ui, Supabase, or another
stack merely because the prompt contains a technology tag.

For React dashboards and SaaS applications:

- build a coherent responsive shell and clear page hierarchy;
- use semantic HTML, labels, visible focus, keyboard-safe controls, and stable
  list keys;
- model loading, empty, error, success, and permission-denied states;
- keep authentication, authorization, tenant, role, and entitlement checks at
  trusted server/data boundaries rather than hiding UI elements;
- keep secrets and privileged clients out of browser bundles;
- validate external input and avoid unsafe HTML;
- reuse existing components before adding dependencies.

Completion requires more than a build. Start the documented development or
preview command, open the relevant page in a browser when available, inspect
console/network failures, exercise the changed user flow, and check a narrow
and a wide viewport. Record the URL and observed result in project status.

If runtime needs unavailable credentials or services, verify the honest
missing-configuration state and report the exact external blocker. Do not add
fake production success.
