param(
  [string]$OutputDir = "./dist/product_bundle",
  [string]$ZipPath = "./release/product_bundle.zip"
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  python -m driver.main export --output-dir $OutputDir --force

  $zipAbs = Resolve-Path (Split-Path -Parent $ZipPath) -ErrorAction SilentlyContinue
  if (-not $zipAbs) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $ZipPath) -Force | Out-Null
  }
  if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
  Compress-Archive -Path "$OutputDir\*" -DestinationPath $ZipPath -Force
  Write-Host "release zip generated: $ZipPath"
}
finally {
  Pop-Location
}
