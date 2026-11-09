<#
.SYNOPSIS
    Sets up the scheduled refresh of the game predictions on this PC.

.DESCRIPTION
    stats.nba.com, where results and the schedule come from, refuses cloud servers such as GitHub's, so
    results are refreshed from a home PC. This script:

      1. clones the repository into its own folder (default %LOCALAPPDATA%\NBAAnalyticsRefresh\repo),
         so the refresh never commits on the branch you are working on or touches your changes
      2. creates a Python environment there and installs requirements.txt
      3. copies the downloaded injury reports from this checkout, so they aren't downloaded again
      4. registers a Windows scheduled task that runs scripts\refresh.ps1 in that clone

    The task runs three times a day, at times on this PC's clock. A run missed while the PC was off or
    asleep starts as soon as it is back on. The GitHub Actions refresh keeps the injury report fresh
    in between. The log is data\cache\refresh.log in the clone.

    Run it again after requirements.txt changes, or to change the times. Python 3.11+ must be installed.

.EXAMPLE
    .\scripts\install-refresh-task.ps1
.EXAMPLE
    .\scripts\install-refresh-task.ps1 -Times '19:00', '23:30'
.EXAMPLE
    .\scripts\install-refresh-task.ps1 -Remove
#>
param(
    [string]$Folder = (Join-Path $env:LOCALAPPDATA 'NBAAnalyticsRefresh'),
    # This PC's clock (set for India, US Eastern + 10:30 in winter). NBA games end by about 1:30 AM
    # Eastern (noon here): 8 PM picks up last night's results, 5 AM comes just before the evening games.
    [string[]]$Times = @('20:00', '00:00', '05:00'),
    [string]$Python = 'python',
    [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$taskName = 'NBA Analytics game refresh'

function Invoke-Native([string]$exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "$exe $($arguments -join ' ') failed (exit $LASTEXITCODE)" }
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed the scheduled task. The clone in $Folder is left in place; delete it if you like."
    return
}

$source = Split-Path $PSScriptRoot -Parent
$repo = Join-Path $Folder 'repo'

if (-not (Test-Path (Join-Path $repo '.git'))) {
    $url = (& git -C $source remote get-url origin).Trim()
    Write-Host "Cloning $url into $repo"
    New-Item -ItemType Directory -Force $Folder | Out-Null
    Invoke-Native git @('clone', '--quiet', '--branch', 'main', $url, $repo)
} else {
    Write-Host "Updating the clone in $repo"
    Invoke-Native git @('-C', $repo, 'pull', '--quiet', '--ff-only')
}

$venvPython = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Host 'Creating the Python environment'
    Invoke-Native $Python @('-m', 'venv', (Join-Path $repo '.venv'))
}
Write-Host 'Installing requirements'
Invoke-Native $venvPython @('-m', 'pip', 'install', '--quiet', '--disable-pip-version-check', '-r', (Join-Path $repo 'requirements.txt'))

$cache = Join-Path $source 'data\cache'
if (Test-Path $cache) {
    Write-Host 'Copying the downloaded injury reports'
    robocopy $cache (Join-Path $repo 'data\cache') /E /XO /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed (exit $LASTEXITCODE)" }
}

$localTimes = foreach ($time in $Times) { [DateTime]::ParseExact($time, 'HH:mm', $null) }

$script = Join-Path $repo 'scripts\refresh.ps1'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`"" `
    -WorkingDirectory $repo
$triggers = foreach ($at in $localTimes) { New-ScheduledTaskTrigger -Daily -At $at }
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
# Runs as you, while you are signed in, so git can use your saved GitHub sign-in to push
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggers -Settings $settings `
    -Principal $principal -Force `
    -Description 'Refreshes the NBA Analytics game predictions (results, schedule, injury report) and pushes them to GitHub.' |
    Out-Null

Write-Host ''
Write-Host "Scheduled '$taskName' daily at $(($localTimes | ForEach-Object { $_.ToString('HH:mm') }) -join ', ') (this PC's time)."
Write-Host "Run it now:   Start-ScheduledTask -TaskName '$taskName'"
Write-Host "Its log:      $(Join-Path $repo 'data\cache\refresh.log')"
Write-Host "Remove it:    .\scripts\install-refresh-task.ps1 -Remove"
