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
$expertCore = Join-Path $PSScriptRoot "pala_expert_installer.py"
$expertLock = Join-Path $pluginRoot "managed-tools.lock.json"
$palaStateRoot = Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "Pala"

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

function Show-PalaResult([pscustomobject]$Payload) {
    if ($null -ne $Payload.healthy -and $null -ne $Payload.codex -and $null -ne $Payload.plugin) {
        $pluginStatus = $Payload.plugin.status
        $codexStatus = $Payload.codex.status
        Write-Host "[Pala] Doctor: healthy=$($Payload.healthy), plugin=$pluginStatus, codex=$codexStatus"
        Write-Host "[Pala] Python=$($Payload.python.ready), Git=$($Payload.git.ready), Codex CLI=$($Payload.codex_cli.ready), Node=$($Payload.node.ready), uv=$($Payload.uv.ready)"
        if ($null -ne $Payload.project.project_registration) {
            Write-Host "[Pala] Proje kaydi=$($Payload.project.project_registration.registered), hook=$($Payload.project.hook_safety.status)"
            if ($Payload.project.hook_safety.status -ne "passed") {
                Write-Host "[Pala] Hook guveni icin Codex'te /hooks komutunu acin; otomatik bypass yapilmadi."
            }
        }
        return
    }
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
            Write-Host "[Pala] Sonuc: $($Payload.status)"
        }
    }
}

function Invoke-PalaExperts([string]$Action) {
    if (-not (Test-Path -LiteralPath $expertCore -PathType Leaf) -or -not (Test-Path -LiteralPath $expertLock -PathType Leaf)) {
        throw "Pala uzman isci kurulumu bulunamadi."
    }
    $expertArgs = @()
    if ($pythonCommand.Count -gt 1) { $expertArgs += $pythonCommand[1..($pythonCommand.Count - 1)] }
    $expertArgs += @($expertCore, $Action, "--lock", $expertLock, "--state-root", $palaStateRoot)
    if ($WhatIfPreference) { $expertArgs += "--dry-run" }
    $expertRaw = (& $executable @expertArgs 2>&1 | Out-String).Trim()
    $expertExit = $LASTEXITCODE
    try {
        $expertPayload = Parse-PalaJson $expertRaw
    } catch {
        throw "Pala uzman isci sonucu okunamadi."
    }
    Write-Host "[Pala] Uzman isciler: $($expertPayload.state)"
    if ($expertExit -ne 0) { exit $expertExit }
}

function Invoke-PalaLocalModel {
    $ollama = Join-Path $palaStateRoot "experts\ollama\0.32.6\expanded\ollama.exe"
    if (-not (Test-Path -LiteralPath $ollama -PathType Leaf)) {
        throw "Pala'ya ait Ollama ikilisi bulunamadi."
    }
    $env:OLLAMA_HOST = "127.0.0.1:11435"
    $env:OLLAMA_MODELS = Join-Path $palaStateRoot "experts\ollama\0.32.6\models"
    $env:OLLAMA_KEEP_ALIVE = "0"
    $list = (& $ollama list 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) {
        Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden | Out-Null
        Start-Sleep -Seconds 2
        $list = (& $ollama list 2>&1 | Out-String)
    }
    if ($LASTEXITCODE -ne 0) { throw "Pala Ollama loopback sunucusu baslatilamadi." }
    if ($list -notmatch "qwen3:4b-instruct\s+0edcdef34593") {
        & $ollama pull "qwen3:4b-instruct"
        if ($LASTEXITCODE -ne 0) { throw "Pala Qwen3 modeli indirilemedi." }
    }
}

if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {
    throw "Pala kurulum cekirdegi bulunamadi: $core"
}

$pythonCommand = Resolve-PalaPython
$executable = $pythonCommand[0]
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
    Invoke-PalaExperts "install"
    if (-not $WhatIfPreference) {
    Invoke-PalaLocalModel
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
    Invoke-PalaExperts "doctor"
    Write-Host "[Pala] Yeni skill ve hook'larin yuklenmesi icin yeni bir Codex sohbeti acin."
    }
} elseif ($Mode -eq "Doctor") {
    Invoke-PalaExperts "doctor"
}

exit 0
