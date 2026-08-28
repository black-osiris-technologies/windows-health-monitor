@echo off
setlocal
cd /d "%~dp0\..\.."
python -m windows_health_monitor monitor --interval 60 --gpu-interval 300 --output-dir monitor-logs --retention-days 30
