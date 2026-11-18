# 股指开盘指标一键安装：装包、准备自己的看板.txt、建天勤账号模板、建任务计划「股指竞价判断」、桌面快捷方式、最后跑检查。
# 运行：powershell -ExecutionPolicy Bypass -File 安装.ps1
# 可重复运行（任务计划会覆盖成一样的设置；看板.txt、账号文件已存在就不动）。不需要管理员权限。
# 跟商品版（qihuoshuju1）互不影响：任务计划名字不一样（「股指竞价判断」），文件夹也分开。

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Tick = Join-Path $Here "股指"

# 1. 找 Python 3.13
$py = $null
$probe = "import sys; print(sys.executable if sys.version_info[:2]==(3,13) else '')"
try { $exe = & py -3.13 -c $probe 2>$null; if ($LASTEXITCODE -eq 0 -and $exe) { $py = "$exe".Trim() } } catch {}
if (-not $py) { try { $exe = & python -c $probe 2>$null; if ($LASTEXITCODE -eq 0 -and $exe) { $py = "$exe".Trim() } } catch {} }
if (-not $py) {
    Write-Host "✘ 没找到 Python 3.13。先装：winget install -e --id Python.Python.3.13 --scope user（或到 python.org 下载 3.13，勾选 Add to PATH），装完重开终端再运行本脚本。" -ForegroundColor Red
    exit 1
}
$pyw = Join-Path (Split-Path $py) "pythonw.exe"
Write-Host "✔ Python：$py"

# 2. 装包（官方源装不上就换清华镜像）
$req = Join-Path $Here "requirements.txt"
& $py -m pip install --disable-pip-version-check -q -r $req
if ($LASTEXITCODE -ne 0) {
    Write-Host "官方源失败，换清华镜像重试……"
    & $py -m pip install --disable-pip-version-check -q -r $req -i https://pypi.tuna.tsinghua.edu.cn/simple
    if ($LASTEXITCODE -ne 0) { Write-Host "✘ 装包失败，看上面的报错" -ForegroundColor Red; exit 1 }
}
Write-Host "✔ 包装好了"

# 3. 自己的 看板.txt（没有就从示例复制一份；以后更新不会动它）
$mine = Join-Path $Tick "看板.txt"
if (-not (Test-Path $mine)) {
    Copy-Item (Join-Path $Tick "看板.示例.txt") $mine
    Write-Host "✔ 从示例复制了 股指\看板.txt（按自己博易云的股指看板改，见安装说明第 4 步）"
} else {
    Write-Host "✔ 股指\看板.txt 已存在（没动它）"
}

# 4. 天勤账号模板（已存在就不动；装过商品版的已经有了。内容由用户自己用记事本填，不要让 AI 填）
$auth = Join-Path $HOME ".tqsdk_auth.json"
if (-not (Test-Path $auth)) {
    '{"user": "在这里填快期账户", "password": "在这里填密码"}' | Out-File -FilePath $auth -Encoding ascii
    Write-Host "✔ 建了账号模板 $auth —— 请自己用记事本打开，把快期账户和密码填进去" -ForegroundColor Yellow
} else {
    Write-Host "✔ 账号文件已存在：$auth（没动它）"
}

# 5. 任务计划「股指竞价判断」：每天 9:27，后台跑，最多 15 分钟（9:29 竞价、9:30 开盘、9:31 标签消失）
$act = New-ScheduledTaskAction -Execute $pyw -Argument "`"$(Join-Path $Tick '竞价判断.py')`"" -WorkingDirectory $Tick
$trg = New-ScheduledTaskTrigger -Daily -At "09:27"
$set = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
$pri = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName "股指竞价判断" -Action $act -Trigger $trg -Settings $set -Principal $pri -Force | Out-Null
Write-Host "✔ 任务计划「股指竞价判断」：每天 09:27"

# 6. 桌面快捷方式
$desk = [Environment]::GetFolderPath("Desktop")
# 「关竞价浮层」：装过商品版的已经有一个（关的是同一种浮层，股指的也能关），没有才建
$lnk = Join-Path $desk "关竞价浮层.lnk"
if (-not (Test-Path $lnk)) {
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
    $s.TargetPath = $pyw
    $s.Arguments = "`"$(Join-Path $Tick '关浮层.pyw')`""
    $s.WorkingDirectory = $Tick
    $s.Save()
    Write-Host "✔ 桌面快捷方式：$lnk"
} else {
    Write-Host "✔ 桌面已经有「关竞价浮层」（商品、股指的浮层都能关）"
}
# 「重新对股指看板」：换图、改好 股指\看板.txt 后双击，代替手敲 --test
$lnk = Join-Path $desk "重新对股指看板.lnk"
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$s.TargetPath = $pyw
$s.Arguments = "`"$(Join-Path $Tick '重新对看板.py')`""
$s.WorkingDirectory = $Tick
$s.IconLocation = "C:\Windows\System32\shell32.dll,238"
$s.Save()
Write-Host "✔ 桌面快捷方式：$lnk"

# 7. 检查
Write-Host "`n—— 检查 ——"
Push-Location $Tick
& $py 检查.py
Pop-Location
Write-Host "`n还剩两步要人做：①（如果上面说账号没填）用记事本填 $auth；② 改好 股指\看板.txt、博易云切到股指看板放最前面，双击桌面「重新对股指看板」对位置（见安装说明第 4 步）"
