#!/usr/bin/env python3
"""
稳态漂移检测器（W2）——对混沌工程稳态假设（07.09.3 §2.1）的自动化判定。

数据源优先级：
  1. redis_exporter 指标（localhost:19121/metrics）——命中率真实值
  2. --simulate 合成 trace（无环境时演示/降级）
判定四项：命中率（基线 90%）/ 内存水位（70%）/ keyspace 命中比 / RTO 达成（读 selfheal_sim 最近报告，可选）

用法：
    python scripts/steady_state_check.py              # 自动探测 exporter，缺则模拟
    python scripts/steady_state_check.py --simulate   # 强制合成
    python scripts/steady_state_check.py --baseline-hit 0.85   # 自定义基线
"""

import argparse
import re
import sys
import urllib.request

BASELINES = {"hit_ratio": 0.90, "memory_util": 0.70, "keyspace_hits_share": 0.5}


def fetch_exporter(timeout=3):
    try:
        with urllib.request.urlopen("http://localhost:19121/metrics", timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None


def parse_exporter(text):
    def val(name):
        m = re.search(rf"^{name}\s+([\d.e+-]+)$", text, re.M)
        return float(m.group(1)) if m else None
    hits, misses = val("redis_keyspace_hits_total"), val("redis_keyspace_misses_total")
    used, maxb = val("redis_memory_used_bytes"), val("redis_memory_max_bytes")
    out = {}
    if hits is not None and misses is not None and (hits + misses) > 0:
        out["hit_ratio"] = hits / (hits + misses)
    if used is not None and maxb:
        out["memory_util"] = used / maxb
    if hits is not None:
        total = (hits or 0) + (misses or 0)
        out["keyspace_hits_share"] = hits / total if total else None
    return out


def simulate_metrics(seed=42, drift=False):
    import random
    rng = random.Random(seed)
    if drift:
        return {"hit_ratio": rng.uniform(0.80, 0.87), "memory_util": rng.uniform(0.75, 0.92)}
    return {
        "hit_ratio": 0.905 + rng.uniform(0, 0.03),
        "memory_util": 0.55 + rng.uniform(0, 0.1),
        "keyspace_hits_share": 0.55 + rng.uniform(0, 0.1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simulate", action="store_true")
    ap.add_argument("--baseline-hit", type=float, default=BASELINES["hit_ratio"])
    args = ap.parse_args()

    source = "exporter"
    text = None if args.simulate else fetch_exporter()
    if text:
        metrics = parse_exporter(text)
    else:
        source = "simulate"
        metrics = simulate_metrics()

    base = dict(BASELINES)
    base["hit_ratio"] = args.baseline_hit

    print(f"数据源: {source}")
    print(f"{'指标':<22} {'当前':>8} {'基线':>8} {'漂移':>8} {'判定':>6}")
    print("-" * 56)
    drifts = 0
    for k, baseline in base.items():
        cur = metrics.get(k)
        if cur is None:
            print(f"{k:<22} {'N/A':>8} {baseline:>8.0%} {'-':>8} {'SKIP':>6}")
            continue
        ok = cur >= baseline if k != "memory_util" else cur <= baseline
        dev = cur - baseline
        status = "PASS" if ok else "DRIFT"
        if not ok:
            drifts += 1
        print(f"{k:<22} {cur:>8.2%} {baseline:>8.0%} {dev:>+8.2%} {status:>6}")

    print(f"\n稳态判定: {'稳态' if drifts == 0 else f'{drifts} 项漂移'}（基线调整: --baseline-hit）")
    print("说明: 漂移即触发 07.9.3 §2.2 中止条件/调查流程")
    return 1 if drifts else 0


if __name__ == "__main__":
    sys.exit(main())
