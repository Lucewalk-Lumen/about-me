#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 6.3 SHARE 分发脚本（agent 可调用的低层原语）

生成 capsule-pack-YYYYMMDD-HHMMSS.zip 分发包。默认净化：不含个人操作记录
（events / genes / rejected），并剥离指向个人任务记录的指针。

用法:
  python3 bin/share_capsules.py                    # 默认净化版
  python3 bin/share_capsules.py --with-audit       # 原状版（含审计链、基因库、被拒候选）
  python3 bin/share_capsules.py --out-dir X        # 自定义输出目录
  python3 bin/share_capsules.py --dry-run          # 只列将打包的内容

退出码:
  0 = 成功
  1 = 资产库不存在 / 无胶囊可分享
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import assets_lib as A  # noqa: E402
from audit_chain import append_event  # noqa: E402
from pkgmeta import load_pkg_meta  # noqa: E402


def main():
    p = argparse.ArgumentParser(description='生成分发胶囊包 (Stage 6.3 SHARE)')
    p.add_argument('--assets', default=os.environ.get('DISTILL_ASSETS_DIR',
                   str(Path.home() / '.workbuddy' / 'distill-assets')),
                   help='资产库目录 (默认 ~/.workbuddy/distill-assets，可用 DISTILL_ASSETS_DIR 覆盖)')
    p.add_argument('--out-dir', default=os.environ.get('DISTILL_BACKUP_DIR',
                   str(Path.home() / 'Documents' / 'distill-backup')),
                   help='输出目录 (默认 ~/Documents/distill-backup，可用 DISTILL_BACKUP_DIR 覆盖)')
    p.add_argument('--with-audit', action='store_true',
                   help='原状打包 (含 events/genes/rejected)，不净化')
    p.add_argument('--dry-run', action='store_true', help='只列将打包文件')
    args = p.parse_args()

    assets_dir = Path(args.assets).expanduser()
    out_dir = Path(args.out_dir).expanduser()

    # 包元数据由 plugin.json 驱动，允许环境变量覆盖
    meta = load_pkg_meta()
    VERSION = os.environ.get('DISTILL_VERSION') or meta['version']
    AUTHOR = os.environ.get('DISTILL_AUTHOR') or meta['author_name']
    AUTHOR_EMAIL = meta['author_email']

    # 1. 资产库与胶囊库
    if not assets_dir.exists():
        print('[X] 资产库不存在: %s' % assets_dir, file=sys.stderr)
        return 1
    try:
        caps, caps_path = A.load_capsules(assets_dir)
    except FileNotFoundError as e:
        print('[X] 未找到胶囊库: %s（资产库为空, 无可分享胶囊）' % e, file=sys.stderr)
        return 1
    except (ValueError, json.JSONDecodeError) as e:
        print('[X] 胶囊库无法解析: %s' % e, file=sys.stderr)
        return 1
    n_caps = len(caps)
    if n_caps == 0:
        print('[X] 胶囊库为空 (0 条), 无可分享内容', file=sys.stderr)
        return 1

    # 2. 命令安全扫描（代码级；模式清单与 agents/distill.md Stage 3 一致）
    cmd_hits = A.scan_dangerous(caps)
    if cmd_hits:
        print('[!]  命令安全扫描：%d 条资产的步骤段命中危险命令模式，分享后复用需人工确认：' % len(cmd_hits))
        for cid, label in cmd_hits:
            print('   - %s: %s' % (cid, label))

    # 3. 组装打包清单（三元组: (源路径, 归档名, 内联内容)；源路径为 None 时写入内联内容）
    files_to_pack = []
    if args.with_audit:
        # 原状版：直接写源文件，保留指针与个人操作记录
        files_to_pack.append((caps_path, 'capsules/capsules.json', None))
        index_src = assets_dir / 'index.md'
        if not index_src.exists():
            index_src = assets_dir / 'capsules' / 'index.md'
        if index_src.exists():
            files_to_pack.append((index_src, 'capsules/index.md', None))
        for fname in ('events.jsonl', 'genes.json', 'rejected.json'):
            f = assets_dir / fname
            if f.exists():
                files_to_pack.append((f, fname, None))
    else:
        # 净化版：剥离私密指针；接收方索引由净化后的胶囊现场生成，
        # 不再原样复制源索引（源索引可能留有指针、绝对路径与时间戳）
        safe_caps = A.sanitize_capsules(caps)
        files_to_pack.append((None, 'capsules/capsules.json',
                              json.dumps(safe_caps, ensure_ascii=False, indent=2)))
        files_to_pack.append((None, 'capsules/index.md',
                              A.render_index(safe_caps, source_note='净化版：索引由分发内容现场生成')))

    # 4. 生成接收方 README.md
    today = datetime.now().strftime('%Y-%m-%d')
    # 净化版/原状版用不同文件名，防止意外覆盖；原状版显式标注「含个人数据」降低误分享风险
    suffix = '-含个人数据' if args.with_audit else ''
    base_name = 'capsule-pack-%s%s' % (datetime.now().strftime('%Y%m%d-%H%M%S'), suffix)
    # 同秒重复运行防覆盖：目标文件已存在则递增后缀
    pack_name = base_name + '.zip'
    _i = 1
    while (out_dir / pack_name).exists():
        _i += 1
        pack_name = '%s-%d.zip' % (base_name, _i)

    if args.with_audit:
        pkg_intro = ('这是一个**原状分发包**——除 `capsules/capsules.json`（胶囊主库）和 '
                     '`capsules/index.md`（检索索引）外，还包含完整事件审计链 `events.jsonl`、'
                     '操作模式库 `genes.json`、被拒候选 `rejected.json`。')
        audit_note = ('本包**含** `events.jsonl` / `genes.json` / `rejected.json`——接收方直接获得完整事件链、'
                      '基因/操作模式库与被拒候选。注意这些属个人操作隐私数据，请谨慎分享')
        audit_copy_steps = ('\n# 3b) 原状版附加文件（可选复制，获得完整事件链/基因/被拒列表）\n'
                            'cp /tmp/capsules-in/events.jsonl   ~/.workbuddy/distill-assets/\n'
                            'cp /tmp/capsules-in/genes.json     ~/.workbuddy/distill-assets/\n'
                            'cp /tmp/capsules-in/rejected.json  ~/.workbuddy/distill-assets/\n')
    else:
        pkg_intro = ('这是一个**已净化的胶囊包**——只含 `capsules/capsules.json`（胶囊主库）和 '
                     '`capsules/index.md`（检索索引），不含个人审计链、操作模式库、被拒候选等私密数据；'
                     '指向个人任务记录的指针也已剥离，索引由分发内容现场生成。')
        audit_note = ('本包**不含** `events.jsonl` / `genes.json` / `rejected.json`——'
                      '你的首次蒸馏会自动建空库起步，无副作用')
        audit_copy_steps = ''

    if AUTHOR_EMAIL.strip():
        contact_line = '发现问题或想反馈胶囊质量，联系：%s' % AUTHOR_EMAIL
    else:
        contact_line = '发现问题或想反馈胶囊质量，请通过分发平台的作者主页联系作者。'

    readme_content = f'''# Distill 胶囊分发包

> 由 **{AUTHOR}** 于 **{today}** 生成
> 含 **{n_caps} 条 capsule**（操作流程包）
> 版本：distill v{VERSION}+

## 这是什么

{pkg_intro}

接收方复制到自己的 `~/.workbuddy/distill-assets/capsules/` 后，distill 首次运行检测到已有胶囊（无 `.first_run` 哨兵但胶囊库非空），**跳过历史补齐**，直接进入日常流程。

## 安装步骤

```bash
# 1) 装 distill 专家包（如已装可跳过）
#    在 WorkBuddy / CodeBuddy 专家中心搜 distill，安装 v{VERSION}+

# 2) 解压分发包到临时目录
unzip capsule-pack-*.zip -d /tmp/capsules-in
#    Windows（PowerShell）等价写法：
#    Expand-Archive capsule-pack-*.zip -DestinationPath $env:TEMP\\capsules-in

# 3) 复制到自己的资产库
mkdir -p ~/.workbuddy/distill-assets/capsules
cp /tmp/capsules-in/capsules/capsules.json ~/.workbuddy/distill-assets/capsules/
cp /tmp/capsules-in/capsules/index.md     ~/.workbuddy/distill-assets/capsules/
#    Windows 等价写法：
#    copy $env:TEMP\\capsules-in\\capsules\\capsules.json $env:USERPROFILE\\.workbuddy\\distill-assets\\capsules\\
#    copy $env:TEMP\\capsules-in\\capsules\\index.md     $env:USERPROFILE\\.workbuddy\\distill-assets\\capsules\\
{audit_copy_steps}
# 4) 验证
python3 bin/query_capsules.py --check
# 应报「结构校验通过」，且条数为 {n_caps}
# 若后面跟一行 [!] 提示「{n_caps} 条缺 src」，属正常：
#   src 是指向**原作者本机记录**的私有指针，净化时已按设计剥离，
#   因此它在接收方这边天然不存在，属"本地可追溯性"提示而非结构错误。
#   若你希望入库资产都带指针，可自行补上指向**你自己**记录的 src。

# 5) 检索一下，确认能调用
python3 bin/query_capsules.py <你的关键词>
```

## 注意事项

- {audit_note}
- 本包**不含** `.first_run` 哨兵——直接进入日常流程，不触发历史补齐
- 本包胶囊**不含** `src`（原生记录指针）——它指向原作者本机记录，属私有字段，
  净化时已剥离；`--check` 会以 `[!]` 提示但不报错。`source`（作者/机构/链接）与
  `source_quote`（原文摘录）**完整保留**，引用来源依旧可追溯
- 引用胶囊时遵守引用保真铁律：不编引用 / 不归观点 / 标注无支撑 / 报告越界
- capsule 是**操作流程知识**（带 R/I/A1/A2/E/B 六段），不是学术结论

## 反馈

{contact_line}
'''
    files_to_pack.append((None, 'README.md', readme_content))

    # 5. 干跑 / 实跑
    if args.dry_run:
        print('【DRY RUN】将打包到 %s:' % (out_dir / pack_name))
        for src_path, arcname, content in files_to_pack:
            if src_path is not None:
                print('  %8d 字节  %s  (源: %s)' % (src_path.stat().st_size, arcname, src_path.name))
            else:
                print('  %8d 字符  %s  (生成)' % (len(content), arcname))
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / pack_name

    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for src_path, arcname, content in files_to_pack:
            if src_path is not None:
                z.write(src_path, arcname)
            else:
                z.writestr(arcname, content)

    # 6. 审计链（type=share），prev_hash 链逻辑与 restore_backup.py 一致（复用 audit_chain）
    try:
        from datetime import timedelta, timezone
        ev_path = assets_dir / 'events.jsonl'
        prev_hash = ''
        if ev_path.exists():
            lines = [l for l in ev_path.read_text(encoding='utf-8').splitlines() if l.strip()]
            if lines:
                prev_hash = json.loads(lines[-1]).get('hash', '')
        tz = timezone(timedelta(hours=8))
        now = datetime.now(tz).isoformat(timespec='seconds')
        mode_audit = '原状版(含审计链)' if args.with_audit else '净化版'
        evt = {
            'ts': now,
            'type': 'share',
            'actor': AUTHOR,
            'msg': '分享分发包 %s (%s, %d capsules)' % (out_path.name, mode_audit, n_caps),
            'pack_path': out_path.name,  # 只存文件名，避免审计链暴露用户主目录绝对路径
            'capsules_shared': n_caps,
            'sanitized': not args.with_audit,
            'src_stripped': not args.with_audit,  # 净化版已剥离指针
            'cmd_scan_hits': len(cmd_hits),       # 危险命令命中数
            'prev_hash': prev_hash,
        }
        append_event(ev_path, evt)
    except Exception as e:
        # 审计失败不阻塞打包，仅警告
        print('[!]  审计链写入失败 (已生成分发包, 不影响数据): %s' % e, file=sys.stderr)

    size_kb = out_path.stat().st_size / 1024
    mode = '原状版(含审计链)' if args.with_audit else '净化版'
    # 内容清单由**实际写入的成员**推导，不硬编码：否则资产库缺 index.md 时提示会谎报「含 index.md」
    _members = [arc for _s, arc, _c in files_to_pack]
    _parts = ['%d capsules' % n_caps]
    if 'capsules/index.md' in _members:
        _parts.append('index.md')
    if 'README.md' in _members:
        _parts.append('README.md')
    print('[OK] 分发包已生成 (%s):' % mode)
    print('   路径: %s' % out_path)
    print('   大小: %.1f KB' % size_kb)
    print('   含:   %s' % ' + '.join(_parts))
    if 'capsules/index.md' not in _members:
        print('   [!] 资产库内没有 index.md，本包不含检索索引（接收方首次跑蒸馏时会自行生成）')
    if args.with_audit:
        print('   [!] 警告：原状版含个人操作隐私（events.jsonl / genes.json / rejected.json），')
        print('      外传前请确认接收方可信，切勿误分享到公开/共享渠道。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
