# Changelog

All notable changes are documented here using [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-08-28

### Added

- Durable Windows System event cursors and restart lookback capture.
- Crash-dump and live-kernel-report inventory with optional retained `MEMORY.DMP` archives.
- Atomic heartbeat status, runtime error logging, and collector-loop recovery.
- Elevated Scheduled Task installer, status command, and safe uninstaller for automatic startup.
- Independent GPU sampling intervals for lower overhead on hybrid-graphics laptops.

### Changed

- Background upgrades now stage code, stop the existing task, replace the package, and verify
  the newly registered task is running before returning.
- Windows event collection now imports the built-in diagnostics module by an explicit system path
  so constrained background environments do not silently lose event data.
- Status output now includes the installed monitor version, hexadecimal Task Scheduler result,
  and heartbeat age.
- Added operator and crash-investigation documentation for unattended deployments.
- CI now parses all Windows PowerShell scripts in addition to Python tests, lint, and builds.

## [0.2.0] - 2026-07-12

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

[Unreleased]: https://github.com/black-osiris-technologies/windows-health-monitor/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/black-osiris-technologies/windows-health-monitor/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/black-osiris-technologies/windows-health-monitor/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/black-osiris-technologies/windows-health-monitor/releases/tag/v0.1.0
