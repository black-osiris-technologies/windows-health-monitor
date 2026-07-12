# Security Policy

## Supported Versions

Security fixes are applied to the latest published release. Pre-1.0 fixes may be delivered through a newer minor release.

## Reporting a Vulnerability

Do not open a public issue for suspected vulnerabilities. Use [GitHub private vulnerability reporting](https://github.com/black-osiris-technologies/windows-health-monitor/security/advisories/new).

Include the affected version, reproduction steps, impact, and a suggested mitigation when available. Remove SMTP credentials, personal addresses, hostnames, process details, and private Windows event data.

## Data Sensitivity

The monitor can collect process names, host information, system metrics, and Windows event messages. Logs remain local unless the operator shares them or enables email delivery. Contributors must preserve local-only defaults and avoid introducing required telemetry or remote storage.
