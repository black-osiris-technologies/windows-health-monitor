# Contributing

## Branching

- `master`: stable/release branch.
- `develop`: integration branch.
- `feature/*`: task branches.

Pull requests are expected for changes into `develop` and `master`.

## Checks

Before opening a PR:

```powershell
python -m pytest
python -m ruff check .
```

## Scope

This project is Windows-first. Cross-platform support should not complicate the Windows diagnostic path unless there is a clear benefit.
