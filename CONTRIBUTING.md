# Contributing to Windows Health Monitor

## Before You Start

- Search existing issues and pull requests.
- Open an issue before large behavioral or architectural changes.
- Remove machine names, private event data, credentials, and personal email addresses from examples and reports.

## Development Workflow

1. Branch from the latest `develop` using `feature/<issue-id>` or `defect/<issue-id>`.
2. Keep Windows diagnostics reliable and avoid unrelated cross-platform abstractions.
3. Add or update tests for behavior changes.
4. Run the required checks.
5. Open a pull request into `develop` and complete the template.

```powershell
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

Release branches are promoted to `master` with normal merge commits and backmerged into `develop`. Release promotions must not be squashed.

## Engineering Expectations

- Keep local collection predictable and low overhead.
- Handle missing optional tools, permissions, and malformed event data gracefully.
- Preserve privacy-first defaults and never add required telemetry.
- Document changes to metrics, output schemas, environment variables, or retention behavior.

By participating, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).
