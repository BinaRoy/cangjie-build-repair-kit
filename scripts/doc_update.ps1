param(
  [Parameter(Mandatory = $true)][string]$DateText,
  [Parameter(Mandatory = $true)][string]$ChangeText,
  [Parameter(Mandatory = $true)][string]$ModulesCsv,
  [Parameter(Mandatory = $true)][string]$VerifyCommand,
  [string]$ResultText = "PASS",
  [string]$RiskText = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  python -m driver.main doc-update `
    --date $DateText `
    --change $ChangeText `
    --modules $ModulesCsv `
    --verify-command $VerifyCommand `
    --result $ResultText `
    --risk $RiskText
}
finally {
  Pop-Location
}
