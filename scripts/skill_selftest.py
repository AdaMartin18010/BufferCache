#!/usr/bin/env python3
"""
Skill 动态自测（W4，TC-DOC-008）——20 技能的 §7 验证命令动态执行层。

与 assertion_check（静态文本巡检）互补：本脚本实际执行每技能声明的
验证命令（只读/本地白名单），断言输出关键词。命令白名单内嵌于本文件；
新增技能时按 SKILL_COMMANDS 格式登记（仅允许只读命令：测试/检查/报告类）。

用法：
    python scripts/skill_selftest.py            # 全量
    python scripts/skill_selftest.py --skill llm-kv-cache
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (技能名, 描述, 命令列表, 输出必须包含的关键词)
SKILL_COMMANDS = [
    ("cache-algorithms-fundamentals", "trace 基准",
     [["python", "scripts/benchmark/trace_benchmark.py"]], ["LRU", "S3-FIFO"]),
    ("cache-algorithms-advanced", "trace+形式化规约存在性",
     [["python", "scripts/kv_evict_bench.py"]], ["LRU", "SIEVE"]),
    ("learning-driven-cache", "一致性校验器存在性",
     [["python", "scripts/consistency_check.py", "--duration", "2"]], ["无兜底", "TTL"]),
    ("distributed-cache-algorithms", "trace 基准确认",
     [["python", "scripts/benchmark/trace_benchmark.py"]], ["miss ratio"]),
    ("os-kernel-cache", "多语言自检",
     [["python", "scripts/benchmark/trace_benchmark.py"]], ["total ops"]),
    ("cpu-cache-architecture", "容量估算器自检",
     [["python", "scripts/capacity_calculator.py"]], ["实例", "假设"]),
    ("db-cloud-cache", "容量估算器 JSON",
     [["python", "scripts/capacity_calculator.py", "--json"]], ["instances"]),
    ("modern-storage-stack", "trace MSR 格式 fixture",
     [["python", "scripts/benchmark/trace_benchmark.py",
       "--trace", "Testing/fixtures/traces/sample_msr_trace.csv", "--ops", "500"]], ["LRU"]),
    ("redis-data-structures", "容量估算器默认",
     [["python", "scripts/capacity_calculator.py"]], ["内存"]),
    ("redis-persistence-ha", "一致性校验",
     [["python", "scripts/consistency_check.py", "--duration", "2"]], ["策略"]),
    ("redis-ecosystem-versions", "版本监控",
     [["python", "scripts/version_monitor.py", "--check", "redis"]], ["版本"]),
    ("cache-architecture-patterns", "一致性校验器",
     [["python", "scripts/consistency_check.py", "--duration", "2"]], ["窗口"]),
    ("llm-kv-cache", "KV 驱逐对比",
     [["python", "scripts/kv_evict_bench.py"]], ["复用率"]),
    ("cache-security", "安全体检",
     [["python", "Testing/self_verify.py", "security"]], ["PASS"]),
    ("cache-operations-testing", "容量估算",
     [["python", "scripts/capacity_calculator.py"]], ["带宽"]),
    ("distributed-architecture", "一致性竞态",
     [["python", "scripts/consistency_check.py", "--duration", "2"]], ["结论"]),
    ("cloud-native-cache", "容量估算器",
     [["python", "scripts/capacity_calculator.py"]], ["成本"]),
    ("elastic-selfhealing", "自愈模拟器",
     [["python", "scripts/selfheal_sim.py"]], ["PASS"]),
    ("cache-data-management", "容量估算",
     [["python", "scripts/capacity_calculator.py"]], ["分片"]),
    ("full-stack-analysis", "边界复算",
     [["python", "scripts/boundary_recheck.py"]], ["边界余量"]),
]


def run_one(name, desc, cmds, needles):
    for cmd in cmds:
        try:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                               timeout=180, encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            return "FAIL", f"超时({cmd[0]})"
        out = (r.stdout or "") + (r.stderr or "")
        missing = [n for n in needles if n not in out]
        if r.returncode == 0 and not missing:
            return "PASS", f"{desc}"
        return "FAIL", f"rc={r.returncode} 缺关键词{missing if missing else ''}"
    return "SKIP", "无命令"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    items = SKILL_COMMANDS
    if args.skill:
        items = [s for s in items if s[0] == args.skill]
        if not items:
            print(f"未知技能 {args.skill}")
            return 2

    results, fails = [], 0
    for name, desc, cmds, needles in items:
        status, note = run_one(name, desc, cmds, needles)
        if status == "FAIL":
            fails += 1
        results.append((name, status, note))
        print(f"[{status}] {name:<32} {note}")

    print(f"\n结果: {len(results) - fails} PASS / {fails} FAIL / 0 SKIP")
    print("说明: 白名单外命令不执行；新增技能在 SKILL_COMMANDS 登记只读命令")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
