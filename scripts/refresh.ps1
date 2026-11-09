# Refreshes the game predictions and publishes them to GitHub (src.game_model.refresh --push), logging
# to data\cache\refresh.log. The scheduled task set up by install-refresh-task.ps1 runs this inside its
# own clone of the repository, never in the folder you work in.

$ErrorActionPreference = 'Continue'
$repo = Split-Path $PSScriptRoot -Parent
$log = Join-Path $repo 'data\cache\refresh.log'
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
if ((Test-Path $log) -and (Get-Item $log).Length -gt 2MB) {
    Move-Item -Force $log "$log.old"
}

function Write-Log([string]$line) {
    Add-Content -Path $log -Value $line -Encoding UTF8
}

Set-Location $repo
$env:PYTHONUNBUFFERED = '1'
$env:PYTHONIOENCODING = 'utf-8'
Write-Log "=== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') ==="
& "$repo\.venv\Scripts\python.exe" -m src.game_model.refresh --push 2>&1 | ForEach-Object { Write-Log "$_" }
$code = $LASTEXITCODE
Write-Log "exit $code"
exit $code
