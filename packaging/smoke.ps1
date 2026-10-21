param([Parameter(Mandatory=$true)][string]$Installer,[string]$Name='smoke')
$ErrorActionPreference = 'Stop'
$installerProcess = Start-Process $Installer -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -PassThru -Wait
if ($installerProcess.ExitCode -ne 0) { throw 'Installer failed' }
$report = Join-Path $env:RUNNER_TEMP "applypilot-$Name.json"
$p = Start-Process "$env:LOCALAPPDATA\Programs\ApplyPilot\ApplyPilot.exe" -ArgumentList '--smoke-test', $report -PassThru
if (-not $p.WaitForExit(120000)) { Stop-Process -Id $p.Id; throw 'Installed smoke test timed out' }
if (Test-Path $report) { Write-Output (Get-Content $report -Raw) }
if ($p.ExitCode -ne 0 -or -not (Test-Path $report)) { throw 'Installed smoke test failed' }
$result = Get-Content $report -Raw | ConvertFrom-Json
if (-not $result.ok) { throw ($result | ConvertTo-Json) }
Write-Output ($result | ConvertTo-Json)
