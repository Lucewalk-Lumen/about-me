#!/usr/bin/env python3
"""Create a prefilled description preview HTML from config.json or markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_TEMPLATE = SKILL_DIR / "assets" / "description-preview.html"


def read_description(args: argparse.Namespace) -> str:
    if args.config:
        try:
            config = json.loads(args.config.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            # 配置读取/解析异常兜底，避免裸 traceback
            raise SystemExit(f"[prepare-description] 读取/解析配置失败：{e}")
        return str(config.get("description") or "")
    if args.description_file:
        try:
            return args.description_file.read_text(encoding="utf-8")
        except OSError as e:
            raise SystemExit(f"[prepare-description] 读取描述文件失败：{e}")
    if args.description:
        return args.description
    raise SystemExit("must provide --config, --description-file, or --description")


def js_template_literal(value: str) -> str:
    # 先转义反斜杠/反引号/插值，再转义 </script> 防止在 <script> 模板字面量中提前闭合（XSS）
    return (value.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
                .replace("</", "<\\/"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare description-preview.html with agent description prefilled")
    parser.add_argument("--config", type=Path, help="agent config.json; reads config.description")
    parser.add_argument("--description-file", type=Path, help="markdown description file")
    parser.add_argument("--description", help="markdown description text")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="bundled description-preview.html")
    parser.add_argument("--output", type=Path, required=True, help="output HTML path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    description = read_description(args)
    html = args.template.read_text(encoding="utf-8")
    marker_start = "const defaultDescription = `"
    marker_end = "`;"
    start = html.find(marker_start)
    if start < 0:
        raise SystemExit("template does not contain defaultDescription marker")
    value_start = start + len(marker_start)
    value_end = html.find(marker_end, value_start)
    if value_end < 0:
        raise SystemExit("template defaultDescription is not terminated")
    html = html[:value_start] + js_template_literal(description) + html[value_end:]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(args.output.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
