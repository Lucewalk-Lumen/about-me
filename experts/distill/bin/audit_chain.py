# -*- coding: utf-8 -*-
"""审计链工具：哈希与链式校验的单一实现。

被 restore_backup.py / share_capsules.py 复用（避免各脚本各自实现导致口径漂移），
也可直接作为命令行工具校验事件链是否被篡改：

    python3 bin/audit_chain.py --verify <资产库目录>
    python3 bin/audit_chain.py --file <events.jsonl 路径>

退出码：0 = 链完整（或尚无审计）；1 = 链断裂 / 行被改写；2 = 参数或路径错误。

哈希语义（完整 64 位 SHA-256，不截断）：
    hash = sha256(json.dumps(去除 hash 字段后的归一化 JSON, sort_keys=True, ensure_ascii=False))
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def compute_hash(evt: dict) -> str:
    """计算事件 hash：对去除 hash 字段后的归一化 JSON 求 SHA-256（完整 64 位）。"""
    body = json.dumps(
        {k: v for k, v in evt.items() if k != "hash"},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def verify_chain(path: Path) -> tuple[bool, list[str]]:
    """校验 events.jsonl 的 prev_hash 链与每行的 hash 自校验。

    返回 (ok, errors)。文件不存在视为 ok（尚未有审计）；空文件视为 ok。
    """
    errors: list[str] = []
    if not path.exists():
        return True, errors
    prev_hash = ""
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for i, ln in enumerate(lines, 1):
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError as e:  # noqa: BLE001
            errors.append(f"L{i}: JSON 解析失败: {e}")
            continue
        # 链式校验：本行 prev_hash 必须等于上一行 hash
        if obj.get("prev_hash", "") != prev_hash:
            errors.append(
                f"L{i}: prev_hash 链断裂 "
                f"(期望 {(prev_hash or '空')[:8]}, 实得 {(obj.get('prev_hash') or '空')[:8]})"
            )
        # 哈希自校验：重算 hash 必须相等
        if obj.get("hash", "") != compute_hash(obj):
            errors.append(f"L{i}: hash 不匹配 (type={obj.get('type')})")
        prev_hash = obj.get("hash", "")
    return (len(errors) == 0), errors


def append_event(path: Path, evt: dict) -> str:
    """追加一条审计事件（自动补 hash），返回其 hash。"""
    evt = dict(evt)
    evt["hash"] = compute_hash(evt)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    return evt["hash"]


def main(argv=None) -> int:
    """命令行入口：校验 events.jsonl 的防篡改链。"""
    import argparse
    import os
    import sys

    p = argparse.ArgumentParser(description="审计链工具：校验 events.jsonl 防篡改链")
    p.add_argument("--verify", metavar="ASSETS_DIR", default="",
                   help="资产库目录（其下的 events.jsonl）")
    p.add_argument("--file", metavar="PATH", default="",
                   help="直接指定 events.jsonl 路径")
    args = p.parse_args(argv)

    if args.file:
        target = Path(args.file).expanduser()
        if not target.is_file():
            print("[X] 找不到文件: %s" % target, file=sys.stderr)
            return 2
    else:
        assets = args.verify or os.environ.get("DISTILL_ASSETS_DIR", "")
        if not assets:
            p.print_help()
            return 2
        assets = Path(assets).expanduser()
        if not assets.is_dir():
            print("[X] 找不到资产库目录: %s" % assets, file=sys.stderr)
            return 2
        target = assets / "events.jsonl"

    if not target.exists():
        print("[OK] 尚无审计链（%s 不存在），视为完整" % target)
        return 0

    lines = [ln for ln in target.read_text(encoding="utf-8").splitlines() if ln.strip()]
    ok, errors = verify_chain(target)
    if ok:
        print("[OK] 审计链完整：%d 行，prev_hash 链与每行 hash 自校验均通过" % len(lines))
        return 0
    print("[X] 审计链异常：%d 行中发现 %d 处问题" % (len(lines), len(errors)), file=sys.stderr)
    for e in errors:
        print("    - %s" % e, file=sys.stderr)
    return 1


if __name__ == "__main__":
    import sys as _sys

    _sys.exit(main())
