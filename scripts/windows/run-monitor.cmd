@echo off
cd /d C:\Users\madal\Documents\Codex\2026-07-08\daca-iti-dau-comenzi-de-aici
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\monitor-system.ps1 -IntervalSeconds 10 -OutputDir .\monitor-logs -RetentionDays 3
