# 教学帮帮团 初始化引导（Windows PowerShell）
# 探测 WorkBuddy 托管 Python，否则使用系统 python3，调用 setup.py。
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 探测 WorkBuddy 托管 Python（Windows 布局为 <versions>\<ver>\python.exe，无 bin\ 子目录），
# 否则回退系统 python；并排除微软应用商店 App-Execution-Alias 桩（执行返回 9009，无法创建 venv）。
$py = (Get-ChildItem "$env:USERPROFILE\.workbuddy\binaries\python\versions\*\python.exe" `
        -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1).FullName
if (-not $py) {
    $p3 = Get-Command python3 -ErrorAction SilentlyContinue
    $p  = Get-Command python  -ErrorAction SilentlyContinue
    $cand = if ($p3) { $p3.Source } elseif ($p) { $p.Source } else { $null }
    if ($cand -and ($cand -notlike "*WindowsApps*")) { $py = $cand }
}
if (-not $py) {
    Write-Error "FATAL: 未找到 Python（需 3.8+）"
    exit 2
}
& $py (Join-Path $ScriptDir setup.py) @args
