# Pala 0.9.5 — Modified install-tree integrity

## Promise

Pala never treats a managed installation as safe to replace merely because the
allowlisted Pala files still look correct. The install-state file records an
exact relative-path and SHA-256 manifest for every copied bundle file.

If any installed path is added, removed, changed, unreadable, or a symlink,
the installation is `modified`. This is a preservation state, not an error
that Pala is allowed to repair automatically.

## Consequences

| Surface | Modified tree result |
| --- | --- |
| Doctor | `plugin=modified`, core `healthy=false`, and one human recovery hint |
| Install / Repair / Update | `modified`, `changed=false`; no bundle swap and no Codex plugin mutation |
| Uninstall | `modified`, `changed=false`; the tree remains intact |

Only bytecode under a real `__pycache__` directory is an allowed runtime
leftover. A `.pyc` or `.pyo` file elsewhere can be user data and therefore
blocks automatic replacement or deletion.

## Recovery boundary

The owner reviews and preserves the changed files first. After deliberately
restoring a known Pala bundle (or moving the user material outside the Pala
install root), Doctor can return `ready` and a normal Repair/Update can resume.
Pala does not delete, move, merge, or overwrite that material on the owner's
behalf.

## T5 ownership boundary

`pala_installer.py` is the compatibility facade. Shared constants and atomic
state writes live in `pala_installer_shared.py`; bundle admission, exact-file
hashes, and modified-tree detection live in `pala_installer_integrity.py`.
`pala_installer_transaction.py` alone owns staging, activation, rollback, and
verified uninstall transactions. `pala_installer_core.py` keeps Codex bridge
adapters, managed state, and doctor observation separate from mutations.

All runtime siblings are required bundle files. `validate_bundle()` rejects a
missing helper before a stage directory is created or an installed tree can be
replaced. The existing added/changed/symlink/bytecode and rollback contract
tests remain the preservation proof.
