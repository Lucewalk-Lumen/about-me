#!/usr/bin/env python3
"""
Stage 6.2 RESTORE 恢复脚本 (agent 备用的低层原语)

通常用户通过 distill agent 说「恢复蒸馏资产」触发, 本脚本作为
agent 实际执行的底层 (或用户在 agent 不可用时手动调用).

用法:
  python3 bin/restore_backup.py                              # 用默认配置
  python3 bin/restore_backup.py --backup-dir ~/custom/path    # 指定备份目录
  python3 bin/restore_backup.py --target-dir ~/.workbuddy/distill-assets
  python3 bin/restore_backup.py --list                       # 只列出可用 zip, 不恢复
  python3 bin/restore_backup.py --force                      # 跳过确认 (危险)

退出码:
  0 = 恢复成功
  1 = 备份目录不存在
  2 = 无 backup-*.zip
  3 = 用户拒绝确认
  4 = 解压/结构校验失败 (zip 损坏、缺 distill-assets/ 子树、子树内无可恢复内容)
  5 = 验证失败 (capsules 数量不一致)
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile
import stat
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import assets_lib as A  # noqa: E402
from audit_chain import append_event  # noqa: E402
from pkgmeta import load_pkg_meta  # noqa: E402

# 用户可见提示语：多处复用，收敛为一处定义，避免同一句散落多份后各自漂移
HINT_EXPORT_FIRST = '   建议先运行「导出蒸馏资产」'


def list_zips(backup_dir: Path) -> list[Path]:
    """返回 backup_dir 下所有 backup-*.zip, 按时间戳从新到旧排序"""
    zips = sorted(backup_dir.glob('backup-*.zip'),
                  key=lambda p: p.name, reverse=True)
    return zips


def parse_zip_ts(zip_path: Path) -> datetime:
    """从 backup-YYYYMMDD-HHMMSS.zip 名字解析时间戳"""
    name = zip_path.stem  # backup-20260804-130211
    try:
        ts_str = name.replace('backup-', '')
        return datetime.strptime(ts_str, '%Y%m%d-%H%M%S')
    except ValueError:
        return datetime.fromtimestamp(zip_path.stat().st_mtime)


def _is_internal_state(rel: str) -> bool:
    """rel 是否为不应恢复的运行时内部状态（版本备份 / 计数器）。

    单一判定入口：结构前置校验与解压跳过共用，避免两处清单漂移。
    """
    return (rel.startswith('distill-versions/')
            or rel == '.counter' or rel.startswith('.counter/'))


def _is_restorable(name: str) -> bool:
    """zip 成员是否会在恢复时真正落盘（有 distill-assets/ 前缀且非内部状态）。"""
    return (name.startswith('distill-assets/')
            and not _is_internal_state(name[len('distill-assets/'):]))


def _check_zip_structure(zf: zipfile.ZipFile, zip_name: str) -> str:
    """恢复前的结构前置校验，返回错误说明（空串 = 通过）。

    必须在**创建还原点、打印进度、写盘之前**调用：拿不到 distill-assets/ 子树
    （或该子树下没有可恢复成员）的 zip 一律立即拒绝，这样既不会留下残留的
    assets.pre-restore-* 目录，也不会先宣布「按 0 条胶囊恢复」再失败。
    """
    names = zf.namelist()
    if not any(n.startswith('distill-assets/') for n in names):
        return ('[X] 该 zip 内没有 distill-assets/ 目录，结构不符: %s\n'
                '    请确认这是本工具导出的 backup-*.zip（归档顶层应为 distill-assets/）' % zip_name)
    if not any(_is_restorable(n) for n in names):
        return ('[X] 该 zip 的 distill-assets/ 下没有可恢复的内容（成员均为运行时内部状态）: %s\n'
                '    只含 distill-versions/ 或 .counter 的归档不构成可恢复备份' % zip_name)
    return ''


def _safe_extract(zf: zipfile.ZipFile, dest) -> dict:
    """Zip-slip 防护：只解压 distill-assets/ 子树，并逐成员校验落点不越界。

    backup zip 可能含穿越到上级目录的成员（例如指向私钥目录的路径）或绝对
    路径成员，直接 extractall 会在目标目录之外任意写文件。此处逐成员过滤：
    只处理前缀为 'distill-assets/' 的成员，且每个成员的落点必须严格落在
    dest 之内；被跳过的成员计入统计，由调用方报出，不做静默丢弃。
    """
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    stats = {"extracted": 0, "outside": 0, "internal_state": 0, "symlink": 0}
    for info in zf.infolist():
        # 精确目录边界：仅放行 distill-assets/ 子树，杜绝 distill-assets2/ 等误匹配
        if not info.filename.startswith("distill-assets/"):
            stats["outside"] += 1
            continue
        # 排除不应恢复的运行时内部状态（版本备份 / 计数器），在解压阶段即跳过
        _base = info.filename[len("distill-assets/"):]
        if _is_internal_state(_base):
            stats["internal_state"] += 1
            continue
        # 拒绝 zip 内的符号链接成员
        if stat.S_ISLNK(info.external_attr >> 16):
            stats["symlink"] += 1
            continue
        target = (dest / info.filename).resolve()
        if target != dest and not str(target).startswith(str(dest) + os.sep):
            # 越界成员：直接跳过（理论上已被前缀过滤挡住，双保险）
            stats["outside"] += 1
            continue
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                out.write(src.read())
        stats["extracted"] += 1
    return stats


def _rollback(pre_dir: Path, target_dir: Path) -> None:
    """验证失败后的补救：把还原点**覆盖复制**回目标目录。

    注意这是覆盖式还原——还原点里的文件会被写回、内容不一致的会被覆盖，
    但**不会删除**本次还原新写入的文件。要完全回到还原前状态需人工清理；
    还原点目录会保留下来供比对与手动处理。
    """
    try:
        shutil.copytree(pre_dir, target_dir, dirs_exist_ok=True, copy_function=shutil.copy2)
        print('   已用还原点覆盖回目标目录: %s' % pre_dir)
        print('   （覆盖式还原：不会删除本次还原新增的文件；如需完全回到还原前，请按该目录比对后人工清理）')
    except Exception:
        print('   [!] 还原点覆盖失败, 请手动处理: 还原点 %s → 目标 %s' % (pre_dir, target_dir), file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description='从 backup-*.zip 恢复胶囊库 (Stage 6.2 RESTORE)')
    p.add_argument('--backup-dir', default=os.environ.get('DISTILL_BACKUP_DIR', str(os.path.expanduser('~/Documents/distill-backup'))),
                   help='备份目录 (默认 ~/Documents/distill-backup，可用 DISTILL_BACKUP_DIR 覆盖)')
    p.add_argument('--target-dir', default=os.environ.get('DISTILL_ASSETS_DIR', str(os.path.expanduser('~/.workbuddy/distill-assets'))),
                   help='恢复目标 (默认 ~/.workbuddy/distill-assets，可用 DISTILL_ASSETS_DIR 覆盖)')
    p.add_argument('--list', action='store_true', help='只列出可用 zip')
    p.add_argument('--force', action='store_true', help='跳过确认 (危险)')
    args = p.parse_args()

    # 审计 actor 默认取包署名，允许环境变量覆盖
    AUTHOR = os.environ.get("DISTILL_AUTHOR") or load_pkg_meta()["author_name"]

    backup_dir = Path(args.backup_dir).expanduser()
    target_dir = Path(args.target_dir).expanduser()

    # 1. 检查备份目录
    if not backup_dir.exists():
        print(f'[X] 备份目录不存在: {backup_dir}', file=sys.stderr)
        print(HINT_EXPORT_FIRST, file=sys.stderr)
        return 1

    # 2. 列 zip
    zips = list_zips(backup_dir)
    if not zips:
        print(f'[X] 备份目录下无 backup-*.zip: {backup_dir}', file=sys.stderr)
        print(HINT_EXPORT_FIRST, file=sys.stderr)
        return 2

    if args.list:
        print(f'备份目录: {backup_dir}')
        print(f'共 {len(zips)} 个 backup zip, 按时间戳从新到旧:')
        for z in zips:
            ts = parse_zip_ts(z)
            size_kb = z.stat().st_size / 1024
            print(f'  {ts.strftime("%Y-%m-%d %H:%M:%S")}  {size_kb:>6.1f} KB  {z.name}')
        return 0

    # 3. 选最新
    latest = zips[0]
    ts = parse_zip_ts(latest)
    size_kb = latest.stat().st_size / 1024
    print(' 将恢复最新备份:')
    print(f'   路径:  {latest}')
    print(f'   时间:  {ts.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'   大小:  {size_kb:.1f} KB')

    # 4. 验证 zip（结构前置校验先于任何还原点创建与进度输出，避免"先宣布恢复、再失败"）
    try:
        with zipfile.ZipFile(latest) as z:
            z.testzip()
            _structure_err = _check_zip_structure(z, latest.name)
            if _structure_err:
                print(_structure_err, file=sys.stderr)
                return 4
            try:
                with z.open('distill-assets/capsules/capsules.json') as f:
                    n_caps = len(A.parse_capsules_text(f.read().decode('utf-8')))
            except KeyError:
                # 尚未产出过胶囊的备份（例如只沉淀了操作模式）同样可恢复，按 0 条处理
                n_caps = 0
                print('   [!] 该 zip 内没有 capsules/capsules.json，按 0 条胶囊恢复')
        print(f'   含:    {n_caps} capsules')
    except (zipfile.BadZipFile, json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
        print(f'[X] zip 损坏或结构异常: {e}', file=sys.stderr)
        return 4

    # 5. 还原前统一快照（无论目标是否存在 / 是否为空，确保任何还原均可回滚）
    ts_now = datetime.now().strftime('%Y%m%d-%H%M%S')
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    pre_dir = target_dir.parent / f'{target_dir.name}.pre-restore-{ts_now}'
    # 同秒重入时避免 FileExistsError，冲突则递增后缀
    _i = 0
    while pre_dir.exists():
        _i += 1
        pre_dir = target_dir.parent / f'{target_dir.name}.pre-restore-{ts_now}-{_i}'
    if target_dir.exists():
        # 目标存在即视为待覆盖；非空（即便仅含非胶囊文件）时要求确认，
        # 避免「存在非胶囊文件的目标目录」被静默整体覆盖（--force 跳过确认）
        _has_content = any(target_dir.iterdir())
        _has_caps = (target_dir / 'capsules' / 'capsules.json').exists()
        if _has_content and not args.force:
            n_existing = 0
            if _has_caps:
                try:
                    n_existing = len(json.loads((target_dir / 'capsules' / 'capsules.json').read_text(encoding='utf-8')))
                except (json.JSONDecodeError, OSError):
                    print('   [!] 目标 capsules.json 无法解析，按空库处理')
                print(f'\n[!]  目标目录已有 {n_existing} 条胶囊: {target_dir}')
            else:
                print(f'\n[!]  目标目录非空（含非胶囊文件），将被覆盖: {target_dir}')
            try:
                ans = input('   是否覆盖? (yes/否) ')
            except EOFError:
                # 非交互环境（管道 / agent 无 stdin 触发）无输入即视为取消，避免裸 traceback
                print('[X] 非交互环境无输入，取消恢复（如需强制请加 --force）')
                return 3
            if ans.strip().lower() not in ('yes', 'y', '是', '确认', '覆盖'):
                print('[X] 用户取消恢复')
                return 3
        # 备份当前到 .pre-restore-XXX/
        print(f'   备份当前到: {pre_dir}')
        shutil.copytree(target_dir, pre_dir)
    else:
        # 目标不存在：仍创建空还原点，保证回滚语义一致
        pre_dir.mkdir(parents=True, exist_ok=True)
        print(f'   目标不存在，已创建空还原点: {pre_dir}')

    # 6. 解压到临时目录
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='distill-restore-') as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(latest) as z:
            stats = _safe_extract(z, tmp_path)
        assets_tmp = tmp_path / 'distill-assets'
        if not assets_tmp.is_dir():
            # 正常不可达（_check_zip_structure 已拦下）；保留为内部一致性兜底
            print('[X] 该 zip 内没有 distill-assets/ 目录，结构不符: %s' % latest.name, file=sys.stderr)
            print('    请确认这是本工具导出的 backup-*.zip（归档顶层应为 distill-assets/）', file=sys.stderr)
            return 4

        _skipped = stats['outside'] + stats['internal_state'] + stats['symlink']
        if _skipped:
            print('   [!] 已跳过 %d 个不应恢复的成员（越界 %d / 运行时内部状态 %d / 符号链接 %d）'
                  % (_skipped, stats['outside'], stats['internal_state'], stats['symlink']))

        # 7. 复制到目标 (合并覆盖，不删除既有文件；pre_dir 为还原点)
        shutil.copytree(assets_tmp, target_dir, dirs_exist_ok=True, copy_function=shutil.copy2)

        # 8. 验证恢复后的数量（解压源 n_caps 与落盘目标对账，捕捉复制/权限损坏；
        #    不与同一 zip 内的 capsules.json 自身比对，那等于同义反复）
        restored_path = target_dir / 'capsules' / 'capsules.json'
        if not restored_path.exists() and n_caps == 0:
            restored_n = 0
        else:
            try:
                restored_n = len(A.parse_capsules_text(restored_path.read_text(encoding='utf-8')))
            except (json.JSONDecodeError, OSError, ValueError, UnicodeDecodeError) as e:
                print(f'[X] 恢复后胶囊库读取失败: {e}', file=sys.stderr)
                _rollback(pre_dir, target_dir)
                return 5
        if restored_n != n_caps:
            print(f'[X] 验证失败: 期望 {n_caps} 条, 实际 {restored_n} 条', file=sys.stderr)
            # 复制在前、验证在后：验证失败立即用还原点覆盖回目标目录（还原点保留不删）
            _rollback(pre_dir, target_dir)
            return 5

    # 9. 写审计
    try:
        ev_path = target_dir / 'events.jsonl'
        prev_hash = ''
        if ev_path.exists():
            lines = [l for l in ev_path.read_text(encoding='utf-8').splitlines() if l.strip()]
            if lines:
                prev_hash = json.loads(lines[-1]).get('hash', '')
        from datetime import timezone, timedelta
        tz = timezone(timedelta(hours=8))
        now = datetime.now(tz).isoformat(timespec='seconds')
        evt = {
            'ts': now,
            'type': 'restore',
            'actor': AUTHOR,
            'msg': f'从 {latest.name} 恢复 {n_caps} capsules',
            'source_zip': latest.name,
            'capsules_restored': n_caps,
            'prev_hash': prev_hash,
        }
        append_event(ev_path, evt)
    except Exception as e:
        # 审计失败不阻塞恢复, 仅警告
        print(f'[!]  审计链写入失败 (已恢复, 不影响数据): {e}')

    # 10. 回报
    print(f'\n[OK] 恢复成功: {n_caps} capsules 已就位 → {target_dir}')
    print('   建议: 跑一次「跑一下蒸馏」触发首次双轮对齐基线')
    return 0


if __name__ == '__main__':
    sys.exit(main())
