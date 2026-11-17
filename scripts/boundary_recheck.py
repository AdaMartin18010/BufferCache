#!/usr/bin/env python3
"""
边界自动复算（W3）——05.6.7 §2.1 M/M/1 反解的脚本化。

输入优先级：
  1. bench_suite 最近 JSON 报告（--from-bench 自动找最新 result_*.json）
  2. 直接参数 --qps --latency-ms
输出: 服务率 μ、利用率 ρ、边界余量 1-ρ、拐点预警（ρ>0.85 告警）；
      四资源最小值提示（05.7.1 瓶颈分析联动）。

用法：
    python scripts/boundary_recheck.py --qps 30000 --latency-ms 0.2
    python scripts/boundary_recheck.py --from-bench
"""

import argparse
import glob
import json
import sys
from pathlib import Path

RESULT_DIR = Path(__file__).resolve().parent.parent / "Testing" / "output" / "bench_suite"


def from_bench():
    files = sorted(glob.glob(str(RESULT_DIR / "result_*.json")))
    if not files:
        return None
    data = json.loads(Path(files[-1]).read_text(encoding="utf-8"))
    for r in data:
        get = r.get("get_rps")
        if get:
            # 延迟未存于报告——用经验 P50 0.103ms（07.5.4 基线）并标注
            return {"qps": get, "latency_ms": 0.103, "scenario": r.get("scenario", "?")}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qps", type=float)
    ap.add_argument("--latency-ms", type=float)
    ap.add_argument("--from-bench", action="store_true")
    args = ap.parse_args()

    src = "args"
    if args.from_bench:
        b = from_bench()
        if not b:
            print("SKIP: 无 bench_suite 报告（先跑 bench_suite.py --save-baseline）")
            return 2
        qps, lat_ms, src = b["qps"], b["latency_ms"], f"bench:{b['scenario']}"
    elif args.qps and args.latency_ms:
        qps, lat_ms = args.qps, args.latency_ms
    else:
        qps, lat_ms = 30000, 0.2  # 文档示例默认值（05.6.7 §2.1）
        src = "default(文档示例)"

    W = lat_ms / 1000.0
    mu = qps + 1.0 / W          # Kleinrock 反解（公式对照表 6.3）
    rho = qps / mu
    margin = 1 - rho

    print(f"输入: λ={qps:,.0f} QPS, W={lat_ms}ms（来源: {src}）")
    print(f"{'指标':<16} {'值':>12} {'说明':<24}")
    print("-" * 52)
    print(f"{'服务率 μ':<16} {mu:>11,.0f} QPS   反解 μ=λ+1/W")
    print(f"{'利用率 ρ':<16} {rho:>12.2%}   λ/μ")
    print(f"{'边界余量 1-ρ':<14} {margin:>12.2%}   {'充足(>20%)' if margin > 0.2 else '紧张(<20%)'}")

    warn = []
    if rho > 0.85:
        warn.append(f"ρ={rho:.0%} 超 0.85 水位——按 05.6.7 §3 阶梯加压实测复核外推")
    if margin < 0.15:
        warn.append("余量 <15%——触发 07.9.4 L2 扩容评估线")
    if warn:
        print("\n预警:")
        for w in warn:
            print(f"  ⚠ {w}")
    else:
        print("\n预警: 无")
    print("提示: M/M/1 为保守近似；四资源瓶颈取最小见 05.7.1")
    return 1 if margin < 0.05 else 0


if __name__ == "__main__":
    sys.exit(main())
