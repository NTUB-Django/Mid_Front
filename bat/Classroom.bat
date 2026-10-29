@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "NTUB_STARTER=%~f0"
set "NTUB_START_MODE=%~1"
powershell.exe -NoProfile -Command "$text=[IO.File]::ReadAllText($env:NTUB_STARTER,[Text.Encoding]::UTF8); $marker=':NTUB_POWERSHELL'; & ([ScriptBlock]::Create($text.Substring($text.LastIndexOf($marker)+$marker.Length)))"
set "NTUB_EXIT_CODE=%ERRORLEVEL%"
if not "%NTUB_EXIT_CODE%"=="0" if /I not "%NTUB_START_MODE%"=="prepare" pause
exit /b %NTUB_EXIT_CODE%
:NTUB_POWERSHELL
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'
$localProjectRoot = Split-Path -Parent (Split-Path -Parent $env:NTUB_STARTER)
$projectRoot = if (Test-Path -LiteralPath (Join-Path $localProjectRoot 'run.py')) { $localProjectRoot } else { Join-Path $env:LOCALAPPDATA 'NTUB-Django-Mid' }
$launcherRoot = Join-Path $env:LOCALAPPDATA 'NTUB-Django-Launcher'
$server = $null
$tunnel = $null
$prepareOnly = $env:NTUB_START_MODE -eq 'prepare'

function Find-Python {
    $candidates = @()
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        $candidates += ,@('py.exe', '-3.12')
        $candidates += ,@('py.exe', '-3')
    }
    $installed = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
    if (Test-Path -LiteralPath $installed) { $candidates += ,@($installed) }
    if (Get-Command python.exe -ErrorAction SilentlyContinue) { $candidates += ,@('python.exe') }
    foreach ($candidate in $candidates) {
        try {
            $program = $candidate[0]
            $arguments = @($candidate | Select-Object -Skip 1)
            $result = & $program @arguments -c 'import sys; assert sys.version_info >= (3,10); print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $result -and (Test-Path -LiteralPath ([string]$result))) {
                return ([string]$result).Trim()
            }
        } catch { }
    }
    return $null
}

function Download-Project {
    if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { throw '私有專案需要 Git。請先登入 GitHub 並安裝 Git，或直接在已下載的 Mid 專案內執行此檔。' }
    Write-Host '正在透過 Git 下載私有專案；請使用有權限的 GitHub 帳號。'
    & git.exe clone --depth 1 --branch main 'https://github.com/NTUB-Django/Mid.git' $projectRoot
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $projectRoot 'run.py'))) { throw '下載私有專案失敗，請確認 GitHub 登入權限。' }
}

function Update-Project {
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.git'))) { throw '找不到 Git 專案。請先從 GitHub 下載 Mid。' }
    & git.exe -C $projectRoot pull --ff-only origin main
    if ($LASTEXITCODE -ne 0) { throw '更新失敗；請確認 GitHub 權限及專案內沒有未提交的修改。' }
}

function Get-Cloudflared {
    New-Item -ItemType Directory -Path $launcherRoot -Force | Out-Null
    $executable = Join-Path $launcherRoot 'cloudflared.exe'
    if (-not (Test-Path -LiteralPath $executable)) {
        Write-Host '正在從 Cloudflare 官方 GitHub 下載 cloudflared。'
        $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/cloudflare/cloudflared/releases/latest'
        $assetName = if ([Environment]::Is64BitOperatingSystem) { 'cloudflared-windows-amd64.exe' } else { 'cloudflared-windows-386.exe' }
        $asset = $release.assets | Where-Object { $_.name -eq $assetName } | Select-Object -First 1
        if (-not $asset -or $asset.digest -notmatch '^sha256:[a-fA-F0-9]{64}$') { throw '無法取得 cloudflared 官方下載檔與校驗碼。' }
        $temporary = Join-Path $launcherRoot 'cloudflared.download'
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $asset.browser_download_url -OutFile $temporary
            $expected = $asset.digest.Substring(7)
            if ((Get-FileHash -LiteralPath $temporary -Algorithm SHA256).Hash -ne $expected) { throw 'cloudflared 下載校驗失敗。' }
            Move-Item -LiteralPath $temporary -Destination $executable -Force
        } finally {
            Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
        }
    }
    return $executable
}

try {
    Write-Host ''
    Write-Host 'NTUB Django MID 課堂展示'
    Write-Host '1  啟動本機網站（直接按 Enter）'
    Write-Host '2  啟動網站與既有 Cloudflare Tunnel'
    Write-Host '3  更新程式後啟動（保留資料庫與帳號，覆蓋程式檔）'
    Write-Host '4  建立自己的管理員'
    $choice = if ($prepareOnly) { '1' } else { Read-Host '請選擇' }
    if ([string]::IsNullOrWhiteSpace($choice)) { $choice = '1' }
    if ($choice -notin @('1', '2', '3', '4')) { throw '請選擇 1 至 4。' }
    $python = Find-Python
    if (-not $python) {
        if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { throw '找不到 Python 或 winget。請安裝 Python 3.12 後重新開啟此檔。' }
        Write-Host '正在使用 winget 為目前使用者安裝 Python 3.12。'
        & winget.exe install --id Python.Python.3.12 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { throw 'Python 安裝失敗，請確認電腦教室允許安裝 Python。' }
        $python = Find-Python
        if (-not $python) { throw 'Python 已安裝，請關閉本視窗後重新執行。' }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'run.py'))) { Download-Project }
    if ($choice -eq '3') { Update-Project }
    Set-Location -LiteralPath $projectRoot
    Write-Host '正在準備環境、資料庫、課程和展示帳號，第一次執行需要網路。'
    & $python (Join-Path $projectRoot 'run.py') setup
    if ($LASTEXITCODE -ne 0) { throw '專案初始化失敗，請查看上方訊息。' }
    $venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if ($choice -eq '4') {
        & $venvPython manage.py createsuperuser
        if ($LASTEXITCODE -ne 0) { throw '管理員建立未完成。' }
        Read-Host '按 Enter 結束' | Out-Null
        exit 0
    }
    if ($prepareOnly) { Write-Host '電腦教室初始化完成。'; exit 0 }
    $portText = Read-Host '連接埠（直接按 Enter 使用 8000）'
    if ([string]::IsNullOrWhiteSpace($portText)) { $portText = '8000' }
    if ($portText -notmatch '^\d{4,5}$' -or [int]$portText -lt 1024 -or [int]$portText -gt 65535) { throw '連接埠必須介於 1024 與 65535。' }
    $port = [int]$portText
    $listener = New-Object System.Net.Sockets.TcpListener([Net.IPAddress]::Loopback, $port)
    try { $listener.Start() } catch { throw "連接埠 $port 已被使用，請重開此檔並選其他連接埠。" } finally { $listener.Stop() }
    $publicUrl = $null
    $credential = $null
    $cloudflared = $null
    if ($choice -eq '2') {
        $domain = (Read-Host '既有 Tunnel 的公開網域（不含 https://）').Trim().ToLowerInvariant()
        if ($domain.Length -gt 253 -or $domain -notmatch '^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$') { throw '請輸入有效網域，例如課堂使用的公開網域。' }
        Write-Host "請先在 Cloudflare 將此網域的服務設定為 http://localhost:$port 。本程式不會建立 DNS 或發布路由。"
        $secureToken = Read-Host '請輸入既有 Tunnel token（不會顯示或存入檔案）' -AsSecureString
        if ($secureToken.Length -lt 80) { throw 'Tunnel token 長度不正確。' }
        $credential = New-Object System.Management.Automation.PSCredential('tunnel', $secureToken)
        $cloudflared = Get-Cloudflared
        $publicUrl = "https://$domain"
        $env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,$domain"
        $env:DJANGO_CSRF_TRUSTED_ORIGINS = $publicUrl
        $env:DJANGO_DEBUG = '0'
        & $venvPython manage.py collectstatic --noinput
        if ($LASTEXITCODE -ne 0) { throw '網站靜態檔案準備失敗。' }
    } else {
        $env:DJANGO_DEBUG = '1'
        $env:DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1'
        $env:DJANGO_CSRF_TRUSTED_ORIGINS = ''
    }
    $server = Start-Process -FilePath $venvPython -ArgumentList @('manage.py', 'runserver', "127.0.0.1:$port", '--noreload') -WorkingDirectory $projectRoot -NoNewWindow -PassThru
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ($server.HasExited) { throw 'Django 啟動失敗，請查看上方訊息。' }
        try {
            $health = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/healthz/" -TimeoutSec 2
            if ($health.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw '網站啟動逾時。' }
    if ($choice -eq '2') {
        try {
            $env:TUNNEL_TOKEN = $credential.GetNetworkCredential().Password
            $tunnel = Start-Process -FilePath $cloudflared -ArgumentList @('tunnel', '--no-autoupdate', 'run') -WorkingDirectory $launcherRoot -PassThru
        } finally {
            Remove-Item Env:TUNNEL_TOKEN -ErrorAction SilentlyContinue
            $credential = $null
            $secureToken.Dispose()
        }
        Write-Host "Cloudflare 已啟動，請確認 Tunnel 視窗顯示連線成功，再開啟 $publicUrl 。"
    }
    $openUrl = if ($publicUrl) { $publicUrl } else { "http://127.0.0.1:$port/" }
    Write-Host ''
    Write-Host "網站：$openUrl"
    Write-Host ('後台：' + $openUrl.TrimEnd('/') + '/admin/')
    Write-Host '預設展示帳號：管理員：admin / admin1234；校方：school@example.com / school123；學生：student@example.com / student123'
    Write-Host "專案與資料庫保存在 $projectRoot"
    Write-Host '這些密碼僅供課堂展示。保留本視窗，按 Ctrl+C 停止網站及本次 Tunnel。'
    Start-Process $openUrl | Out-Null
    while (-not $server.HasExited) {
        if ($null -ne $tunnel -and $tunnel.HasExited) { throw 'Cloudflare 已停止，請查看 Tunnel 視窗訊息後重新啟動。' }
        Start-Sleep -Seconds 1
    }
} catch {
    Write-Host ("啟動失敗：" + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally {
    if ($null -ne $tunnel -and -not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id -ErrorAction SilentlyContinue }
    if ($null -ne $server -and -not $server.HasExited) { Stop-Process -Id $server.Id -ErrorAction SilentlyContinue }
    Remove-Item Env:TUNNEL_TOKEN -ErrorAction SilentlyContinue
}
