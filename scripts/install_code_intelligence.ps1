param(
    [string]$ProjectPath = ".",
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version = "2.3.7",
    [switch]$DryRun,
    [switch]$ConfigureCodex,
    [switch]$BuildGraph
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$project = (Resolve-Path -LiteralPath $ProjectPath).Path
$spec = "code-review-graph==$Version"

git -C $project rev-parse --show-toplevel *> $null
if ($LASTEXITCODE -ne 0) { throw "Hedef klasor bir Git deposu degil: $project" }

function Show-Step([string]$Text) { Write-Host "[Pala code intelligence] $Text" }
function Run([string]$File, [string[]]$CommandArgs) {
    Show-Step ("{0} {1}" -f $File, ($CommandArgs -join " "))
    if ($DryRun) { return }
    Push-Location $project
    try {
        & $File @CommandArgs
        if ($LASTEXITCODE -ne 0) { throw "Komut basarisiz oldu: $File" }
    } finally { Pop-Location }
}

function Find-Crg {
    $command = Get-Command code-review-graph -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) {
        $bin = (& $uv.Source tool dir --bin).Trim()
        $candidate = Join-Path $bin "code-review-graph.exe"
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    return $null
}

$crg = Find-Crg
$needsInstall = -not $crg
if ($crg -and -not $DryRun) {
    $reportedVersion = (& $crg --version 2>&1 | Out-String).Trim()
    $needsInstall = $reportedVersion -notmatch [regex]::Escape($Version)
}

if ($needsInstall) {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Run -File "uv" -CommandArgs @("tool", "install", "--force", $spec)
    } elseif (Get-Command pipx -ErrorAction SilentlyContinue) {
        Run -File "pipx" -CommandArgs @("install", "--force", $spec)
    } else {
        throw "Izole kurulum icin uv veya pipx gerekli. Global pip kullanilmadi."
    }
    if (-not $DryRun) { $crg = Find-Crg }
}

function Run-Crg([string[]]$CrgArgs) {
    if ($crg) {
        Run -File $crg -CommandArgs $CrgArgs
    } elseif (Get-Command uvx -ErrorAction SilentlyContinue) {
        Run -File "uvx" -CommandArgs (@("--from", $spec, "code-review-graph") + $CrgArgs)
    } elseif (-not $DryRun) {
        throw "Kurulum tamamlandi ancak code-review-graph bulunamadi."
    }
}

if ($ConfigureCodex) { Run-Crg -CrgArgs @("install", "--platform", "codex") }
if ($BuildGraph) { Run-Crg -CrgArgs @("build") }
Run-Crg -CrgArgs @("--version")
Show-Step "Tamamlandi. Codex ayari ve graph build yalniz acik bayrakla degistirilir."
