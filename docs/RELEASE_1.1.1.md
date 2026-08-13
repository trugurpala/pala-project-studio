# Pala 1.1.1

Pala 1.1.1 is a focused Control Center and Codex-native verification patch.

## Fixed

- A clean installation with no active project renders the complete read-only
  `PALA CONTROL CENTER` and its four owner questions.
- Active-project and unreadable-project states keep the same owner surface;
  unreadable data is reported without exposing a stack trace.
- Current UI identity comes from `product-identity.json`.
- Both `paneli aç` and `paneli ac` open one refreshed Control Center; ordinary
  workflows do not open browser or helper UI.

## Artifact

The release artifact is `pala-project-studio-1.1.1.zip`. Its checksum and
evidence manifest are attached to the public release after deterministic source,
portable, installed-profile, isolated Codex, and Quality Engine verification.

Pala 1.1.0 remains an immutable historical public release.
