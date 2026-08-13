<#
    Pala installer entry point. The machine-readable ReleaseTruth lives in
    product-identity.json; this entry point does not own a second version.
    .SYNOPSIS
    Pala Project Studio'yu atomik ve idempotent bicimde yonetir.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet("Install", "Doctor", "Repair", "Update", "Uninstall", "Status")]
    [string]$Mode = "Install"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
# Keep Python JSON stdout UTF-8 so Doctor does not crash on cp1254 consoles.
if (-not $env:PYTHONIOENCODING) { $env:PYTHONIOENCODING = "utf-8" }
if (-not $env:PYTHONUTF8) { $env:PYTHONUTF8 = "1" }

$pluginRoot = Split-Path -Path $PSScriptRoot -Parent
$core = Join-Path $PSScriptRoot "pala_installer.py"

function Resolve-PalaPython {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) { return @($launcher.Source, "-3") }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @($python.Source) }
    throw "Python bulunamadi. Pala icin Python 3.10 veya ustu gereklidir."
}

function Extract-PalaJson([string]$Text) {
    $start = $Text.IndexOf("{")
    if ($start -lt 0) { return $null }
    $depth = 0
    $inString = $false
    $escaped = $false
    for ($index = $start; $index -lt $Text.Length; $index++) {
        $char = $Text[$index]
        if ($escaped) {
            $escaped = $false
            continue
        }
        if ($inString) {
            if ($char -eq '\') { $escaped = $true }
            elseif ($char -eq '"') { $inString = $false }
            continue
        }
        switch ($char) {
            '"' { $inString = $true }
            '{' { $depth += 1 }
            '}' {
                $depth -= 1
                if ($depth -eq 0) {
                    return $Text.Substring($start, $index - $start + 1)
                }
            }
        }
    }
    return $null
}

function Parse-PalaJson([string]$RawText) {
    $payloadText = Extract-PalaJson $RawText
    if ($null -eq $payloadText) { throw "Pala JSON yükü bulunamadi." }
    try {
        return $payloadText | ConvertFrom-Json -ErrorAction Stop
    } catch {
        throw "Pala JSON yükü ayrıştırılamadi."
    }
}

function Show-PalaGuiNextSteps([pscustomobject]$Payload) {
    if ($null -ne $Payload.gui_next_steps -and "$($Payload.gui_next_steps)".Trim().Length -gt 0) {
        Write-Host ""
        foreach ($line in ("$($Payload.gui_next_steps)" -split "`r?`n")) {
            if ("$line".Trim().Length -gt 0) {
                Write-Host "[Pala] $line"
            }
        }
        return
    }
    Write-Host ""
    Write-Host "[Pala] Sonraki 3 adim (Codex Work):"
    Write-Host "[Pala] 1) Plugins'te Pala gorunuyor mu kontrol edin."
    Write-Host "[Pala] 2) /hooks ile Pala hook guvenini (trust) verin."
    Write-Host "[Pala] 3) Yeni bir sohbet acin."
}

function Show-PalaResult([pscustomobject]$Payload) {
    if ($null -ne $Payload.version) {
        $displayVersion = "$($Payload.version)".Split("+")[0]
        Write-Host "[Pala] Pala $displayVersion"
    }
    if ($null -ne $Payload.healthy -and $null -ne $Payload.codex -and $null -ne $Payload.plugin) {
        $pluginStatus = $Payload.plugin.status
        $codexStatus = $Payload.codex.status
        Write-Host "[Pala] Doctor: healthy=$($Payload.healthy), plugin=$pluginStatus, codex=$codexStatus"
        if ($null -ne $Payload.source_version) { Write-Host "[Pala] Source=$($Payload.source_version) (base=$($Payload.source_base_version)), beklenen=$($Payload.expected_version) (base=$($Payload.expected_base_version)), bundle=$($Payload.installed_bundle_version), Codex plugin=$($Payload.codex_plugin_version)" }
        if ($null -ne $Payload.marketplace_source_type) { Write-Host "[Pala] Marketplace kaynak=$($Payload.marketplace_source_type), refresh=$($Payload.marketplace_refresh_status), cache=$($Payload.cache_status), version-ready=$($Payload.version_ready)" }
        if ($null -ne $Payload.plugin_ready) {
            Write-Host "[Pala] Cekirdek(plugin_ready)=$($Payload.plugin_ready)"
        }
        if ($null -ne $Payload.workbench) {
            Write-Host "[Pala] Professional Workbench=$($Payload.workbench.status)"
        }
        Write-Host "[Pala] Python=$($Payload.python.ready), Git=$($Payload.git.ready), Codex CLI=$($Payload.codex_cli.ready), Node=$($Payload.node.ready), uv=$($Payload.uv.ready)"
        if ($null -ne $Payload.codex_cli.hint -and "$($Payload.codex_cli.hint)".Trim().Length -gt 0) {
            Write-Host "[Pala] $($Payload.codex_cli.hint)"
        }
        if ($null -ne $Payload.project.project_registration) {
            Write-Host "[Pala] Proje kaydi=$($Payload.project.project_registration.registered), hook_safety=$($Payload.project.hook_safety.status)"
        }
        if ($null -ne $Payload.plugin_next_step -and "$($Payload.plugin_next_step)".Trim().Length -gt 0) {
            Write-Host "[Pala] $($Payload.plugin_next_step)"
        }
        if ($null -ne $Payload.hooks_next_step -and "$($Payload.hooks_next_step)".Trim().Length -gt 0) {
            Write-Host "[Pala] $($Payload.hooks_next_step)"
        } elseif ($null -ne $Payload.project.hook_safety -and $Payload.project.hook_safety.status -ne "passed") {
            Write-Host "[Pala] Hook dosya guvenligi veya Codex Work /hooks trust gerekir; otomatik bypass yok."
        }
        if ($null -ne $Payload.shared_store -and $null -ne $Payload.shared_store.db_path) {
            Write-Host "[Pala] Ortak store: $($Payload.shared_store.db_path) (tek makine; bulut sync yok)"
            Write-Host "[Pala] Host: Codex=plugin+hooks · Cursor=ince skill/rules · CLI=ayni sqlite"
        }
        return
    }
    switch ($Payload.status) {
        "ready" { Write-Host "[Pala] Zaten hazir; dosyalar degistirilmedi." }
        "installed" { Write-Host "[Pala] Pala hazir." }
        "migrated" { Write-Host "[Pala] Pala guncellendi; onceki kurulum guvenle tasindi." }
        "updated" { Write-Host "[Pala] Pala guncellendi." }
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
            Write-Host "[Pala] Sonuc: $($Payload.status)"
        }
    }
}

if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {
    throw "Pala kurulum cekirdegi bulunamadi: $core"
}

$pythonCommand = Resolve-PalaPython
$executable = $pythonCommand[0]

if ($Mode -eq "Status") {
    $stateScript = Join-Path $PSScriptRoot "pala_state.py"
    $catalogScript = Join-Path $PSScriptRoot "pala_catalog.py"
    $reportScript = Join-Path $PSScriptRoot "pala_report.py"
    $projectRoot = (Get-Location).Path
    Write-Host "[Pala] Durum: $projectRoot"
    $memoryArgs = @()
    if ($pythonCommand.Count -gt 1) { $memoryArgs += $pythonCommand[1..($pythonCommand.Count - 1)] }
    $memoryArgs += @($stateScript, "memory", "--cwd", $projectRoot)
    & $executable @memoryArgs
    $statusExit = $LASTEXITCODE
    Write-Host ""
    $summaryArgs = @()
    if ($pythonCommand.Count -gt 1) { $summaryArgs += $pythonCommand[1..($pythonCommand.Count - 1)] }
    $summaryArgs += @($catalogScript, "summary", "--cwd", $projectRoot)
    & $executable @summaryArgs
    if ($statusExit -eq 0 -and $null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) {
        $statusExit = $LASTEXITCODE
    }
    if (-not $WhatIfPreference) {
        $reportArgs = @()
        if ($pythonCommand.Count -gt 1) { $reportArgs += $pythonCommand[1..($pythonCommand.Count - 1)] }
        $reportArgs += @($reportScript, "--cwd", $projectRoot, "--open")
        $reportOut = (& $executable @reportArgs 2>&1 | Out-String).Trim()
        if ($statusExit -eq 0 -and $null -ne $LASTEXITCODE -and $LASTEXITCODE -ne 0) {
            $statusExit = $LASTEXITCODE
        }
        if ($reportOut) {
            Write-Host "[Pala] Durum sayfasi: $reportOut"
        }
    }
    exit $statusExit
}

$arguments = @()
if ($pythonCommand.Count -gt 1) { $arguments += $pythonCommand[1..($pythonCommand.Count - 1)] }
$arguments += @($core, $Mode.ToLowerInvariant(), "--source", $pluginRoot, "--project-root", (Get-Location).Path)
if ($WhatIfPreference) { $arguments += "--dry-run" }

Write-Host "[Pala] Islem: $Mode"
$raw = (& $executable @arguments 2>&1 | Out-String).Trim()
$exitCode = $LASTEXITCODE
try {
    $payload = Parse-PalaJson $raw
} catch {
    Write-Error "Pala kurulum sonucu okunamadi."
    exit 1
}

Show-PalaResult $payload
if ($exitCode -ne 0) { exit $exitCode }

if ($Mode -in @("Install", "Update", "Repair")) {
    if (-not $WhatIfPreference) {
    $doctorArgs = @()
    if ($pythonCommand.Count -gt 1) { $doctorArgs += $pythonCommand[1..($pythonCommand.Count - 1)] }
    $doctorArgs += @($core, "doctor", "--source", $pluginRoot, "--project-root", (Get-Location).Path)
    $doctorRaw = (& $executable @doctorArgs 2>&1 | Out-String).Trim()
    $doctorExit = $LASTEXITCODE
    try {
        $doctor = Parse-PalaJson $doctorRaw
    } catch {
        Write-Error "Pala doktor sonucu okunamadi."
        exit 1
    }
    Show-PalaResult $doctor
    if ($doctorExit -ne 0) { exit $doctorExit }
    if ($Mode -eq "Install") {
        Show-PalaGuiNextSteps $doctor
    } else {
        Write-Host "[Pala] Yeni skill ve hook'larin yuklenmesi icin yeni bir Codex sohbeti acin."
    }
    }
}

exit 0
