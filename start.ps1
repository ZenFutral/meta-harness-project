<#
.SYNOPSIS
    Meta-Harness 1-Click PowerShell Launcher
.DESCRIPTION
    Starts all subsystems, builds/verifies Repomap index, initializes SWE Orchestrator state,
    starts the GUI web server, and launches the browser dashboard.
#>

param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8080,
    [switch]$NoBrowser,
    [switch]$SkipIndex
)

$Host.UI.RawUI.WindowTitle = "Meta-Harness // 1-Click Launcher"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

# Resolve python executable
$pyCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pyCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pyCmd = "py"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pyCmd = "python3"
}

if (-not $pyCmd) {
    Write-Host "[!] Error: Python was not found in your system PATH." -ForegroundColor Red
    Write-Host "[!] Please install Python 3.9+ from https://www.python.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

$argsList = @("start.py", "--host", $HostAddress, "--port", $Port.ToString())
if ($NoBrowser) { $argsList += "--no-browser" }
if ($SkipIndex) { $argsList += "--skip-index" }

& $pyCmd $argsList
