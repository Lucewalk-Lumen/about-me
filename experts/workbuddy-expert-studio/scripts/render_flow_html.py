#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_flow_html.py — 九阶段流水线可视化生成器（数据驱动、零第三方依赖）。

用途：把本团的九阶段协作流程 + 角色分工渲染成一张自包含、可嵌入、
可二次优化的 HTML 报告（assets/flow-report.html），供智能体在交付物中嵌入网页或做
前端优化时使用。

设计原则（"更合理"的重构目标）：
  - 内容（STAGES / ROLES）与表现（CSS / 模板）分离，去掉旧版一整坨写死的 HTML 字符串；
  - 阶段卡片由数据循环生成，不逐阶段复制粘贴 markup；
  - 纯标准库；从包根或脚本位置推导输出路径；CLI 可单独跑。

用法：python3 scripts/render_flow_html.py [包根]   # 包根必须是已存在的目录（否则报错退出，不生成垃圾目录）
"""
import argparse
import os
import sys

OUT_REL = os.path.join("assets", "flow-report.html")

# ---------------------------------------------------------------------------
# 内容数据（单一事实源，来自 references/workbuddy-expert-studio-flow-9stage.md）
# ---------------------------------------------------------------------------

ROLES = [
    ("workbuddy-expert-studio-team-lead", "齐衡", "交付总监（主理人）· 统筹编排与质量把关"),
    ("agent-diagnostician", "沈证", "立项诊断官 · 阶段 1"),
    ("agent-architect", "高构", "结构设计官 · 阶段 2"),
    ("agent-engineer", "柯码", "实现分片官 · 阶段 3–4"),
    ("agent-auditor", "严证", "取证核查官 · 阶段 5"),
    ("agent-packager", "包洁", "干净落位官 · 阶段 6"),
    ("agent-release-chronicler", "史衡", "验收沉淀官 · 阶段 7–9"),
]

STAGES = [
    {
        "no": 1,
        "title": "立项与诊断",
        "owner": "agent-diagnostician",
        "summary": "拿到被驳回的包，第一件事不是改，是证伪用户的猜测。",
        "actions": [
            "解包 → 全量静态分析（不抽查）",
            "本机实测关键命令，保留原始输出",
            "按多维标准推演，三档标注（实测 / 静态推断 / 推断待验证）",
        ],
        "discipline": "结论分三档标注，推测不与根因混淆",
    },
    {
        "no": 2,
        "title": "结构设计",
        "owner": "agent-architect",
        "summary": "定包骨架与协作拓扑，把结构纪律落成清晰约定。",
        "actions": [
            "包骨架：目录结构、清单、成员与技能组织",
            "成员结构六要素：角色 / 领域 / 框架 / 数据 / 输出 / 回传",
            "协作拓扑：建团 → 路由 → 中转（成员不直连）→ 回传 → 质量把关",
        ],
        "discipline": "设计红线：禁用 emoji 图标、渐变发光毛玻璃、AI 模板味文案",
    },
    {
        "no": 3,
        "title": "实现与分片",
        "owner": "agent-engineer",
        "summary": "长文档会自动拆分，确保不超出平台能完整读取的长度。",
        "actions": [
            "主文件按平台口径估算长度，超限即规划拆分",
            "正文只留流程、规则与索引，长细则移入分片",
            "能力边界具体到数字，不写「可优化」",
        ],
        "discipline": "长度按平台口径统计，确保拆分判断准确",
    },
    {
        "no": 4,
        "title": "质量校验",
        "owner": "agent-engineer",
        "summary": "把每一步的检查标准写成自动校验，随流程一起运行。",
        "actions": [
            "检查文件是否齐全、用词是否规范、篇幅是否超限、分片是否完整",
            "新增功能时，同轮补上对应校验",
            "确保校验真的会拦住问题：缺失文件必报错、复原后必通过",
        ],
        "discipline": "每条校验都要验证：既会正确拦截、也不误伤",
    },
    {
        "no": 5,
        "title": "审计与取证",
        "owner": "agent-auditor",
        "summary": "审查脚本必须真跑一遍，拿产物清单逐个核对。",
        "actions": [
            "结构化文件写完再读回核对（先写后检等于没检）",
            "静态扫描命中逐条甄别，不甩命中数",
            "报告零命中时，必须用反例自证",
        ],
        "discipline": "误报与漏报同等对待，不为通过而放宽标准",
    },
    {
        "no": 6,
        "title": "干净打包",
        "owner": "agent-packager",
        "summary": "三条禁令：禁指向上一轮名字 / 禁相对路径 / 改完必复跑验证。",
        "actions": [
            "换版本九步：解压隔离 → 比对 → 排查风险 → 备份 → 回读",
            "校验在副本环境进行，不在正式产物上直接改",
            "替换与复核分离（另写独立复核）",
        ],
        "discipline": "校验在副本进行；替换后另写独立复核",
    },
    {
        "no": 7,
        "title": "验收放行",
        "owner": "agent-release-chronicler",
        "summary": "官方校验器通过 ≠ 可以上线；深度审查仍可能发现实质缺陷。",
        "actions": [
            "验收清单可脚本复跑（期望值 / 当前值 / 严重度）",
            "一键复跑，结果分通过 / 告警 / 失败",
        ],
        "discipline": "官方校验通过不等于无缺陷，深度审查不可省",
    },
    {
        "no": 8,
        "title": "版本治理",
        "owner": "agent-release-chronicler",
        "summary": "版本号以插件清单为唯一真源；更新日志不作为版本依据。",
        "actions": [
            "计数类数字实时取自校验结果，不手写",
            "文档引用校验结果，不手写口径",
        ],
        "discipline": "版本单一真源；四处一致性核对",
    },
    {
        "no": 9,
        "title": "沉淀资产",
        "owner": "agent-release-chronicler",
        "summary": "把可复用做法落成经验卡片，回灌演进环。",
        "actions": [
            "蒸馏六段资产 R/I/A1/A2/E/B，三关：可操作 / 可复用 / 独特",
            "经验卡片字段：场景 / 方法 / 避坑 / 效果 / 延伸 / 标签",
        ],
        "discipline": "删除是红线：默认移动代替删除，删除先征求同意",
    },
]

# ---------------------------------------------------------------------------
# 表现层（CSS / 模板）
# ---------------------------------------------------------------------------

CSS = """
:root{
  --bg:#f7f8fa; --card:#ffffff; --ink:#1f2933; --muted:#6b7280;
  --line:#e5e7eb; --accent:#2563eb; --accent-soft:#eff4ff;
  --ok:#16a34a; --warn:#d97706; --rail:#cbd5e1;
}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.6;padding:32px 20px}
.wrap{max-width:920px;margin:0 auto}
h1{font-size:24px;margin:0 0 4px}
.sub{color:var(--muted);margin:0 0 24px;font-size:14px}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 28px}
.legend .chip{background:var(--card);border:1px solid var(--line);border-radius:999px;
  padding:4px 12px;font-size:12px;color:var(--muted)}
.flow{position:relative;padding-left:28px}
.flow::before{content:"";position:absolute;left:11px;top:8px;bottom:8px;width:2px;background:var(--rail)}
.stage{position:relative;background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;margin:0 0 16px}
.stage::before{content:"";position:absolute;left:-21px;top:22px;width:12px;height:12px;border-radius:50%;
  background:var(--accent);border:3px solid var(--bg)}
.stage .head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.stage .no{font-weight:700;color:var(--accent);font-size:13px}
.stage .name{font-size:17px;font-weight:600}
.stage .owner{margin-left:auto;font-size:12px;color:var(--muted)}
.stage .summary{margin:8px 0 10px;font-size:14px}
.stage ul{margin:0 0 10px;padding-left:18px;font-size:13px;color:#374151}
.stage .disc{font-size:12px;background:var(--accent-soft);color:var(--accent);
  border-radius:8px;padding:6px 10px;display:inline-block}
footer{color:var(--muted);font-size:12px;margin-top:8px;text-align:center}
"""


def _esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _role_label(role_id):
    for rid, name, _desc in ROLES:
        if rid == role_id:
            return name
    return role_id


def _stage_card(stage):
    items = "".join(f"<li>{_esc(a)}</li>" for a in stage["actions"])
    return f"""  <section class="stage">
    <div class="head">
      <span class="no">阶段 {stage['no']}</span>
      <span class="name">{_esc(stage['title'])}</span>
      <span class="owner">负责：{_esc(_role_label(stage['owner']))}</span>
    </div>
    <p class="summary">{_esc(stage['summary'])}</p>
    <ul>{items}</ul>
    <span class="disc">纪律：{_esc(stage['discipline'])}</span>
  </section>"""


def render():
    chips = "".join(
        f'<span class="chip">{_esc(name)} · {_esc(desc.split("·")[0].strip())}</span>'
        for _rid, name, desc in ROLES
    )
    cards = "\n".join(_stage_card(s) for s in STAGES)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WorkBuddy 专家开发工坊 · 九阶段流水线可视化</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <h1>WorkBuddy 专家开发工坊 · 九阶段流水线</h1>
  <p class="sub">九阶段一步步推进：先对齐需求，再设计、撰写、检查、打包与验收；每一步都可复跑、可追溯。</p>
  <div class="legend">{chips}</div>
  <div class="flow">
{cards}
  </div>
  <footer>WorkBuddy 专家开发工坊 · 九阶段协作流程一览</footer>
</div>
</body>
</html>
"""


def build_parser():
    ap = argparse.ArgumentParser(
        prog="render_flow_html.py",
        description="生成九阶段流水线可视化 HTML（assets/flow-report.html，数据驱动、可嵌入）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="包根必须是已存在的目录；非法入参（如把 -h/占位符当包根）不会生成垃圾目录。")
    ap.add_argument("pkg", nargs="?", default=None,
                    help="包根目录（默认脚本上级目录；必须已存在）")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    pkg = args.pkg or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pkg = os.path.abspath(pkg)
    # R5：校验 sys.argv[1] 必须是**存在的目录**，否则报错退出（此前会生成 `--help/` 之类的垃圾目录）
    if not os.path.isdir(pkg):
        print(f"[FAIL] render_flow_html: 包根不是已存在的目录: {pkg}", file=sys.stderr)
        return 2
    out = os.path.join(pkg, OUT_REL)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render())
    print(f"[OK] render_flow_html: 已生成 {os.path.relpath(out, pkg)}（{len(STAGES)} 阶段 / {len(ROLES)} 角色）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
