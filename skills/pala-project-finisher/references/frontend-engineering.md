# Frontend Engineering

Follow the existing router, rendering model, component library, styling system,
state conventions, and accessibility baseline. For a new frontend, derive
these from the accepted architecture and design direction.

Own code by user capability:

```text
app shell/routing
features/<capability>
shared UI primitives
API and wire adapters
shared hooks/utilities
tokens/global foundations
test support
```

This is a responsibility map, not a mandatory folder template. Colocate
feature-specific components, state, schemas, and tests. Promote code to shared
only after real reuse.

Keep route/page/App components as composition boundaries. Move data loading,
mutations, validation, and derived behavior into named owners. Keep server
state, URL state, form state, and ephemeral UI state distinct. Avoid a global
store until cross-feature coordination proves it necessary.

For Next.js or another hybrid framework, inspect the installed framework
version and current official guidance before applying version-specific routing,
rendering, or server/client conventions. Preserve the existing boundary unless
the accepted architecture requires a change. Do not expose secrets or trusted
authorization decisions to the browser.

For React/Vite or another SPA, keep transport in an API adapter rather than
components. Validate wire data at the boundary when failure would otherwise
corrupt state. Model loading, empty, error, stale, success, and denied states.

Use Tailwind CSS or shadcn/ui only when selected or already present. Reuse
tokens and primitives; do not mix a copied template's theme with a second
design system. Strip template demo data, routes, branding, analytics, auth
assumptions, and unused packages.

Require semantic HTML, labels, keyboard operation, visible focus, meaningful
headings, responsive behavior, stable list keys, safe rendering, and honest
data states. Build the real usable product surface before marketing decoration.

Verify with the real development/preview process and Browser/IAB when
available. Exercise the core workflow, inspect console/network errors, and
check at least one narrow and one wide viewport. A successful build is not
visual or interaction proof.
