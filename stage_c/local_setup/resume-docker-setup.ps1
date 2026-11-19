# Run after WSL/Ubuntu is installed and any required Windows restart is complete.
# Installs Docker Engine in Ubuntu, then runs only its benign hello-world check.
$ErrorActionPreference = 'Stop'
$setupRuntime = Join-Path $PSScriptRoot 'runtime'
New-Item -ItemType Directory -Path $setupRuntime -Force | Out-Null
$setupResult = Join-Path $setupRuntime 'docker-install-result.json'
$setupLog = Join-Path $setupRuntime 'docker-install.log'
$setupScript = (Join-Path $PSScriptRoot 'install-docker-ubuntu.sh')
$setupDrive = [IO.Path]::GetPathRoot($setupScript).Substring(0, 1).ToLowerInvariant()
$setupLinuxPath = '/mnt/' + $setupDrive + '/' + $setupScript.Substring(3).Replace('\', '/')
$setupState = [ordered]@{
    started_at = [DateTime]::UtcNow.ToString('o')
    completed = $false
    verified = $false
    exit_code = $null
    error = $null
}
$setupState | ConvertTo-Json | Set-Content -LiteralPath $setupResult -Encoding UTF8
Start-Transcript -LiteralPath $setupLog -Append | Out-Null
try {
    & "$env:SystemRoot\System32\wsl.exe" --distribution Ubuntu-24.04 --user root --exec bash $setupLinuxPath
    $setupState.exit_code = $LASTEXITCODE
    if ($LASTEXITCODE -ne 0) {
        throw "Docker setup did not complete (exit $LASTEXITCODE). Inspect the setup log."
    }
    $setupState.verified = $true
} catch {
    $setupState.error = $_.Exception.Message
} finally {
    $setupState.completed = $true
    $setupState.finished_at = [DateTime]::UtcNow.ToString('o')
    $setupState | ConvertTo-Json | Set-Content -LiteralPath $setupResult -Encoding UTF8
    Stop-Transcript | Out-Null
}
if (-not $setupState.verified) {
    throw $setupState.error
}
