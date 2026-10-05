# Read-only check: is a Frontier Core already running? Writes result for diagnostics.
$out = Join-Path $PSScriptRoot '..\Saves\Guardian_Test\Logs\session-preflight.txt'
$core = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
  Where-Object { $_.CommandLine -match 'frontier\.probe' }
$d2 = Get-Process destiny2 -ErrorAction SilentlyContinue
$nms = Get-Process NMS -ErrorAction SilentlyContinue
$lines = @("time=$(Get-Date -Format o)",
  "core_count=$(@($core).Count)",
  ($core | ForEach-Object { "core pid=$($_.ProcessId) cmd=$($_.CommandLine)" }),
  "destiny2_running=$([bool]$d2)", "nms_running=$([bool]$nms)")
$lines | Out-File -Encoding utf8 $out
if (@($core).Count -gt 0) { exit 1 } else { exit 0 }
