param(
    [ValidateSet('setup','start')][string]$Mode = 'start',
    [ValidateRange(1024,65535)][int]$Port = 8000
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$demoProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $demoProjectRoot

function Find-DemoPython {
    $candidates = @()
    if (Get-Command py.exe -ErrorAction SilentlyContinue) { $candidates += ,@('py.exe','-3') }
    if (Get-Command python.exe -ErrorAction SilentlyContinue) { $candidates += ,@('python.exe') }
    foreach ($version in @('314','313','312','311','310')) {
        $candidate = Join-Path $env:LOCALAPPDATA "Programs\Python\Python$version\python.exe"
        if (Test-Path -LiteralPath $candidate) { $candidates += ,@($candidate) }
    }
    foreach ($candidate in $candidates) {
        try {
            $exe = $candidate[0]
            $arguments = @($candidate | Select-Object -Skip 1)
            $result = & $exe @arguments -c 'import sys; assert sys.version_info >= (3,10); print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $result -and (Test-Path -LiteralPath ([string]$result).Trim())) { return ([string]$result).Trim() }
        } catch { }
    }
    return $null
}

try {
    $python = Find-DemoPython
    if (-not $python) {
        if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { throw 'Python 3.10+ was not found. Install Python from python.org (Add Python to PATH), reopen this window, then try again.' }
        Write-Host 'Installing Python 3.12 for the current Windows user...'
        & winget.exe install --id Python.Python.3.12 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { throw 'Python installation failed. See bat\commands.txt for manual steps.' }
        $python = Find-DemoPython
        if (-not $python) { throw 'Reopen this BAT after Python has finished installing.' }
    }
    Write-Host 'NTUB Mid_Front - local browser demonstration'
    if ($Mode -eq 'setup') {
        & $python (Join-Path $demoProjectRoot 'run.py') setup
    } else {
        Write-Host "Open http://localhost:$Port/ after the server starts."
        Write-Host 'Login: ntub / 12345678. Keep this window open; Ctrl+C stops the server.'
        & $python (Join-Path $demoProjectRoot 'run.py') start --port $Port
    }
    if ($LASTEXITCODE -ne 0) { throw "Command failed (exit $LASTEXITCODE). See bat\commands.txt." }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
