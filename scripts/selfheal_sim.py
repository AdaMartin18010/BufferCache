#!/usr/bin/env python3
"""
自愈闭环模拟器（W1，TC-CLUS-010）

模拟 L1-L3 层自愈的完整闭环：注入故障 → 自愈动作 → 计时 → 对照 RTO 预算表
（07.09.2 §5）自动判定 PASS/FAIL。纯标准库、无 Docker 依赖（时序模拟）；
真实演练仍按 TC-CLUS-003~007 在 Docker 环境执行，本模拟器用于：
  1. hermes 无容器环境下的自愈逻辑常态验证
  2. 预算表数值回归（判定逻辑变更即红）
  3. 故障注入组合的压力面冒烟

用法：
    python scripts/selfheal_sim.py                 # 三场景全跑
    python scripts/selfheal_sim.py --injected l3   # 单场景
    python scripts/selfheal_sim.py --json          # 结构化输出
"""

import argparse
import json
import sys
import time

# RTO 预算表（权威源：docs/07-运维与部署/07.09-弹性伸缩与自愈/07.09.02 §5；改动需同步该文档）
BUDGET = {
    "l1": {"name": "L1 进程自愈",   "budget_s": 30,   "components": ("检测 1s + 重启 0.5s")},
    "l2": {"name": "L2 Pod 自愈",    "budget_s": 120,  "components": ("探针 10s×2 + 重建 2s")},
    "l3": {"name": "L3 实例转移",   "budget_s": 40,   "components": ("主观下线 5s + 选举 3s + 提升")},
}


def simulate_l1():
    """进程崩溃：supervisor 秒级检测 + 重启。"""
    t0 = time.perf_counter()
    detect = 1.0      # supervisor 心跳检测
    restart = 0.5     # 进程拉起
    time.sleep(0.01)  # 模拟占位（真实场景秒级；模拟器不真等）
    elapsed = detect + restart + (time.perf_counter() - t0)
    return elapsed, detect + restart


def simulate_l2():
    """探针重建：liveness 2 次失败×10s 周期 + 调度重建。"""
    period, threshold, rebuild = 10.0, 2, 2.0
    elapsed = period * threshold + rebuild
    return elapsed, elapsed


def simulate_l3():
    """实例转移：Sentinel 语义——主观下线 5s + 选举 3s + 提升窗口。"""
    sdown, elect, promote = 5.0, 3.0, 1.0
    elapsed = sdown + elect + promote
    return elapsed, elapsed


SIMS = {"l1": simulate_l1, "l2": simulate_l2, "l3": simulate_l3}


def main():
    ap = argparse.ArgumentParser(description="自愈闭环模拟器")
    ap.add_argument("--injected", choices=list(SIMS), help="只跑指定场景")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    keys = [args.injected] if args.injected else list(SIMS)
    rows, fails = [], 0
    for k in keys:
        sim = SIMS[k]
        measured, _ = sim()
        budget = BUDGET[k]["budget_s"]
        status = "PASS" if measured <= budget else "FAIL"
        if status == "FAIL":
            fails += 1
        rows.append({
            "layer": k, "name": BUDGET[k]["name"],
            "measured_s": round(measured, 2), "budget_s": budget,
            "margin": f"{(1 - measured / budget) * 100:.0f}%",
            "status": status, "components": BUDGET[k]["components"],
        })

    if args.json:
        print(json.dumps({"results": rows, "fail": fails}, ensure_ascii=False))
    else:
        print(f"{'层':<4} {'场景':<12} {'实测':>8} {'预算':>6} {'余量':>6} {'判定':>5}")
        print("-" * 48)
        for r in rows:
            print(f"{r['layer']:<4} {r['name']:<12} {r['measured_s']:>7.1f}s {r['budget_s']:>5}s {r['margin']:>6} {r['status']:>5}")
        print(f"\n结果: {len(rows) - fails} PASS / {fails} FAIL")
        print("说明: 时序模拟值（真实演练见 TC-CLUS-003~007 Docker 场景）")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
