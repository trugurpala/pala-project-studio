# Backend Engineering

Follow existing service boundaries and conventions. For new services, begin as
one deployable unit and separate responsibilities through modules before
introducing processes or microservices.

Use this dependency direction when compatible with the language/framework:

```text
transport/API -> application/use cases -> domain
infrastructure/providers -> domain/application interfaces
domain -> no web, database, filesystem, clock, or vendor implementation
```

Keep routes/controllers thin: parse and authorize input, call one use case, and
map the result. Put business invariants in domain owners, orchestration in use
cases, and external effects behind explicit adapters. Do not reuse transport
DTOs as mutable domain state merely to save a type.

Define:

- typed configuration with startup validation and no committed secrets;
- stable error categories and safe client-facing mappings;
- structured logs with correlation fields and no sensitive payloads;
- explicit time, timezone, money/precision, identity, null, and retry semantics;
- transaction and idempotency boundaries for state-changing operations;
- migration ownership and rollback/compatibility rules for persisted schemas;
- timeouts, bounded pagination/batches, backpressure, and cancellation where
  external work can grow.

Validate external input at the boundary and external responses before trusted
use. Authentication identifies callers; authorization remains at the trusted
operation/data boundary. Never rely on hidden UI controls for permission.

Tests should cover domain invariants without a server, use cases with controlled
adapters, API contracts through the public transport, and real persistence
integration where schema/query behavior matters. Mock only unstable external
systems, not the behavior being asserted.

Run the documented server or worker, verify startup/health, exercise the
changed API or job path, and inspect errors/logs. A unit-test-only backend is
not operationally complete.
