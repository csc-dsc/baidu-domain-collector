# 最初的 PowerShell 入口：读取现有 Edge 当前百度结果页，不导航、不新建标签页。
$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$outputDir = Join-Path $projectRoot 'output'
$probe = Join-Path $scriptDir 'collect_current_page.py'

# 未设置环境变量时，从 PATH 中查找 browser-harness。
$harness = if ($env:BROWSER_HARNESS) { $env:BROWSER_HARNESS } else { 'browser-harness' }
if ($env:BROWSER_HARNESS -and -not (Test-Path -LiteralPath $harness)) {
    throw "BROWSER_HARNESS 指向的文件不存在：$harness"
}

# 该命令经 stdin 发送给 browser-harness；它附着现有 Edge 并返回 JSON。
$raw = Get-Content -LiteralPath $probe -Raw -Encoding UTF8 | & $harness
if ($LASTEXITCODE -ne 0) {
    throw "browser-harness 失败：$raw"
}
$result = ($raw -join [Environment]::NewLine) | ConvertFrom-Json

# 结果使用时间戳新文件名，既不覆盖旧结果，也不写入源码目录。
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$jsonPath = Join-Path $outputDir "ps1-page-$stamp.json"
$textPath = Join-Path $outputDir "ps1-subdomains-$stamp.txt"
$result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
[System.IO.File]::WriteAllLines($textPath, [string[]]@($result.domains), [System.Text.UTF8Encoding]::new($false))

Write-Output "页面状态：$($result.status)；域名数：$(@($result.domains).Count)"
Write-Output "证据：$jsonPath"
Write-Output "域名：$textPath"
if ($result.status -ne 'ok') {
    Write-Output '未获得正常结果页，已记录状态；未操作验证页面。'
}

