# Changelog

All notable changes are documented here using [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Renamed the project and Python package from `omp-windows-health-monitor` to `windows-health-monitor`.
- Introduced `WHM_*` configuration names while preserving legacy `OMP_HEALTH_*` aliases.
- Expanded documentation, CI, contribution, and security guidance.

## [0.1.0] - 2026-07-12

### Added

- Windows system sampling and hourly log rotation.
- NVIDIA GPU collection through `nvidia-smi`.
- Windows System event collection.
- Optional daily-deduplicated email alerts.

[Unreleased]: https://github.com/black-osiris-technologies/windows-health-monitor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/black-osiris-technologies/windows-health-monitor/releases/tag/v0.1.0
