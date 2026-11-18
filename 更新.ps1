# 更新股指开盘指标到 GitHub 上的最新版。只换程序，不动自己的 股指\看板.txt、数据、账号。
# 运行：powershell -ExecutionPolicy Bypass -File 更新.ps1
# 不要在 9:25–9:32 之间更新（股指竞价判断正在跑）。

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Repo = "https://github.com/wumingxiaocao8-code/wmxc-guzhishuju"

$now = Get-Date
$a = $now.Date.AddHours(9).AddMinutes(25); $b = $a.AddMinutes(7)
if ($now -ge $a -and $now -le $b) { Write-Host "✘ 现在股指竞价判断正在跑，过了 $($b.ToString('HH:mm')) 再更新" -ForegroundColor Red; exit 1 }

$git = Get-Command git -ErrorAction SilentlyContinue
if ($git -and (Test-Path (Join-Path $Here ".git"))) {
    Push-Location $Here
    git pull --ff-only
    $ok = $LASTEXITCODE -eq 0
    Pop-Location
    if (-not $ok) { Write-Host "✘ git pull 失败（多半是改过仓库里的程序文件）。把报错给 AI 看" -ForegroundColor Red; exit 1 }
} else {
    # 下载压缩包装的：下最新的压缩包，覆盖程序文件（自己的设置不在压缩包里，不会被盖掉）
    $tmp = Join-Path $env:TEMP ("股指指标更新_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
    New-Item -ItemType Directory -Path $tmp | Out-Null
    $zip = Join-Path $tmp "main.zip"
    Write-Host "下载 $Repo 最新版……"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest "$Repo/archive/refs/heads/main.zip" -OutFile $zip -UseBasicParsing
    Expand-Archive $zip $tmp
    $src = Get-ChildItem $tmp -Directory | Select-Object -First 1
    Copy-Item (Join-Path $src.FullName "*") $Here -Recurse -Force
    Write-Host "✔ 程序文件已覆盖（下载的临时文件在 $tmp，可以拖进回收站）"
}

# 包有变化时补装（没变化几秒就过）
$py = $null
$probe = "import sys; print(sys.executable if sys.version_info[:2]==(3,13) else '')"
try { $exe = & py -3.13 -c $probe 2>$null; if ($LASTEXITCODE -eq 0 -and $exe) { $py = "$exe".Trim() } } catch {}
if (-not $py) { try { $exe = & python -c $probe 2>$null; if ($LASTEXITCODE -eq 0 -and $exe) { $py = "$exe".Trim() } } catch {} }
if (-not $py) { Write-Host "✘ 程序文件已更新，但找不到 Python 3.13，没法检查和补装要用的包。把这段话给 AI 看" -ForegroundColor Red; exit 1 }
& $py -m pip install --disable-pip-version-check -q -r (Join-Path $Here "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host "官方源装不上，换清华镜像再试……"
    & $py -m pip install --disable-pip-version-check -q -r (Join-Path $Here "requirements.txt") -i https://pypi.tuna.tsinghua.edu.cn/simple
    if ($LASTEXITCODE -ne 0) { Write-Host "✘ 程序文件已更新，但要用的包两次都没装上，明早的股指竞价判断可能跑不起来。把上面的报错给 AI 看" -ForegroundColor Red; exit 1 }
}
& $py -c "import tqsdk, pandas, numpy, scipy, PIL, openpyxl"
if ($LASTEXITCODE -ne 0) { Write-Host "✘ 包装完了但 import 不进来。把这段话给 AI 看" -ForegroundColor Red; exit 1 }
Write-Host "✔ 要用的包都在"

# 念一下最新的更新记录
Write-Host "`n—— 最新的更新记录 ——"
$lines = Get-Content (Join-Path $Here "更新记录.md") -Encoding UTF8
$start = ($lines | Select-String -Pattern "^## " | Select-Object -First 2)
if ($start) {
    $from = $start[0].LineNumber - 1
    $to = if ($start.Count -gt 1) { $start[1].LineNumber - 2 } else { $lines.Count - 1 }
    $lines[$from..$to] | ForEach-Object { Write-Host $_ }
}
Write-Host "`n看板.示例.txt 是作者现在的股指看板（合约月份会跟着换）；自己的 股指\看板.txt 没动，换月了记得自己改、再双击「重新对股指看板」。"
