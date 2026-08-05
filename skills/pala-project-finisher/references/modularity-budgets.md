# Modularity Budgets

Clean code is ownership and change safety, not maximum file count. Keep each
module focused enough that its purpose, public interface, dependencies, and
tests can be understood without reading unrelated behavior.

Use growth triggers during every ticket:

| Trigger | Required response |
| --- | --- |
| New responsibility in an already large/high-touch module | Create or extract a focused owner unless a documented invariant requires locality |
| Function or component mixes orchestration, validation, I/O, and presentation | Separate the independently testable responsibilities |
| Third copy of behavior or styling | Introduce the smallest shared abstraction |
| Public API grows for one internal caller | Keep it private or move ownership |
| New dependency replaces a small stable helper | Reject unless maintenance/security value exceeds its cost |

Numeric review heuristics:

- Around 800 lines in a high-touch source module: do not add another feature
  without a recorded reason or focused extraction.
- Around 80 lines in a function or 250 lines in a UI component: inspect for
  mixed responsibilities before extending it.

These are review triggers, not automatic rewrite commands. Generated files,
declarative schemas, data tables, and tightly coupled protocol definitions may
justify larger units. Record the reason. Never mix unrelated cleanup into a
feature ticket merely to satisfy a number.

Prefer feature ownership over horizontal dumping grounds named `utils`,
`helpers`, `common`, or `services`. Keep public surfaces small, dependencies
inward, side effects injectable, and tests near the behavior owner.

Low-code accelerators are welcome when they remove boilerplate and remain
inspectable, replaceable, licensed, and testable. Reject abstractions,
generators, or templates that hide the core workflow or make a small change
require edits across unrelated layers.
