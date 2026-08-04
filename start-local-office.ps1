<#
Start the local WeAgent web application with the Smart Office service.

Usage:
  powershell -ExecutionPolicy Bypass -File .\start-local-office.ps1

It starts only missing processes and waits for their health checks:
  core API      http://127.0.0.1:5002/api/health
  office API    http://127.0.0.1:5103/api/office/health
  web frontend  http://127.0.0.1:8080
#>

[CmdletBinding()]
param(
  [switch]$NoFrontend
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = $PSScriptRoot
$BackendRoot = Join-Path $ProjectRoot 'backend'
$OfficeRoot = Join-Path $BackendRoot 'services\office'
$FrontendRoot = Join-Path $ProjectRoot 'frontend'
$PythonPath = Join-Path $BackendRoot '.venv\Scripts\python.exe'

function Test-TcpPort {
  param([int]$Port)
  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $pending = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
    if (-not $pending.AsyncWaitHandle.WaitOne(500)) { return $false }
    $client.EndConnect($pending)
    return $true
  } catch {
    return $false
  } finally {
    $client.Close()
  }
}

function Wait-Healthy {
  param(
    [string]$Name,
    [string]$Url,
    [int]$Attempts = 30
  )
  for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    try {
      $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri $Url
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
        Write-Host "[ready] $Name" -ForegroundColor Green
        return
      }
    } catch {
      # The child process may still be importing dependencies or connecting to MySQL.
    }
    Start-Sleep -Milliseconds 700
  }
  throw "$Name did not become healthy: $Url"
}

function Start-MissingProcess {
  param(
    [string]$Name,
    [int]$Port,
    [string]$FilePath,
    [string[]]$ArgumentList,
    [string]$WorkingDirectory
  )
  if (Test-TcpPort -Port $Port) {
    Write-Host "[reuse] $Name is already listening on $Port" -ForegroundColor Yellow
    return
  }
  Write-Host "[start] $Name" -ForegroundColor Cyan
  Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -WorkingDirectory $WorkingDirectory -WindowStyle Hidden
}

if (-not (Test-Path -LiteralPath $PythonPath)) {
  throw "Python virtual environment not found: $PythonPath"
}
if (-not (Test-Path -LiteralPath $OfficeRoot)) {
  throw "Smart Office service directory not found: $OfficeRoot"
}

Start-MissingProcess -Name 'Core API' -Port 5002 -FilePath $PythonPath -ArgumentList @('run.py') -WorkingDirectory $BackendRoot
Wait-Healthy -Name 'Core API' -Url 'http://127.0.0.1:5002/api/health'

Start-MissingProcess -Name 'Smart Office API' -Port 5103 -FilePath $PythonPath -ArgumentList @('app.py') -WorkingDirectory $OfficeRoot
Wait-Healthy -Name 'Smart Office API' -Url 'http://127.0.0.1:5103/api/office/health'
Wait-Healthy -Name 'Office gateway route' -Url 'http://127.0.0.1:5002/api/domain/office/health'

if (-not $NoFrontend) {
  if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw 'npm.cmd was not found. Install Node.js and reopen PowerShell.'
  }
  Start-MissingProcess -Name 'Web frontend' -Port 8080 -FilePath 'cmd.exe' -ArgumentList @('/c', 'npm run serve') -WorkingDirectory $FrontendRoot
  # 首次启动 Vue 开发服务器需要编译依赖，通常比后端健康检查更慢。
  # 用实际 HTTP 响应判断就绪，避免端口刚监听但页面尚不能访问，或等待过短误报失败。
  Wait-Healthy -Name 'Web frontend: http://127.0.0.1:8080' -Url 'http://127.0.0.1:8080/' -Attempts 90
}

Write-Host ''
Write-Host 'WeAgent Smart Office is ready.' -ForegroundColor Green
Write-Host 'Open: http://127.0.0.1:8080'
