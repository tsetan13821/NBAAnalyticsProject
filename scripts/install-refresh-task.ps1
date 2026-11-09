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

    The task runs three times a day, at times given in US Eastern time and converted to this PC's time
    zone. A run missed while the PC was off or asleep starts as soon as it is back on. The pre-game
    injury reports, overnight in Asia and Europe, are covered by the GitHub Actions refresh. The log is
    data\cache\refresh.log in the clone.

    Run it again after requirements.txt changes, or to change the times. Python 3.11+ must be installed.

.EXAMPLE
    .\scripts\install-refresh-task.ps1
.EXAMPLE
    .\scripts\install-refresh-task.ps1 -Remove
#>
param(
    [string]$Folder = (Join-Path $env:LOCALAPPDATA 'NBAAnalyticsRefresh'),
    # US Eastern. Games end by about 1:30 AM ET and the results are online soon after.
    [string[]]$EasternTimes = @('02:30', '08:00', '12:30'),
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

# Eastern times to this PC's clock (computed for today: rerun after a daylight-saving change to stay exact)
$eastern = [TimeZoneInfo]::FindSystemTimeZoneById('Eastern Standard Time')
$today = [DateTime]::Today
$localTimes = foreach ($time in $EasternTimes) {
    $et = [DateTime]::ParseExact($time, 'HH:mm', $null)
    $at = [DateTime]::new($today.Year, $today.Month, $today.Day, $et.Hour, $et.Minute, 0, [DateTimeKind]::Unspecified)
    [TimeZoneInfo]::ConvertTime($at, $eastern, [TimeZoneInfo]::Local)
}

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
