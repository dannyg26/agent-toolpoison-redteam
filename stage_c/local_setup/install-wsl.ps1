# Installs Microsoft's WSL and Ubuntu only. Does not restart Windows or run CTF code.
$ErrorActionPreference = 'Stop'
$setupRuntime = Join-Path $PSScriptRoot 'runtime'
New-Item -ItemType Directory -Path $setupRuntime -Force | Out-Null
$setupLog = Join-Path $setupRuntime 'wsl-install.log'
$setupResult = Join-Path $setupRuntime 'wsl-install-result.json'
$setupState = [ordered]@{
    started_at = [DateTime]::UtcNow.ToString('o')
    completed = $false
    exit_code = $null
    error = $null
    automatic_restart_requested = $false
}
$setupState | ConvertTo-Json | Set-Content -LiteralPath $setupResult -Encoding UTF8
Start-Transcript -LiteralPath $setupLog -Append | Out-Null
try {
    $setupPrincipal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $setupPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'WSL installation requires an administrator-approved process.'
    }
    & "$env:SystemRoot\System32\wsl.exe" --install --distribution Ubuntu-24.04 --web-download --no-launch
    $setupState.exit_code = $LASTEXITCODE
} catch {
    $setupState.error = $_.Exception.Message
} finally {
    $setupState.completed = $true
    $setupState.finished_at = [DateTime]::UtcNow.ToString('o')
    $setupState | ConvertTo-Json | Set-Content -LiteralPath $setupResult -Encoding UTF8
    Stop-Transcript | Out-Null
}
