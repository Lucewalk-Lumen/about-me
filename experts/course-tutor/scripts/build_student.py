#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「学生端包」zip（· 上传 open WorkBuddy 审核的学生端包）。

**通用版**学生端包——不内嵌教师真实定位、不含任何课程清单，学生自动发现课程中枢。
学生安装后通过「文档授权」连接教师中枢并自动同步。

在教师包根目录运行：
    python scripts/build_student.py

产物：dist/course-companion-<版本>.zip
"""

import json
import os
import re
import shutil
import sys
import zipfile


def _harden_console():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_harden_console()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
PLUGIN_JSON = os.path.join(ROOT, ".codebuddy-plugin", "plugin.json")
STUDENT_DIR = os.path.join(ROOT, "student")
STUDENT_PROMPT = os.path.join(STUDENT_DIR, "student_prompt.md")
STUDENT_TEMPLATE = os.path.join(STUDENT_DIR, "student_plugin_template.json")
STUDENT_DH = os.path.join(STUDENT_DIR, "data_hub_config.json")
STAGING = os.path.join(ROOT, ".build_staging", "student_pkg")
DIST_DIR = os.path.join(ROOT, "dist")
MAX_EXPERT_PROMPT_CHARS = 20000
AGENT_FRONTMATTER_ALLOWED = ("name", "description", "displayName", "profession", "maxTurns", "skills")
PLUGIN_ROOT_REF_RE = re.compile(r"\$\{CODEBUDDY_PLUGIN_ROOT\}/([A-Za-z0-9_./\-]+)")
TEXT_SUFFIXES = (".md", ".json", ".txt", ".yml", ".yaml")
SKIP_FILE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
SKIP_DIR_NAMES = {"__MACOSX", "__pycache__"}
SKIP_FILE_SUFFIXES = (".pyc", ".pyo")


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def read_version():
    return str(load_json(PLUGIN_JSON).get("version", "0.0.0"))


def build_frontmatter():
    return (
        "---\n"
        "name: course-companion\n"
        "description: Course Companion (student edition) — zero preset. Student authorizes the teacher's hub document to connect, verifies identity by student ID + name, learns with Socratic guidance, and auto-syncs course materials. No course info is bundled.\n"
        "displayName:\n"
        '  en: "Yunzhi"\n'
        '  zh: "耘知"\n'
        "profession:\n"
        '  en: "Course Companion"\n'
        '  zh: "课程伴学精灵"\n'
        "maxTurns: 120\n"
        "---\n"
    )


def copy_tree(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*sorted(SKIP_FILE_NAMES | SKIP_DIR_NAMES), "*.pyc", "*.pyo"))


def check_frontmatter(path, label):
    raw = open(path, encoding="utf-8", errors="replace").read()
    lines = raw.split("\n")
    if not lines or lines[0].strip() != "---":
        print(f"[FAIL] {label} 缺少 frontmatter")
        sys.exit(1)
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        print(f"[FAIL] {label} frontmatter 未闭合")
        sys.exit(1)
    top = [lines[j].split(":", 1)[0].strip() for j in range(1, end)
           if lines[j][:1] not in (" ", "\t", "#") and ":" in lines[j]]
    illegal = [k for k in top if k not in AGENT_FRONTMATTER_ALLOWED]
    if illegal:
        print(f"[FAIL] {label} frontmatter 含白名单外键 {illegal}")
        sys.exit(1)


def check_length(path):
    raw = open(path, "rb").read()
    total = len(raw.decode("utf-8"))
    if total > MAX_EXPERT_PROMPT_CHARS:
        print(f"[FAIL] 学生端 主指令 超长 {total} > {MAX_EXPERT_PROMPT_CHARS}，会被静默截断")
        sys.exit(1)
    print(f"[OK] 学生端 主指令 长度 {total} 字符（上限 {MAX_EXPERT_PROMPT_CHARS}）")


def check_plugin_root_refs(staging):
    problems = []
    for dp, _, fns in os.walk(staging):
        for fn in fns:
            if not fn.endswith(TEXT_SUFFIXES):
                continue
            fp = os.path.join(dp, fn)
            rel = os.path.relpath(fp, staging).replace(os.sep, "/")
            try:
                text = open(fp, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if "\x00" in text:
                continue
            for m in PLUGIN_ROOT_REF_RE.finditer(text):
                p = m.group(1).strip().rstrip("/")
                if not os.path.exists(os.path.join(staging, p.replace("/", os.sep))):
                    problems.append(f"包内 `${{CODEBUDDY_PLUGIN_ROOT}}/{p}` 不存在（出现于 {rel}）")
    return problems


def main():
    version = read_version()
    os.makedirs(DIST_DIR, exist_ok=True)
    # 1. 暂存：学生 skill 细则 + 脚本 + 头像 + 占位配置
    if os.path.exists(STAGING):
        shutil.rmtree(STAGING)
    os.makedirs(STAGING)
    copy_tree(os.path.join(ROOT, "student", "references", "skill"), os.path.join(STAGING, "references", "skill"))
    # 显式清单复制（审计修复：不再整目录拷贝 ROOT/scripts——
    # 否则教师端脚本会泄漏进学生包）
    os.makedirs(os.path.join(STAGING, "scripts"), exist_ok=True)
    for py in ("sync_assets.py", "discover_hub.py", "fetch_assets.py"):
        src = os.path.join(ROOT, "scripts", py)
        if not os.path.exists(src):
            print(f"[FAIL] 缺少 {py}，无法随学生端包分发：{src}")
            sys.exit(1)
        shutil.copyfile(src, os.path.join(STAGING, "scripts", py))
    # 学生端运行时脚本（skill 正文以 ${CODEBUDDY_PLUGIN_ROOT}/xxx.py 引用，必须随包分发）
    for py in ("course_tdoc.py", "course_calendar.py", "course_warn.py"):
        src = os.path.join(ROOT, py)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(STAGING, py))
    # 我的积分（学生侧）：与通用学生包一致，随包分发（单源：包根）
    os.makedirs(os.path.join(STAGING, "scripts"), exist_ok=True)
    for py in ("course_points.py", "course_usage_log.py"):
        src = os.path.join(ROOT, py)
        if not os.path.exists(src):
            print(f"[FAIL] 包根缺少 {py}，无法随学生端包分发：{src}")
            sys.exit(1)
        shutil.copyfile(src, os.path.join(STAGING, "scripts", py))
    # 头像
    os.makedirs(os.path.join(STAGING, "avatars"), exist_ok=True)
    shutil.copyfile(os.path.join(ROOT, "student", "avatars", "student.png"),
                   os.path.join(STAGING, "avatars", "student.png"))
    # 占位配置（不预置课程：courses 为空）
    shutil.copyfile(STUDENT_DH, os.path.join(STAGING, "data_hub_config.json"))
    # 学生端《更新记录》（随包分发，学生可感知变更）
    STUDENT_CHANGELOG = os.path.join(STUDENT_DIR, "CHANGELOG.md")
    if not os.path.exists(STUDENT_CHANGELOG):
        print(f"[FAIL] 缺少学生端 CHANGELOG，无法随包分发：{STUDENT_CHANGELOG}")
        sys.exit(1)
    shutil.copyfile(STUDENT_CHANGELOG, os.path.join(STAGING, "CHANGELOG.md"))
    # 学生端《使用说明》（学生视角 README，写到产物根）
    STUDENT_README = os.path.join(STUDENT_DIR, "README.md")
    if not os.path.exists(STUDENT_README):
        print(f"[FAIL] 缺少学生端 README，无法随包分发：{STUDENT_README}")
        sys.exit(1)
    shutil.copyfile(STUDENT_README, os.path.join(STAGING, "README.md"))
    # 2. 合成 agent md
    frontmatter = build_frontmatter()
    body = open(STUDENT_PROMPT, encoding="utf-8").read()
    agent_dir = os.path.join(STAGING, "agents")
    os.makedirs(agent_dir, exist_ok=True)
    with open(os.path.join(agent_dir, "course-companion.md"), "w", encoding="utf-8", newline="") as f:
        f.write(frontmatter + "\n" + body)
    check_frontmatter(os.path.join(agent_dir, "course-companion.md"), "学生端智能体")
    check_length(os.path.join(agent_dir, "course-companion.md"))
    # 3. 清单（注入 version 单一真源）
    template = load_json(STUDENT_TEMPLATE)
    teacher = load_json(PLUGIN_JSON)
    injected = {k: teacher[k] for k in ("version", "categoryId", "author", "license") if k in teacher}
    template.update(injected)
    # ── 九维元数据硬门禁（对照官方规范快照；不过则拒绝出包，防「专家中心不显示」类静默失败）──
    meta_problems = []
    for lang in ("zh", "en"):
        if template.get("defaultInitPrompt", {}).get(lang) != template.get("quickPrompts", [{}])[0].get(lang):
            meta_problems.append(f"defaultInitPrompt.{lang} != quickPrompts[0].{lang}（官方硬判据：首启提示语须与第一条推荐提示词完全一致）")
    zh_desc = template.get("displayDescription", {}).get("zh", "")
    cn = sum(1 for ch in zh_desc if "\u4e00" <= ch <= "\u9fff")
    if not (40 <= cn <= 50):
        meta_problems.append(f"displayDescription.zh 中文字数 {cn}（要求 40–50）")
    if template.get("plugin") != template.get("name"):
        meta_problems.append("plugin != name")
    if len(template.get("tags", [])) != 3:
        meta_problems.append(f"tags 数量 {len(template.get('tags', []))}（固定 3 个）")
    if len(template.get("quickPrompts", [])) != 3:
        meta_problems.append(f"quickPrompts 数量 {len(template.get('quickPrompts', []))}（固定 3 个）")
    for k in ("version", "categoryId", "author", "license"):
        if k not in template:
            meta_problems.append(f"缺少必填字段 {k}（应由教师包清单注入）")
    if meta_problems:
        print("[FAIL] 学生端包清单元数据门禁未通过（装包侧会静默拒收）：")
        for p in meta_problems:
            print("   - " + p)
        shutil.rmtree(STAGING)
        sys.exit(1)
    print("[OK] 清单元数据门禁通过（defaultInitPrompt==quickPrompts[0] · zh 40–50 字 · plugin==name · 3+3 · 必填齐）")
    pdir = os.path.join(STAGING, ".codebuddy-plugin")
    os.makedirs(pdir, exist_ok=True)
    with open(os.path.join(pdir, "plugin.json"), "w", encoding="utf-8", newline="") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
        f.write("\n")
    # 4. 包根引用自洽
    problems = check_plugin_root_refs(STAGING)
    if problems:
        print("[FAIL] 包根引用自洽未通过：")
        for p in problems:
            print("   - " + p)
        shutil.rmtree(STAGING)
        sys.exit(1)
    # 5. 打包
    top = f"course-companion-{version}"
    zp = os.path.join(DIST_DIR, top + ".zip")
    if os.path.exists(zp):
        os.remove(zp)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
        for dp, dns, fns in os.walk(STAGING):
            dns[:] = [d for d in dns if not should_skip(d)]
            for fn in fns:
                if should_skip(fn):
                    continue
                fp = os.path.join(dp, fn)
                rel = os.path.relpath(fp, STAGING)
                zf.write(fp, os.path.join(top, rel).replace(os.sep, "/"))
    shutil.rmtree(STAGING)
    print(f"[OK] 学生端包已生成（通用版）：{zp}")
    print(f"   顶层目录: {top}/")
    print("   接入提醒：学生安装后**自动发现教师课程中枢**即可连接，无需内嵌定位、无需重装即可自动同步。")


def should_skip(name):
    return name in SKIP_FILE_NAMES or name in SKIP_DIR_NAMES or name.endswith(SKIP_FILE_SUFFIXES)


if __name__ == "__main__":
    main()
