# Architecture Selection

Existing projects keep their framework, router, package manager, styling
system, test runner, and service boundaries unless evidence shows they cannot
meet the requested outcome.

For greenfield or materially changed products, compare only credible options:

| Need | Typical fit |
| --- | --- |
| SEO, server rendering, integrated web routes/actions, full-stack React | Next.js or an equivalent server-capable framework |
| Authenticated internal dashboard with a separate API | React with Vite or the existing SPA framework |
| Static content with limited interaction | Static/site framework before a full application stack |
| API, jobs, domain workflows | Existing backend language/framework or the smallest supported service |
| Desktop/mobile | Platform-appropriate shell with shared contracts, not a web framework by habit |

Decide from:

- deployment and hosting boundary;
- rendering and routing needs;
- authentication and authorization ownership;
- data locality, persistence, latency, offline, and background work;
- team/repository competence and maintenance cost;
- testing, observability, security, and upgrade path;
- availability of compatible maintained foundations.

Next.js, React, Tailwind CSS, shadcn/ui, SaaS, admin dashboard, and free-template
tags never constitute approval by themselves. Use Tailwind or a component
registry only when it matches the selected styling ownership and does not
create a second design system.

Record one accepted decision with alternatives and trade-offs. Avoid speculative
microservices, queues, databases, state libraries, design systems, or cloud
products. Start with one deployable unit unless a measured boundary requires
more.

Define dependency direction before folders. Business/domain rules must not
depend on UI, transport, storage, or provider implementations. Shared wire
contracts must not become a dumping ground for application behavior.
