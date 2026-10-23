#!/usr/bin/env python3
"""Audit a SKILL.md against WorkBuddy Agent Skills rules.

Severity:
  ERROR  -> breaks/degrades the skill on WorkBuddy (fails CI)
  WARN   -> WorkBuddy ignores it, or it's a soft guideline (does not fail CI)

The SKILL.md format itself is an open standard
(https://github.com/agentskills/agentskills) — `name` + `description` are the
only universally-required fields. WorkBuddy additionally supports the Skill tool
and MCP-server tool names.

Usage: python3 tools/validate_skill.py [path/to/SKILL.md]
"""
import argparse
import re
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr so the [OK] / [X] result glyphs don't raise
# UnicodeEncodeError on Windows consoles that default to a legacy code page
# (e.g. GBK / cp936).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# WorkBuddy's tool model. WorkBuddy supports the Skill tool and MCP-server tool
# names in addition to the base tool set; unknown tokens are treated as
# MCP-server names and raise a soft warning, not an error.
WORKBUDDY_TOOLS = {
    "Bash", "Read", "Write", "Edit", "Glob", "Grep",
    "WebFetch", "WebSearch", "Skill", "Task", "TodoWrite", "NotebookEdit",
}

RULES = {
    "label": "WorkBuddy",
    "tools": WORKBUDDY_TOOLS,
    "recognized_keys": {"name", "description", "allowed-tools", "license", "version"},
    "reserved_name_words": set(),
    "bash_tool_names": {"Bash"},
    # Unknown tokens are likely MCP-server names in WorkBuddy — soft warn.
    "unknown_tool_severity": "warn",
}


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None, None
    end = text.find("\n---", 3)
    if end == -1:
        return None, None
    return text[3:end].lstrip("\n"), text[end + 4:]


def get_scalar(fm, key):
    m = re.search(rf"^{re.escape(key)}:\s*(.*)$", fm, re.MULTILINE)
    return m.group(1).strip().strip('"').strip("'") if m else None


def get_list_items(fm, key):
    items, capturing = [], False
    for ln in fm.splitlines():
        if re.match(rf"^{re.escape(key)}:\s*$", ln):
            capturing = True
            continue
        if capturing:
            m = re.match(r"^\s*-\s*(.+)$", ln)
            if m:
                items.append(m.group(1).strip())
            elif re.match(r"^[A-Za-z][\w-]*:", ln):
                break
    return items


def top_level_keys(fm):
    return [m.group(1) for ln in fm.splitlines()
            if (m := re.match(r"^([A-Za-z][\w-]*):", ln))]


def tool_base(entry):
    """Bash(python3 *) -> Bash ; Read -> Read ; My-MCP(do_thing) -> My-MCP."""
    return entry.split("(", 1)[0].strip()


def audit(path):
    rules = RULES
    label = rules["label"]
    text = Path(path).read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    errors, warns = [], []
    if fm is None:
        return ["no valid YAML frontmatter (--- block)"], []

    name = get_scalar(fm, "name")
    if not name:
        errors.append("name: missing (required)")
    else:
        if len(name) > 64:
            errors.append(f"name: {len(name)} > 64 chars")
        if not re.fullmatch(r"[a-z0-9-]+", name):
            errors.append(f"name: '{name}' must be lowercase letters/digits/hyphens")

    desc = get_scalar(fm, "description")
    if not desc:
        errors.append("description: missing (required)")
    elif len(desc) > 1024:
        errors.append(f"description: {len(desc)} > 1024 chars")

    # Tool grant analysis
    tools = get_list_items(fm, "allowed-tools")
    if not tools:
        inline = get_scalar(fm, "allowed-tools")
        if inline:
            tools = inline.split()
    if tools:  # a restriction is declared -> WorkBuddy enforces it
        bases = {tool_base(t) for t in tools}
        known = {b for b in bases if b in rules["tools"]}
        unknown = [t for t in tools if tool_base(t) not in rules["tools"]]
        uses_bash = bool(re.search(r"```bash", body)) or "python3 " in body
        if uses_bash and not (bases & rules["bash_tool_names"]):
            bash_names = " or ".join(f"'{n}'" for n in sorted(rules["bash_tool_names"]))
            errors.append(
                f"allowed-tools declares a restriction but omits {bash_names}, yet the "
                f"skill runs bash/python3 — under {label} those steps would be blocked"
            )
        if not known and rules["tools"]:
            warns.append(
                f"allowed-tools: no recognized {label} tool in the list "
                f"(unrecognized entries are treated as MCP-server names)"
            )
        if unknown:
            warns.append(
                f"allowed-tools: {unknown} are not {label} built-in tool names "
                f"(treated as MCP-server names)"
            )

    for k in top_level_keys(fm):
        if k not in rules["recognized_keys"]:
            warns.append(f"frontmatter '{k}': not a recognized {label} key (ignored by {label})")

    n = len(text.splitlines())
    if n > 500:
        warns.append(f"body: {n} lines > 500 (soft guideline for optimal performance)")

    return errors, warns


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", default="SKILL.md",
                        help="Path to SKILL.md (default: SKILL.md)")
    args = parser.parse_args()

    errors, warns = audit(args.path)
    label = RULES["label"]
    for w in warns:
        print(f"  WARN  {w}")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        print(f"[X] {args.path} [{label}]: {len(errors)} error(s), {len(warns)} warning(s)")
        sys.exit(1)
    print(f"[OK] {args.path} [{label}]: no {label}-breaking issues ({len(warns)} warning(s))")


if __name__ == "__main__":
    main()
