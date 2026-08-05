<#
    .SYNOPSIS
    Install, inspect or uninstall the Pala Project Studio plugin bundle for the current Windows user.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("Install", "Doctor", "Repair", "Uninstall")]
    [string]$Mode = "Install"
)

$ErrorActionPreference = "Stop"

$pluginRoot = Split-Path -Path $PSScriptRoot -Parent
$installRoot = Join-Path $env:USERPROFILE "plugins\pala-project-studio"
$logDir = Join-Path $env:LOCALAPPDATA "Pala\logs"
$logFile = Join-Path $logDir "install-pala.log"

$requiredFiles = @(
    (Join-Path $pluginRoot ".codex-plugin\plugin.json"),
    (Join-Path $pluginRoot "scripts\pala_state.py"),
    (Join-Path $pluginRoot "scripts\pala_hook.py"),
    (Join-Path $pluginRoot "hooks\hooks.json")
)

function Write-InstallLog {
    param([string]$Message)
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $entry = "{0:u} [{1}] {2}" -f (Get-Date), $Mode, $Message
    Add-Content -Path $logFile -Value $entry
}

function Resolve-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return $py.Source }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return $python.Source }
    throw "Python bulunamadı. py veya python komutu kurulu olmalı."
}

function Invoke-PalaDoctor {
    $python = Resolve-Python
    $scriptPath = Join-Path $pluginRoot "scripts\pala_state.py"
    $json = & $python $scriptPath "doctor" "--cwd" $pluginRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[Pala] Doctor command failed."
        return $false
    }
    try {
        $payload = $json | ConvertFrom-Json
    } catch {
        Write-Host "[Pala] Doctor output could not be parsed as JSON."
        return $false
    }
    $payload | ConvertTo-Json -Depth 8
    if ($payload.healthy -eq $true) {
        return $true
    }
    Write-Host "[Pala] Repair suggestion: run /hooks and /doctor once again after hook changes."
    return $false
}

function Test-PluginBundle {
    foreach ($path in $requiredFiles) {
        if (-not (Test-Path $path)) {
            throw "Eksik dosya: $path"
        }
    }
}

function Install-Bundle {
    Test-PluginBundle
    if ($PSCmdlet.ShouldProcess($installRoot, "Install or update Pala")) {
        if (Test-Path $installRoot) {
            Remove-Item -Path $installRoot -Recurse -Force
        }
        Copy-Item -Path (Join-Path $pluginRoot "*") -Destination $installRoot -Recurse
        Write-InstallLog "Installed or updated from $pluginRoot to $installRoot"
        Write-Host "[Pala] Install completed: $installRoot"
    }
}

function Uninstall-Bundle {
    if ($PSCmdlet.ShouldProcess($installRoot, "Remove installed Pala")) {
        if (Test-Path $installRoot) {
            Remove-Item -Path $installRoot -Recurse -Force
            Write-InstallLog "Uninstalled from $installRoot"
            Write-Host "[Pala] Uninstall completed."
        } else {
            Write-Host "[Pala] No installation found."
        }
    }
}

function Invoke-Repair {
    Write-Host "[Pala] Repair flow: uninstalling then reinstalling."
    Uninstall-Bundle
    Install-Bundle
    Write-Host "[Pala] Repair flow completed."
}

Write-Host "[Pala] Mode: $Mode"
switch ($Mode) {
    "Install" {
        Install-Bundle
        $ok = Invoke-PalaDoctor
        Write-Host "[Pala] Doctor check passed: $ok"
    }
    "Doctor" {
        $ok = Invoke-PalaDoctor
        Write-Host "[Pala] Doctor check passed: $ok"
        if (-not $ok) { exit 2 }
    }
    "Repair" {
        Invoke-Repair
        $ok = Invoke-PalaDoctor
        Write-Host "[Pala] Post-repair doctor check passed: $ok"
        if (-not $ok) { exit 2 }
    }
    "Uninstall" {
        Uninstall-Bundle
    }
}
