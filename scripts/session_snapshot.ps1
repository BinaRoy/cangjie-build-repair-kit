param(
  [string]$OutputPath = "./docs/session_snapshot.md",
  [string]$SourceDoc = "./docs/development_assessment_and_followup.md"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  python -m driver.main snapshot --output $OutputPath --source-doc $SourceDoc
}
finally {
  Pop-Location
}
