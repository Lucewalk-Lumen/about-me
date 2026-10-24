#!/usr/bin/env python3
"""HRM 实战参谋团 · 任务生命周期账本（状态同步 + 错误恢复，零三方依赖）

解决的问题
----------
主理人现有「超时先问进度、二次无回传才可代写」是**人工兜底**，缺少：
  - 跨阶段**持久化状态**（成员 spawn→dispatch→return→verify→gate→deliver 全程可查、可断点续跑）
  - **重试预算**（可恢复错误自动重发，超限进死信）
  - **熔断**（某 specialist 连续失败达阈值即临时停用，避免无限重试死循环）
  - **死信队列**（超出重试预算的任务集中留痕，转人工 DRI）

本工具以单一 JSON 文件为账本（默认位于用户数据目录，可用 --store 覆盖），
供主理人在编排层显式调用。它不侵入成员 Agent 逻辑，只做「状态真相源 + 恢复策略」。

阶段状态机（每个 task）
----------------------
  spawned → dispatched → returned → verified → gated → delivered
                 │            │           │          │
            (fail)       (fail/验签失败) (fail)   (BLOCKED)
                 └──────────┴───────────┴──────────┘
                          → 计 attempt；未超预算则 retryable；超限 → dead_letter

强制执行
----------------------
以下约束由代码强制，违规以 exit 2 + 结构化
错误（illegal_transition / task_blocked）拒绝：
  - 阶段迁移必须落在 LEGAL_TRANSITIONS 表内，非法跳跃直接拒绝；
  - gate BLOCKED 落盘 blocked 标志，deliver 硬拒（对齐 contracts.md 硬规则）；
  - dispatch 前检查熔断（can_dispatch），open 状态拒绝派单；
  - `verified` 的 --ok 默认为 false（fail-closed），须显式 --ok true 才记通过；
  - 账本写入为原子写（临时文件 + os.replace），损坏账本被隔离为 .corrupt 并告警。

熔断（per-agent）
----------------
  consecutive_failures[agent] 达 circuit_threshold（默认 3）→ 该 agent 进入 open 状态，
  can_dispatch(agent) 返回 False，主理人应改用替代 specialist 或转人工；
  冷却 cooldown_sec（默认 600）后转 half-open，下次成功即 reset 为 closed。

CLI 示例
--------
  python3 task_ledger.py --store /tmp/ledger.json spawn T1 recruitment-pipeline --intent 招聘
  python3 task_ledger.py --store /tmp/ledger.json dispatch T1
  python3 task_ledger.py --store /tmp/ledger.json return T1 --envelope /tmp/env.json
  python3 task_ledger.py --store /tmp/ledger.json gate T1 PASSED
  python3 task_ledger.py --store /tmp/ledger.json deliver T1
  python3 task_ledger.py --store /tmp/ledger.json fail T1 --reason "验签失败" --code E041
  python3 task_ledger.py --store /tmp/ledger.json status T1
  python3 task_ledger.py --store /tmp/ledger.json summary
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Set

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from security.envelope import Envelope  # noqa: E402


DEFAULT_STORE = os.path.join(
    os.getenv("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share"),
    "hrm-advisory-corps", "task_ledger.json",
)

VALID_PHASES = ["spawned", "dispatched", "returned", "verified", "gated", "delivered", "dead_letter"]

# 合法阶段迁移表（键=当前阶段，值=允许迁移到的阶段集合）。
# 迁移必须受控：若无此表，`spawn → deliver` 可直接跳 succeed，绕过 dispatch/return/verify/gate。
# 说明：正向主链严格受限（spawned 不能直接到 gated/delivered）；
# 但「任一活跃阶段失败 → returned（可重试）」是合法回退路径，
# 否则 fail/retry 在早期阶段会被误判为非法迁移而无法计失败。
LEGAL_TRANSITIONS: Dict[str, Set[str]] = {
    "spawned":     {"dispatched", "returned", "dead_letter"},
    "dispatched":  {"returned", "verified", "dead_letter"},
    "returned":    {"verified", "gated", "returned", "dispatched", "dead_letter"},
    "verified":    {"gated", "returned", "dispatched", "dead_letter"},
    "gated":       {"delivered", "dispatched", "returned", "dead_letter"},
    "delivered":   set(),          # 终态：不可再迁移（重试须经 dead_letter 人工介入）
    "dead_letter": {"dispatched"},  # 仅人工 DRI 介入后可重新派单（retry 校验死信后放行）
}


class TransitionError(RuntimeError):
    """非法阶段迁移（结构化错误，CLI 以 exit 2 报出）。"""

    def __init__(self, task_id: str, frm: str, to: str, reason: str = "") -> None:
        self.task_id, self.frm, self.to = task_id, frm, to
        self.code = "E099"
        self.reason = reason or "非法阶段迁移：%s → %s（允许：%s）" % (
            frm, to, "、".join(sorted(LEGAL_TRANSITIONS.get(frm, set()))) or "无（终态）")
        super().__init__("task %s 阶段迁移被拒 [%s] %s" % (task_id, self.code, self.reason))

    def to_dict(self) -> Dict[str, Any]:
        return {"error": "illegal_transition", "code": self.code,
                "task_id": self.task_id, "from": self.frm, "to": self.to,
                "reason": self.reason}


class BlockedError(RuntimeError):
    """任务被合规闸 BLOCKED，禁止进入 deliver。"""

    def __init__(self, task_id: str, reason: str) -> None:
        self.task_id = task_id
        self.code = "E030"
        self.reason = reason
        super().__init__("task %s 处于 BLOCKED 状态，禁止交付 [%s] %s" % (task_id, self.code, reason))

    def to_dict(self) -> Dict[str, Any]:
        return {"error": "task_blocked", "code": self.code,
                "task_id": self.task_id, "reason": self.reason}


class Ledger:
    def __init__(self, store: str, max_retries: int = 2, circuit_threshold: int = 3,
                 cooldown_sec: int = 600) -> None:
        self.store = store
        self.max_retries = max_retries
        self.circuit_threshold = circuit_threshold
        self.cooldown_sec = cooldown_sec
        self.data: Dict[str, Any] = {"tasks": {}, "circuit": {}, "dead_letter": []}
        self._load()

    # -- 持久化 ----------------------------------------------------------------
    def _load(self) -> None:
        if os.path.exists(self.store):
            try:
                with open(self.store, encoding="utf-8") as f:
                    self.data = json.load(f)
                for k in ("tasks", "circuit", "dead_letter"):
                    self.data.setdefault(k, {} if k != "dead_letter" else [])
            except (OSError, ValueError):
                # 损坏账本不得静默吞掉（伪装成「没有任务」）：显式告警并隔离损坏文件。
                sys.stderr.write(
                    "[ERR] 账本文件不可读或 JSON 已损坏，已隔离为 %s.corrupt 并以空账本启动：%s\n"
                    % (self.store, self.store))
                try:
                    os.replace(self.store, self.store + ".corrupt")
                except OSError:
                    pass
                self.data = {"tasks": {}, "circuit": {}, "dead_letter": []}
        os.makedirs(os.path.dirname(self.store) or ".", exist_ok=True)

    def _save(self) -> None:
        """原子写：同目录临时文件 + os.replace。

        直接 open(w) 覆写在进程崩溃/断电时会留下被截断的 JSON，等于账本丢失；
        os.replace 在同一文件系统内是原子的，读者要么看到旧内容要么看到新内容。
        """
        d = os.path.dirname(self.store) or "."
        os.makedirs(d, exist_ok=True)
        tmp = self.store + ".tmp.%d" % os.getpid()
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.store)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # -- 熔断 ----------------------------------------------------------------
    def _circuit_open(self, agent: str) -> bool:
        c = self.data["circuit"].get(agent)
        if not c or c.get("state") != "open":
            return False
        if time.time() - c.get("opened_at", 0) >= self.cooldown_sec:
            c["state"] = "half-open"
            # half-open 状态必须立即持久化，否则进程一退出即丢失，
            # 冷却期实际变成无限长（只能靠手删文件解除）。
            self._save()
            return False
        return True

    def can_dispatch(self, agent: str) -> bool:
        if self._circuit_open(agent):
            return False
        return True

    def _on_agent_success(self, agent: str) -> None:
        self.data["circuit"].pop(agent, None)

    def _on_agent_failure(self, agent: str) -> None:
        c = self.data["circuit"].setdefault(agent, {"state": "closed", "consecutive": 0, "opened_at": 0})
        c["consecutive"] = c.get("consecutive", 0) + 1
        if c["consecutive"] >= self.circuit_threshold:
            c["state"] = "open"
            c["opened_at"] = time.time()

    # -- 任务操作 ------------------------------------------------------------
    def spawn(self, task_id: str, agent: str, intent: str) -> Dict[str, Any]:
        if not self.can_dispatch(agent):
            raise RuntimeError("agent %s 处于熔断 open 状态，禁止 dispatch；请改用替代 specialist 或转人工 DRI" % agent)
        self.data["tasks"][task_id] = {
            "task_id": task_id, "agent": agent, "intent": intent,
            "phase": "spawned", "attempts": 0, "history": [],
            "created_at": time.time(),
        }
        self._save()
        return self.data["tasks"][task_id]

    def _append(self, task_id: str, phase: str, note: str = "") -> None:
        t = self.data["tasks"].get(task_id)
        if not t:
            raise KeyError("未知 task_id: %s" % task_id)
        cur = t.get("phase", "spawned")
        if phase != cur and phase not in LEGAL_TRANSITIONS.get(cur, set()):
            # 状态机强制：非法迁移直接抛结构化错误，不静默改写阶段。
            raise TransitionError(task_id, cur, phase)
        t["phase"] = phase
        t["history"].append({"phase": phase, "at": time.time(), "note": note})
        self._save()

    def dispatch(self, task_id: str) -> Dict[str, Any]:
        t = self.data["tasks"].get(task_id)
        if not t:
            raise KeyError("未知 task_id: %s" % task_id)
        # 派单前必须过熔断检查，熔断打开后禁止派单。
        if self._circuit_open(t["agent"]):
            raise RuntimeError("agent %s 熔断 open 状态，禁止 dispatch；请改用替代 specialist 或转人工 DRI" % t["agent"])
        t["attempts"] += 1
        self._append(task_id, "dispatched", "attempt=%d" % t["attempts"])
        return t

    def record_return(self, task_id: str, envelope_path: Optional[str]) -> Dict[str, Any]:
        t = self.data["tasks"].get(task_id)
        if not t:
            raise KeyError("未知 task_id: %s" % task_id)
        note = "回传收到"
        if envelope_path:
            try:
                with open(envelope_path, encoding="utf-8") as f:
                    env = json.load(f)
                ok = Envelope.verify(env)
                if ok:
                    self._on_agent_success(t["agent"])
                else:
                    self._on_agent_failure(t["agent"])
                    note = "回传信封验签失败（疑似伪造/篡改/重放）"
                    t["last_error"] = {"code": "E041", "reason": note}
            except (OSError, ValueError):
                note = "回传信封不可读，按验签失败处置"
                self._on_agent_failure(t["agent"])
        self._append(task_id, "returned", note)
        return t

    def record_verified(self, task_id: str, ok: bool) -> Dict[str, Any]:
        t = self.data["tasks"].get(task_id)
        if not t:
            raise KeyError("未知 task_id: %s" % task_id)
        if ok:
            self._on_agent_success(t["agent"])
            self._append(task_id, "verified", "验签/校验通过")
        else:
            self._on_agent_failure(t["agent"])
            t.setdefault("last_error", {})["code"] = "E041"
            self._append(task_id, "returned", "校验未过，计一次失败")
        return t

    def record_gate(self, task_id: str, gate: str) -> Dict[str, Any]:
        t = self.data["tasks"].get(task_id)
        if not t:
            raise KeyError("未知 task_id: %s" % task_id)
        gate_u = str(gate).upper()
        if gate_u == "BLOCKED":
            # BLOCKED 必须落盘阻断标志（对齐 contracts.md「BLOCKED 不得进 deliver」），
            # 否则 record_deliver 无法拦截。
            t["last_error"] = {"code": "E030", "reason": "合规闸门 BLOCKED，转人工 DRI"}
            t["blocked"] = True
            t["blocked_reason"] = "合规闸门 BLOCKED（gate=BLOCKED），需人工 DRI 复核后方可重新放行"
            t["blocked_at"] = time.time()
            self._append(task_id, "gated", "BLOCKED → 转人工 DRI（不可自动放行）")
        else:
            # 非 BLOCKED 的闸门结论解除阻断标志（人工复核后可重新走流程）。
            t["blocked"] = False
            t["blocked_reason"] = ""
            self._append(task_id, "gated", "gate=%s" % gate_u)
        return t

    def record_deliver(self, task_id: str) -> Dict[str, Any]:
        t = self.data["tasks"].get(task_id)
        if not t:
            raise KeyError("未知 task_id: %s" % task_id)
        # BLOCKED 任务硬拒交付（对齐 contracts.md 硬规则）。
        if t.get("blocked"):
            raise BlockedError(task_id, t.get("blocked_reason") or "合规闸门 BLOCKED，未解除阻断")
        # 阶段机校验：必须先经过 gated 才能 deliver（spawn → deliver 直接跳会被拒）。
        self._append(task_id, "delivered", "已交付")
        return self.data["tasks"].get(task_id, {})

    def fail(self, task_id: str, reason: str, code: str = "E099") -> Dict[str, Any]:
        """记录一次失败；未超重试预算返回 retryable=True，否则进死信。"""
        t = self.data["tasks"].get(task_id)
        if not t:
            raise KeyError("未知 task_id: %s" % task_id)
        t["attempts"] += 1
        self._on_agent_failure(t["agent"])
        t["last_error"] = {"code": code, "reason": reason}
        # 重试预算：首次派单算 attempt=1；允许 max_retries 次重试，
        # 即总尝试次数上限 = 1 + max_retries。
        retryable = t["attempts"] <= self.max_retries + 1
        if retryable:
            self._append(task_id, "returned", "失败但可重试：%s" % reason)
        else:
            # 不再预先直接改写 phase（那会绕过 _append 的迁移校验），统一由 _append 落阶段。
            self.data["dead_letter"].append({
                "task_id": task_id, "agent": t["agent"], "intent": t["intent"],
                "reason": reason, "code": code, "at": time.time(),
            })
            self._append(task_id, "dead_letter", "超出重试预算，进死信：%s" % reason)
        self._save()
        return {"retryable": retryable, "task": t}

    def retry(self, task_id: str) -> Dict[str, Any]:
        """在重试预算内重新 dispatch 失败任务（验签失败自动重发）。

        前置约束：
          - 已交付任务不可重试；
          - 已在死信队列的任务需人工 DRI 介入，拒绝自动 retry；
          - 命中熔断（agent 连续失败达阈值）的任务拒绝重发，主理人应改用替代 specialist 或转人工。
        超出预算的 retry 同样进死信，避免无限重试死循环。
        """
        t = self.data["tasks"].get(task_id)
        if not t:
            raise KeyError("未知 task_id: %s" % task_id)
        if t["phase"] == "delivered":
            raise RuntimeError("task %s 已交付，不可重试" % task_id)
        if any(dl.get("task_id") == task_id for dl in self.data.get("dead_letter", [])):
            raise RuntimeError("task %s 已在死信队列，需人工 DRI 介入，不可自动 retry" % task_id)
        if self._circuit_open(t["agent"]):
            raise RuntimeError("agent %s 熔断中，retry 被拒；改用替代 specialist 或转人工 DRI" % t["agent"])
        t["attempts"] += 1
        retryable = t["attempts"] <= self.max_retries + 1
        if not retryable:
            self.data["dead_letter"].append({
                "task_id": task_id, "agent": t["agent"], "intent": t["intent"],
                "reason": "retry 超出预算", "code": "E099", "at": time.time(),
            })
            self._append(task_id, "dead_letter", "retry 超预算，进死信")
            self._save()
            return {"retryable": False, "task": t}
        t["last_error"] = {}
        self._append(task_id, "dispatched", "retry attempt=%d（自动重发）" % t["attempts"])
        self._save()
        return {"retryable": True, "task": t}

    def dashboard(self) -> Dict[str, Any]:
        """人类可读质量看板：团队级 QM-08/09 指标 + 目标值与达标状态。"""
        s = self.summary()
        targets = {
            "delivery_rate_pct": {
                "target": ">=95",
                "actual": s["delivery_rate_pct"],
                "ok": s["delivery_rate_pct"] is not None and s["delivery_rate_pct"] >= 95,
            },
            "error_recovery_rate_pct": {
                "target": ">=90",
                "actual": s["error_recovery_rate_pct"],
                "ok": s["error_recovery_rate_pct"] is not None and s["error_recovery_rate_pct"] >= 90,
            },
            "dead_letter": {
                "target": "==0",
                "actual": s["dead_letter"],
                "ok": s["dead_letter"] == 0,
            },
            "open_circuits": {
                "target": "==0",
                "actual": len(s["open_circuits"]),
                "ok": len(s["open_circuits"]) == 0,
            },
        }
        return {"summary": s, "targets": targets}

    # -- 查询 ----------------------------------------------------------------
    def status(self, task_id: str) -> Dict[str, Any]:
        return self.data["tasks"].get(task_id, {})

    def summary(self) -> Dict[str, Any]:
        tasks = self.data["tasks"].values()
        by_phase: Dict[str, int] = {p: 0 for p in VALID_PHASES}
        agent_err: Dict[str, int] = {}
        for t in tasks:
            by_phase[t.get("phase", "spawned")] = by_phase.get(t.get("phase", "spawned"), 0) + 1
            if t.get("last_error"):
                agent_err[t["agent"]] = agent_err.get(t["agent"], 0) + 1
        total = len(tasks)
        delivered = by_phase.get("delivered", 0)
        # 死信队列列表为权威来源，避免与 by_phase["dead_letter"] 重复计数
        dead = len(self.data.get("dead_letter", []))
        # 错误恢复成功率定义：出现过 last_error 的任务中，最终成功交付的比例
        # （无错误则 None，不编造数字）。口径以真实错误计数为准。
        error_tasks = [t for t in tasks if t.get("last_error")]
        if error_tasks:
            recovered = sum(1 for t in error_tasks if t.get("phase") == "delivered")
            recovery_rate = round(recovered / len(error_tasks) * 100, 1)
        else:
            recovery_rate = None
        return {
            "total_tasks": total,
            "by_phase": by_phase,
            "delivered": delivered,
            "dead_letter": dead,
            "agent_error_counts": agent_err,
            "open_circuits": {a: c for a, c in self.data["circuit"].items() if c.get("state") == "open"},
            "delivery_rate_pct": round(delivered / total * 100, 1) if total else None,
            "error_recovery_rate_pct": recovery_rate,
            "error_tasks": len(error_tasks),
        }


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(prog="task_ledger.py", description="HRM 任务生命周期账本")
    ap.add_argument("--store", default=DEFAULT_STORE, help="账本 JSON 路径（默认用户数据目录）")
    ap.add_argument("--max-retries", type=int, default=2, help="每任务最大重试次数")
    ap.add_argument("--circuit-threshold", type=int, default=3, help="agent 连续失败熔断阈值")
    sub = ap.add_subparsers(dest="cmd")

    for name in ("spawn", "dispatch", "return", "record_return", "verified", "gate", "deliver", "fail", "status", "summary", "can-dispatch", "retry", "dashboard"):
        p = sub.add_parser(name)
        if name in ("spawn",):
            p.add_argument("task_id"); p.add_argument("agent"); p.add_argument("--intent", default="")
        elif name in ("return", "record_return"):
            p.add_argument("task_id"); p.add_argument("--envelope", default=None)
        elif name in ("verified",):
            # 默认必须 fail-closed：不传 --ok 一律视为未通过，
            # 必须显式 `--ok true` 才能记为校验通过（避免「省略参数即放行」）。
            p.add_argument("task_id")
            p.add_argument("--ok", type=lambda x: str(x).lower() == "true", default=False,
                           help="校验是否通过（默认 false，即 fail-closed；须显式 --ok true）")
        elif name in ("gate",):
            p.add_argument("task_id"); p.add_argument("gate")
        elif name in ("dispatch", "deliver", "status", "retry"):
            p.add_argument("task_id")
        elif name in ("can-dispatch",):
            p.add_argument("agent")
        elif name == "fail":
            p.add_argument("task_id"); p.add_argument("--reason", default=""); p.add_argument("--code", default="E099")
        # summary / dashboard 无位置参数

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 2

    lg = Ledger(args.store, max_retries=args.max_retries, circuit_threshold=args.circuit_threshold)
    try:
        if args.cmd == "spawn":
            out = lg.spawn(args.task_id, args.agent, args.intent)
        elif args.cmd == "dispatch":
            out = lg.dispatch(args.task_id)
        elif args.cmd in ("return", "record_return"):
            out = lg.record_return(args.task_id, args.envelope)
        elif args.cmd == "verified":
            out = lg.record_verified(args.task_id, args.ok)
        elif args.cmd == "gate":
            out = lg.record_gate(args.task_id, args.gate)
        elif args.cmd == "deliver":
            out = lg.record_deliver(args.task_id)
        elif args.cmd == "can-dispatch":
            out = {"agent": args.agent, "dispatchable": lg.can_dispatch(args.agent)}
        elif args.cmd == "fail":
            out = lg.fail(args.task_id, args.reason, args.code)
        elif args.cmd == "retry":
            out = lg.retry(args.task_id)
        elif args.cmd == "status":
            out = lg.status(args.task_id)
        elif args.cmd == "summary":
            out = lg.summary()
        elif args.cmd == "dashboard":
            out = lg.dashboard()
        else:
            ap.print_help()
            return 2
    except (TransitionError, BlockedError) as e:
        # 结构化错误输出（stdout JSON + stderr 摘要），退出码 2 保持不变。
        print(json.dumps(e.to_dict(), ensure_ascii=False, indent=2))
        sys.stderr.write("[ERR] %s\n" % e)
        return 2
    except (KeyError, RuntimeError) as e:
        sys.stderr.write("[ERR] %s\n" % e)
        return 2

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
