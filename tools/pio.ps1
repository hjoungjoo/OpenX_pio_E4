$ErrorActionPreference = "Stop"
$PioArgs = $args

$candidates = New-Object System.Collections.Generic.List[string]

if ($env:PLATFORMIO_CLI) {
  $candidates.Add($env:PLATFORMIO_CLI)
}

$pathCommand = Get-Command pio -ErrorAction SilentlyContinue
if ($pathCommand) {
  $candidates.Add($pathCommand.Source)
}

$commonPaths = @(
  "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe",
  "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts\pio.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python311\Scripts\pio.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python310\Scripts\pio.exe"
)

foreach ($path in $commonPaths) {
  if ($path) {
    $candidates.Add($path)
  }
}

$pio = $candidates |
  Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
  Select-Object -First 1

if (-not $pio) {
  Write-Error "PlatformIO CLI was not found. Install the PlatformIO IDE extension, or set PLATFORMIO_CLI to pio.exe."
  exit 127
}

& $pio @PioArgs
exit $LASTEXITCODE
