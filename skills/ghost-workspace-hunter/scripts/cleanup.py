#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy 数字任务空间清理（跨平台版）
- 删除 workspaces 表中 basename 为时间戳格式的记录（仍有未删活跃会话则跳过）
- 关联磁盘目录 / 孤儿项目目录 / 会话缓存 移入回收站 / 废纸篓（可恢复）
平台：darwin / win32
  · macOS 路径已验证（~/.workbuddy/workbuddy.db、~/WorkBuddy）。
  · Windows 路径已据本机实测文档核实：%USERPROFILE%\\.workbuddy\\workbuddy.db 与
    %USERPROFILE%\\WorkBuddy；回收站走 PowerShell VB FileIO（SendToRecycleBin，抑制弹窗）。
  · 两者均可由环境变量 WORKBUDDY_DB / WORKBUDDY_ROOT 覆盖。
"""
import os
import re
import sys
import shutil
import sqlite3
import datetime
import subprocess

STAMP_RE = re.compile(r'^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$')


def detect_paths():
    plat = sys.platform
    env = os.environ
    if plat == 'win32':
        userprofile = env.get('USERPROFILE', env.get('HOME', ''))
        # 已据 Windows 本机实测文档核实：%USERPROFILE%\\.workbuddy\\workbuddy.db
        db = env.get('WORKBUDDY_DB') or os.path.join(userprofile, '.workbuddy', 'workbuddy.db')
        appdata = env.get('APPDATA', '')
        candidates = [db]
        if appdata:
            # 未经验证的次选：部分应用会把数据放 %APPDATA%\\workbuddy
            candidates.append(os.path.join(appdata, 'workbuddy', 'workbuddy.db'))
        root = env.get('WORKBUDDY_ROOT') or os.path.join(userprofile, 'WorkBuddy')
    else:
        db = env.get('WORKBUDDY_DB') or os.path.expanduser('~/.workbuddy/workbuddy.db')
        root = env.get('WORKBUDDY_ROOT') or os.path.expanduser('~/WorkBuddy')
        candidates = [db]
    db_path = next((c for c in candidates if c and os.path.isfile(c)), candidates[0])
    return plat, db_path, root


def to_trash(plat, src):
    """移动 src 到回收站；返回 (ok, dest_or_reason)。"""
    base = os.path.basename(src.rstrip('/\\'))
    tag = datetime.datetime.now().strftime('.%Y%m%d%H%M%S')
    if plat == 'win32':
        # 走 PowerShell VB FileIO 入回收站（SendToReRecycleBin），抑制确认弹窗；
        # 用 -LiteralPath 避免路径中 [] 等字符被当作通配。
        ps = (
            '$p = $args[0];'
            'Add-Type -AssemblyName Microsoft.VisualBasic;'
            'if (Test-Path -LiteralPath $p -PathType Container) {'
            '[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory('
            '$p, "OnlyErrorDialogs", "SendToRecycleBin")'
            '} else {'
            '[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile('
            '$p, "OnlyErrorDialogs", "SendToRecycleBin")'
            '}'
        )
        try:
            subprocess.run(['powershell.exe', '-NoProfile', '-Command', ps, src],
                           check=True, capture_output=True, timeout=60)
            return True, '(回收站)'
        except Exception as e:  # noqa: BLE001
            return False, str(e)
    trash = os.path.expanduser('~/.Trash')
    os.makedirs(trash, exist_ok=True)
    dest = os.path.join(trash, base + tag)
    try:
        shutil.move(src, dest)
        return True, dest
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def main():
    plat, db, root = detect_paths()
    print("═══════ WorkBuddy 数字任务空间清理（跨平台）═══════")
    print("平台:", "Windows" if plat == 'win32' else "macOS")
    print("数据库:", db)
    print("工作空间根:", root)
    if not os.path.isfile(db):
        print("✗ 找不到数据库:", db)
        sys.exit(1)

    # ---- 0. 备份 ----
    db_dir = os.path.dirname(db)
    if plat == 'win32':
        bk = os.path.join(db_dir, 'workbuddy.db.backup-' +
                          datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    else:
        cfg = os.path.join(root, '使用配置')
        os.makedirs(cfg, exist_ok=True)
        bk = os.path.join(cfg, 'workbuddy.db.backup-' +
                          datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    try:
        shutil.copy2(db, bk)
        print("✓ 已备份数据库 →", bk)
    except Exception as e:  # noqa: BLE001
        print("! 备份失败:", e)
    print()

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = [r['path'] for r in conn.execute("SELECT path FROM workspaces")]
    stamps = [p for p in rows if p and STAMP_RE.match(os.path.basename(p.rstrip('/\\')))]

    # Step 1: 记录
    print("── 1. 数字任务空间记录 ──")
    if not stamps:
        print("  (无时间戳工作空间)")
    rdel = skip = 0
    deleted = []          # 记录已删的工作空间路径（下游缓存/磁盘清理仅作用于这些）
    skipped = []          # 因活跃会话跳过的路径（整目录一律保留）
    for p in stamps:
        cur = conn.execute(
            "SELECT COUNT(*) c FROM sessions WHERE cwd=? AND deleted_at IS NULL",
            (p,)).fetchone()['c']
        if cur and cur > 0:
            print("  ! 跳过（仍有活跃未删会话，整目录保留）:", p)
            skip += 1
            skipped.append(p)
            continue
        conn.execute("DELETE FROM workspaces WHERE path=?", (p,))
        rdel += 1
        deleted.append(p)
        print("  ✗ 已删记录:", p)
    conn.commit()
    print(f"  清除记录 {rdel} 条 / 跳过 {skip} 条\n")

    # 收集会话 id（仅已删记录对应的会话；跳过的整目录保留，其缓存不动）
    sids = []
    for p in deleted:
        for r in conn.execute("SELECT id FROM sessions WHERE cwd=?", (p,)):
            sids.append(r['id'])
    conn.close()

    # Step 2: 会话缓存
    print("── 2. 关联会话缓存 ──")
    adisp = os.path.join(db_dir, 'assistant-display')
    ftm = os.path.join(db_dir, 'file-tree-manifests')
    cache = 0
    for sid in sids:
        for d in (adisp, ftm):
            f = os.path.join(d, sid + '.json')
            if os.path.isfile(f):
                ok, _ = to_trash(plat, f)
                cache += 1 if ok else 0
    print(f"  移出缓存 {cache} 个\n")

    # Step 3: 磁盘时间戳目录（仅清理记录已删的工作空间；跳过者整目录保留）
    print("── 3. 磁盘上的时间戳目录 ──")
    disk = 0
    deleted_bases = {os.path.basename(p.rstrip('/\\')) for p in deleted}
    if os.path.isdir(root):
        for name in os.listdir(root):
            full = os.path.join(root, name)
            if os.path.isdir(full) and STAMP_RE.match(name):
                if name in deleted_bases:
                    ok, dest = to_trash(plat, full)
                    if ok:
                        disk += 1
                        print("  ✗ 已移入回收站:", name)
                    else:
                        print(f"  ! 移动失败 {name}: {dest}")
                else:
                    print("  - 保留（记录未删/有活跃会话）:", name)
    print(f"  移出目录 {disk} 个\n")

    # Step 4: 孤儿项目目录（仅 macOS；Windows 命名规则不同，跳过并提示）
    print("── 4. 孤儿会话数据目录 ──")
    orphan = 0
    proj = os.path.join(db_dir, 'projects')
    if plat != 'win32' and os.path.isdir(proj):
        for name in os.listdir(proj):
            if name.startswith('WorkBuddy-'):
                suffix = name[len('WorkBuddy-'):]
                m = STAMP_RE.match(suffix)
                if m and not os.path.isdir(os.path.join(root, m.group(0))):
                    full = os.path.join(proj, name)
                    ok, _ = to_trash(plat, full)
                    if ok:
                        orphan += 1
                        print("  ✗ 已移入回收站:", name)
    else:
        print("  (Windows 平台省略：项目目录命名规则待验证)")
    print(f"  移出 {orphan} 项\n")

    # 结果
    print("── 5. 清理后工作空间列表 ──")
    c2 = sqlite3.connect(db)
    c2.row_factory = sqlite3.Row
    for r in c2.execute("SELECT rowid, path FROM workspaces ORDER BY last_opened_at DESC"):
        print(f"  {r['rowid']}  {r['path']}")
    c2.close()
    print("\n说明：basename 为时间戳格式的工作空间即「数字任务空间」，由未先选工作空间即开干触发；")
    print("      本脚本仅清理此类，不触碰命名真实工作空间。Windows 路径已据本机实测文档核实，")
    print("      仍可用 WORKBUDDY_DB / WORKBUDDY_ROOT 环境变量覆盖。")


if __name__ == '__main__':
    main()
