# Investigating a Windows Crash

Windows Health Monitor preserves context for later analysis; it does not prevent a blue screen,
driver reset, power loss, or hardware failure. Its value is the timeline that survives the reboot.

## Immediately After a Crash

1. Let Windows finish starting and wait for the monitor's configured startup delay.
2. Do not run disk cleanup or delete `MEMORY.DMP`, minidumps, or live-kernel reports.
3. Run `scripts\windows\show-monitor-status.ps1` and confirm the heartbeat advances.
4. Copy the relevant hourly metrics, event log, and crash-artifact inventory to a separate working
   directory before experimenting with drivers or system settings.
5. If full-dump archiving was enabled, confirm `CrashArchiveStatus` names the retained dump.

The monitor's default evidence is stored under `%ProgramData%\WindowsHealthMonitor`. See the
[operations guide](operations.md) for the complete layout and access rules.

## Build a Timeline

Start with the last healthy metrics before the failure, then correlate them with System events and
crash artifacts:

- `Kernel-Power` event 41 confirms an unexpected shutdown or restart, but does not identify the
  root cause on its own.
- `WER-SystemErrorReporting` and BugCheck events can contain the stop code and dump location.
- Display, `dxgkrnl`, and vendor display-driver events can indicate GPU resets or timeouts.
- `WHEA` events can indicate hardware-reported CPU, memory, PCIe, or bus errors.
- Disk, NTFS, storage, USB, and Plug and Play events help correlate device removal or I/O failures.
- `crash-artifacts.json` records paths, sizes, and timestamps; it does not parse dump contents.

An event near the crash is correlation, not proof. Prefer the kernel dump's failing stack and
module evidence, then use metrics and events to confirm the surrounding conditions.

## Analyze a Dump

Open the preserved dump in a compatible Windows debugger and begin with:

```text
!analyze -v
```

Record the bugcheck code, parameters, failing thread, stack, named module, and debugger bucket.
Compare the dump timestamp with the monitor's event and metric files. A named driver is strong
evidence when the faulting instruction and stack are inside that module; it is not automatically
proof that the physical device is defective.

Keep the original dump unchanged. Work from a copy, especially before installing symbols or
running third-party analysis tools.

## Known Blind Spots

- A complete kernel freeze or sudden power loss can prevent the current in-memory sample from
  reaching disk.
- Windows must be configured to write a dump, and the destination needs enough free space.
- A rapidly rolling System event log can discard older evidence before the monitor reads it.
- Sampling can miss short spikes between intervals.
- Full memory dumps can contain credentials, document contents, encryption material, and other
  private memory. Never publish one without an explicit disclosure review.

If evidence remains inconclusive, use Windows Performance Recorder or targeted vendor diagnostics
for the next reproduction rather than increasing every monitor frequency indefinitely.

