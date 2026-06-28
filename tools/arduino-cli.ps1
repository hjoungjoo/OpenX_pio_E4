[CmdletBinding()]
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $ArduinoArgs
)

$ErrorActionPreference = "Stop"

$candidates = New-Object System.Collections.Generic.List[string]

if ($env:ARDUINO_CLI) {
  $candidates.Add($env:ARDUINO_CLI)
}

$pathCommand = Get-Command arduino-cli -ErrorAction SilentlyContinue
if ($pathCommand) {
  $candidates.Add($pathCommand.Source)
}

$commonPaths = @(
  "$env:ProgramFiles\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe",
  "${env:ProgramFiles(x86)}\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe",
  "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
)

foreach ($path in $commonPaths) {
  if ($path) {
    $candidates.Add($path)
  }
}

$cli = $candidates |
  Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
  Select-Object -First 1

if (-not $cli) {
  Write-Error "arduino-cli was not found. Install Arduino IDE 2.x or Arduino CLI, or set ARDUINO_CLI to arduino-cli.exe."
  exit 127
}

& $cli @ArduinoArgs
exit $LASTEXITCODE
