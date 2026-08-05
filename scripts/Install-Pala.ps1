<#
    .SYNOPSIS
    Pala Project Studio'yu atomik ve idempotent bicimde yonetir.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet("Install", "Doctor", "Repair", "Update", "Uninstall")]
    [string]$Mode = "Install"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

$pluginRoot = Split-Path -Path $PSScriptRoot -Parent
$core = Join-Path $PSScriptRoot "pala_installer.py"
$logRoot = Join-Path $env:LOCALAPPDATA "Pala\logs"
$logFile = Join-Path $logRoot "install-pala.log"

function Resolve-PalaPython {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) { return @($launcher.Source, "-3") }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @($python.Source) }
    throw "Python bulunamadi. Pala icin Python 3.10 veya ustu gereklidir."
}

function Write-PalaLog([string]$Text) {
    if (-not (Test-Path -LiteralPath $logRoot)) {
        New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
    }
    if ((Test-Path -LiteralPath $logFile) -and
        (Get-Item -LiteralPath $logFile).Length -gt 1MB) {
        $archive = Join-Path $logRoot "install-pala.previous.log"
        Move-Item -LiteralPath $logFile -Destination $archive -Force
    }
    $safe = $Text -replace '(?i)(token|password|secret|api[_-]?key)\s*[:=]\s*\S+', '$1=[redacted]'
    Add-Content -LiteralPath $logFile -Value ("{0:u} [{1}] {2}" -f (Get-Date), $Mode, $safe)
}

function Show-PalaResult([pscustomobject]$Payload) {
    switch ($Payload.status) {
        "ready" { Write-Host "[Pala] Zaten hazir; dosyalar degistirilmedi." }
        "installed" { Write-Host "[Pala] Kurulum tamamlandi." }
        "migrated" { Write-Host "[Pala] Onceki Pala kurulumu guvenle guncellendi ve yonetim kaydi olusturuldu." }
        "updated" { Write-Host "[Pala] Guncelleme tamamlandi." }
        "repaired" { Write-Host "[Pala] Bozuk Pala kurulumu onarildi." }
        "uninstalled" { Write-Host "[Pala] Pala'ya ait kurulum kaldirildi." }
        "absent" { Write-Host "[Pala] Kaldirilacak Pala kurulumu yok." }
        "would_install" { Write-Host "[Pala] Onizleme: Pala kurulacak." }
        "would_update" { Write-Host "[Pala] Onizleme: Pala guncellenecek." }
        "would_repair" { Write-Host "[Pala] Onizleme: Pala onarilacak." }
        "would_uninstall" { Write-Host "[Pala] Onizleme: Pala kaldirilacak." }
        "external_conflict" { Write-Host "[Pala] Ayni konumda Pala'ya ait oldugu dogrulanamayan icerik var; dokunulmadi." }
        "modified" { Write-Host "[Pala] Kurulum sonradan degistirilmis; kullanici dosyalarini korumak icin dokunulmadi." }
        default {
            if ($null -ne $Payload.healthy) {
                $pluginStatus = $Payload.plugin.status
                Write-Host "[Pala] Doctor: healthy=$($Payload.healthy), plugin=$pluginStatus"
            } else {
                Write-Host "[Pala] Sonuç: $($Payload.status)"
            }
        }
    }
}

if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {
    throw "Pala kurulum cekirdegi bulunamadi: $core"
}

$pythonCommand = Resolve-PalaPython
$executable = $pythonCommand[0]
$arguments = @()
if ($pythonCommand.Count -gt 1) { $arguments += $pythonCommand[1..($pythonCommand.Count - 1)] }
$arguments += @($core, $Mode.ToLowerInvariant(), "--source", $pluginRoot)
if ($WhatIfPreference) { $arguments += "--dry-run" }

Write-Host "[Pala] Islem: $Mode"
$raw = (& $executable @arguments 2>&1 | Out-String).Trim()
$exitCode = $LASTEXITCODE
try {
    $payload = $raw | ConvertFrom-Json
} catch {
    Write-PalaLog "Kurulum cekirdegi gecersiz cikti uretti."
    Write-Error "Pala kurulum sonucu okunamadi."
    exit 1
}

Show-PalaResult $payload
if (-not $WhatIfPreference) {
    Write-PalaLog ("status={0}; changed={1}" -f $payload.status, $payload.changed)
}
if ($exitCode -ne 0) { exit $exitCode }

if ($Mode -in @("Install", "Update", "Repair") -and -not $WhatIfPreference) {
    $doctorArgs = @()
    if ($pythonCommand.Count -gt 1) { $doctorArgs += $pythonCommand[1..($pythonCommand.Count - 1)] }
    $doctorArgs += @($core, "doctor", "--source", $pluginRoot)
    $doctorRaw = (& $executable @doctorArgs 2>&1 | Out-String).Trim()
    $doctorExit = $LASTEXITCODE
    $doctor = $doctorRaw | ConvertFrom-Json
    Show-PalaResult $doctor
    Write-PalaLog ("doctor_healthy={0}; plugin={1}" -f $doctor.healthy, $doctor.plugin.status)
    if ($doctorExit -ne 0) { exit $doctorExit }
    Write-Host "[Pala] Yeni skill ve hook'larin yuklenmesi icin yeni bir Codex sohbeti acin."
}

exit 0
