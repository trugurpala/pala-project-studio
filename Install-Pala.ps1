<#
    Pala 1.1.2 installer entry point. The machine-readable ReleaseTruth lives in
    product-identity.json; this entry point does not own a second version.
    Pala Project Studio icin tek Windows giris noktasi.
    Ornek: powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet("Install", "Doctor", "Repair", "Update", "Uninstall", "Status")]
    [string]$Mode = "Install"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $PSScriptRoot "scripts\Install-Pala.ps1"
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw "Pala kurulum betigi bulunamadi: $runner"
}

$arguments = @{ Mode = $Mode }
if ($WhatIfPreference) { $arguments["WhatIf"] = $true }
& $runner @arguments
exit $LASTEXITCODE
