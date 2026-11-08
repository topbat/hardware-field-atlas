param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8765,
    [switch]$Build
)

$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    uv sync --locked --python 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Python 环境安装失败' }
    if ($Build -or -not (Test-Path -LiteralPath 'web/dist/index.html')) {
        npm.cmd --prefix web ci
        if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败' }
        npm.cmd --prefix web run build
        if ($LASTEXITCODE -ne 0) { throw '前端构建失败' }
    }
    $atlasUv = @('run', '--no-sync')
    if (Test-Path -LiteralPath '.env') { $atlasUv += @('--env-file', '.env') }
    $atlasUv += @('uvicorn', 'atlas.main:create_app', '--factory', '--app-dir', 'server',
                   '--host', '127.0.0.1', '--port', [string]$Port, '--no-proxy-headers')
    Write-Host "硬件志 http://127.0.0.1:$Port"
    uv @atlasUv
    if ($LASTEXITCODE -ne 0) { throw '硬件志服务退出' }
} finally {
    Pop-Location
}
